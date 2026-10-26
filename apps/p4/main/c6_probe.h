// SPDX-License-Identifier: MIT
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define P4_C6_CIS_MAX 256U
#define P4_C6_PROBE_MS 20000U
// This is a public peripheral probe, with no key/approval entry point.
typedef struct {uint16_t manufacturer,device;uint8_t cccr,functions;uint16_t cis_used;} p4_c6_identity_t;
typedef struct {int level;bool input,output;uint32_t function,signal;} p4_c6_pad_t;
typedef enum {P4_C6_VALID=0,P4_C6_TIMED_OUT=1,P4_C6_OTHER_ERROR=2} p4_c6_reply_t;
typedef enum {P4_C6_UNAVAILABLE=0,P4_C6_OBSERVED=1,P4_C6_INCONCLUSIVE=2,P4_C6_FAILED=3,P4_C6_CLEANUP_FAILED=4} p4_c6_outcome_t;
typedef struct {
    p4_c6_outcome_t outcome;unsigned phase;
    bool baseline,low_attempted,released,recovered;
    int primary_error,cleanup_error,pad_error;
    p4_c6_reply_t first_low,last_low;
    p4_c6_identity_t identity;
    p4_c6_pad_t initial,low,release,final;
    uint64_t start_ms,last_ms,end_ms;
} p4_c6_result_t;
// Fixed internal product adapter; not host supplied, no consent semantics.
typedef struct {
    int64_t (*now)(void);
    int (*prepare)(void);
    int (*identity)(p4_c6_identity_t *);
    int (*low)(void);
    int (*release)(void);
    int (*pad)(p4_c6_pad_t *);
    p4_c6_reply_t (*read)(void);
    void (*wait)(uint32_t);
    void (*report)(const p4_c6_result_t *);
} p4_c6_ops_t;
bool p4_c6_parse_cis(const uint8_t *,size_t,p4_c6_identity_t *);
void p4_c6_run(const p4_c6_ops_t *,p4_c6_result_t *,uint64_t start_ms);
_Noreturn void p4_c6_public_probe(void);
void p4_c6_before_abort(void);
