// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdbool.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include "scan_admission.h"
static unsigned available,feeds,attempts,admitted;
static atomic_bool enabled;
int xSemaphoreTake(SemaphoreHandle_t token,uint32_t wait) {(void)token;assert(!wait);if(!available)return pdFALSE;available=0;return pdTRUE;}
int xSemaphoreGive(SemaphoreHandle_t token) {(void)token;assert(!available);available=1;return pdTRUE;}
_Noreturn void p4_fatal(void) {abort();}
void p4_worker_idle(uint32_t delay) {
 assert(delay==0 || delay==10);feeds++;
 // Force a camera-admission attempt at the exact former check/feed race.
 attempts++;if(atomic_load(&enabled) && xSemaphoreTake((void *)1,0)==pdTRUE)admitted++;
 assert(!available && !admitted);
}
int main(void) {
 atomic_store(&enabled,false);available=0;
 p4_scan_resume((void *)1,&enabled);assert(feeds==1 && attempts==1 && !admitted && available && atomic_load(&enabled));
 p4_scan_idle_feed((void *)1);assert(feeds==2 && attempts==2 && !admitted && available);
 assert(xSemaphoreTake((void *)1,0)==pdTRUE); // camera now admits raw work
 atomic_store(&enabled,false);p4_scan_idle_feed((void *)1);assert(feeds==2 && !available);
 // Once that operation is collected, feed under the retained admission token.
 p4_scan_resume((void *)1,&enabled);assert(feeds==3 && attempts==3 && available && !admitted);
 puts("Actual scan helpers: camera cannot admit at feed boundary; outstanding raw token prevents feed PASS (native deterministic semaphore mocks)");
}
