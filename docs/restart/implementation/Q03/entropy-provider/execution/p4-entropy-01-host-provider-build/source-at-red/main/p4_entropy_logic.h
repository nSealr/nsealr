// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
enum { P4_RNG_OK=0,P4_RNG_ARGUMENT=-1,P4_RNG_UNAVAILABLE=-2,P4_RNG_OWNERSHIP=-3,
 P4_RNG_READBACK=-4,P4_RNG_TIMEOUT=-5,P4_RNG_HEALTH=-6,P4_RNG_INTERRUPTED=-7,
 P4_RNG_PROVIDER=-8,P4_RNG_CLEANUP=-9 };
enum { P4_BANK_SYSTEM=1,P4_BANK_TRNG=2,P4_BANK_ADC=4,P4_BANK_ANALOG=8 };
enum { P4_E_BUS=1U<<0,P4_E_FUNC=1U<<1,P4_E_RESET_RELEASED=1U<<2,
 P4_E_XTAL=1U<<3,P4_E_DIV0=1U<<4,P4_E_SAR_DIV15=1U<<5,
 P4_E_TIMER=1U<<6,P4_E_TIMER_SELECT=1U<<7,P4_E_TARGET100=1U<<8,
 P4_E_PATTERN_LEN=1U<<9,P4_E_PATTERN=1U<<10,P4_E_DIGITAL=1U<<11,
 P4_E_POWER=1U<<12,P4_E_CAL2166=1U<<13,P4_E_REFERENCE=1U<<14,
 P4_E_TRNG_CLOCK=1U<<15,P4_E_TRNG_RESET=1U<<16,P4_E_SAMPLE=1U<<17,
 P4_E_XOR_TIMER=1U<<18,P4_E_PSCALE255=1U<<19,P4_E_CPU_XTAL=1U<<20 };
#define P4_RNG_ACTIVE ((1U<<21)-1)
typedef struct {
 uint32_t readable,flags,cpu_hz,apb_hz,xtal_hz,analog_refs;
 uint32_t trng_cfg,trng_date,trng_reset,adc_ctrl,adc_ctrl2;
 uint32_t clock_source,clock_div,clock_bus,reset_adc,pattern,calibration,reference;
} p4_entropy_snapshot_t;
typedef struct {
 p4_entropy_snapshot_t before,enabled,after,rest;
 int64_t elapsed_us;
 int32_t status;
 uint32_t words,source_enable_calls,source_disable_calls,released;
} p4_entropy_report_t;
_Static_assert(sizeof(p4_entropy_report_t)<=512,"bounded INTERNAL public report");
typedef struct { uint8_t previous[32];bool have_previous,poisoned; } p4_entropy_state_t;
typedef struct { uint32_t generation;bool bound,busy,used,poisoned; } p4_entropy_admission_t;
int p4_entropy_admit(p4_entropy_admission_t*,bool correct_worker);
// Fixed private seam for this P4 provider, not runtime source selection.
typedef struct {
 void *context;
 int (*try_lock)(void*,unsigned);
 int (*release_lock)(void*,unsigned);
 void (*bus)(void*,bool);
 bool (*bus_released)(void*);
 void (*source)(void*,bool);
 int (*snapshot)(void*,bool,p4_entropy_snapshot_t*);
 int (*word)(void*,uint32_t*,size_t*);
 bool (*guard)(void*);
 int64_t (*now)(void*);
 void (*pause)(void*);
 uint32_t analog_increment;
 int64_t start_us;
} p4_entropy_ops_t;
void p4_entropy_wipe(uint8_t*,size_t);
bool p4_entropy_active(const p4_entropy_snapshot_t*);
int p4_entropy_collect(p4_entropy_state_t*,const p4_entropy_ops_t*,uint8_t*,size_t,p4_entropy_report_t*);
