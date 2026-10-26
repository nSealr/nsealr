// SPDX-License-Identifier: MIT
// Native public-only S3. Only the known fixture identity; no secret endpoints or entropy provider.
// Board pins/ST7789 extra commands: LilyGO1cc41eb1; see THIRD_PARTY.md.
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "sdkconfig.h"
#include "esp_err.h"
#include "esp_system.h"
#include "esp_heap_caps.h"
#include "esp_lcd_io_i80.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_timer.h"
#include "driver/gpio.h"
#include "otg_transport.h"
#include "public_restart.h"
#include "s3_entropy.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "pin_config.h"
#include "display_init.h"
#include "button_probe.h"
#include "session_buttons.h"
#include "session_input.h"
#define PROGMEM
#include "public_font.h"
#undef PROGMEM
extern "C" {
struct S3ExchangeResult { int32_t status; uint32_t length; };
static_assert(sizeof(S3ExchangeResult)==8,"Rust/C result layout");
using PresentCallback=int32_t(*)(uint32_t,uint32_t,uint32_t,const uint8_t*,size_t,const uint8_t*,size_t,const uint8_t*,size_t);
using NowCallback=int32_t(*)(uint64_t*);
using CancelCallback=int32_t(*)();
using AuxCallback=int32_t(*)(uint8_t*,size_t,size_t*);
int32_t nsealr_s3_public_feed(uint8_t);
int32_t nsealr_s3_public_reset_input();
int32_t nsealr_s3_public_key(uint8_t*,size_t);
S3ExchangeResult nsealr_s3_public_exchange(uint8_t*,size_t,PresentCallback,NowCallback,CancelCallback,AuxCallback);
}
static SessionMenu menu;
static bool local_locked=true;
static uint32_t grant_epoch;
static OtgBoot otg_boot;
static bool clock_started;
static bool transport_failed;
static uint32_t review_frames;
static uint64_t deadline_seconds;
static uint8_t response[1024];
static char public_hex[65];


#if CONFIG_ESP_MAIN_TASK_STACK_SIZE != 98304
#error "The public core check requires the reviewed finite native main-task stack"
#endif
static constexpr int width = 320;
static constexpr int height = 170;
static esp_lcd_panel_handle_t panel;
static esp_lcd_panel_io_handle_t panel_io;
static SemaphoreHandle_t transferred;
static uint16_t *frame;
static ProbeButton buttons[2];
static bool transfer_done(esp_lcd_panel_io_handle_t,
                          esp_lcd_panel_io_event_data_t *, void *user) {
    BaseType_t wake = pdFALSE;
    xSemaphoreGiveFromISR(static_cast<SemaphoreHandle_t>(user), &wake);
    return wake == pdTRUE;
}

static void usb_line(const char *text) { otg_line(text); }

static void rectangle(int x, int y, int w, int h, uint16_t color) {
    for (int row = y; row < y + h; ++row)
        for (int col = x; col < x + w; ++col)
            frame[row * width + col] = color;
}

