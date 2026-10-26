// SPDX-License-Identifier: MIT
#pragma once
#include "quirc.h"
// Called only after count==1, by the sole worker; no allocation/resizing.
// Returns 0 on a bounded nsealr1 frame. attempts is diagnostic, never authority.
int p4_decode_one(struct quirc_code *code,struct quirc_data *data,unsigned *attempts);
