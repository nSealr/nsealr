// SPDX-License-Identifier: MIT
// Native API mock only; no target watchdog or timing claim.
#pragma once
typedef void *SemaphoreHandle_t;
#include <stdint.h>
int xSemaphoreTake(SemaphoreHandle_t,uint32_t);
int xSemaphoreGive(SemaphoreHandle_t);
