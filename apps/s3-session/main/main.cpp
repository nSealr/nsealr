// SPDX-License-Identifier: MIT
// Native public-only S3 foundation. No secret import, signing or entropy provider.
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
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "pin_config.h"
#include "display_init.h"
#include "button_probe.h"
#include "session_buttons.h"
#define PROGMEM
#include "public_font.h"
#undef PROGMEM
extern "C" {
struct S3ExchangeResult { int32_t status; uint32_t length; };
static_assert(sizeof(S3ExchangeResult)==8,"Rust/C result layout");
using PresentCallback=int32_t(*)(uint32_t,uint32_t,uint32_t,const uint8_t*,size_t,const uint8_t*,size_t,const uint8_t*,size_t);
using NowCallback=int32_t(*)(uint64_t*);
using CancelCallback=int32_t(*)();
int32_t nsealr_s3_public_feed(uint8_t);
int32_t nsealr_s3_public_reset_input();
int32_t nsealr_s3_public_key(uint8_t*,size_t);
S3ExchangeResult nsealr_s3_public_exchange(uint8_t*,size_t,PresentCallback,NowCallback,CancelCallback);
}
static SessionMenu menu;
static bool local_locked;
static bool clock_started;
static bool transport_failed;
static uint32_t review_frames;
static uint64_t deadline_seconds;
static uint8_t response[1024];
static char public_hex[65];


#if CONFIG_ESP_MAIN_TASK_STACK_SIZE != 65536
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

static void usb_line(const char *text) {
    // Public diagnostics only. Finite blocking; a missing host cannot stop IO.
    (void)usb_serial_jtag_write_bytes(text, std::strlen(text), pdMS_TO_TICKS(20));
}

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
static void status_screen(const char *status) {
    banner();int row=0;
    (void)cells(reinterpret_cast<const uint8_t*>(status),std::strlen(status),row,0xffff);
    (void)cells(reinterpret_cast<const uint8_t*>(public_hex),26,row,0x07e0);
    (void)cells(reinterpret_cast<const uint8_t*>(public_hex+26),26,row,0x07e0);
    (void)cells(reinterpret_cast<const uint8_t*>(public_hex+52),12,row,0x07e0);
    small(158,"0: rotate180 | 14: enable | both: lock",0xffff);flush_frame();
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
    return local_locked || !usb_serial_jtag_is_connected();
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
        if(action==SessionAction::Lock){local_locked=true;menu.enabled=false;return 4;}
        if(action!=SessionAction::None)return int32_t(action);
        uint8_t hostile[64];
        (void)usb_serial_jtag_read_bytes(hostile,sizeof(hostile),0);
        vTaskDelay(1);
    }
}
static void discard_input() {
    uint8_t discarded[2048];
    (void)usb_serial_jtag_read_bytes(discarded,sizeof(discarded),0);
    (void)nsealr_s3_public_reset_input();
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
    usb_serial_jtag_driver_config_t usb={.tx_buffer_size=1024,.rx_buffer_size=2048};
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
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
    status_screen("Known public scalar 3\nLocal enable required");
    usb_line("s3-public-session-v1 public-scalar=3 no-secret-endpoints\n");
    SessionGesture idle;
    for(;;){
        poll_buttons();const auto a=gesture(idle,false);
        const auto change=menu.apply(a);
        if(change==SessionMenuChange::Lock){
            local_locked=true;discard_input();
            status_screen("LOCKED - public test");idle=SessionGesture{};
        } else if(change==SessionMenuChange::Rotate){
            local_locked=true;discard_input();
            // Both MX/MY bits change: 180 degrees, with the same MV/gap/geometry.
            ESP_ERROR_CHECK(esp_lcd_panel_mirror(panel,menu.rotated,!menu.rotated));
            status_screen("ROTATED - locked");idle=SessionGesture{};
        } else if(change==SessionMenuChange::Enable){
            discard_input();local_locked=transport_failed;
            if(transport_failed){menu.enabled=false;status_screen("TX UNCERTAIN - reset");}
            else status_screen("READY - public requests");
            idle=SessionGesture{};
        }
        if(!usb_serial_jtag_is_connected()&&menu.enabled){
            menu.enabled=false;local_locked=true;discard_input();status_screen("DISCONNECTED - locked");idle=SessionGesture{};
        }
        uint8_t input[64];const int got=usb_serial_jtag_read_bytes(input,sizeof(input),0);
        if(menu.enabled && got>0)for(int i=0;i<got;++i){
            const int32_t state=nsealr_s3_public_feed(input[i]);
            if(state==1){
                clock_started=false;local_locked=false;review_frames=0;
                const int64_t started_us=esp_timer_get_time();
                const auto r=nsealr_s3_public_exchange(response,sizeof(response),present_review,trusted_now,cancelled);
                const int64_t elapsed_us=esp_timer_get_time()-started_us;
                const auto minimum_stack=uxTaskGetStackHighWaterMark(nullptr);
                uint64_t now=0;
                // No display/IO callback between the final local sample and bounded TX.
                const bool release=trusted_now(&now)==0&&now<deadline_seconds&&!cancelled();
                const bool attempted=release&&r.length>0&&r.length<=sizeof(response);
                const int queued=attempted?
                    usb_serial_jtag_write_bytes(response,r.length,pdMS_TO_TICKS(200)):0;
                // A return count is queue acceptance, never proof of host receipt.
                // Even return0 can follow a prefix already copied to hardware FIFO.
                if((attempted&&queued!=int(r.length))||r.length>sizeof(response))transport_failed=true;
                std::memset(response,0,sizeof(response));
                menu.enabled=false;discard_input();idle=SessionGesture{};
                if(r.status==0&&queued==int(r.length)&&attempted)status_screen("RESULT QUEUED - public test");
                else if(r.status==-5)status_screen("REJECTED - no signature");
                else if(r.status==-7)status_screen("EXPIRED - no signature");
                else if(r.status==-11)status_screen("LOCKED - no signature");
                else status_screen(transport_failed?"TX UNCERTAIN - reset":"FAILED - review again");
                if(attempted&&!transport_failed){
                    char line[192];
                    std::snprintf(line,sizeof(line),"s3-public-result-v1 status=%ld tx_report=%d frames=%lu elapsed_us=%lld stack_min_free_bytes=%lu\n",
                        (long)r.status,queued,(unsigned long)review_frames,(long long)elapsed_us,(unsigned long)minimum_stack);
                    usb_line(line);
                }
                break; // Remaining bytes from this read cannot start another request.
            }
            if(state<0){discard_input();break;}
        }
        vTaskDelay(1);
    }
}
