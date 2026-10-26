// SPDX-License-Identifier: MIT
// Native API mock only; no target watchdog or timing claim.
#pragma once
#include "freertos/task.h"
#define ESP_OK 0
int esp_task_wdt_add(TaskHandle_t);
int esp_task_wdt_status(TaskHandle_t);
int esp_task_wdt_reset(void);
