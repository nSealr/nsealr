// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
void p4_worker_watchdog_start(void);
void p4_worker_idle(uint32_t delay_ms);
void p4_worker_fault_probe(void);
