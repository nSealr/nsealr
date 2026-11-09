// SPDX-License-Identifier: MIT
#include "board_rng_logic.h"
#include <string.h>
void board_rng_wipe(uint8_t *p,size_t n) {volatile uint8_t *v=p;while(n--)*v++=0;}
int board_rng_lease_begin(board_rng_admission_t *s,uint32_t purpose,uint32_t identity,uint32_t operation) {
 if(!s->bound || s->busy || s->lease)return P4_RNG_OWNERSHIP;
 if(s->poisoned || !identity || !operation)return P4_RNG_UNAVAILABLE;
 if(purpose!=BOARD_ENTROPY_SEED && purpose!=BOARD_ENTROPY_AUX)return P4_RNG_ARGUMENT;
 if(s->identity && s->identity!=identity)return P4_RNG_OWNERSHIP;
 if(s->identity && operation<=s->operation)return P4_RNG_UNAVAILABLE;
 if(s->generation==UINT32_MAX){s->poisoned=true;return P4_RNG_UNAVAILABLE;}
 s->identity=identity;s->operation=operation;s->purpose=purpose;
 s->draws=0;s->limit=purpose==BOARD_ENTROPY_SEED?8U:1U;s->lease=true;return P4_RNG_OK;
}
int board_rng_admit(board_rng_admission_t *s,bool correct_worker) {
 if(!s->bound || !correct_worker || s->busy)return P4_RNG_OWNERSHIP;
 if(s->poisoned || !s->lease || s->draws>=s->limit)return P4_RNG_UNAVAILABLE;
 if(s->generation==UINT32_MAX){s->poisoned=true;return P4_RNG_UNAVAILABLE;}
 s->busy=true;s->used=true;++s->draws;++s->generation;return P4_RNG_OK;
}
int board_rng_lease_end(board_rng_admission_t *s) {
 if(s->busy || !s->lease)return P4_RNG_OWNERSHIP;
 s->lease=false;s->purpose=0;s->limit=0;
 return s->poisoned?P4_RNG_UNAVAILABLE:P4_RNG_OK;
}
int board_rng_identity_retire(board_rng_admission_t *s,board_rng_state_t *history) {
 if(s->busy){s->poisoned=true;return P4_RNG_OWNERSHIP;}
 board_rng_wipe(history->previous,32);history->have_previous=false;
 s->identity=0;s->operation=0;s->purpose=0;s->draws=0;s->limit=0;s->lease=false;
 return s->poisoned || history->poisoned?P4_RNG_UNAVAILABLE:P4_RNG_OK;
}
bool board_rng_active(const board_rng_snapshot_t *s) {
 return s->readable==15 && s->flags==P4_RNG_ACTIVE;
}
int board_rng_warm_locks(const board_rng_ops_t *o) {
 bool locks[2]={false,false};int status=P4_RNG_OK;
 for(unsigned unit=0;unit<2;++unit){
  if(o->try_lock(o->context,unit)!=0){status=P4_RNG_OWNERSHIP;break;}
  locks[unit]=true;
 }
 for(unsigned unit=2;unit>0;--unit)
  if(locks[unit-1] && o->release_lock(o->context,unit-1)!=0)status=P4_RNG_CLEANUP;
 return status;
}
static int check(const board_rng_ops_t *o,int64_t start,int64_t *last) {
 if(!o->guard(o->context))return P4_RNG_INTERRUPTED;
 const int64_t t=o->now(o->context);
 if(start<0 || t<*last || t-start>=50000)return P4_RNG_TIMEOUT;
 *last=t;return P4_RNG_OK;
}
int board_rng_collect(board_rng_state_t *state,const board_rng_ops_t *o,
 uint8_t *out,size_t capacity,board_rng_report_t *r) {
 memset(r,0,sizeof(*r));r->status=P4_RNG_UNAVAILABLE;
 if(!out || capacity!=32)return r->status=P4_RNG_ARGUMENT;
 const int64_t start=o->start_us;int64_t last=start;
 uint8_t staging[32]={0};bool locks[2]={false,false},bus=false,source=false;
 board_rng_wipe(out,32);
 int status=state->poisoned?P4_RNG_UNAVAILABLE:check(o,start,&last);
 for(unsigned unit=0;unit<2 && status==P4_RNG_OK;++unit) {
  if(o->try_lock(o->context,unit)!=0){status=P4_RNG_OWNERSHIP;break;}
  locks[unit]=true;status=check(o,start,&last);
 }
 if(status==P4_RNG_OK)status=o->snapshot(o->context,false,&r->before);
 if(status==P4_RNG_OK)status=check(o,start,&last);
 // No reset or normalization of an unexpected active owner.
 if(status==P4_RNG_OK && ((r->before.flags&P4_E_TRNG_CLOCK) ||
   ((r->before.readable&P4_BANK_ADC)&&(r->before.flags&(P4_E_TIMER|P4_E_DIGITAL))) ||
   // Helper holds one ANA ref; each REGI2C access temporarily takes one more.
   r->before.analog_refs>253))status=P4_RNG_OWNERSHIP;
 if(status==P4_RNG_OK){o->bus(o->context,true);bus=true;status=check(o,start,&last);}
 if(status==P4_RNG_OK)status=o->snapshot(o->context,false,&r->enabled);
 if(status==P4_RNG_OK && (r->enabled.flags&(P4_E_BUS|P4_E_FUNC|P4_E_RESET_RELEASED))!=
   (P4_E_BUS|P4_E_FUNC|P4_E_RESET_RELEASED))status=P4_RNG_READBACK;
 if(status==P4_RNG_OK)status=check(o,start,&last);
 if(status==P4_RNG_OK){
  o->source(o->context,true);source=true;++r->source_enable_calls;
  status=check(o,start,&last);
 }
 if(status==P4_RNG_OK)status=o->snapshot(o->context,true,&r->enabled);
 if(status==P4_RNG_OK && (!board_rng_active(&r->enabled) ||
   r->enabled.analog_refs!=r->before.analog_refs+o->analog_increment))status=P4_RNG_READBACK;
 bool settled=false;
 if(status==P4_RNG_OK){
  status=check(o,start,&last);const int64_t settle_start=last;
  for(unsigned poll=0;poll<256 && status==P4_RNG_OK;++poll){
   status=check(o,start,&last);if(status!=P4_RNG_OK)break;
   if(last-settle_start>=2000){settled=true;break;}
   o->pause(o->context);
  }
  if(status==P4_RNG_OK && !settled)status=P4_RNG_TIMEOUT;
 }
 for(unsigned i=0;i<8 && status==P4_RNG_OK;++i){
  status=check(o,start,&last);if(status!=P4_RNG_OK)break;
  board_rng_snapshot_t current;
  status=o->snapshot(o->context,true,&current);
  if(status==P4_RNG_OK && (!board_rng_active(&current) ||
    current.analog_refs!=r->before.analog_refs+o->analog_increment))status=P4_RNG_READBACK;
  if(status==P4_RNG_OK)status=check(o,start,&last);
  if(status!=P4_RNG_OK)break;
  uint32_t word=0;size_t got=0;
  status=o->word(o->context,&word,&got);
  if(status==P4_RNG_OK && got!=4)status=P4_RNG_PROVIDER;
  if(status==P4_RNG_OK){memcpy(staging+4*i,&word,4);++r->words;}
  board_rng_wipe((uint8_t*)&word,4);
  if(status==P4_RNG_OK)status=check(o,start,&last);
 }
 if(status==P4_RNG_OK)status=o->snapshot(o->context,true,&r->after);
 if(status==P4_RNG_OK && (!board_rng_active(&r->after) ||
   r->after.analog_refs!=r->before.analog_refs+o->analog_increment))status=P4_RNG_READBACK;
 if(status==P4_RNG_OK){
  bool zero=true,ones=true,repeated=true;
  for(unsigned i=0;i<32;++i){zero=zero&&staging[i]==0;ones=ones&&staging[i]==255;
   if(i>=4 && staging[i]!=staging[i%4])repeated=false;}
  if(zero || ones || repeated || (state->have_previous &&
    memcmp(state->previous,staging,32)==0))status=P4_RNG_HEALTH;
 }
 bool cleanup_ok=true;
 if(source){
  o->source(o->context,false);++r->source_disable_calls;
  if(o->snapshot(o->context,false,&r->rest)!=P4_RNG_OK ||
    !(r->rest.readable&P4_BANK_ADC) || (r->rest.flags&(P4_E_TRNG_CLOCK|P4_E_TIMER|P4_E_DIGITAL)) ||
    r->rest.analog_refs!=r->before.analog_refs)cleanup_ok=false;
 }
 if(bus){o->bus(o->context,false);if(!o->bus_released(o->context))cleanup_ok=false;else r->released=1;}
 for(unsigned unit=2;unit>0;--unit)
  if(locks[unit-1] && o->release_lock(o->context,unit-1)!=0)cleanup_ok=false;
 if(!cleanup_ok){status=P4_RNG_CLEANUP;state->poisoned=true;}
 if(status==P4_RNG_OK)status=check(o,start,&last);
 if(status==P4_RNG_OK){
  memcpy(state->previous,staging,32);state->have_previous=true;
  memcpy(out,staging,32);
 }else{board_rng_wipe(state->previous,32);state->have_previous=false;}
 board_rng_wipe(staging,32);
 // Final deadline/revocation check still precedes return to Rust.
 if(status==P4_RNG_OK){
  status=check(o,start,&last);
  if(status!=P4_RNG_OK){board_rng_wipe(out,32);board_rng_wipe(state->previous,32);state->have_previous=false;}
 }
 const int64_t end=o->now(o->context);
 r->elapsed_us=start>=0&&end>=start?end-start:-1;r->status=status;
 return status;
}
