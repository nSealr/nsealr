// SPDX-License-Identifier: MIT
#include "local_input.h"
void p4_button_begin(p4_button_t *b, bool pressed, uint64_t now) {
    *b = (p4_button_t){.changed=now,.last=now,.raw=pressed,.stable=pressed};
}
int p4_button_poll(p4_button_t *b, bool pressed, uint64_t now, bool decision) {
    if (now < b->last) return -1;
    b->last=now;
    if (b->state==3) return 0;
    if (pressed != b->raw) {b->raw=pressed; b->changed=now;}
    if (now-b->changed < 40) return 0;
    bool transition = b->stable != b->raw;
    b->stable=b->raw;
    if (b->state==0) {if (!b->stable) b->state=1; return 0;}
    if (b->state==1 && transition && b->stable) {b->state=2; b->pressed=now; return 0;}
    if (b->state==2) {
        uint64_t elapsed = now-b->pressed;
        if (elapsed > 5000) {b->state=3; return 4;}
        if (transition && !b->stable) {b->state=3; return decision && elapsed>=1500 ? 3:4;}
    }
    return 0;
}
