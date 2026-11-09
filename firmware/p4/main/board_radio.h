// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
// Fixed normal-mode GPIO54 policy for the pinned Waveshare board.
// A successful call samples the real pad/config; no RAM-only admission.
// phase is an internal static diagnostic label, never a host authority.
bool board_radio_begin(void);
bool board_radio_check(const char *phase);
void board_radio_before_abort(void);
