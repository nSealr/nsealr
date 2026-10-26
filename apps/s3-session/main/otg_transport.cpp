// SPDX-License-Identifier: MIT
// Public-only OTG observation. No ROM helper, console or secret memory endpoint.
#include "otg_transport.h"
#include "public_marker.h"
#include <cstdio>
#include <cstring>
#include "sdkconfig.h"
#include "esp_attr.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_memory_utils.h"
#include "esp_timer.h"
#include "soc/rtc_cntl_struct.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "tinyusb.h"
#include "tinyusb_cdc_acm.h"
#include "tusb.h"
#include "device/dcd.h"
#include "device/usbd_pvt.h"

#if CONFIG_ESP_MAIN_TASK_STACK_SIZE != 98304 || !CONFIG_ESP_CONSOLE_NONE
#error "Public OTG requires the reviewed internal main stack and no console"
#endif
static_assert(CFG_TUD_CDC==1 && CFG_TUD_MSC==0 && CFG_TUD_HID==0 && CFG_TUD_MIDI==0 &&
    CFG_TUD_VENDOR==0 && CFG_TUD_NCM==0 && CFG_TUD_ECM_RNDIS==0 && CFG_TUD_DFU==0 &&
    CFG_TUD_DFU_RUNTIME==0 && CFG_TUD_MTP==0 && CFG_TUD_BTH==0,"CDC-only closure");
static_assert(CFG_TUSB_DEBUG==0 && CFG_TUD_CDC_RX_BUFSIZE==2048 &&
    CFG_TUD_CDC_TX_BUFSIZE==1024 && CFG_TUD_CDC_EP_BUFSIZE==64,"bounded public CDC");

static portMUX_TYPE lock=portMUX_INITIALIZER_UNLOCKED;
static OtgState state;
static TaskHandle_t usb_task;
static bool usb_internal=false,main_internal=false;
static OtgBoot boot;
static __NOINIT_ATTR volatile PublicMarker internal_marker;
static RTC_NOINIT_ATTR volatile PublicMarker rtc_marker;
static volatile PublicMarker bss_marker;
static uint32_t reported[unsigned(OtgEvent::Count)]={};
static bool have_report=false,reported_poison=false;
static int64_t next_report_us=0;

