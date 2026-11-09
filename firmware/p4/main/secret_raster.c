// SPDX-License-Identifier: MIT
#include "secret_raster.h"
#include "secret_glyphs.h"

/* This is deliberately independent of LVGL: no secret enters a label, cache,
 * draw task or generic allocator. Only this caller-owned DMA tile contains pixels. */
static uint16_t ink(unsigned alpha) {
    unsigned red = (7 * (15 - alpha) + 236 * alpha) / 15;
    unsigned green = (6 * (15 - alpha) + 230 * alpha) / 15;
    unsigned blue = (13 * (15 - alpha) + 247 * alpha) / 15;
    return (uint16_t)(((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3));
}

static bool raster(const uint8_t *text, size_t n, unsigned row, uint16_t *tile, size_t capacity,
                   bool explicit_lines) {
    if (!tile || capacity != P4_SECRET_TILE_PIXELS || (n && !text) || row >= 12 || n > 135)
        return false;
    unsigned lines = 0, columns = 0;
    for (size_t i = 0; i < n; i++) {
        if (explicit_lines && text[i] == '\n') {
            if (++lines >= 8)
                return false;
            columns = 0;
        } else {
            if (text[i] < 32 || text[i] > 126)
                return false;
            if (explicit_lines && ++columns > 16)
                return false;
        }
    }
    if (!explicit_lines && n > 63)
        return false;
    for (size_t i = 0; i < capacity; i++)
        tile[i] = ink(0);
    for (unsigned y = 0; y < 16; y++) {
        unsigned line = (row * 16 + y) / 24, glyph_y = (row * 16 + y) % 24;
        size_t start = line * 16, length = n > start ? n - start : 0;
        if (explicit_lines) {
            start = 0;
            unsigned current = 0;
            while (start < n && current < line)
                if (text[start++] == '\n')
                    current++;
            length = 0;
            if (current == line)
                while (start + length < n && text[start + length] != '\n')
                    length++;
        }
        if (length > 16)
            length = 16;
        for (unsigned col = 0; col < length; col++) {
            for (unsigned x = 0; x < 16; x++) {
                unsigned alpha =
                    (secret_glyph[text[start + col] - 32][glyph_y][x / 2] >> (x % 2 ? 0 : 4)) & 15;
                tile[y * 320 + 32 + col * 16 + x] = ink(alpha);
            }
        }
    }
    return true;
}

bool p4_secret_raster(const uint8_t *text, size_t n, unsigned row, uint16_t *tile,
                      size_t capacity) {
    return raster(text, n, row, tile, capacity, false);
}
bool p4_secret_raster_lines(const uint8_t *text, size_t n, unsigned row, uint16_t *tile,
                            size_t capacity) {
    return raster(text, n, row, tile, capacity, true);
}
