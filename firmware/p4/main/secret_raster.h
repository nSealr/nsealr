// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#define P4_SECRET_TILE_PIXELS (320U*16U)
#define P4_SECRET_COLUMNS 16U
bool p4_secret_raster(const uint8_t*,size_t,unsigned,uint16_t*,size_t);
// Up to eight explicitly wrapped ASCII lines; no clipping or implicit reflow.
bool p4_secret_raster_lines(const uint8_t*,size_t,unsigned,uint16_t*,size_t);
// Private next-letter mask is rasterized directly, never stored in LVGL objects.
bool p4_word_keyboard_tile(uint32_t valid,unsigned row,uint16_t *tile,size_t capacity);
