// SPDX-License-Identifier: MIT
// Display init and board pins derived from Xinyuan-LilyGO/T-Display-S3
// 1cc41eb1c76b2f3215130a3dd64e7138ce00b482. See THIRD_PARTY.md.
#include <Arduino.h>
#include <TFT_eSPI.h>
#include "pin_config.h"
#include "display_init.h"
#include "button_probe.h"

static_assert(PIN_BUTTON_1 == 0 && PIN_BUTTON_2 == 14, "Wrong button pin contract");
#if PIN_LCD_WR != TFT_WR || PIN_LCD_RD != TFT_RD || PIN_LCD_CS != TFT_CS || \
    PIN_LCD_DC != TFT_DC || PIN_LCD_RES != TFT_RST || PIN_LCD_D0 != TFT_D0 || \
    PIN_LCD_D1 != TFT_D1 || PIN_LCD_D2 != TFT_D2 || PIN_LCD_D3 != TFT_D3 || \
    PIN_LCD_D4 != TFT_D4 || PIN_LCD_D5 != TFT_D5 || PIN_LCD_D6 != TFT_D6 || \
    PIN_LCD_D7 != TFT_D7 || PIN_LCD_BL != TFT_BL || TFT_WIDTH != 170 || TFT_HEIGHT != 320
#error "Pinned TFT_eSPI Setup206 is required"
#endif
static TFT_eSPI tft;
static ProbeButton buttons[2];
static uint32_t received_ignored = 0;
static uint32_t last_status = 0;

static void draw_status() {
    tft.fillRect(2, 48, 316, 96, TFT_BLACK);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("PUBLIC IO PROBE - NO SIGNER", 8, 50, 2);
    for (unsigned i = 0; i < 2; ++i) {
        const auto &b = buttons[i];
        char line[64];
        snprintf(line, sizeof(line), "GPIO%u %-4s %-7s count %lu", b.gpio,
                 b.stable_down ? "DOWN" : "UP", b.armed ? "ARMED" : "RELEASE",
                 (unsigned long)b.presses);
        tft.drawString(line, 8, 74 + (int)i * 22, 2);
    }
    tft.drawString("USB input ignored; both buttons local", 8, 122, 2);
}

void setup() {
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);
    pinMode(PIN_BUTTON_1, INPUT_PULLUP);
    pinMode(PIN_BUTTON_2, INPUT_PULLUP);
    const uint32_t now = millis();
    buttons[0] = probe_button_start(PIN_BUTTON_1, digitalRead(PIN_BUTTON_1) == LOW, now);
    buttons[1] = probe_button_start(PIN_BUTTON_2, digitalRead(PIN_BUTTON_2) == LOW, now);
    Serial.begin(115200);
    tft.begin();
    for (const auto &cmd : lcd_st7789v) {
        tft.writecommand(cmd.cmd);
        for (uint8_t j = 0; j < (cmd.len & 0x7fU); ++j) tft.writedata(cmd.data[j]);
        if ((cmd.len & 0x80U) != 0) delay(120);
    }
    tft.setRotation(3);
    tft.fillScreen(TFT_BLACK);
    tft.drawRect(0, 0, 320, 170, TFT_WHITE);
    const uint16_t colors[4] = {TFT_RED, TFT_GREEN, TFT_BLUE, TFT_WHITE};
    for (int i = 0; i < 4; ++i) tft.fillRect(4 + i * 78, 4, 76, 36, colors[i]);
    draw_status();
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("320x170 border / RGBW", 8, 148, 2);
    pinMode(PIN_LCD_BL, OUTPUT);
    digitalWrite(PIN_LCD_BL, HIGH);
}

void loop() {
    const uint32_t now = millis();
    bool draw_changed = false;
    for (auto &b : buttons) {
        const auto edge = probe_button_update(b, digitalRead(b.gpio) == LOW, now);
        if (edge != ProbeEdge::None) {
            draw_changed = true;
            Serial.printf("s3-io-v1 gpio=%u edge=%s count=%lu uptime_ms=%lu\n", b.gpio,
                edge == ProbeEdge::Pressed ? "press" : edge == ProbeEdge::Armed ? "armed" : "release",
                (unsigned long)b.presses, (unsigned long)now);
        }
    }
    // Ignore bytes rather than accepting any host-controlled input/approval.
    // Work per iteration is bounded; no received contents are printed/stored.
    for (unsigned i = 0; i < 64 && Serial.available() > 0; ++i) {
        (void)Serial.read();
        ++received_ignored;
    }
    if (draw_changed) draw_status();
    if ((uint32_t)(now - last_status) >= 1000U) {
        last_status = now;
        Serial.printf("s3-io-v1 status uptime_ms=%lu gpio0=%u gpio14=%u count0=%lu count14=%lu ignored_bytes=%lu\n",
            (unsigned long)now, buttons[0].stable_down, buttons[1].stable_down,
            (unsigned long)buttons[0].presses, (unsigned long)buttons[1].presses,
            (unsigned long)received_ignored);
    }
    delay(5);
}
