// SPDX-License-Identifier: MIT
#include "../include/button_probe.h"
#include <cassert>
#include <climits>
#include <cstdio>
int main() {
    auto b = probe_button_start(14, true, 0);
    assert(probe_button_update(b, true, 1000) == ProbeEdge::None);
    assert(b.presses == 0 && !b.armed);
    assert(probe_button_update(b, false, 1001) == ProbeEdge::None);
    assert(probe_button_update(b, false, 1040) == ProbeEdge::None);
    assert(probe_button_update(b, false, 1041) == ProbeEdge::Armed);
    assert(b.presses == 0);
    assert(probe_button_update(b, true, 1100) == ProbeEdge::None);
    assert(probe_button_update(b, false, 1110) == ProbeEdge::None);
    assert(probe_button_update(b, true, 1120) == ProbeEdge::None);
    assert(probe_button_update(b, true, 1159) == ProbeEdge::None);
    assert(probe_button_update(b, true, 1160) == ProbeEdge::Pressed);
    assert(b.presses == 1);
    assert(probe_button_update(b, true, 3000) == ProbeEdge::None);
    assert(b.presses == 1);
    assert(probe_button_update(b, false, 3001) == ProbeEdge::None);
    assert(probe_button_update(b, false, 3041) == ProbeEdge::Released);
    auto w = probe_button_start(0, false, UINT_MAX - 30U);
    assert(probe_button_update(w, true, UINT_MAX - 20U) == ProbeEdge::None);
    assert(probe_button_update(w, true, 18U) == ProbeEdge::None);
    assert(probe_button_update(w, true, 19U) == ProbeEdge::Pressed);
    assert(w.presses == 1 && b.presses == 1);
    puts("PASS held-at-start, release-to-arm, bounce, held-once, release, millisecond wrap");
}
