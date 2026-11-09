// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
bool p4_frame_gray_raw(const uint8_t *rgb,size_t length,uint32_t width,uint32_t height,uint8_t *gray,size_t capacity);
bool p4_gray_preview(const uint8_t *gray,size_t length,uint16_t *out,size_t pixels);
