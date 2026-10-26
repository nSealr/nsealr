// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
// Fixed normal-mode GPIO54 policy for the pinned Waveshare board.
// A successful call samples the real pad/config; no RAM-only admission.
// phase is an internal static diagnostic label, never a host authority.
bool p4_c6_guard_begin(void);
bool p4_c6_guard_check(const char *phase);
void p4_c6_guard_before_abort(void);
