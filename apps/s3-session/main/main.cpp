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
static uint32_t ignored;
static int32_t abi_rc = -99;
static bool abi_negatives;
static bool abi_guards;
static char abi_hex[129];
static int64_t abi_elapsed_us;
static UBaseType_t abi_stack_raw;
extern "C" int32_t nsealr_s3_abi_check(uint8_t *, size_t);

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

static void digit(int x, int y, unsigned value, uint16_t color) {
    // Own diagnostic seven-segment glyphs, no external font dependency.
    constexpr uint8_t segments[10] = {0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    const uint8_t s = segments[value % 10];
    if (s & 1) rectangle(x + 3,y,18,3,color);
    if (s & 2) rectangle(x + 21,y + 3,3,16,color);
    if (s & 4) rectangle(x + 21,y + 22,3,16,color);
    if (s & 8) rectangle(x + 3,y + 38,18,3,color);
    if (s & 16) rectangle(x,y + 22,3,16,color);
    if (s & 32) rectangle(x,y + 3,3,16,color);
    if (s & 64) rectangle(x + 3,y + 19,18,3,color);
}

static void present() {
    std::memset(frame, 0, width * height * sizeof(*frame));
    rectangle(0,0,width,2,0xffff); rectangle(0,height-2,width,2,0xffff);
    rectangle(0,0,2,height,0xffff); rectangle(width-2,0,2,height,0xffff);
    rectangle(4,4,76,24,0xf800); rectangle(82,4,76,24,0x07e0);
    rectangle(160,4,76,24,0x001f); rectangle(238,4,76,24,0xffff);
    digit(8,36,1,0xffff); digit(282,36,2,0xffff);
    digit(8,122,3,0xffff); digit(282,122,4,0xffff);
    for (unsigned i=0;i<2;++i) {
        const int x=72+int(i)*100;
        rectangle(x,52,64,16,buttons[i].stable_down ? 0xf800 : 0x07e0);
        digit(x+20,78,buttons[i].presses,0xffff);
    }
    const uint16_t core_color = abi_rc == 0 && abi_negatives && abi_guards ? 0x07e0 : 0xf800;
    rectangle(112,138,96,18,core_color);
    while (xSemaphoreTake(transferred,0) == pdTRUE) {}
    ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(panel,0,0,width,height,frame));
    // One framebuffer: never rewrite pixels until the actual DMA transfer ends.
    if (xSemaphoreTake(transferred,pdMS_TO_TICKS(1000)) != pdTRUE) {
        esp_system_abort("public LCD completion timeout");
    }
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

static void public_core_check() {
    uint8_t guarded[66]; std::memset(guarded,0xa5,sizeof(guarded));
    abi_negatives=nsealr_s3_abi_check(nullptr,64)==-1;
    for(size_t cap:{size_t(0),size_t(63),size_t(65)}) {
        const int32_t rc=nsealr_s3_abi_check(guarded+1,cap);
        abi_negatives=abi_negatives && rc==-1;
    }
    for(uint8_t b:guarded) abi_negatives=abi_negatives && b==0xa5;
    const int64_t start=esp_timer_get_time();
    abi_rc=nsealr_s3_abi_check(guarded+1,64);
    abi_elapsed_us=esp_timer_get_time()-start;
    abi_stack_raw=uxTaskGetStackHighWaterMark(nullptr);
    abi_guards=guarded[0]==0xa5 && guarded[65]==0xa5;
    constexpr char hex[]="0123456789abcdef";
    for(unsigned i=0;i<64;++i) {
        abi_hex[i*2]=hex[guarded[i+1]>>4];abi_hex[i*2+1]=hex[guarded[i+1]&15];
    }
    abi_hex[128]=0;
}

extern "C" void app_main() {
    usb_serial_jtag_driver_config_t usb = {.tx_buffer_size=1024,.rx_buffer_size=256};
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    const int pins[2]={PIN_BUTTON_1,PIN_BUTTON_2};
    for(unsigned i=0;i<2;++i) {
        gpio_config_t c = {}; c.pin_bit_mask=1ULL<<pins[i];c.mode=GPIO_MODE_INPUT;
        c.pull_up_en=GPIO_PULLUP_ENABLE;
        ESP_ERROR_CHECK(gpio_config(&c));
        buttons[i]=probe_button_start(uint8_t(pins[i]),gpio_get_level(gpio_num_t(pins[i]))==0,uint32_t(esp_timer_get_time()/1000));
    }
    display_init();
    public_core_check();
    present();
    int64_t last=0;
    for(;;) {
        const int64_t now=esp_timer_get_time();
        bool redraw=false;
        for(auto &button:buttons) {
            const auto edge=probe_button_update(button,gpio_get_level(gpio_num_t(button.gpio))==0,uint32_t(now/1000));
            if(edge!=ProbeEdge::None) {
                redraw=true;
                char line[128];
                std::snprintf(line,sizeof(line),"s3-native-v1 gpio=%u edge=%u count=%lu\n",
                    unsigned(button.gpio),unsigned(edge),(unsigned long)button.presses);
                usb_line(line);
            }
        }
        uint8_t input[64];
        const int got=usb_serial_jtag_read_bytes(input,sizeof(input),0);
        if(got>0) ignored+=unsigned(got); // No received bytes echoed/stored/interpreted.
        if(redraw) present();
        if(now-last>=1000000) {
            last=now;
            char status[256];
            std::snprintf(status,sizeof(status),"s3-native-abi-v1 rc=%ld negative=%u guards=%u elapsed_us=%lld stack_raw=%lu public_hex=%s\n",
                (long)abi_rc,unsigned(abi_negatives),unsigned(abi_guards),(long long)abi_elapsed_us,
                (unsigned long)abi_stack_raw,abi_hex);
            usb_line(status);
            std::snprintf(status,sizeof(status),"s3-native-v1 gpio0=%u gpio14=%u count0=%lu count14=%lu ignored_bytes=%lu\n",
                unsigned(buttons[0].stable_down),unsigned(buttons[1].stable_down),
                (unsigned long)buttons[0].presses,(unsigned long)buttons[1].presses,(unsigned long)ignored);
            usb_line(status);
        }
        vTaskDelay(1); // At least one real RTOS tick, including the100Hz SDK default.
    }
}
