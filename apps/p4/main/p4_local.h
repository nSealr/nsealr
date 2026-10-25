// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include "lvgl.h"
void p4_ui_init(lv_display_t *display);
void p4_ui_status(const char *text);
void p4_boot_check(void);
void p4_wait_new_action(void);
int p4_show_response(const uint8_t *payload, size_t len, uint64_t deadline_ms);
int64_t p4_monotonic_ms(void);
int p4_memory_internal(const uint8_t *, size_t);
_Noreturn void p4_fatal(void);
int p4_present(uint32_t,const uint8_t *,size_t,const uint8_t *,size_t,
 const uint8_t *,size_t,size_t,size_t,uint64_t);
