// SPDX-License-Identifier: MIT
#include "p4_local.h"
#include "local_input.h"
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
static atomic_uint action, generation, touch_generation;
static atomic_bool navigation_ready, draw_failed;
static const char *TAG="p4_local";

int64_t p4_monotonic_ms(void) {return esp_timer_get_time()/1000;}
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
static bool boot_pressed(void) {return gpio_get_level(BOOT_GPIO)==0;}
static esp_err_t track_draw(lv_display_t *display,esp_lcd_panel_handle_t panel,
 int x0,int y0,int x1,int y1,const void *pixels,void *context) {
    (void)display;(void)context;
    esp_err_t e=esp_lcd_panel_draw_bitmap(panel,x0,y0,x1,y1,pixels);
    if(e!=ESP_OK) atomic_store(&draw_failed,true);
    return e;
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
    lv_obj_set_width(o,width);lv_obj_set_pos(o,x,y);
    lv_label_set_long_mode(o,LV_LABEL_LONG_CLIP);lv_label_set_text(o,value);return o;
}
// Worker owns screen updates; action capture stays disabled through DMA commit.
static lv_obj_t *start_screen(void) {
    atomic_store(&navigation_ready,false);atomic_store(&action,0);
    atomic_fetch_add(&generation,1);atomic_store(&touch_generation,0);
    if(esp_lv_adapter_lock(1000)!=ESP_OK) p4_fatal();
    if(esp_lv_adapter_set_dummy_draw(screen,false)!=ESP_OK) p4_fatal();
    lv_obj_t *root=lv_screen_active();lv_obj_clean(root);
    lv_obj_set_style_bg_color(root,lv_color_white(),0);
    text_at(root,"PUBLIC TEST IDENTITY",16,8,288);
    text_at(root,"NOT A SECURE VAULT",16,30,288);
    atomic_store(&draw_failed,false);return root;
}
static int commit_screen(void) {
    esp_lv_adapter_unlock();
    if(esp_lv_adapter_refresh_now(screen)!=ESP_OK) return -1;
    // Public adapter waits for in-flight DMA before relinquishing the panel.
    // A stuck DMA may block here: liveness/watchdog remains a measured gate.
    if(esp_lv_adapter_set_dummy_draw(screen,true)!=ESP_OK || atomic_load(&draw_failed)) return -1;
    return 0;
}
void p4_ui_init(lv_display_t *display) {
    screen=display;
    gpio_config_t c={.pin_bit_mask=1ULL<<BOOT_GPIO,.mode=GPIO_MODE_INPUT,
        .pull_up_en=GPIO_PULLUP_ENABLE,.pull_down_en=GPIO_PULLDOWN_DISABLE,.intr_type=GPIO_INTR_DISABLE};
    ESP_ERROR_CHECK(gpio_config(&c));
    esp_lv_adapter_draw_bitmap_callbacks_t cb={.custom_draw_bitmap=track_draw};
    ESP_ERROR_CHECK(esp_lv_adapter_set_draw_bitmap_callbacks(screen,&cb,NULL));
}
void p4_ui_status(const char *text) {
    lv_obj_t *root=start_screen();text_at(root,text,16,100,288);
    if(commit_screen()!=0) p4_fatal();
}
void p4_wait_new_action(void) {
    p4_button_t b;p4_button_begin(&b,boot_pressed(),p4_monotonic_ms());
    for(;;) {int a=p4_button_poll(&b,boot_pressed(),p4_monotonic_ms(),false);
        if(a==4) return;
        if(a<0) p4_fatal();
        vTaskDelay(pdMS_TO_TICKS(10));}
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
    p4_button_t b;p4_button_begin(&b,boot_pressed(),p4_monotonic_ms());
    uint64_t neutral_since=(uint64_t)p4_monotonic_ms();
    for(;;) {
        uint64_t now=(uint64_t)p4_monotonic_ms();
        if(now>=deadline || atomic_load(&draw_failed)) {atomic_store(&navigation_ready,false);return -1;}
        int local=p4_button_poll(&b,boot_pressed(),now,decision!=0);
        if(local) {atomic_store(&navigation_ready,false);return local;}
        if(!decision) {
            if(!touch_released()) neutral_since=now;
            else if(now-neutral_since>=40 && b.state==1) atomic_store(&navigation_ready,true);
            unsigned a=atomic_exchange(&action,0);
            if(a==1 || a==2) {atomic_store(&navigation_ready,false);return (int)a;}
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
int p4_show_response(const uint8_t *payload,size_t length,uint64_t deadline_ms) {
    if(!payload || !length || length>1536 || (uint64_t)p4_monotonic_ms()>=deadline_ms) return -1;
    lv_obj_t *root=start_screen();
    text_at(root,"SCAN PUBLIC RESPONSE",16,72,288);
    lv_obj_t *qr=lv_qrcode_create(root);if(!qr) p4_fatal();
    lv_qrcode_set_size(qr,288);lv_qrcode_set_dark_color(qr,lv_color_black());
    lv_qrcode_set_light_color(qr,lv_color_white());lv_obj_set_pos(qr,16,112);
    lv_result_t result=lv_qrcode_update(qr,payload,(uint32_t)length);
    text_at(root,"Verify in original client\nTap BOOT to clear",16,426,288);
    if((uint64_t)p4_monotonic_ms()>=deadline_ms) {
        lv_obj_delete(qr);text_at(root,"EXPIRED / NO RESPONSE",16,120,288);
        (void)commit_screen();return -1;
    }
    int committed=commit_screen();
    return result==LV_RESULT_OK && committed==0 && (uint64_t)p4_monotonic_ms()<deadline_ms ? 0:-1;
}
