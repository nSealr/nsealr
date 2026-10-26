// SPDX-License-Identifier: MIT
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include "app_video.h"
#include "frame_pixels.h"
#include "p4_local.h"
#include "quirc.h"
#include "decode_one.h"
#include "worker_watchdog.h"
#include "scan_admission.h"
#include "c6_guard.h"
#include "p4_entropy.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_private/esp_cache_private.h"
#include "esp_log.h"
#include "esp_memory_utils.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "bsp/display.h"

extern int p4_engine_init(void);
extern int p4_engine_run(const uint8_t *,size_t,uint8_t *,size_t);
extern size_t p4_engine_bytes(void);
extern uint64_t p4_engine_response_deadline_ms(void);
extern size_t p4_decoder_retained(void);
#define WORKER_STACK_BYTES (96*1024)
static struct quirc *decoder;
static struct quirc_code *code;
static struct quirc_data *data;
static uint8_t *response;
static SemaphoreHandle_t owned, copied;
static const uint8_t *borrowed_rgb;
static size_t borrowed_length;
static uint32_t borrowed_width, borrowed_height;
static TaskHandle_t worker_handle;
static atomic_bool scan_enabled;
static const char *TAG="p4_optical";

static void camera_frame(uint8_t *rgb,uint8_t index,uint32_t width,uint32_t height,size_t length,void *context) {
    (void)index;(void)context;
    static int64_t last;
    int64_t now=p4_monotonic_ms();
    if(!atomic_load(&scan_enabled) || now-last<150 || xSemaphoreTake(owned,0)!=pdTRUE)return;
    atomic_store(&scan_enabled,false);last=now;
    // Camera retains its buffer until the worker completes the bounded copy.
    // Only worker calls quirc, preview or Rust. No second frame may own it.
    borrowed_rgb=rgb;borrowed_length=length;borrowed_width=width;borrowed_height=height;
    xTaskNotifyGive(worker_handle);
    if(xSemaphoreTake(copied,portMAX_DELAY)!=pdTRUE)p4_fatal();
}
static void resume_scan(void) {p4_scan_resume(owned,&scan_enabled);}

