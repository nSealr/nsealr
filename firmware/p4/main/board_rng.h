// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
bool board_rng_bind_worker(void);
bool board_rng_used(void);
ptrdiff_t board_rng_fill32(uint8_t*,size_t);
void board_rng_log_report(void);

// Private worker-only lease API. End releases admission, never identity history.
int board_rng_begin(uint32_t purpose,uint32_t identity,uint32_t operation);
int board_rng_end(void);
int board_rng_retire(void);
uint32_t board_rng_generation(void);

void board_rng_wipe(uint8_t*,size_t);
