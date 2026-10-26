// SPDX-License-Identifier: MIT
// Native API mock only; no target watchdog or timing claim.
#pragma once
#include <stdint.h>
#define pdMS_TO_TICKS(n) (n)
#define portMAX_DELAY UINT32_MAX
