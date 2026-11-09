// SPDX-License-Identifier: MIT
#include "secret_qr.h"
#include "board_rng_logic.h"
#include "src/libs/qrcode/qrcodegen.h"
#include <string.h>
_Static_assert(P4_SECRET_QR_BYTES == qrcodegen_BUFFER_LEN_FOR_VERSION(20), "QR storage bound");
void p4_secret_qr_clear(p4_secret_qr_t *state) {
    if (state)
        board_rng_wipe((uint8_t *)state, sizeof(*state));
}
bool p4_secret_qr_encode(p4_secret_qr_t *state, const uint8_t *bytes, size_t length) {
    if (!state)
        return false;
    p4_secret_qr_clear(state);
    if (!bytes || !length || length > 586)
        return false;
    memcpy(state->work, bytes, length);
    bool encoded = qrcodegen_encodeBinary(state->work, length, state->matrix, qrcodegen_Ecc_MEDIUM,
                                          1, 20, qrcodegen_Mask_AUTO, true);
    board_rng_wipe(state->work, sizeof(state->work));
    if (!encoded) {
        p4_secret_qr_clear(state);
        return false;
    }
    state->modules = (unsigned)qrcodegen_getSize(state->matrix);
    if (state->modules < 21 || state->modules > 97) {
        p4_secret_qr_clear(state);
        return false;
    }
    state->scale = 256 / (state->modules + 8); // Four light modules on every edge.
    state->left = (320 - (state->modules + 8) * state->scale) / 2;
    state->top = (256 - (state->modules + 8) * state->scale) / 2;
    state->ready = true;
    return true;
}
bool p4_secret_qr_tile(const p4_secret_qr_t *state, unsigned row, uint16_t *tile, size_t capacity) {
    if (!state || !state->ready || row >= P4_SECRET_QR_ROWS || !tile ||
        capacity != P4_SECRET_TILE_PIXELS)
        return false;
    for (unsigned y = 0; y < 16; ++y)
        for (unsigned x = 0; x < 320; ++x) {
            int px = (int)x - (int)state->left, py = (int)(row * 16 + y) - (int)state->top;
            bool dark = false;
            if (px >= 0 && py >= 0) {
                int mx = px / (int)state->scale - 4, my = py / (int)state->scale - 4;
                if (mx >= 0 && my >= 0 && mx < (int)state->modules && my < (int)state->modules)
                    dark = qrcodegen_getModule(state->matrix, mx, my);
            }
            tile[y * 320 + x] = dark ? 0 : 0xffff;
        }
    return true;
}
bool p4_secret_qr_region_tile(const p4_secret_qr_t *state, unsigned column, unsigned block_row,
                              unsigned tile_row, uint16_t *tile, size_t capacity) {
    if (!state || !state->ready || column >= (state->modules + 4) / 5 ||
        block_row >= (state->modules + 4) / 5 || tile_row >= P4_SECRET_QR_ROWS || !tile ||
        capacity != P4_SECRET_TILE_PIXELS)
        return false;
    for (unsigned y = 0; y < 16; y++)
        for (unsigned x = 0; x < 320; x++) {
            unsigned py = tile_row * 16 + y;
            uint16_t color = 0x0021;
            if (x >= 35 && x < 285 && py < 250) {
                unsigned px = x - 35, mx = column * 5 + px / 50, my = block_row * 5 + py / 50;
                if (mx >= state->modules || my >= state->modules)
                    color = ((px + py) % 12 < 2) ? 0x8410 : 0xc618;
                else if (px % 50 == 0 || py % 50 == 0 || px == 249 || py == 249)
                    color = 0x8410;
                else
                    color = qrcodegen_getModule(state->matrix, (int)mx, (int)my) ? 0 : 0xffff;
            }
            tile[y * 320 + x] = color;
        }
    return true;
}
