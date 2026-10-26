// SPDX-License-Identifier: MIT
#include "p4_local.h"
#include "local_input.h"
#include "frame_pixels.h"
#include "worker_watchdog.h"
#include "display_ack.h"
#include "bsp/esp-bsp.h"
#include "bsp/display.h"
#include "esp_lv_adapter_input.h"
#include "bsp/touch.h"
#include "esp_attr.h"
#include "freertos/semphr.h"
#include "esp_heap_caps.h"
#include "src/misc/cache/instance/lv_image_cache.h"
#include <stdio.h>
#include <string.h>
#include <stdatomic.h>
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "esp_memory_utils.h"
#include "esp_system.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lv_adapter.h"
#include "esp_lv_adapter_display.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define BOOT_GPIO GPIO_NUM_35
static lv_display_t *screen;
static uint16_t *preview_pixels;
static lv_image_dsc_t preview;
static atomic_uint action, generation, touch_generation;
static atomic_bool navigation_ready;
static const char *TAG="p4_local";
static SemaphoreHandle_t color_done;
static portMUX_TYPE ack_lock=portMUX_INITIALIZER_UNLOCKED;
static p4_display_ack_t ack;
static uint32_t frame_generation;
static void poison_draw(void) {
    portENTER_CRITICAL(&ack_lock);p4_display_ack_fail(&ack);portEXIT_CRITICAL(&ack_lock);
}
bool p4_display_failed(void) {
    portENTER_CRITICAL(&ack_lock);bool failed=ack.failed;portEXIT_CRITICAL(&ack_lock);return failed;
}


int64_t IRAM_ATTR p4_monotonic_ms(void) {return esp_timer_get_time()/1000;}
// This is an explicitly public deterministic test source, not qualified entropy.
ptrdiff_t p4_fixture_auxiliary(uint8_t *destination,size_t capacity) {
    if(!destination || capacity!=32)return -1;
    memset(destination,0x22,32);return 32;
}