static void glyph(int x,int y,uint8_t c,uint16_t color,int scale=2) {
    for(int col=0;col<5;++col) for(int row=0;row<8;++row)
        if(font[unsigned(c)*5+unsigned(col)]&(1U<<row))
            rectangle(x+col*scale,y+row*scale,scale,scale,color);
}
static bool cells(const uint8_t *p,size_t n,int &row,uint16_t color) {
    int col=0;
    for(size_t i=0;i<n;++i) {
        const uint8_t c=p[i];
        if(c=='\n'){++row;col=0;continue;}
        if(c<32||c>126||col>=26||row>=8)return false;
        glyph(4+col*12,28+row*16,c,color);++col;
    }
    ++row;return row<=8;
}
static void small(int y,const char *s,uint16_t color) {
    const int length=int(std::strlen(s));
    const int start=menu.rotated?width-4-length*6:4;
    for(int x=start;*s && x>=0 && x+6<=width;x+=6,++s)glyph(x,y,uint8_t(*s),color,1);
}
static void flush_frame() {
    while(xSemaphoreTake(transferred,0)==pdTRUE){}
    ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(panel,0,0,width,height,frame));
    if(xSemaphoreTake(transferred,pdMS_TO_TICKS(1000))!=pdTRUE)
        esp_system_abort("public LCD completion timeout");
}
static void banner() {
    std::memset(frame,0,width*height*sizeof(*frame));
    const char *t="PUBLIC TEST KEY - S3";
    for(int x=4;*t;x+=12,++t)glyph(x,1,uint8_t(*t),0xffe0);
    small(18,menu.rotated?"BUTTONS RIGHT":"BUTTONS LEFT",0x07ff);
}
static void status_screen(const char *status,const char *footer="0:rotate/hold5s restart |14:enable |both:lock") {
    banner();int row=0;
    if(!cells(reinterpret_cast<const uint8_t*>(status),std::strlen(status),row,0xffff)||
        !cells(reinterpret_cast<const uint8_t*>(public_hex),26,row,0x07e0)||
        !cells(reinterpret_cast<const uint8_t*>(public_hex+26),26,row,0x07e0)||
        !cells(reinterpret_cast<const uint8_t*>(public_hex+52),12,row,0x07e0))
        esp_system_abort("public status geometry");
    char observation[53];
    const auto transport=otg_snapshot();
    std::snprintf(observation,sizeof(observation),"B%lu R%lu E%lu prev:%u%u%u",
        (unsigned long)otg_boot.generation,(unsigned long)otg_boot.reset_reason,(unsigned long)transport.epoch,
        otg_boot.previous_internal,otg_boot.previous_rtc,otg_boot.previous_bss);
    small(146,observation,0x07ff);
    small(158,footer,0xffff);flush_frame();
}
static void poll_buttons() {
    const uint32_t now=uint32_t(esp_timer_get_time()/1000);
    for(auto &b:buttons)
        (void)probe_button_update(b,gpio_get_level(gpio_num_t(b.gpio))==0,now);
}
static SessionAction gesture(SessionGesture &g,bool decision) {
    return g.update(uint32_t(esp_timer_get_time()/1000),
        buttons[0].stable_down,buttons[1].stable_down,
        gpio_get_level(gpio_num_t(PIN_BUTTON_1))==0,
        gpio_get_level(gpio_num_t(PIN_BUTTON_2))==0,decision);
}
static int32_t trusted_now(uint64_t *out) {
    const int64_t us=esp_timer_get_time();if(us<0||!out)return -1;
    *out=uint64_t(us)/1000000;
    if(!clock_started){clock_started=true;deadline_seconds=*out+100;}
    return 0;
}
static int32_t cancelled() {
    return local_locked || !otg_current(grant_epoch);
}
static int32_t present_review(uint32_t kind,uint32_t index,uint32_t total,
    const uint8_t *label,size_t label_n,const uint8_t *body,size_t body_n,
    const uint8_t *position,size_t position_n) {
    if(kind>1||index>=total||total>128||!label||!body||!position)return -1;
    banner();int row=0;
    if(!cells(label,label_n,row,0xffff)||!cells(body,body_n,row,0xffff)||
        !cells(position,position_n,row,0x07ff))return -1;
    small(158,kind?"0: reject | 14 hold1.5s: approve | both: lock":
        "0: back | 14: next | both hold1.5s: lock",0xffff);
    flush_frame();
    ++review_frames;
    // All physical events must follow this successful complete DMA commit.
    SessionGesture g;
    for(;;) {
        uint64_t now=0;
        if(trusted_now(&now)!=0||now>=deadline_seconds)return 0;
        if(cancelled())return 0;
        poll_buttons();const auto action=gesture(g,kind==1);
        if(cancelled())return 0;
        if(action==SessionAction::Lock){local_locked=true;menu.enabled=false;return 4;}
        if(action!=SessionAction::None)return int32_t(action);
        uint8_t hostile[64];
        (void)otg_read(hostile,sizeof(hostile));
        vTaskDelay(1);
    }
}
static SessionDrain discard_input() {
    const auto result=session_discard([](uint8_t *p,size_t n){
        return otg_read(p,n);
    });
    (void)nsealr_s3_public_reset_input();
    return result;
}
struct PublicEntropyDraw {uint8_t sample[32];S3EntropyReport report;};
static PublicEntropyDraw diagnostic_draws[4];
static_assert(sizeof(diagnostic_draws)+sizeof(S3EntropyReport)<=2048,"finite public instrumentation");
static void public_entropy_check(){
    status_screen("PUBLIC RNG - NO IDENTITY\nLocal test or skip","0: skip |14: four public draws |both: lock");
    SessionGesture choice;
    for(;;){
        poll_buttons();const auto action=gesture(choice,false);
        if(action==SessionAction::Back||action==SessionAction::Lock)return;
        if(action==SessionAction::Next){
            if(otg_snapshot().usable())break;
            status_screen("USB NOT READY - locked\nOpen logger, then retry","0: skip |14: public test");choice=SessionGesture{};
        }
        vTaskDelay(1);
    }
    s3_entropy_diagnostic_mode(true);
    S3EntropyStatus status=S3EntropyStatus::Unavailable;unsigned complete=0;
    for(unsigned i=0;i<4;++i){
        status_screen("PUBLIC32 BYTE DRAW\nNot identity material","Readbacks and sample: public serial log");
        s3_entropy_bind_public_epoch(otg_snapshot().epoch);size_t written=0;
        status=S3EntropyStatus(nsealr_s3_public_auxiliary(diagnostic_draws[i].sample,32,&written));
        diagnostic_draws[i].report=s3_entropy_last_report();
        s3_entropy_log_report(i+1,status==S3EntropyStatus::PublicDraw?diagnostic_draws[i].sample:nullptr);
        if(status!=S3EntropyStatus::PublicDraw||written!=32)break;
        ++complete;
    }
    s3_entropy_diagnostic_mode(false);
    char text[72];std::snprintf(text,sizeof(text),"PUBLIC RNG status %ld\n%u/4 - NOT QUALIFIED",(long)status,complete);
    status_screen(text,"Fresh0/14: known public fixture |no real keys");
    SessionGesture acknowledge;
    for(;;){poll_buttons();if(gesture(acknowledge,false)!=SessionAction::None)return;vTaskDelay(1);}
}
static void display_init() {
    gpio_set_direction(gpio_num_t(PIN_POWER_ON),GPIO_MODE_OUTPUT);
    gpio_set_level(gpio_num_t(PIN_POWER_ON),1);
    gpio_set_direction(gpio_num_t(PIN_LCD_RD),GPIO_MODE_OUTPUT);
    gpio_set_level(gpio_num_t(PIN_LCD_RD),1);
    transferred=xSemaphoreCreateBinary();
    if (!transferred) esp_system_abort("public LCD semaphore unavailable");
    esp_lcd_i80_bus_config_t bus = {};
    bus.dc_gpio_num=PIN_LCD_DC; bus.wr_gpio_num=PIN_LCD_WR;
    bus.clk_src=LCD_CLK_SRC_DEFAULT;
    const int data[8]={PIN_LCD_D0,PIN_LCD_D1,PIN_LCD_D2,PIN_LCD_D3,
                       PIN_LCD_D4,PIN_LCD_D5,PIN_LCD_D6,PIN_LCD_D7};
    for(unsigned i=0;i<8;++i) bus.data_gpio_nums[i]=data[i];
    bus.bus_width=8; bus.max_transfer_bytes=width*height*2;
    bus.psram_trans_align=64;
    esp_lcd_i80_bus_handle_t handle;
    ESP_ERROR_CHECK(esp_lcd_new_i80_bus(&bus,&handle));
    esp_lcd_panel_io_i80_config_t io = {};
    io.cs_gpio_num=PIN_LCD_CS; io.pclk_hz=10000000;
    io.trans_queue_depth=1; io.lcd_cmd_bits=8; io.lcd_param_bits=8;
    io.dc_levels.dc_data_level=1; io.on_color_trans_done=transfer_done;
    io.user_ctx=transferred;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_i80(handle,&io,&panel_io));
    esp_lcd_panel_dev_config_t config = {};
    config.reset_gpio_num=PIN_LCD_RES;
    config.rgb_ele_order=LCD_RGB_ELEMENT_ORDER_RGB;
    config.data_endian=LCD_RGB_DATA_ENDIAN_LITTLE;
    config.bits_per_pixel=16;
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(panel_io,&config,&panel));
    ESP_ERROR_CHECK(esp_lcd_panel_reset(panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
    ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel,true));
    ESP_ERROR_CHECK(esp_lcd_panel_swap_xy(panel,true));
    ESP_ERROR_CHECK(esp_lcd_panel_mirror(panel,false,true));
    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(panel,0,35));
    for (const auto &cmd:lcd_st7789v) {
        ESP_ERROR_CHECK(esp_lcd_panel_io_tx_param(panel_io,cmd.cmd,cmd.data,cmd.len&0x7f));
        if(cmd.len&0x80) vTaskDelay(pdMS_TO_TICKS(120));
    }
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel,true));
    frame=static_cast<uint16_t *>(heap_caps_aligned_alloc(64,width*height*2,
                                            MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!frame) esp_system_abort("public framebuffer unavailable");
    gpio_set_direction(gpio_num_t(PIN_LCD_BL),GPIO_MODE_OUTPUT);
    gpio_set_level(gpio_num_t(PIN_LCD_BL),1);
}

