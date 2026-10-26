// SPDX-License-Identifier: MIT
#include "../main/p4_entropy_logic.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);abort();}}while(0)
enum fault {OK,LOCK1,LOCK2,INITIAL_TRNG,INITIAL_DIGITAL,BUS_ENABLE,ENABLE,READBACK,
 WORD_ERROR,WORD_ZERO_COUNT,WORD_SHORT,WORD_LONG,ZERO,ONES,STUCK,FOREIGN_REF,
 CLEANUP,BUS_FREE,RELEASE1,RELEASE2,TIME_LOCK,TIME_ENABLE,TIME_WORD,TIME_CLEANUP,
 CLOCK_BACK,FROZEN,GUARD_BEFORE,GUARD_WORD,GUARD_AFTER};
typedef struct {
 enum fault fault;bool locks[2],source,bad_bus;
 unsigned attempts[2],releases[2],bus_count,bus_claims,bus_frees,enabled,disabled,words,pauses;
 uint32_t refs,baseline,peak,seed;
 int64_t time;
} mock_t;
static mock_t mock(enum fault f){mock_t m={0};m.fault=f;m.time=100;m.refs=m.baseline=2;return m;}
static int try_lock(void *p,unsigned unit){
 mock_t *m=p;CHECK(unit<2);++m->attempts[unit];CHECK(!m->locks[unit]);
 if((m->fault==LOCK1 && unit==0)||(m->fault==LOCK2 && unit==1))return -1;
 m->locks[unit]=true;
 if(m->fault==TIME_LOCK && unit==0)m->time+=50000;
 return 0;
}
static int release_lock(void *p,unsigned unit){
 mock_t *m=p;CHECK(unit<2 && m->locks[unit]);m->locks[unit]=false;++m->releases[unit];
 return (m->fault==RELEASE1 && unit==0)||(m->fault==RELEASE2 && unit==1)?-1:0;
}
static void bus(void *p,bool on){
 mock_t *m=p;CHECK(m->locks[0]&&m->locks[1]);
 if(on){++m->bus_count;++m->bus_claims;
 if(m->fault==BUS_ENABLE)m->bad_bus=true;}
 else{CHECK(m->bus_count);--m->bus_count;++m->bus_frees;}
}
static bool released(void *p){mock_t *m=p;return !m->bus_count&&m->fault!=BUS_FREE;}
static void source(void *p,bool on){
 mock_t *m=p;CHECK(m->locks[0]&&m->locks[1]&&m->bus_count);
 if(on){
  CHECK(!m->source);m->source=true;++m->enabled;++m->refs;
  // Exact SDK helper holds one ref; each REGI2C call temporarily holds another.
  ++m->refs;m->peak=m->refs;--m->refs;
  if(m->fault==TIME_ENABLE)m->time+=50000;
 }else{
  CHECK(m->source&&m->refs);m->source=false;++m->disabled;--m->refs;
  if(m->fault==TIME_CLEANUP)m->time+=50000;
 }
}
static int snapshot(void *p,bool analog,p4_entropy_snapshot_t *s){
 mock_t *m=p;memset(s,0,sizeof(*s));s->readable=P4_BANK_SYSTEM;s->analog_refs=m->refs;
 if(m->bus_count&&!m->bad_bus){s->readable|=P4_BANK_ADC;s->flags=P4_E_BUS|P4_E_FUNC|P4_E_RESET_RELEASED;}
 if(analog){
  CHECK(m->source);s->readable=15;s->flags=P4_RNG_ACTIVE;
  // Constant sample counter remains diagnostic and never gates success.
  s->trng_cfg=0;s->calibration=2166;s->reference=1;
  if(m->fault==ENABLE)s->flags&=~P4_E_SAMPLE;
  if(m->fault==READBACK && m->words>=3)s->flags&=~P4_E_TIMER;
 }else if(!m->enabled){
  if(m->fault==INITIAL_TRNG)s->flags|=P4_E_TRNG_CLOCK;
  if(m->fault==INITIAL_DIGITAL){s->readable|=P4_BANK_ADC;s->flags|=P4_E_DIGITAL;}
 }else if(m->fault==CLEANUP)s->flags|=P4_E_TRNG_CLOCK;
 return P4_RNG_OK;
}
static int word(void *p,uint32_t *out,size_t *n){
 mock_t *m=p;CHECK(m->source&&m->locks[0]&&m->locks[1]&&m->bus_count);
 ++m->words;*n=4;*out=0x10203040U+m->seed+m->words*0x01010101U;
 if(m->fault==ZERO)*out=0;
 if(m->fault==ONES)*out=UINT32_MAX;
 if(m->fault==STUCK)*out=0x55555555;
 if(m->words==3){
  if(m->fault==WORD_ERROR)return P4_RNG_PROVIDER;
  if(m->fault==WORD_ZERO_COUNT)*n=0;
 if(m->fault==WORD_SHORT)*n=3;
 if(m->fault==WORD_LONG)*n=5;
  if(m->fault==FOREIGN_REF)++m->refs;
  if(m->fault==TIME_WORD)m->time+=50000;
  if(m->fault==CLOCK_BACK)m->time=0;
 }
 return P4_RNG_OK;
}
static bool guard(void *p){
 mock_t *m=p;return m->fault!=GUARD_BEFORE && !(m->fault==GUARD_WORD&&m->words>=3) &&
  !(m->fault==GUARD_AFTER&&m->disabled);
}
static int64_t now(void *p){return ((mock_t*)p)->time;}
static void pause_source(void *p){mock_t *m=p;++m->pauses;
 if(m->fault!=FROZEN)m->time+=20;}
