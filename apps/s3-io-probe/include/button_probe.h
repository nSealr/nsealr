// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>

// IO diagnostics only. No operation authorization or long-press approval.
struct ProbeButton {
    uint8_t gpio;
    bool raw_down;
    bool stable_down;
    bool armed;
    uint32_t changed_ms;
    uint32_t presses;
};
static inline ProbeButton probe_button_start(uint8_t gpio, bool down, uint32_t now) {
    return {gpio, down, down, !down, now, 0};
}
enum class ProbeEdge { None, Released, Pressed, Armed };
static inline ProbeEdge probe_button_update(ProbeButton &b, bool down, uint32_t now) {
    if (down != b.raw_down) {
        b.raw_down = down;
        b.changed_ms = now;
    }
    if ((uint32_t)(now - b.changed_ms) < 40U || down == b.stable_down) {
        return ProbeEdge::None;
    }
    b.stable_down = down;
    if (!b.armed) {
        if (!down) {
            b.armed = true;
            return ProbeEdge::Armed;
        }
        return ProbeEdge::None;
    }
    if (down) {
        ++b.presses;
        return ProbeEdge::Pressed;
    }
    return ProbeEdge::Released;
}