static uint32_t observe(OtgEvent event,bool a=false,bool b=false,uint32_t baud=0) {
    portENTER_CRITICAL_SAFE(&lock);
    state.event(event,a,b,baud);
    const uint32_t ticket=state.counts[unsigned(OtgEvent::BusReset)];
    portEXIT_CRITICAL_SAFE(&lock);
    return ticket;
}
static void task_observed() {
    int stack_sample=0;
    portENTER_CRITICAL_SAFE(&lock);
    usb_task=xTaskGetCurrentTaskHandle();
    usb_internal=esp_ptr_internal(&stack_sample);
    portEXIT_CRITICAL_SAFE(&lock);
}
// The pin invokes this only AFTER a successful TinyUSB queue send. It cannot
// observe a dropped event or prove that a physical disconnect was detected.
static void reset_processed(void *param) {
    portENTER_CRITICAL_SAFE(&lock);
    state.reset_processed(uint32_t(reinterpret_cast<uintptr_t>(param)));
    portEXIT_CRITICAL_SAFE(&lock);
}
extern "C" void tud_event_hook_cb(uint8_t,uint32_t event,bool in_isr) {
    if(event!=DCD_EVENT_BUS_RESET)return;
    const uint32_t ticket=observe(OtgEvent::BusReset);
    // The exact DWC2 port emits this from its USB ISR. Its FIFO barrier follows
    // usbd_reset. Never use the task variant: it waits forever on a full queue.
    // A rejected ISR enqueue (or an unexpected task-origin reset) leaves pending
    // sticky and authorization closed. No vendor mutation or extra queue/task.
    if(in_isr)usbd_defer_func(reset_processed,reinterpret_cast<void*>(uintptr_t(ticket)),true);
}
static void device_event(tinyusb_event_t *event,void *) {
    if(!event)return;
    task_observed();
    switch(event->id){
    case TINYUSB_EVENT_ATTACHED: observe(OtgEvent::Attached);break;
    case TINYUSB_EVENT_DETACHED: observe(OtgEvent::Detached);break;
    case TINYUSB_EVENT_SUSPENDED: observe(OtgEvent::Suspend);break;
    case TINYUSB_EVENT_RESUMED: observe(OtgEvent::Resume);break;
    default: observe(OtgEvent::Count);break;
    }
}
static void cdc_event(int,cdcacm_event_t *event) {
    if(!event)return;
    task_observed();
    if(event->type==CDC_EVENT_LINE_STATE_CHANGED)
        observe(OtgEvent::LineState,event->line_state_changed_data.dtr,event->line_state_changed_data.rts);
    else if(event->type==CDC_EVENT_LINE_CODING_CHANGED){
        const auto *coding=event->line_coding_changed_data.p_line_coding;
        if(coding)observe(OtgEvent::LineCoding,false,false,coding->bit_rate);
    }
}
OtgState otg_snapshot() {
    portENTER_CRITICAL_SAFE(&lock);const auto copy=state;portEXIT_CRITICAL_SAFE(&lock);return copy;
}
bool otg_current(uint32_t grant) {return otg_snapshot().current(grant);}
static uint32_t mux_value(){return (RTCCNTL.usb_conf.sw_hw_usb_phy_sel<<1)|RTCCNTL.usb_conf.sw_usb_phy_sel;}
static PublicMarker read_marker(const volatile PublicMarker &from) {
    PublicMarker result={};for(unsigned i=0;i<16;++i)result.words[i]=from.words[i];return result;
}
static void write_marker(volatile PublicMarker &to,const PublicMarker &from) {
    for(unsigned i=0;i<16;++i)to.words[i]=from.words[i];
}
// Espressif VID and TinyUSB CDC-only default PID, for this public experiment.
// iSerialNumber=0 and explicit strings avoid the component's eFuse-MAC fallback.
static const tusb_desc_device_t device_descriptor={
    .bLength=sizeof(tusb_desc_device_t),.bDescriptorType=TUSB_DESC_DEVICE,.bcdUSB=0x0200,
    .bDeviceClass=TUSB_CLASS_MISC,.bDeviceSubClass=MISC_SUBCLASS_COMMON,.bDeviceProtocol=MISC_PROTOCOL_IAD,
    .bMaxPacketSize0=64,.idVendor=0x303a,.idProduct=0x4001,.bcdDevice=0x0100,
    .iManufacturer=1,.iProduct=2,.iSerialNumber=0,.bNumConfigurations=1
};
static const uint8_t configuration_descriptor[]={
    TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,100),
    TUD_CDC_DESCRIPTOR(0,3,0x81,8,0x02,0x82,64)
};
static const char language[]={0x09,0x04};
static const char *strings[]={language,"nsealr public experiment","S3 public OTG CDC","Public requests"};
OtgBoot otg_start() {
    int stack_sample=0;main_internal=esp_ptr_internal(&stack_sample);
    const auto previous_i=read_marker(internal_marker),previous_r=read_marker(rtc_marker),previous_b=read_marker(bss_marker);
    boot={1,uint32_t(esp_reset_reason()),mux_value(),0,marker_valid(previous_i),marker_valid(previous_r),marker_valid(previous_b)};
    if(boot.previous_rtc&&previous_r.words[2]<UINT32_MAX)boot.generation=previous_r.words[2]+1;
    const auto marker=public_marker(boot.generation);
    write_marker(internal_marker,marker);write_marker(rtc_marker,marker);write_marker(bss_marker,marker);
    // These allocations/callback registrations need no installed hardware in this
    // exact pin (cdc.c/tinyusb_cdc_acm.c). Register before the device can enumerate.
    tinyusb_config_cdcacm_t acm={};acm.cdc_port=TINYUSB_CDC_ACM_0;
    acm.callback_line_state_changed=cdc_event;acm.callback_line_coding_changed=cdc_event;
    ESP_ERROR_CHECK(tinyusb_cdcacm_init(&acm));
    tinyusb_config_t config={};config.port=TINYUSB_PORT_FULL_SPEED_0;
    // No verified VBUS GPIO: do not invent self-powered disconnect detection.
    config.task.size=4096;config.task.priority=5;config.task.xCoreID=1;
    config.descriptor.device=&device_descriptor;config.descriptor.string=strings;
    config.descriptor.string_count=4;config.descriptor.full_speed_config=configuration_descriptor;
    config.event_cb=device_event;
    ESP_ERROR_CHECK(tinyusb_driver_install(&config));
    boot.mux_after=mux_value();
    if(!main_internal||boot.mux_after!=3)esp_system_abort("public OTG internal stack/mux mismatch");
    return boot;
}
int otg_read(uint8_t *bytes,size_t capacity) {
    size_t got=0;
    if(!bytes||capacity>2048||tinyusb_cdcacm_read(TINYUSB_CDC_ACM_0,bytes,capacity,&got)!=ESP_OK||got>capacity)return -1;
    return int(got);
}
int otg_queue_response(const uint8_t *bytes,size_t length,uint32_t grant) {
    if(!bytes||!length||length>1024||!otg_current(grant)||tud_cdc_n_write_available(0)<length)return 0;
    const size_t queued=tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0,bytes,length);
    (void)tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0,0);
    // A concurrent revocation may follow a prefix/full frame already queued.
    // Mark the transport uncertain, never retry or claim those bytes recalled.
    return otg_current(grant)?int(queued):-1;
}
void otg_line(const char *line) {
    const size_t n=std::strlen(line);
    const auto snapshot=otg_snapshot();
    // Fixed public diagnostics may explain a poisoned authorization state.
    if(n>384||!snapshot.configured||snapshot.suspended||!snapshot.dtr||tud_cdc_n_write_available(0)<n)return;
    (void)tinyusb_cdcacm_write_queue(TINYUSB_CDC_ACM_0,reinterpret_cast<const uint8_t*>(line),n);
    (void)tinyusb_cdcacm_write_flush(TINYUSB_CDC_ACM_0,0);
}
void otg_report_idle() {
    const int64_t now=esp_timer_get_time();const auto snapshot=otg_snapshot();
    if(now<next_report_us||!snapshot.configured||snapshot.suspended||!snapshot.dtr||tud_cdc_n_write_available(0)<768)return;
    if(have_report&&reported_poison==snapshot.poisoned&&std::memcmp(reported,snapshot.counts,sizeof(reported))==0)return;
    TaskHandle_t task;bool internal;
    portENTER_CRITICAL_SAFE(&lock);task=usb_task;internal=usb_internal;portEXIT_CRITICAL_SAFE(&lock);
    const auto usb_free=task?uxTaskGetStackHighWaterMark(task):0;
    char line[384];
    std::snprintf(line,sizeof(line),"s3-otg-marker-v1 boot=%lu reset=%lu mux=%lu/%lu previous=%u%u%u current=%u%u%u main_internal=%u usb_internal=%u main_free=%lu usb_free=%lu heap_min=%u heap_largest=%u\n",
        (unsigned long)boot.generation,(unsigned long)boot.reset_reason,(unsigned long)boot.mux_before,(unsigned long)mux_value(),
        boot.previous_internal,boot.previous_rtc,boot.previous_bss,marker_valid(read_marker(internal_marker)),marker_valid(read_marker(rtc_marker)),marker_valid(read_marker(bss_marker)),
        main_internal,internal,(unsigned long)uxTaskGetStackHighWaterMark(nullptr),(unsigned long)usb_free,
        unsigned(heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)),unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT)));
    otg_line(line);
    std::snprintf(line,sizeof(line),"s3-otg-events-v1 epoch=%lu cfg=%u suspend=%u dtr=%u rts=%u poison=%u pending=%u baud=%lu counts=%lu,%lu,%lu,%lu,%lu,%lu,%lu us=%lld\n",
        (unsigned long)snapshot.epoch,snapshot.configured,snapshot.suspended,snapshot.dtr,snapshot.rts,snapshot.poisoned,snapshot.reset_pending,(unsigned long)snapshot.baud,
        (unsigned long)snapshot.counts[0],(unsigned long)snapshot.counts[1],(unsigned long)snapshot.counts[2],(unsigned long)snapshot.counts[3],
        (unsigned long)snapshot.counts[4],(unsigned long)snapshot.counts[5],(unsigned long)snapshot.counts[6],(long long)now);
    otg_line(line);std::memcpy(reported,snapshot.counts,sizeof(reported));have_report=true;reported_poison=snapshot.poisoned;next_report_us=now+1000000;
}
