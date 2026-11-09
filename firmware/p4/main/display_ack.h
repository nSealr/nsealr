// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stdint.h>
#define P4_FRAME_COMMIT_MS 2000U
// Protected by the same task/ISR critical section in p4_local.c. One physical
// transfer at a time; identifiers do not pretend to be supplied by the SPI chip.
typedef struct {
    uint32_t generation, serial, pending_serial, completed_serial, sent, completed;
    uint64_t deadline;
    bool active, pending, failed;
} p4_display_ack_t;
bool p4_display_ack_begin(p4_display_ack_t *,uint32_t,uint64_t);
bool p4_display_ack_submit(p4_display_ack_t *,uint32_t,uint64_t,uint32_t *);
bool p4_display_ack_complete(p4_display_ack_t *,uint32_t,uint32_t,uint64_t);
bool p4_display_ack_collected(p4_display_ack_t *,uint32_t,uint32_t,uint64_t);
bool p4_display_ack_finish(p4_display_ack_t *,uint32_t,uint64_t);
void p4_display_ack_fail(p4_display_ack_t *);
bool p4_display_ack_abandon(p4_display_ack_t *,uint32_t);