extern "C" void app_main() {
    otg_boot=otg_start();
    const int pins[2]={PIN_BUTTON_1,PIN_BUTTON_2};
    for(unsigned i=0;i<2;++i){
        gpio_config_t c={};c.pin_bit_mask=1ULL<<pins[i];c.mode=GPIO_MODE_INPUT;c.pull_up_en=GPIO_PULLUP_ENABLE;
        ESP_ERROR_CHECK(gpio_config(&c));
        buttons[i]=probe_button_start(uint8_t(pins[i]),gpio_get_level(gpio_num_t(pins[i]))==0,uint32_t(esp_timer_get_time()/1000));
    }
    display_init();
    uint8_t key[32];
    if(nsealr_s3_public_key(key,sizeof(key))!=0)esp_system_abort("public fixture key unavailable");
    constexpr char hex[]="0123456789abcdef";
    for(unsigned i=0;i<32;++i){public_hex[2*i]=hex[key[i]>>4];public_hex[2*i+1]=hex[key[i]&15];}
    public_hex[64]=0;
    public_entropy_check();
    status_screen("Known public scalar 3\nLocal enable required");
    SessionGesture idle;
    PublicRestart restart;
    unsigned shown_countdown=0;
    uint32_t seen_epoch=otg_snapshot().epoch;
    bool seen_poison=false;
    for(;;){
        const auto transport=otg_snapshot();
        if(transport.epoch!=seen_epoch||transport.poisoned!=seen_poison){
            seen_poison=transport.poisoned;
            seen_epoch=transport.epoch;idle=SessionGesture{};restart=PublicRestart{};shown_countdown=0;
            if(menu.enabled){menu.enabled=false;local_locked=true;discard_input();status_screen("USB EVENT - locked");}
        }
        poll_buttons();
        const uint32_t ms=uint32_t(esp_timer_get_time()/1000);
        const bool raw_l=gpio_get_level(gpio_num_t(PIN_BUTTON_1))==0;
        const bool raw_r=gpio_get_level(gpio_num_t(PIN_BUTTON_2))==0;
        if(restart.update(ms,buttons[0].stable_down,buttons[1].stable_down,raw_l,raw_r,!menu.enabled&&local_locked)){
            // Public local diagnostic only. No host/control-line/1200-baud path.
            status_screen("PUBLIC RESTART - TEST");
            esp_restart();
        }
        const unsigned countdown=restart.countdown(ms);
        if(countdown&&countdown!=shown_countdown){
            shown_countdown=countdown;char text[53];
            std::snprintf(text,sizeof(text),"PUBLIC RESTART in %us\nRelease: rotate only",countdown);
            status_screen(text);
        }
        const auto a=gesture(idle,false);
        const auto change=menu.apply(a);
        if(change==SessionMenuChange::Lock){
            local_locked=true;discard_input();
            status_screen("LOCKED - public test");idle=SessionGesture{};restart=PublicRestart{};shown_countdown=0;
        } else if(change==SessionMenuChange::Rotate){
            local_locked=true;discard_input();
            ESP_ERROR_CHECK(esp_lcd_panel_mirror(panel,menu.rotated,!menu.rotated));
            status_screen("ROTATED - locked");idle=SessionGesture{};restart=PublicRestart{};shown_countdown=0;
        } else if(change==SessionMenuChange::Enable){
            // Capture BEFORE drain. A callback during drain/display never gets
            // acknowledged by clearing a shared pending bit or reading a newer epoch.
            const uint32_t candidate=otg_snapshot().epoch;
            const auto drained=discard_input();
            grant_epoch=candidate;
            local_locked=transport_failed||drained!=SessionDrain::Empty||!otg_current(candidate);
            if(local_locked)menu.enabled=false;
            if(transport_failed)status_screen("TX UNCERTAIN - reset");
            else if(drained!=SessionDrain::Empty)status_screen("INPUT BUSY - try again");
            else if(local_locked)status_screen("USB NOT READY - locked");
            else status_screen("READY - public requests");
            idle=SessionGesture{};restart=PublicRestart{};shown_countdown=0;
        }
        // Display DMA/drain may block; recheck before consuming or admitting bytes.
        if(menu.enabled&&cancelled()){
            menu.enabled=false;local_locked=true;discard_input();status_screen("USB EVENT - locked");
            idle=SessionGesture{};restart=PublicRestart{};
        }
        uint8_t input[64];const int got=otg_read(input,sizeof(input));
        if(got<0){menu.enabled=false;local_locked=true;discard_input();status_screen("INPUT FAILED - locked");idle=SessionGesture{};restart=PublicRestart{};}
        if(menu.enabled&&!cancelled()&&got>0)for(int i=0;i<got;++i){
            if(cancelled())break;
            const int32_t state=nsealr_s3_public_feed(input[i]);
            if(state==1){
                clock_started=false;review_frames=0;
                const int64_t started_us=esp_timer_get_time();
                s3_entropy_bind_public_epoch(grant_epoch);
                const auto r=nsealr_s3_public_exchange(response,sizeof(response),present_review,trusted_now,cancelled,nsealr_s3_public_auxiliary);
                const int64_t elapsed_us=esp_timer_get_time()-started_us;
                const auto minimum_stack=uxTaskGetStackHighWaterMark(nullptr);
                uint64_t now=0;
                const bool release=trusted_now(&now)==0&&now<deadline_seconds&&!cancelled();
                const bool attempted=release&&r.length>0&&r.length<=sizeof(response);
                // Wrapper checks the grant again before and after nonblocking FIFO TX.
                const int queued=attempted?otg_queue_response(response,r.length,grant_epoch):0;
                if((attempted&&queued!=int(r.length))||r.length>sizeof(response))transport_failed=true;
                std::memset(response,0,sizeof(response));
                menu.enabled=false;local_locked=true;discard_input();idle=SessionGesture{};restart=PublicRestart{};
                if(r.status==0&&queued==int(r.length)&&attempted)status_screen("RESULT QUEUED - TEST ONLY");
                else if(r.status==-5)status_screen("REJECTED - no signature");
                else if(r.status==-7)status_screen("EXPIRED - no signature");
                else if(r.status==-11)status_screen("LOCKED - no signature");
                else if(r.status==-8)status_screen("PUBLIC AUX STOPPED\nRestart before new attempt");
                else status_screen(transport_failed?"TX UNCERTAIN - reset":"FAILED - review again");
                if(attempted&&!transport_failed){
                    char line[192];
                    std::snprintf(line,sizeof(line),"s3-public-result-v1 status=%ld tx_report=%d frames=%lu elapsed_us=%lld stack_min_free_bytes=%lu\n",
                        (long)r.status,queued,(unsigned long)review_frames,(long long)elapsed_us,(unsigned long)minimum_stack);
                    usb_line(line);
                }
                s3_entropy_log_report(0,nullptr);
                break;
            }
            if(state<0){menu.enabled=false;local_locked=true;discard_input();status_screen("INPUT FAILED - locked");idle=SessionGesture{};restart=PublicRestart{};break;}
        }
        if(!menu.enabled)otg_report_idle();
        vTaskDelay(1);
    }
}
