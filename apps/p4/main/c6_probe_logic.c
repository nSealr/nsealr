// SPDX-License-Identifier: MIT
#include "c6_probe.h"
#include <string.h>
static bool identity_valid(const p4_c6_identity_t *i) {
    return i->manufacturer==0x0092 && i->device==0x6666 && i->functions>=1 && i->functions<=7 &&
        i->cccr!=0xff && i->cis_used>=7 && i->cis_used<=P4_C6_CIS_MAX;
}
static bool pad_low(const p4_c6_pad_t *p) {return p->input && p->output && p->level==0;}
static bool pad_high(const p4_c6_pad_t *p) {return p->input && !p->output && p->level==1;}
static bool alive(const p4_c6_ops_t *o,p4_c6_result_t *r) {
    int64_t t=o->now();
    if(t<0 || (uint64_t)t<r->last_ms || (uint64_t)t-r->start_ms>=P4_C6_PROBE_MS) {
        r->primary_error=-100;r->outcome=P4_C6_INCONCLUSIVE;return false;
    }
    r->last_ms=(uint64_t)t;return true;
}
static bool stage(const p4_c6_ops_t *o,p4_c6_result_t *r,unsigned phase) {
    r->phase=phase;if(!alive(o,r))return false;o->report(r);return alive(o,r);
}
bool p4_c6_parse_cis(const uint8_t *b,size_t n,p4_c6_identity_t *id) {
    if(!b || !id || !n || n>P4_C6_CIS_MAX)return false;
    bool manfid=false;size_t at=0;
    for(unsigned tuple=0;tuple<64 && at<n;tuple++) {
        uint8_t code=b[at++];if(code==0)continue;
        if(code==0xff) {id->cis_used=(uint16_t)at;return manfid;}
        if(at>=n)return false;
        size_t len=b[at++];if(len>n-at)return false;
        if(code==0x20) {
            if(manfid || len!=4)return false;
            id->manufacturer=(uint16_t)(b[at]|((uint16_t)b[at+1]<<8));
            id->device=(uint16_t)(b[at+2]|((uint16_t)b[at+3]<<8));manfid=true;
            // Pinned IDF6.0.2 C6 HINF_CFG_DATA0 defaults: user146/device26214.
            // These are configurable generic endpoint IDs, not a silicon ID.
            if(id->manufacturer!=0x0092 || id->device!=0x6666)return false;
        }
        at+=len;
    }
    return false;
}
void p4_c6_run(const p4_c6_ops_t *o,p4_c6_result_t *r,uint64_t start_ms) {
    memset(r,0,sizeof(*r));r->outcome=P4_C6_UNAVAILABLE;
    r->initial.level=r->low.level=r->release.level=r->final.level=-1;
    r->first_low=r->last_low=P4_C6_OTHER_ERROR;
    r->start_ms=r->last_ms=start_ms;
    int64_t t=o->now();if(t<0 || (uint64_t)t<start_ms || start_ms>UINT64_MAX-P4_C6_PROBE_MS) {r->primary_error=-100;r->outcome=P4_C6_INCONCLUSIVE;return;}
    if(!stage(o,r,1))goto done;
    r->primary_error=o->prepare();if(r->primary_error || !alive(o,r))goto done;
    r->pad_error=o->pad(&r->initial);if(r->pad_error || !pad_high(&r->initial) || !alive(o,r))goto done;
    r->primary_error=o->identity(&r->identity);if(r->primary_error || !alive(o,r) || !identity_valid(&r->identity))goto done;
    r->baseline=true;r->outcome=P4_C6_INCONCLUSIVE;
    if(!stage(o,r,2))goto done;
    r->low_attempted=true; // Even a partial/failed low call requires cleanup.
    r->primary_error=o->low();if(r->primary_error)goto failed;
    if(!alive(o,r))goto done;
    o->wait(10);if(!alive(o,r))goto done;
    r->pad_error=o->pad(&r->low);if(r->pad_error || !pad_low(&r->low))goto failed;
    if(!alive(o,r))goto done;
    r->first_low=o->read();if(!alive(o,r))goto done;
    if(r->first_low!=P4_C6_TIMED_OUT) {r->outcome=r->first_low==P4_C6_VALID?P4_C6_FAILED:P4_C6_INCONCLUSIVE;goto done;}
    if(!stage(o,r,3))goto done;
    r->primary_error=o->release();if(r->primary_error)goto failed;
    if(!alive(o,r))goto done;
    r->released=true;o->wait(1500);if(!alive(o,r))goto done;
    r->pad_error=o->pad(&r->release);if(r->pad_error || !pad_high(&r->release))goto failed;
    if(!alive(o,r))goto done;
    p4_c6_identity_t recovery={0};
    r->primary_error=o->identity(&recovery);if(r->primary_error || !alive(o,r))goto done;
    if(!identity_valid(&recovery) || recovery.manufacturer!=r->identity.manufacturer || recovery.device!=r->identity.device ||
       recovery.cccr!=r->identity.cccr || recovery.functions!=r->identity.functions ||
       recovery.cis_used!=r->identity.cis_used)goto failed;
    r->recovered=true;
    if(!stage(o,r,4))goto done;
    r->primary_error=o->low();if(r->primary_error)goto failed;
    if(!alive(o,r))goto done;
    o->wait(10);if(!alive(o,r))goto done;
    p4_c6_pad_t p={.level=-1};r->pad_error=o->pad(&p);
    if(r->pad_error || !pad_low(&p))goto failed;
    if(!alive(o,r))goto done;
    r->last_low=o->read();if(!alive(o,r))goto done;
    if(r->last_low!=P4_C6_TIMED_OUT) {r->outcome=r->last_low==P4_C6_VALID?P4_C6_FAILED:P4_C6_INCONCLUSIVE;goto done;}
    r->outcome=P4_C6_OBSERVED;goto done;
failed:
    r->outcome=P4_C6_FAILED;
done:
    // Best effort on EVERY returning path after low admission, independent of
    // the original failure/deadline. No safe-cleanup claim on an error/readback.
    if(r->low_attempted) {
        r->cleanup_error=o->low();o->wait(10);
        r->pad_error=o->pad(&r->final);
        if(r->cleanup_error || r->pad_error || !pad_low(&r->final))r->outcome=P4_C6_CLEANUP_FAILED;
    } else r->pad_error=o->pad(&r->final);
    t=o->now();if(t>=0)r->end_ms=(uint64_t)t;
    r->phase=5;o->report(r);
}
