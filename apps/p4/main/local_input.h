// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct { uint64_t changed, pressed, last; bool raw, stable; unsigned state; } p4_button_t;
void p4_button_begin(p4_button_t *b, bool pressed, uint64_t now);
// 0 none,3 approve,4 reject,-1 clock error. All actions are local edge-bound.
int p4_button_poll(p4_button_t *b, bool pressed, uint64_t now, bool decision);
