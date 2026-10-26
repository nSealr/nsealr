// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdio.h>
#include "display_ack.h"
int main(void) {
 p4_display_ack_t a={0};uint32_t serial;
 assert(p4_display_ack_begin(&a,1,100));assert(a.deadline==2100);
 assert(p4_display_ack_submit(&a,1,110,&serial));assert(serial==1);
 assert(p4_display_ack_complete(&a,1,serial,120));
 assert(p4_display_ack_collected(&a,1,serial,121));
 assert(p4_display_ack_submit(&a,1,2000,&serial));assert(a.deadline==2100); // no per-stripe extension
 assert(p4_display_ack_complete(&a,1,serial,2050));
 assert(p4_display_ack_collected(&a,1,serial,2051));assert(p4_display_ack_finish(&a,1,2099));
 assert(p4_display_ack_begin(&a,2,2200));assert(p4_display_ack_submit(&a,2,2201,&serial));
 assert(!p4_display_ack_complete(&a,1,serial,2202)); // wrong generation sticky
 assert(a.failed && !p4_display_ack_finish(&a,2,2203));
 a=(p4_display_ack_t){0};assert(!p4_display_ack_complete(&a,0,0,0)); // residual before first frame
 assert(!p4_display_ack_begin(&a,1,1));
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));
 assert(p4_display_ack_submit(&a,1,1,&serial));assert(!p4_display_ack_collected(&a,1,serial,2)); // missing ACK
 assert(a.failed && !p4_display_ack_begin(&a,2,3));
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));assert(p4_display_ack_submit(&a,1,1,&serial));
 assert(!p4_display_ack_complete(&a,1,serial+1,2)); // wrong serial
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));assert(p4_display_ack_submit(&a,1,1,&serial));
 assert(p4_display_ack_complete(&a,1,serial,2));assert(!p4_display_ack_complete(&a,1,serial,3)); // duplicate ACK
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));assert(p4_display_ack_submit(&a,1,1,&serial));
 assert(!p4_display_ack_complete(&a,1,serial,2000)); // equality expires
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));assert(!p4_display_ack_finish(&a,1,1)); // empty frame
 a=(p4_display_ack_t){0};assert(p4_display_ack_begin(&a,1,0));assert(p4_display_ack_abandon(&a,1));
 assert(p4_display_ack_begin(&a,2,1));assert(p4_display_ack_submit(&a,2,2,&serial));assert(!p4_display_ack_abandon(&a,2));
 a=(p4_display_ack_t){.serial=UINT32_MAX};assert(p4_display_ack_begin(&a,1,0));assert(!p4_display_ack_submit(&a,1,1,&serial));
 a=(p4_display_ack_t){0};assert(!p4_display_ack_begin(&a,1,UINT64_MAX-1999));
 puts("ACK model: serialized stripes, fixed deadline, missing/residual/duplicate/wrong-generation/wrong-serial/late ACK and wrap refused PASS; not hardware evidence");
}
