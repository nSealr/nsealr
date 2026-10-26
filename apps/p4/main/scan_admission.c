// SPDX-License-Identifier: MIT
#include "scan_admission.h"
#include "worker_watchdog.h"
#include "p4_local.h"
void p4_scan_resume(SemaphoreHandle_t token,atomic_bool *enabled) {
    // Worker has collected the previous operation and still holds admission.
    p4_worker_idle(10);atomic_store(enabled,true);
    if(xSemaphoreGive(token)!=pdTRUE)p4_fatal();
}
void p4_scan_idle_feed(SemaphoreHandle_t token) {
    // Protect the check and feed with the very token used by camera admission.
    if(xSemaphoreTake(token,0)==pdTRUE) {
        p4_worker_idle(0);
        if(xSemaphoreGive(token)!=pdTRUE)p4_fatal();
    }
}
