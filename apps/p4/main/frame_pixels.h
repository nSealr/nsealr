// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
bool p4_frame_gray180(const uint8_t *rgb,size_t length,uint32_t width,uint32_t height,uint8_t *gray,size_t capacity);