static void worker(void *unused) {
    (void)unused;uint8_t local=0;
    if(!esp_ptr_internal(&local))p4_fatal();
    p4_worker_watchdog_start();
    p4_worker_fault_probe();
#if P4_WDT_PROBE_MODE == 0
    if(!p4_c6_guard_begin())p4_fatal();
    if(esp_reset_reason()!=ESP_RST_POWERON) {
        p4_ui_status("PUBLIC NORMAL UNAVAILABLE\nPrevious reset; no session\nNo engine/key admitted");
        for(;;)p4_worker_idle(250);
    }
#endif
    if(!p4_entropy_bind_worker())p4_fatal();
    p4_boot_check();
    if(!p4_c6_guard_check("engine-init-before"))p4_fatal();
    if(p4_engine_init()!=0 || !p4_c6_guard_check("engine-init-after"))p4_fatal();
    ESP_LOGI(TAG,"PUBLIC TEST11x32 only; engine=%u internal stack=%u bytes decoder=%u bytes",
        (unsigned)p4_engine_bytes(),WORKER_STACK_BYTES,(unsigned)p4_decoder_retained());
    p4_ui_status("SCAN ONE nsealr1 QR\nPublic test identity only\nTouch never approves");
    atomic_store(&scan_enabled,true);
    for(;;) {
        if(!ulTaskNotifyTake(pdTRUE,pdMS_TO_TICKS(250))) {
            // A callback holding a raw frame is outstanding work: do not feed.
            p4_scan_idle_feed(owned);
            continue;
        }
        int64_t start=p4_monotonic_ms();int w,h;
        uint8_t *gray=quirc_begin(decoder,&w,&h);
        bool valid=w==800 && h==800 && p4_frame_gray_raw(borrowed_rgb,borrowed_length,
            borrowed_width,borrowed_height,gray,640000);
        borrowed_rgb=NULL;xSemaphoreGive(copied);
        if(!valid) {resume_scan();continue;}
        if(p4_scan_preview(gray,640000)!=0)p4_fatal();
        quirc_end(decoder);
        int count=quirc_count(decoder);
        int64_t detection=p4_monotonic_ms()-start;
        if(count!=1) {
            if(count>1)ESP_LOGW(TAG,"Ambiguous frame rejected;count=%d detect_ms=%lld",count,(long long)detection);
            resume_scan();continue;
        }
        quirc_extract(decoder,0,code);
        unsigned attempts;
        if(p4_decode_one(code,data,&attempts)!=0) {resume_scan();continue;}
        ESP_LOGI(TAG,"One bounded operation QR; gray_preview_detect_decode_ms=%lld; attempts=%u; payload omitted",
            (long long)(p4_monotonic_ms()-start),attempts);
        if(!p4_c6_guard_check("operation-before"))p4_fatal();
        int n=p4_engine_run(data->payload,(size_t)data->payload_len,response,1536);
        if(!p4_c6_guard_check("operation-after")) {
            memset(response,0,1536);memset(data,0,sizeof(*data));p4_fatal();
        }
        p4_entropy_log_report();
        bool shown=false;
        if(n>0 && p4_show_response(response,(size_t)n,1536,p4_engine_response_deadline_ms())==0) {
            shown=true;
            ESP_LOGI(TAG,"PUBLIC response ready; stack_remaining=%u; free_internal=%u; no payload logging",
                (unsigned)uxTaskGetStackHighWaterMark(NULL),(unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
            p4_wait_response_clear(response,1536,p4_engine_response_deadline_ms());
        } else {
            char message[110];snprintf(message,sizeof(message),p4_entropy_used()?
                "PUBLIC AUX STOPPED\nNo response; reason %d\nRestart required":
                "REFUSED / NO RESPONSE\nReason %d\nTap BOOT to scan again",n);
            p4_ui_status(message);ESP_LOGW(TAG,"Operation refused;code=%d; stack_remaining=%u",n,(unsigned)uxTaskGetStackHighWaterMark(NULL));
            if(!p4_entropy_used())p4_wait_new_action();
        }
        memset(response,0,1536);memset(data,0,sizeof(*data));
        if(p4_entropy_used()){
            if(shown)p4_ui_status("PUBLIC TEST COMPLETE\nRestart for another test");
            for(;;)p4_worker_idle(250);
        }
        p4_ui_status("SCAN ONE NEW REQUEST\nPublic test identity only\nTouch never approves");resume_scan();
    }
}
void app_main(void) {
    ESP_LOGW(TAG,"PUBLIC probe_mode=%d reset_reason=%d",P4_WDT_PROBE_MODE,(int)esp_reset_reason());
    ESP_LOGW(TAG,"PUBLIC TEST FIXTURE BINARY: published11 identity; fallible auxiliary fault=%d; no production custody/entropy claim",p4_entropy_fault_mode());
    lv_display_t *display=p4_display_start();
    if(!display || lv_display_get_horizontal_resolution(display)!=320 || lv_display_get_vertical_resolution(display)!=480)p4_fatal();
    decoder=quirc_new();
    if(!decoder || quirc_resize(decoder,800,800)!=0)p4_fatal();
    code=heap_caps_calloc(1,sizeof(*code),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    data=heap_caps_calloc(1,sizeof(*data),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    response=heap_caps_calloc(1,1536,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    owned=xSemaphoreCreateBinary();copied=xSemaphoreCreateBinary();
    if(!code || !data || !response || !owned || !copied)p4_fatal();
    xSemaphoreGive(owned);
    StackType_t *stack=heap_caps_calloc(1,WORKER_STACK_BYTES,MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
    StaticTask_t *task=heap_caps_calloc(1,sizeof(*task),MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
    if(!stack || !task || !p4_memory_internal((uint8_t *)stack,WORKER_STACK_BYTES))p4_fatal();
    worker_handle=xTaskCreateStaticPinnedToCore(worker,"p4_rust_optical",WORKER_STACK_BYTES,NULL,4,stack,task,1);
    if(!worker_handle)p4_fatal();
    ESP_ERROR_CHECK(app_video_main(bsp_i2c_get_handle()));
    int fd=app_video_open(ESP_VIDEO_MIPI_CSI_DEVICE_NAME,APP_VIDEO_FMT);if(fd<0 || app_video_get_buf_size()!=1280000)p4_fatal();
    size_t alignment=64;ESP_ERROR_CHECK(esp_cache_get_alignment(MALLOC_CAP_SPIRAM,&alignment));
    void *frames[2];for(unsigned i=0;i<2;i++) {
        frames[i]=heap_caps_aligned_calloc(alignment,1,1280000,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);if(!frames[i])p4_fatal();
    }
    ESP_ERROR_CHECK(app_video_set_bufs(fd,2,(const void **)frames));
    ESP_ERROR_CHECK(app_video_register_frame_operation_cb(camera_frame));
    ESP_ERROR_CHECK(app_video_stream_task_start(fd,0,NULL));
}
