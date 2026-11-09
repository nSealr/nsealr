#include "photo_capture.h"
#include "board_rng_logic.h"
#include "nsealr.h"
#include <string.h>

void p4_photo_clear(p4_photo_capture *state) {
    if (state)
        board_rng_wipe((uint8_t *)state, sizeof(*state));
}
void p4_photo_begin(p4_photo_capture *state) {
    if (!state)
        return;
    p4_photo_clear(state);
    state->active = true;
}
bool p4_photo_add(p4_photo_capture *state, const uint8_t *rgb, size_t length, bool final) {
    if (!state || !state->active || state->captured || !rgb || length != P4_PHOTO_FRAME_BYTES ||
        (final && state->frames < 4))
        return false;
    uint32_t fingerprint = 2166136261u;
    bool uniform = true;
    for (size_t i = 0; i < length; i++) {
        /* Only a stuck-frame check, never an entropy estimate or extractor. */
        fingerprint = (fingerprint ^ rgb[i]) * 16777619u;
        if (rgb[i] != rgb[i & 1])
            uniform = false;
    }
    if (uniform || (state->frames && fingerprint == state->previous))
        return false;
    if (state->frames < 4)
        for (uint32_t i = 0; i < state->frames; i++)
            if (state->first[i] == fingerprint)
                return false;
    if (ns_photo_frame_hash(state->digest, rgb, length, final) != NS_OK) {
        p4_photo_clear(state);
        return false;
    }
    if (state->frames < 4)
        state->first[state->frames] = fingerprint;
    state->previous = fingerprint;
    if (state->frames == UINT32_MAX) {
        p4_photo_clear(state);
        return false;
    }
    state->frames++;
    state->captured = final;
    return true;
}
bool p4_photo_take(p4_photo_capture *state, uint8_t digest[32]) {
    if (!digest)
        return false;
    board_rng_wipe(digest, 32);
    if (!state || !state->active || !state->captured)
        return false;
    memcpy(digest, state->digest, 32);
    p4_photo_clear(state);
    return true;
}
