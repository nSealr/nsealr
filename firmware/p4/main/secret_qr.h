// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "secret_raster.h"
#define P4_SECRET_QR_BYTES 1178U
#define P4_SECRET_QR_ROWS 16U
typedef struct {
 uint8_t work[P4_SECRET_QR_BYTES],matrix[P4_SECRET_QR_BYTES];
 unsigned modules,scale,left,top;
 bool ready;
} p4_secret_qr_t;
// Caller must keep this owned state internal and wipe after every exit.
bool p4_secret_qr_encode(p4_secret_qr_t*,const uint8_t*,size_t);
bool p4_secret_qr_tile(const p4_secret_qr_t*,unsigned,uint16_t*,size_t);
void p4_secret_qr_clear(p4_secret_qr_t*);
