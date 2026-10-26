// SPDX-License-Identifier: MIT
#include "c6_probe.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
enum {NORMAL,BASE_FAIL,BAD_ID,INPUT_OFF,LOW_ERR,LOW_INPUT_OFF,LOW_VALID,LOW_OTHER,RELEASE_ERR,RECOVERY_ERR,RECOVERY_MISMATCH,SECOND_VALID,CLEANUP_ERR,CLEANUP_INPUT_OFF,CLEANUP_HIGH,TIME_BEFORE_LOW,TIME_AFTER_LOW,CLOCK_BACK,TIME_IN_PAD,PREP_ERR,CASE_COUNT};
static unsigned scenario,lows,releases,identities,reads,pads,reports;
static int64_t clock_ms;
static bool driven;
static int64_t now(void) {return clock_ms;}
static int prepare(void) {return scenario==PREP_ERR?-1:0;}
static int identity(p4_c6_identity_t *id) {
 identities++;*id=(p4_c6_identity_t){.manufacturer=0x0092,.device=0x6666,.cccr=0x32,.functions=1,.cis_used=7};
 if(scenario==BASE_FAIL && identities==1)return -7;
 if(scenario==BAD_ID && identities==1)id->manufacturer=0x1234;
 if(scenario==RECOVERY_ERR && identities==2)return -8;
 if(scenario==RECOVERY_MISMATCH && identities==2)id->cccr=0x31;
 return 0;
}
static int low(void) {
 lows++;driven=true;
 if(scenario==LOW_ERR && lows==1)return -9;
 if(scenario==CLEANUP_ERR && lows==3)return -10;
 return 0;
}
static int release(void) {releases++;if(scenario==RELEASE_ERR)return -11;driven=false;return 0;}
static int pad(p4_c6_pad_t *p) {
 pads++;*p=(p4_c6_pad_t){.level=driven?0:1,.input=true,.output=driven};
 if(scenario==INPUT_OFF && !lows){p->input=false;p->level=-1;}
 if(scenario==LOW_INPUT_OFF && lows==1){p->input=false;p->level=-1;}
 if(scenario==CLEANUP_INPUT_OFF && lows==3){p->input=false;p->level=-1;}
 if(scenario==CLEANUP_HIGH && lows==3)p->level=1;
 if(scenario==TIME_IN_PAD && lows==1)clock_ms+=20000;
 return 0;
}
static p4_c6_reply_t read_link(void) {
 reads++;
 if((scenario==LOW_VALID && reads==1)||(scenario==SECOND_VALID && reads==2))return P4_C6_VALID;
 if(scenario==LOW_OTHER && reads==1)return P4_C6_OTHER_ERROR;
 return P4_C6_TIMED_OUT;
}
static void wait_ms(uint32_t ms) {
 clock_ms+=ms;
 if(scenario==TIME_AFTER_LOW && lows==1)clock_ms+=20000;
 if(scenario==CLOCK_BACK && lows==1)clock_ms=0;
}
static void report(const p4_c6_result_t *r) {
 reports++;
 if(scenario==TIME_BEFORE_LOW && r->phase==2)clock_ms+=20000;
}
static void cis_cases(void) {
 p4_c6_identity_t id={0};uint8_t good[]={0x20,4,0x92,0,0x66,0x66,0xff};
 assert(p4_c6_parse_cis(good,sizeof(good),&id));assert(id.manufacturer==0x92 && id.device==0x6666 && id.cis_used==7);
 for(size_t n=0;n<sizeof(good);n++)assert(!p4_c6_parse_cis(good,n,&id));
 uint8_t duplicate[]={0x20,4,0x92,0,0x66,0x66,0x20,4,0x92,0,0x66,0x66,0xff};assert(!p4_c6_parse_cis(duplicate,sizeof(duplicate),&id));
 uint8_t bad[]={0x20,4,0x34,0x12,0x66,0x66,0xff};assert(!p4_c6_parse_cis(bad,sizeof(bad),&id));
 uint8_t overrun[]={0x20,255,0x92,0,0x66,0x66,0xff};assert(!p4_c6_parse_cis(overrun,sizeof(overrun),&id));
 uint8_t nulls[65]={0};nulls[64]=0xff;assert(!p4_c6_parse_cis(nulls,sizeof(nulls),&id));
 assert(!p4_c6_parse_cis(good,257,&id));
 uint8_t boundary[256];memset(boundary,0xff,sizeof(boundary));boundary[0]=0x15;boundary[1]=247;
 memcpy(boundary+249,good,sizeof(good));assert(p4_c6_parse_cis(boundary,sizeof(boundary),&id));assert(id.cis_used==256);
}
int main(void) {
 cis_cases();const p4_c6_ops_t ops={now,prepare,identity,low,release,pad,read_link,wait_ms,report};
 for(scenario=0;scenario<CASE_COUNT;scenario++) {
  lows=releases=identities=reads=pads=reports=0;clock_ms=100;driven=false;
  p4_c6_result_t r;p4_c6_run(&ops,&r,100);
  assert(releases<=1);
  if(scenario==BASE_FAIL || scenario==BAD_ID || scenario==INPUT_OFF || scenario==PREP_ERR || scenario==TIME_BEFORE_LOW) {
   assert(!r.low_attempted && lows==0 && releases==0 && r.outcome!=P4_C6_OBSERVED);
  } else {
   assert(r.low_attempted && lows>=2); // Cleanup attempted on every post-low return.
  }
  if(scenario==NORMAL)assert(r.outcome==P4_C6_OBSERVED && lows==3 && releases==1 && r.final.level==0 && r.final.input && r.final.output);
  else assert(r.outcome!=P4_C6_OBSERVED);
  if(scenario==CLEANUP_ERR || scenario==CLEANUP_INPUT_OFF || scenario==CLEANUP_HIGH)assert(r.outcome==P4_C6_CLEANUP_FAILED);
  if(scenario==LOW_VALID || scenario==LOW_OTHER)assert(!releases && reads==1);
  if(scenario==TIME_AFTER_LOW || scenario==CLOCK_BACK || scenario==TIME_IN_PAD)assert(!releases && !reads && r.primary_error==-100);
  printf("case=%u result=%u low_attempts=%u release=%u read=%u final_pad=%d input=%d output=%d cleanup=%d\n",scenario,r.outcome,lows,releases,reads,r.final.level,r.final.input,r.final.output,r.cleanup_error);
 }
 puts("CIS bounded parser +20 causal-sequence cases PASS (mock peripheral/clock inputs, not hardware/RF evidence)");
}