static p4_entropy_ops_t ops(mock_t *m){
 const p4_entropy_ops_t o={.context=m,.try_lock=try_lock,.release_lock=release_lock,.bus=bus,
 .bus_released=released,.source=source,.snapshot=snapshot,.word=word,.guard=guard,
 .now=now,.pause=pause_source,.analog_increment=1,.start_us=m->time};return o;
}
typedef struct {uint8_t before[16],data[32],after[16];} guarded_t;
static guarded_t guarded(void){guarded_t g;memset(&g,0xa7,sizeof(g));return g;}
static void guards(const guarded_t *g){for(unsigned i=0;i<16;++i){CHECK(g->before[i]==0xa7);CHECK(g->after[i]==0xa7);}}
static void zero(const uint8_t *data){for(unsigned i=0;i<32;++i)CHECK(data[i]==0);}
int main(void){
 CHECK(sizeof(p4_entropy_report_t)<=512);
 p4_entropy_snapshot_t a={.readable=15,.flags=P4_RNG_ACTIVE};CHECK(p4_entropy_active(&a));
 for(unsigned bit=0;bit<21;++bit){p4_entropy_snapshot_t b=a;b.flags^=1U<<bit;CHECK(!p4_entropy_active(&b));}
 for(unsigned mask=0;mask<15;++mask){p4_entropy_snapshot_t b=a;b.readable=mask;CHECK(!p4_entropy_active(&b));}
 p4_entropy_admission_t adm={0};CHECK(p4_entropy_admit(&adm,true)==P4_RNG_OWNERSHIP);
 adm.bound=true;CHECK(p4_entropy_admit(&adm,false)==P4_RNG_OWNERSHIP);CHECK(!adm.used&&!adm.busy);
 CHECK(p4_entropy_admit(&adm,true)==P4_RNG_OK);CHECK(adm.used&&adm.busy&&adm.generation==1);
 CHECK(p4_entropy_admit(&adm,true)==P4_RNG_OWNERSHIP);CHECK(adm.generation==1);
 adm.busy=false;CHECK(p4_entropy_admit(&adm,true)==P4_RNG_UNAVAILABLE);CHECK(adm.generation==1);
 adm=(p4_entropy_admission_t){.bound=true,.generation=UINT32_MAX};
 CHECK(p4_entropy_admit(&adm,true)==P4_RNG_UNAVAILABLE&&adm.poisoned&&!adm.busy);
 adm.generation=0;CHECK(p4_entropy_admit(&adm,true)==P4_RNG_UNAVAILABLE);
 for(enum fault fault=OK;fault<=GUARD_AFTER;++fault){
  mock_t m=mock(fault);p4_entropy_state_t state={0};p4_entropy_report_t r;guarded_t g=guarded();p4_entropy_ops_t o=ops(&m);
  const int status=p4_entropy_collect(&state,&o,g.data,32,&r);guards(&g);
  CHECK(!m.locks[0]&&!m.locks[1]&&!m.source&&m.bus_count==0);
  CHECK(m.enabled==m.disabled&&m.bus_claims==m.bus_frees);
  if(fault==OK){CHECK(status==P4_RNG_OK&&r.words==8&&m.words==8&&state.have_previous&&r.released==1);}
  else{CHECK(status!=P4_RNG_OK&&!state.have_previous);zero(g.data);zero(state.previous);}
  CHECK(m.refs==m.baseline+(fault==FOREIGN_REF?1U:0U));
  if(fault==LOCK1)CHECK(!m.releases[0]&&!m.releases[1]&&!m.bus_claims);
  if(fault==LOCK2)CHECK(m.releases[0]==1&&!m.releases[1]&&!m.bus_claims);
  if(fault==INITIAL_TRNG||fault==INITIAL_DIGITAL)CHECK(!m.bus_claims&&!m.enabled);
  if(fault==BUS_ENABLE)CHECK(!m.enabled&&status==P4_RNG_READBACK);
  if(fault==FOREIGN_REF||fault==CLEANUP||fault==BUS_FREE||fault==RELEASE1||fault==RELEASE2)
   CHECK(state.poisoned&&status==P4_RNG_CLEANUP);
  if(fault==TIME_LOCK)CHECK(!m.bus_claims&&!m.enabled&&status==P4_RNG_TIMEOUT);
  if(fault==FROZEN)CHECK(m.pauses==256&&!m.words&&status==P4_RNG_TIMEOUT);
  if(fault==ZERO||fault==ONES||fault==STUCK)CHECK(status==P4_RNG_HEALTH&&r.words==8);
  if(fault==TIME_CLEANUP)CHECK(r.elapsed_us>=50000&&status==P4_RNG_TIMEOUT);
  if(fault==GUARD_BEFORE)CHECK(!m.attempts[0]&&!m.enabled);
 }
 // Shared analog users retain their own count; reserve the SDK transient ref.
 for(unsigned base=0;base<=255;++base){
  if(base!=0&&base!=2&&base!=253&&base!=254&&base!=255)continue;
  mock_t m=mock(OK);m.refs=m.baseline=base;p4_entropy_state_t state={0};p4_entropy_report_t r;
  guarded_t g=guarded();p4_entropy_ops_t o=ops(&m);
  int status=p4_entropy_collect(&state,&o,g.data,32,&r);guards(&g);CHECK(m.refs==base);
  if(base<=253)CHECK(status==P4_RNG_OK&&m.peak==base+2);
  else{CHECK(status==P4_RNG_OWNERSHIP&&!m.bus_claims&&!m.enabled);zero(g.data);}
 }
 p4_entropy_state_t history={0};mock_t first=mock(OK);p4_entropy_report_t r;guarded_t g=guarded();p4_entropy_ops_t o=ops(&first);
 CHECK(p4_entropy_collect(&history,&o,g.data,32,&r)==P4_RNG_OK);
 mock_t same=mock(OK);o=ops(&same);CHECK(p4_entropy_collect(&history,&o,g.data,32,&r)==P4_RNG_HEALTH);zero(g.data);guards(&g);
 mock_t fresh=mock(OK);fresh.seed=3;o=ops(&fresh);CHECK(p4_entropy_collect(&history,&o,g.data,32,&r)==P4_RNG_OK);
 for(size_t cap=0;cap<=33;++cap){
  if(cap==32)continue;
  mock_t m=mock(OK);o=ops(&m);g=guarded();
  CHECK(p4_entropy_collect(&history,&o,g.data,cap,&r)==P4_RNG_ARGUMENT);
  CHECK(!m.attempts[0]&&!m.bus_claims&&!m.enabled);for(unsigned i=0;i<32;++i)CHECK(g.data[i]==0xa7);guards(&g);
 }
 mock_t poisoned=mock(OK);o=ops(&poisoned);history.poisoned=true;g=guarded();
 CHECK(p4_entropy_collect(&history,&o,g.data,32,&r)==P4_RNG_UNAVAILABLE);CHECK(!poisoned.attempts[0]);zero(g.data);guards(&g);
 printf("PASS P4 public entropy: %u checks; actual lease/admission/collection policies, full guards; not hardware evidence\n",checks);
}
