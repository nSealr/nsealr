#include "photo_capture.h"
#include "power_status.h"
#include "secret_qr.h"
#include "src/libs/qrcode/qrcodegen.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool zero(const void *ptr, size_t n) {
    const uint8_t *bytes = ptr;
    for (size_t i = 0; i < n; i++)
        if (bytes[i])
            return false;
    return true;
}
static void power(void) {
    assert(p4_power_classify(0x4a, 0x28, 0x40) == P4_POWER_EXTERNAL);
    assert(p4_power_classify(0x4a, 0x20, 0) == P4_POWER_EXTERNAL);
    assert(p4_power_classify(0x4a, 0x08, 0x40) == P4_POWER_BATTERY);
    assert(p4_power_classify(0x4a, 0x08, 0x20) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0x4a, 0x08, 0) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0x4a, 0x08, 0xc0) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0x4a, 0, 0x40) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0x4a, 0x0a, 0x40) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0x4a, 0x0c, 0x40) == P4_POWER_UNKNOWN);
    assert(p4_power_classify(0xff, 0x08, 0x40) == P4_POWER_UNKNOWN);
}
static void capture(void) {
    uint8_t *frame = calloc(1, P4_PHOTO_FRAME_BYTES), digest[32];
    assert(frame);
    p4_photo_capture photo;
    p4_photo_begin(&photo);
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    frame[8] = 1;
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES - 1, false));
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, true));
    assert(!p4_photo_take(&photo, digest) && zero(digest, sizeof(digest)));
    assert(p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    frame[8] = 2;
    assert(p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    frame[8] = 1;
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    for (unsigned i = 3; i <= 4; i++) {
        frame[8] = (uint8_t)i;
        assert(p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    }
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, true));
    frame[8] = 5;
    assert(p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, true));
    assert(!p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    assert(p4_photo_take(&photo, digest) && !zero(digest, sizeof(digest)));
    assert(zero(&photo, sizeof(photo)));
    assert(!p4_photo_take(&photo, digest) && zero(digest, sizeof(digest)));
    p4_photo_begin(&photo);
    assert(p4_photo_add(&photo, frame, P4_PHOTO_FRAME_BYTES, false));
    p4_photo_clear(&photo);
    assert(zero(&photo, sizeof(photo)));
    free(frame);
}
static void qr_grid(void) {
    const uint8_t seed[] = "000000000000000000000000000000000000000000000003";
    p4_secret_qr_t qr;
    uint16_t tile[P4_SECRET_TILE_PIXELS];
    assert(p4_secret_qr_encode(&qr, seed, sizeof(seed) - 1));
    unsigned blocks = (qr.modules + 4) / 5;
    /* Every cell center must match the encoded matrix, including edge blocks. */
    for (unsigned row = 0; row < blocks; row++)
        for (unsigned col = 0; col < blocks; col++)
            for (unsigned cy = 0; cy < 5; cy++) {
                unsigned py = cy * 50 + 25;
                assert(
                    p4_secret_qr_region_tile(&qr, col, row, py / 16, tile, P4_SECRET_TILE_PIXELS));
                for (unsigned cx = 0; cx < 5; cx++) {
                    unsigned mx = col * 5 + cx, my = row * 5 + cy;
                    uint16_t pixel = tile[(py % 16) * 320 + 35 + cx * 50 + 25];
                    if (mx < qr.modules && my < qr.modules)
                        assert(pixel == (qrcodegen_getModule(qr.matrix, mx, my) ? 0 : 0xffff));
                    else
                        assert(pixel != 0 && pixel != 0xffff);
                }
            }
    assert(!p4_secret_qr_region_tile(&qr, blocks, 0, 0, tile, P4_SECRET_TILE_PIXELS));
    assert(!p4_secret_qr_region_tile(&qr, 0, blocks, 0, tile, P4_SECRET_TILE_PIXELS));
    p4_secret_qr_clear(&qr);
    assert(zero(&qr, sizeof(qr)));
}
int main(void) {
    power();
    capture();
    qr_grid();
    puts("P4 photo admission, power states and QR transcription passed");
}
