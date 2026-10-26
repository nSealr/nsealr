// SPDX-License-Identifier: MIT
// Native API mock only; no target watchdog or timing claim.
#pragma once
#include <stdint.h>
typedef void *TaskHandle_t;
TaskHandle_t xTaskGetCurrentTaskHandle(void);
void vTaskDelay(uint32_t);
