// SPDX-License-Identifier: MIT
#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include "worker_watchdog.h"
#include "freertos/task.h"
static void *current=(void *)1,*subscribed;
static unsigned adds,feeds,delays;
static jmp_buf failure;
static int reset_result;
TaskHandle_t xTaskGetCurrentTaskHandle(void) {return current;}
int esp_task_wdt_add(TaskHandle_t who) {adds++;subscribed=who;return 0;}
int esp_task_wdt_status(TaskHandle_t who) {return who==subscribed?0:-1;}
int esp_task_wdt_reset(void) {assert(current==subscribed);feeds++;return reset_result;}
void vTaskDelay(uint32_t ticks) {assert(ticks<=250);delays++;}
_Noreturn void p4_fatal(void) {longjmp(failure,1);}
int main(void) {
 if(!setjmp(failure)) {p4_worker_idle(10);assert(!"unregistered feed admitted");}
 assert(!feeds && !adds);
 p4_worker_watchdog_start();assert(adds==1 && subscribed==current);
 p4_worker_idle(10);assert(feeds==1 && delays==1);
 current=(void *)2;
 if(!setjmp(failure)) {p4_worker_idle(10);assert(!"foreign task fed owner");}
 assert(feeds==1 && delays==1);
 current=(void *)1;
 if(!setjmp(failure)) {p4_worker_idle(251);assert(!"unbounded cooperative delay admitted");}
 assert(feeds==1 && delays==1);
 if(!setjmp(failure)) {p4_worker_watchdog_start();assert(!"duplicate owner registered");}
 assert(adds==1);
 reset_result=-1;
 if(!setjmp(failure)) {p4_worker_idle(10);assert(!"reset error ignored");}
 assert(feeds==2 && delays==1);
 puts("single registered worker; foreign/unregistered/duplicate owner and feed failure refused PASS (native mocks only)");
}
