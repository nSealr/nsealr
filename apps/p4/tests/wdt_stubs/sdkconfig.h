// SPDX-License-Identifier: MIT
// Native API mock only; no target watchdog or timing claim.
#pragma once
#define CONFIG_ESP_TASK_WDT_EN 1
#define CONFIG_ESP_TASK_WDT_INIT 1
#define CONFIG_ESP_TASK_WDT_PANIC 1
#define CONFIG_ESP_TASK_WDT_TIMEOUT_S 5
#define CONFIG_ESP_SYSTEM_PANIC_SILENT_REBOOT 1
#define CONFIG_ESP_COREDUMP_ENABLE_TO_NONE 1
