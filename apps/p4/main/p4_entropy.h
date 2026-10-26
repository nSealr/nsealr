// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
bool p4_entropy_bind_worker(void);
bool p4_entropy_used(void);
int p4_entropy_fault_mode(void);
ptrdiff_t p4_entropy_fill32(uint8_t*,size_t);
void p4_entropy_log_report(void);
