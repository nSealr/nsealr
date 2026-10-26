// SPDX-License-Identifier: MIT
#include "display_ack.h"
#include "esp_attr.h"
static bool IRAM_ATTR fail(p4_display_ack_t *a) {a->failed=true;return false;}
void p4_display_ack_fail(p4_display_ack_t *a) {a->failed=true;}
bool p4_display_ack_begin(p4_display_ack_t *a,uint32_t generation,uint64_t now) {
    if(a->failed || a->active || a->pending || !generation || generation<=a->generation ||
       now>UINT64_MAX-P4_FRAME_COMMIT_MS)return fail(a);
    a->generation=generation;a->deadline=now+P4_FRAME_COMMIT_MS;
    a->sent=a->completed=0;a->active=true;return true;
}
bool p4_display_ack_submit(p4_display_ack_t *a,uint32_t generation,uint64_t now,uint32_t *serial) {
    if(a->failed || !a->active || a->pending || a->generation!=generation || now>=a->deadline ||
       a->serial==UINT32_MAX || a->sent==UINT32_MAX)return fail(a);
    *serial=++a->serial;a->pending_serial=*serial;a->sent++;a->pending=true;return true;
}
bool IRAM_ATTR p4_display_ack_complete(p4_display_ack_t *a,uint32_t generation,uint32_t serial,uint64_t now) {
    if(a->failed || !a->active || !a->pending || a->generation!=generation ||
       a->pending_serial!=serial || now>=a->deadline)return fail(a);
    a->pending=false;a->completed_serial=serial;a->completed++;return true;
}
bool p4_display_ack_collected(p4_display_ack_t *a,uint32_t generation,uint32_t serial,uint64_t now) {
    if(a->failed || !a->active || a->pending || a->generation!=generation ||
       a->completed_serial!=serial || a->sent!=a->completed || now>=a->deadline)return fail(a);
    return true;
}
bool p4_display_ack_finish(p4_display_ack_t *a,uint32_t generation,uint64_t now) {
    if(a->failed || !a->active || a->pending || a->generation!=generation || !a->sent ||
       a->sent!=a->completed || now>=a->deadline)return fail(a);
    a->active=false;return true;
}
bool p4_display_ack_abandon(p4_display_ack_t *a,uint32_t generation) {
    if(a->failed || !a->active || a->pending || a->generation!=generation || a->sent)return fail(a);
    a->active=false;return true;
}