int p4_memory_internal(const uint8_t *p,size_t n) {
    return p && n && esp_ptr_internal(p) && esp_ptr_internal(p+n-1);
}
_Noreturn void p4_fatal(void) {
    ESP_LOGE(TAG,"PUBLIC TEST application stopped; no response admission");
    esp_restart(); for (;;) vTaskDelay(1);
}
bool p4_boot_pressed(void) {return gpio_get_level(BOOT_GPIO)==0;}
// This is the only physical IO callback, installed before adapter start.
// Forward the real last-color completion to the adapter, preserving flush_ready.
static bool IRAM_ATTR color_complete(esp_lcd_panel_io_handle_t io,esp_lcd_panel_io_event_data_t *event,void *context) {
    (void)io;(void)event;(void)context;
    bool adapter_yield=esp_lv_adapter_display_notify_color_trans_done_from_isr(screen);
    BaseType_t wake=pdFALSE;
    portENTER_CRITICAL_ISR(&ack_lock);
    // IDF does not supply a transaction ID. Startup has zero inflight colors,
    // and track_draw cannot submit another until this one is collected.
    bool valid=p4_display_ack_complete(&ack,ack.generation,ack.pending_serial,(uint64_t)p4_monotonic_ms());
    portEXIT_CRITICAL_ISR(&ack_lock);
    if(valid)xSemaphoreGiveFromISR(color_done,&wake);
    return adapter_yield || wake==pdTRUE;
}
static esp_err_t track_draw(lv_display_t *display,esp_lcd_panel_handle_t panel,
 int x0,int y0,int x1,int y1,const void *pixels,void *context) {
    (void)context;
    if(display!=screen || p4_display_failed())return ESP_ERR_INVALID_STATE;
    // A residual signal is a protocol error, never evidence for the new stripe.
    if(xSemaphoreTake(color_done,0)==pdTRUE) {poison_draw();return ESP_ERR_INVALID_STATE;}
    uint32_t serial=0;uint64_t end;
    portENTER_CRITICAL(&ack_lock);
    bool submitted=p4_display_ack_submit(&ack,frame_generation,(uint64_t)p4_monotonic_ms(),&serial);
    end=ack.deadline;
    portEXIT_CRITICAL(&ack_lock);
    if(!submitted) {poison_draw();return ESP_ERR_INVALID_STATE;}
    esp_err_t e=esp_lcd_panel_draw_bitmap(panel,x0,y0,x1,y1,pixels);
    if(e!=ESP_OK) {poison_draw();return e;}
    uint64_t now=(uint64_t)p4_monotonic_ms();
    if(now>=end || xSemaphoreTake(color_done,pdMS_TO_TICKS((uint32_t)(end-now)))!=pdTRUE) {
        poison_draw();return ESP_ERR_TIMEOUT;
    }
    portENTER_CRITICAL(&ack_lock);
    bool collected=p4_display_ack_collected(&ack,frame_generation,serial,(uint64_t)p4_monotonic_ms());
    portEXIT_CRITICAL(&ack_lock);
    if(!collected) {poison_draw();return ESP_ERR_TIMEOUT;}
    return ESP_OK;
}
static void nav_event(lv_event_t *event) {
    if(!atomic_load(&navigation_ready)) return;
    unsigned current=atomic_load(&generation);
    if(lv_event_get_code(event)==LV_EVENT_PRESSED) atomic_store(&touch_generation,current);
    if(lv_event_get_code(event)==LV_EVENT_RELEASED && atomic_load(&touch_generation)==current) {
        atomic_store(&navigation_ready,false);
        atomic_store(&action,(unsigned)(uintptr_t)lv_event_get_user_data(event));
    }
}
static bool touch_released(void) {
    bool released=true;
    if(esp_lv_adapter_lock(100)!=ESP_OK) return false;
    for(lv_indev_t *d=lv_indev_get_next(NULL);d;d=lv_indev_get_next(d)) {
        if(lv_indev_get_type(d)==LV_INDEV_TYPE_POINTER && lv_indev_get_state(d)!=LV_INDEV_STATE_RELEASED) released=false;
    }
    esp_lv_adapter_unlock(); return released;
}
static lv_obj_t *text_at(lv_obj_t *parent,const char *value,int x,int y,int width) {
    lv_obj_t *o=lv_label_create(parent);if(!o) p4_fatal();
    lv_obj_set_style_text_font(o,&lv_font_unscii_16,0);
    lv_obj_set_style_text_color(o,lv_color_black(),0);
    lv_obj_set_style_bg_color(o,lv_color_white(),0);lv_obj_set_style_bg_opa(o,LV_OPA_COVER,0);
    lv_obj_set_width(o,width);lv_obj_set_pos(o,x,y);
    lv_label_set_long_mode(o,LV_LABEL_LONG_CLIP);lv_label_set_text(o,value);return o;
}
// Worker owns screen updates; action capture stays disabled through DMA commit.
static lv_obj_t *start_screen(void) {
    atomic_store(&navigation_ready,false);atomic_store(&action,0);
    unsigned next=atomic_fetch_add(&generation,1)+1;atomic_store(&touch_generation,0);
    if(!next || p4_display_failed())p4_fatal();
    if(esp_lv_adapter_lock(1000)!=ESP_OK) p4_fatal();
    frame_generation=next;
    portENTER_CRITICAL(&ack_lock);
    bool started=p4_display_ack_begin(&ack,next,(uint64_t)p4_monotonic_ms());
    portEXIT_CRITICAL(&ack_lock);
    if(!started || esp_lv_adapter_set_dummy_draw(screen,false)!=ESP_OK)p4_fatal();
    lv_obj_t *root=lv_screen_active();lv_obj_clean(root);
    lv_obj_set_style_bg_color(root,lv_color_white(),0);
    text_at(root,"PUBLIC TEST IDENTITY",16,8,288);
    text_at(root,"NOT A SECURE VAULT",16,30,288);
    return root;
}
static int commit_screen(void) {
    esp_lv_adapter_unlock();
    if(esp_lv_adapter_refresh_now(screen)!=ESP_OK) {poison_draw();return -1;}
    // Dummy mode prevents future draws; it is NOT the physical ACK boundary.
    if(esp_lv_adapter_set_dummy_draw(screen,true)!=ESP_OK) {poison_draw();return -1;}
    portENTER_CRITICAL(&ack_lock);
    bool committed=p4_display_ack_finish(&ack,frame_generation,(uint64_t)p4_monotonic_ms());
    portEXIT_CRITICAL(&ack_lock);
    if(!committed)poison_draw();
    return committed && !p4_display_failed()?0:-1;
}
static void p4_ui_init(lv_display_t *display) {
    screen=display;
    color_done=xSemaphoreCreateBinary();if(!color_done)p4_fatal();
    preview_pixels=heap_caps_calloc(153600,sizeof(uint16_t),MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    if(!preview_pixels)p4_fatal();
    preview=(lv_image_dsc_t){.header={.magic=LV_IMAGE_HEADER_MAGIC,.cf=LV_COLOR_FORMAT_RGB565,
        .w=320,.h=480,.stride=640},.data_size=307200,.data=(const uint8_t *)preview_pixels};
    gpio_config_t c={.pin_bit_mask=1ULL<<BOOT_GPIO,.mode=GPIO_MODE_INPUT,
        .pull_up_en=GPIO_PULLUP_ENABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,.intr_type=GPIO_INTR_DISABLE};
    ESP_ERROR_CHECK(gpio_config(&c));
    esp_lv_adapter_draw_bitmap_callbacks_t cb={.custom_draw_bitmap=track_draw};
    ESP_ERROR_CHECK(esp_lv_adapter_set_draw_bitmap_callbacks(screen,&cb,NULL));
}
lv_display_t *p4_display_start(void) {
    // Same admitted BSP init/profile. Own handles let the app install one IO
    // callback before any LVGL rendering; no replacement/handover race.
    esp_lv_adapter_config_t adapter=ESP_LV_ADAPTER_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(esp_lv_adapter_init(&adapter));
    ESP_ERROR_CHECK(esp_lv_adapter_set_default_display_idf_callback_registration_enabled(false));
    ESP_ERROR_CHECK(bsp_display_brightness_init());
    bsp_lcd_handles_t handles;
    ESP_ERROR_CHECK(bsp_display_new_with_handles(NULL,&handles));
    esp_lv_adapter_display_config_t display_config={.panel=handles.panel,.panel_io=handles.io,
        .profile={.interface=ESP_LV_ADAPTER_PANEL_IF_OTHER,.rotation=ESP_LV_ADAPTER_ROTATE_0,
            .hor_res=320,.ver_res=480,.buffer_height=50,.use_psram=false,.enable_ppa_accel=false,
            .require_double_buffer=false},.tear_avoid_mode=ESP_LV_ADAPTER_TEAR_AVOID_MODE_NONE};
    lv_display_t *display=esp_lv_adapter_register_display(&display_config);if(!display)p4_fatal();
    p4_ui_init(display);
    esp_lcd_panel_io_callbacks_t cb={.on_color_trans_done=color_complete};
    ESP_ERROR_CHECK(esp_lcd_panel_io_register_event_callbacks(handles.io,&cb,NULL));
    ESP_ERROR_CHECK(esp_lv_adapter_set_dummy_draw(display,true));
    bsp_touch_config_t touch_config={0};esp_lcd_touch_handle_t touch;
    ESP_ERROR_CHECK(bsp_touch_new(&touch_config,&touch));
    esp_lv_adapter_touch_config_t input=ESP_LV_ADAPTER_TOUCH_DEFAULT_CONFIG(display,touch);
    if(!esp_lv_adapter_register_touch(&input))p4_fatal();
    ESP_ERROR_CHECK(esp_lv_adapter_start());
    return display;
}
void p4_clear_response(bool expired) {
    atomic_store(&navigation_ready,false);atomic_store(&action,0);
    // Hide the old pixels before rebuilding. Failure never re-enables the lamp.
    if(bsp_display_backlight_off()!=ESP_OK)p4_fatal();
    p4_ui_status(expired?"RESPONSE EXPIRED\nPublic QR cleared":"RESPONSE CLEARED");
}
void p4_ui_status(const char *text) {
    lv_obj_t *root=start_screen();text_at(root,text,16,100,288);
    if(commit_screen()!=0 || bsp_display_backlight_on()!=ESP_OK)p4_fatal();
}
// Snapshot the exact decoder grayscale before quirc_end thresholds it in place.
int p4_scan_preview(const uint8_t *gray,size_t length) {
    lv_obj_t *root=start_screen();
    if(!p4_gray_preview(gray,length,preview_pixels,153600)) {esp_lv_adapter_unlock();return -1;}
    lv_image_cache_drop(&preview);
    lv_obj_t *image=lv_image_create(root);if(!image)p4_fatal();
    lv_image_set_src(image,&preview);lv_obj_set_pos(image,0,0);lv_obj_move_background(image);
    return commit_screen();
}
void p4_wait_new_action(void) {
    p4_button_t b;p4_button_begin(&b,p4_boot_pressed(),p4_monotonic_ms());
    for(;;) {if(p4_display_failed())p4_fatal();
        int a=p4_button_poll(&b,p4_boot_pressed(),p4_monotonic_ms(),false);
        if(a==4) return;
        if(a<0) p4_fatal();
        p4_worker_idle(10);}
}
void p4_boot_check(void) {
    p4_ui_status("INPUT CHECK GPIO35\nRelease, then tap BOOT\nPWR/RST are not consent");
    p4_wait_new_action();
    ESP_LOGI(TAG,"Local GPIO35 press/release observed; operator must confirm mapping");
}
static bool append_text(char *text,size_t *used,const uint8_t *value,size_t n) {
    if(n>264 || *used+n+2>=500) return false;
    for(size_t i=0;i<n;i++) if((value[i]<32 || value[i]>126) && value[i]!='\n') return false;
    memcpy(text+*used,value,n);*used+=n;text[(*used)++]='\n';text[*used]=0;return true;
}
int p4_present(uint32_t decision,const uint8_t *label,size_t label_len,
 const uint8_t *body,size_t body_len,const uint8_t *position,size_t position_len,
 size_t index,size_t total,uint64_t deadline) {
    if(decision>1 || !label || !body || !position || label_len>176 || position_len>9 || !total || index>=total || total>64) return -1;
    char text[500]={0};size_t used=0;
    if(!append_text(text,&used,label,label_len) || !append_text(text,&used,body,body_len) || !append_text(text,&used,position,position_len)) return -1;
    unsigned lines=0,columns=0;
    for(size_t i=0;i<used;i++) {if(text[i]=='\n') {lines++;columns=0;}else if(++columns>32) return -1;}
    if(lines>8) return -1;
    lv_obj_t *root=start_screen();text_at(root,text,32,104,256);
    if(decision) text_at(root,"BOOT: tap=REJECT\nHold 1.5..5s + release\n= APPROVE (this frame)",16,360,288);
    else {
        for(unsigned i=0;i<2;i++) {
            lv_obj_t *button=lv_button_create(root);if(!button) p4_fatal();
            lv_obj_set_pos(button,16+(int)i*152,370);lv_obj_set_size(button,136,56);
            lv_obj_set_style_bg_color(button,lv_color_hex(0xdddddd),0);
            text_at(button,i?"NEXT":"BACK",16,12,100);
            lv_obj_add_event_cb(button,nav_event,LV_EVENT_ALL,(void *)(uintptr_t)(i?1:2));
        }
        text_at(root,"BOOT press/release=REJECT",16,448,288);
    }
    if(commit_screen()!=0 || (uint64_t)p4_monotonic_ms()>=deadline) return -1;
    p4_button_t b;p4_button_begin(&b,p4_boot_pressed(),p4_monotonic_ms());
    uint64_t neutral_since=(uint64_t)p4_monotonic_ms();
    for(;;) {
        uint64_t now=(uint64_t)p4_monotonic_ms();
        if(now>=deadline || p4_display_failed()) {atomic_store(&navigation_ready,false);return -1;}
        int local=p4_button_poll(&b,p4_boot_pressed(),now,decision!=0);
        if(local) {atomic_store(&navigation_ready,false);return (uint64_t)p4_monotonic_ms()<deadline && !p4_display_failed()?local:-1;}
        if(!decision) {
            bool released=touch_released();
            if((uint64_t)p4_monotonic_ms()>=deadline) {atomic_store(&navigation_ready,false);return -1;}
            if(!released) neutral_since=now;
            else if(now-neutral_since>=40 && b.state==1) atomic_store(&navigation_ready,true);
            unsigned a=atomic_exchange(&action,0);
            if(a==1 || a==2) {atomic_store(&navigation_ready,false);return (uint64_t)p4_monotonic_ms()<deadline && !p4_display_failed()?(int)a:-1;}
        }
        p4_worker_idle(10);
    }
}
int p4_show_response(uint8_t *payload,size_t length,size_t capacity,uint64_t deadline_ms) {
    if(!payload || capacity!=1536)return -1;
    if(!length || length>capacity || (uint64_t)p4_monotonic_ms()>=deadline_ms) {
        memset(payload,0,capacity);p4_clear_response(true);return -1;
    }
    // No partially drawn QR can be published while the lamp is off.
    if(bsp_display_backlight_off()!=ESP_OK)p4_fatal();
    lv_obj_t *root=start_screen();
    text_at(root,"SCAN PUBLIC RESPONSE",16,72,288);
    lv_obj_t *qr=lv_qrcode_create(root);if(!qr) p4_fatal();
    lv_qrcode_set_size(qr,288);lv_qrcode_set_dark_color(qr,lv_color_black());
    lv_qrcode_set_light_color(qr,lv_color_white());lv_obj_set_pos(qr,16,112);
    lv_result_t result=lv_qrcode_update(qr,payload,(uint32_t)length);
    text_at(root,"Verify in original client\nTap BOOT to clear",16,426,288);
    if((uint64_t)p4_monotonic_ms()>=deadline_ms || result!=LV_RESULT_OK) {
        // Drop the uncommitted QR while holding the LVGL lock, then erase it.
        lv_obj_delete(qr);memset(payload,0,1536);
        if(esp_lv_adapter_set_dummy_draw(screen,true)!=ESP_OK)poison_draw();
        esp_lv_adapter_unlock();
        // The in-progress frame has not been submitted; abandon it explicitly.
        portENTER_CRITICAL(&ack_lock);
        bool abandoned=p4_display_ack_abandon(&ack,frame_generation);
        portEXIT_CRITICAL(&ack_lock);
        if(!abandoned)poison_draw();
        p4_clear_response(true);return -1;
    }
    int committed=commit_screen();
    if(committed!=0 || (uint64_t)p4_monotonic_ms()>=deadline_ms) {
        memset(payload,0,1536);p4_clear_response(true);return -1;
    }
    if(bsp_display_backlight_on()!=ESP_OK)p4_fatal();
    if((uint64_t)p4_monotonic_ms()>=deadline_ms) {
        memset(payload,0,capacity);p4_clear_response(true);return -1;
    }
    return 0;
}
