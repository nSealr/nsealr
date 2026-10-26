// SPDX-License-Identifier: MIT
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "p4_local.h"
static uint8_t response[1536];
static unsigned mode,clears,feeds;
static uint64_t start,deadline;
int64_t p4_monotonic_ms(void) {struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));return t.tv_sec*1000+t.tv_nsec/1000000;}
bool p4_display_failed(void) {return false;}
bool p4_boot_pressed(void) {uint64_t elapsed=(uint64_t)p4_monotonic_ms()-start;return mode==1?(elapsed>=70 && elapsed<130):mode==2?elapsed<80:false;}
_Noreturn void p4_fatal(void) {abort();}
void p4_worker_idle(uint32_t ms) {assert(ms<=10);feeds++;struct timespec t={.tv_nsec=(long)ms*1000000};assert(!nanosleep(&t,NULL));}
void p4_clear_response(bool expired) {
 clears++;for(size_t i=0;i<sizeof(response);i++)assert(!response[i]);
 assert(expired==((uint64_t)p4_monotonic_ms()>=deadline));
}
int main(void) {
 for(mode=0;mode<3;mode++) {
  memset(response,0x7b,sizeof(response));start=(uint64_t)p4_monotonic_ms();deadline=start+(mode==1?500:200);
  unsigned old=clears;p4_wait_response_clear(response,sizeof(response),deadline);assert(clears==old+1);
  uint64_t elapsed=(uint64_t)p4_monotonic_ms()-start;
  if(mode!=1)assert((uint64_t)p4_monotonic_ms()>=deadline);else assert((uint64_t)p4_monotonic_ms()<deadline);
  printf("response mode=%u elapsed_ms=%llu clear_calls=1 zero_before_clear=PASS\n",mode,(unsigned long long)elapsed);
 }
 assert(feeds>0);puts("Real CLOCK_MONOTONIC: no-BOOT expiry, fresh tap clear and preheld release ignored; same absolute deadline PASS (mock UI clear only)");
}
