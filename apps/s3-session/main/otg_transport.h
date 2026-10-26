// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "otg_state.h"
struct OtgBoot {
    uint32_t generation, reset_reason, mux_before, mux_after;
    bool previous_internal, previous_rtc, previous_bss;
};
OtgBoot otg_start();
OtgState otg_snapshot();
bool otg_current(uint32_t grant);
int otg_read(uint8_t *bytes,size_t capacity);
int otg_queue_response(const uint8_t *bytes,size_t length,uint32_t grant);
void otg_line(const char *line);
void otg_report_idle();
