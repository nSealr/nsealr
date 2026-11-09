#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define P4_PHOTO_FRAME_BYTES 1280000u
typedef struct {
    uint8_t digest[32];
    uint32_t first[4], previous, frames;
    bool active, captured;
} p4_photo_capture;

void p4_photo_begin(p4_photo_capture *state);
void p4_photo_clear(p4_photo_capture *state);
/* Obvious dead/repeated frames are rejected; this does not measure entropy. */
bool p4_photo_add(p4_photo_capture *state, const uint8_t *rgb565, size_t length, bool final);
bool p4_photo_take(p4_photo_capture *state, uint8_t digest[32]);
