// SPDX-License-Identifier: MIT
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include "app_video.h"
#include "frame_pixels.h"
#include "p4_local.h"
#include "quirc.h"
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
static SemaphoreHandle_t owned;
static TaskHandle_t worker_handle;
static atomic_bool scan_enabled;
static const char *TAG="p4_optical";

static void camera_frame(uint8_t *rgb,uint8_t index,uint32_t width,uint32_t height,size_t length,void *context) {
    (void)index;(void)context;
    static int64_t last;
    int64_t now=p4_monotonic_ms();
    if(!atomic_load(&scan_enabled) || now-last<150 || xSemaphoreTake(owned,0)!=pdTRUE)return;
    atomic_store(&scan_enabled,false);last=now;
    int w,h;uint8_t *gray=quirc_begin(decoder,&w,&h);
    if(w!=800 || h!=800 || !p4_frame_gray180(rgb,length,width,height,gray,640000)) {
        atomic_store(&scan_enabled,true);xSemaphoreGive(owned);return;
    }
    xTaskNotifyGive(worker_handle);
}
static void resume_scan(void) {atomic_store(&scan_enabled,true);xSemaphoreGive(owned);}
static void worker(void *unused) {
    (void)unused;uint8_t local=0;
    if(!esp_ptr_internal(&local))p4_fatal();
    p4_boot_check();
    if(p4_engine_init()!=0)p4_fatal();
    ESP_LOGI(TAG,"PUBLIC TEST11x32 only; engine=%u internal stack=%u bytes decoder=%u bytes",
        (unsigned)p4_engine_bytes(),WORKER_STACK_BYTES,(unsigned)p4_decoder_retained());
    p4_ui_status("SCAN ONE nsealr1 QR\nPublic test identity only\nTouch never approves");
    atomic_store(&scan_enabled,true);
    for(;;) {
        ulTaskNotifyTake(pdTRUE,portMAX_DELAY);
        int64_t start=p4_monotonic_ms();quirc_end(decoder);
        int count=quirc_count(decoder);
        int64_t detection=p4_monotonic_ms()-start;
        if(count!=1) {
            if(count>1)ESP_LOGW(TAG,"Ambiguous frame rejected;count=%d detect_ms=%lld",count,(long long)detection);
            resume_scan();continue;
        }
        quirc_extract(decoder,0,code);
        if(code->size>117 || code->size<21) {resume_scan();continue;}
        quirc_decode_error_t result=quirc_decode(code,data);
        if(result!=QUIRC_SUCCESS || data->payload_len<8 || data->payload_len>947 ||
            memcmp(data->payload,"nsealr1:",8)!=0) {resume_scan();continue;}
        ESP_LOGI(TAG,"One bounded operation QR; detect_decode_ms=%lld; payload content omitted",
            (long long)(p4_monotonic_ms()-start));
        int n=p4_engine_run(data->payload,(size_t)data->payload_len,response,1536);
        if(n>0 && p4_show_response(response,(size_t)n,p4_engine_response_deadline_ms())==0) {
            ESP_LOGI(TAG,"PUBLIC response ready; stack_remaining=%u; free_internal=%u; no payload logging",
                (unsigned)uxTaskGetStackHighWaterMark(NULL),(unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
            p4_wait_new_action();
        } else {
            char message[110];snprintf(message,sizeof(message),"REFUSED / NO RESPONSE\nReason %d\nTap BOOT to scan again",n);
            p4_ui_status(message);ESP_LOGW(TAG,"Operation refused;code=%d; stack_remaining=%u",n,(unsigned)uxTaskGetStackHighWaterMark(NULL));
            p4_wait_new_action();
        }
        memset(response,0,1536);memset(data,0,sizeof(*data));
        p4_ui_status("SCAN ONE NEW REQUEST\nPublic test identity only\nTouch never approves");resume_scan();
    }
}
void app_main(void) {
    ESP_LOGW(TAG,"PUBLIC TEST FIXTURE BINARY: deterministic identity/auxiliary; no production custody/entropy claim");
    lv_display_t *display=bsp_display_start();
    if(!display || lv_display_get_horizontal_resolution(display)!=320 || lv_display_get_vertical_resolution(display)!=480)p4_fatal();
    ESP_ERROR_CHECK(bsp_display_backlight_on());p4_ui_init(display);
    decoder=quirc_new();
    if(!decoder || quirc_resize(decoder,800,800)!=0)p4_fatal();
    code=heap_caps_calloc(1,sizeof(*code),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    data=heap_caps_calloc(1,sizeof(*data),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    response=heap_caps_calloc(1,1536,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    owned=xSemaphoreCreateBinary();
    if(!code || !data || !response || !owned)p4_fatal();
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
