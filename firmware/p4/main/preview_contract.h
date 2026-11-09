/* SPDX-FileCopyrightText: 2026 nSealr contributors
 * SPDX-License-Identifier: CC0-1.0
 * Bounded geometry for the measured P4 camera/display probe only.
 */
#ifndef NSEALR_PREVIEW_CONTRACT_H
#define NSEALR_PREVIEW_CONTRACT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define PREVIEW_CAMERA_WIDTH 800U
#define PREVIEW_CAMERA_HEIGHT 800U
#define PREVIEW_DISPLAY_WIDTH 320U
#define PREVIEW_DISPLAY_HEIGHT 480U
#define PREVIEW_CAMERA_BYTES ((size_t)1280000U)
typedef struct {
    uint32_t x, y, width, height;
    float scale;
} preview_crop_t;
static inline bool preview_frame_valid(uint32_t width, uint32_t height, size_t bytes)
{
    return width == PREVIEW_CAMERA_WIDTH && height == PREVIEW_CAMERA_HEIGHT &&
           bytes == PREVIEW_CAMERA_BYTES;
}
static inline bool preview_crop(uint32_t camera_width, uint32_t camera_height,
                                uint32_t display_width, uint32_t display_height,
                                preview_crop_t *out)
{
    if (out == NULL || camera_width != PREVIEW_CAMERA_WIDTH ||
        camera_height != PREVIEW_CAMERA_HEIGHT ||
        display_width != PREVIEW_DISPLAY_WIDTH || display_height != PREVIEW_DISPLAY_HEIGHT) {
        return false;
    }
    /* PPA scaling has 4 fractional bits. 512x768 * 10/16 exactly fills
     * 320x480. Arbitrary float ratios are truncated by the SDK and leave
     * unwritten edges. Crop symmetrically inside the actual camera frame. */
    *out = (preview_crop_t){.x = 144U, .y = 16U, .width = 512U, .height = 768U,
                           .scale = 10.0f / 16.0f};
    return true;
}
#endif
