// SPDX-License-Identifier: MIT
#pragma once
#include <stdatomic.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
void p4_scan_resume(SemaphoreHandle_t token,atomic_bool *enabled);
void p4_scan_idle_feed(SemaphoreHandle_t token);
