// SPDX-License-Identifier: MIT
#include "p4_local.h"
#include "worker_watchdog.h"
#include "local_input.h"
#include <string.h>
void p4_wait_response_clear(uint8_t *response,size_t capacity,uint64_t deadline) {
    if(!response || capacity!=1536)p4_fatal();
    p4_button_t button;p4_button_begin(&button,p4_boot_pressed(),p4_monotonic_ms());
    bool expired;
    for(;;) {
        uint64_t now=(uint64_t)p4_monotonic_ms();expired=now>=deadline;
        if(expired || p4_display_failed())break;
        int action=p4_button_poll(&button,p4_boot_pressed(),now,false);
        if(action<0) {memset(response,0,capacity);p4_clear_response(true);p4_fatal();}
        if(action==4)break;
        uint64_t remaining=deadline-now;
        p4_worker_idle((uint32_t)(remaining<10?remaining:10));
    }
    expired=(uint64_t)p4_monotonic_ms()>=deadline;
    memset(response,0,capacity);
    p4_clear_response(expired);
}
