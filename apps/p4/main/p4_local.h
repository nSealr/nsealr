// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include "lvgl.h"
lv_display_t *p4_display_start(void);
void p4_ui_status(const char *text);
void p4_boot_check(void);
void p4_wait_new_action(void);
int p4_show_response(uint8_t *payload, size_t len, size_t capacity, uint64_t deadline_ms);
int64_t p4_monotonic_ms(void);
int p4_memory_internal(const uint8_t *, size_t);
_Noreturn void p4_fatal(void);
int p4_present(uint32_t,const uint8_t *,size_t,const uint8_t *,size_t,
 const uint8_t *,size_t,size_t,size_t,uint64_t);
int p4_scan_preview(const uint8_t *gray,size_t length);
bool p4_display_failed(void);
bool p4_boot_pressed(void);
void p4_clear_response(bool expired);
void p4_wait_response_clear(uint8_t *response,size_t capacity,uint64_t deadline);
