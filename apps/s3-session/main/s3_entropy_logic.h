// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <cstring>
// This one S3 adapter is an experimental public source, never identity admission.
enum class S3EntropyStatus : int32_t { PublicDraw=0, Argument=-1, Unavailable=-2,
    Ownership=-3, Readback=-4, Timeout=-5, Health=-6, Interrupted=-7, Provider=-8, Cleanup=-9 };
enum : uint32_t { EntropySystem=1,EntropySens=2,EntropyAnalog=4,EntropyDigital=8,EntropyData=16 };
// Active flags are decoded from the named e099 registers, not provider assertions.
enum : uint32_t { E_Rng=1U<<0,E_Rc=1U<<1,E_Bus=1U<<2,E_NoReset=1U<<3,E_DigiClock=1U<<4,
 E_SarClock=1U<<5,E_Power=1U<<6,E_Digital1=1U<<7,E_NoRtc2=1U<<8,E_Timer=1U<<9,
 E_TimerSelect=1U<<10,E_NoStartForce=1U<<11,E_Unlimited=1U<<12,E_Arb=1U<<13,
 E_Double=1U<<14,E_PatternLength=1U<<15 };
constexpr uint32_t S3_ENTROPY_ACTIVE=(1U<<16)-1;
struct S3EntropySnapshot {
    uint32_t readable=0,system_clock=0,system_reset=0,wifi_clock=0,rtc_clock=0;
    uint32_t cpu_hz=0,apb_hz=0,references=0,flags=0,reference_mask=0;
    uint32_t clock_select=0,clock_div=0,sar_div=0,timer_target=0,pattern1=0,pattern2=0;
    uint32_t filter0=0,filter1=0,data1=0,data2=0;
    uint32_t lcd_clock=0,usb_mux=0,pin_signature=0;
};
inline bool s3_entropy_active(const S3EntropySnapshot &s) {
    return s.readable==(EntropySystem|EntropySens|EntropyAnalog|EntropyDigital|EntropyData)&&
      s.references==1&&s.flags==S3_ENTROPY_ACTIVE&&s.reference_mask==3&&
      s.cpu_hz==240000000&&s.apb_hz==80000000&&s.clock_select==2&&s.clock_div==3&&
      s.sar_div==3&&s.timer_target==70&&s.pattern1==0xafffff&&s.pattern2==0xafffff&&
      s.filter0==13&&s.filter1==13;
}
inline bool s3_entropy_rest(const S3EntropySnapshot &s) {
    // Digital/data banks are gated/in reset and are deliberately not validated.
    return s.readable==(EntropySystem|EntropySens|EntropyAnalog)&&s.references==0&&
      !(s.flags&(E_Bus|E_NoReset|E_Power|E_Digital1))&&s.reference_mask==0;
}
struct S3EntropyReport {
    S3EntropySnapshot before,enabled,after,rest;
    int64_t elapsed_us=0;
    uint8_t words=0,progress_before=0,progress_after=0,reserved=0;
    S3EntropyStatus status=S3EntropyStatus::Unavailable;
};
static_assert(sizeof(S3EntropyReport)==384,"private report retains the2048byte diagnostic cap");
// Compact phase evidence: initial read, initial1, observed clear0, fresh1.
enum : uint8_t { ProgressRead=1,ProgressInitialSet=2,ProgressClearZero=4,ProgressFresh=8 };
struct S3EntropyBudget {
    unsigned diagnostic=0,auxiliary=0;
    bool take(bool test){if(test){if(diagnostic>=4)return false;++diagnostic;}
        else{if(auxiliary>=1)return false;++auxiliary;}return true;}
};
struct S3EntropyState {uint8_t previous[32]={};bool have_previous=false,poisoned=false;};
inline void s3_entropy_wipe(uint8_t *p,size_t n) {
    volatile uint8_t *v=p;for(size_t i=0;i<n;++i)v[i]=0;
}
// Private, fixed test seam for this S3 source, never host-supplied callbacks.
struct S3EntropyOps {
    void *context;
    S3EntropyStatus (*claim)(void*,S3EntropySnapshot*);
    S3EntropyStatus (*enable)(void*);
    S3EntropyStatus (*snapshot)(void*,S3EntropySnapshot*);
    S3EntropyStatus (*word)(void*,uint32_t*,size_t*);
    S3EntropyStatus (*cleanup)(void*,bool,S3EntropySnapshot*);
    void (*unlock)(void*);
    int64_t (*now)(void*);
    bool (*interrupted)(void*);
    void (*pause)(void*);
    S3EntropyStatus (*timer)(void*,bool);
    S3EntropyStatus (*completion)(void*,bool,bool*);
};
inline S3EntropyStatus s3_entropy_collect(S3EntropyState &state,const S3EntropyOps &o,
    uint8_t *destination,size_t capacity,size_t *written,S3EntropyReport &report) {
    report=S3EntropyReport{};
    if(!destination||capacity!=32||!written){report.status=S3EntropyStatus::Argument;return report.status;}
    *written=0;
    // One real budget includes claim, enable, settle, both witnesses and cleanup.
    const int64_t start=o.now(o.context);int64_t last=start;
    s3_entropy_wipe(destination,32);
    uint8_t staging[32]={};bool owned=false,attempted=false;
    auto check=[&](){
        if(o.interrupted(o.context))return S3EntropyStatus::Interrupted;
        const int64_t t=o.now(o.context);
        if(t<0||t<last||start<0||t-start>=50000)return S3EntropyStatus::Timeout;
        last=t;return S3EntropyStatus::PublicDraw;
    };
    auto status=o.claim(o.context,&report.before);
    if(status!=S3EntropyStatus::PublicDraw){
        const int64_t end=o.now(o.context);report.elapsed_us=start>=0&&end>=start?end-start:-1;
        report.status=status;return status;
    }
    owned=true;
    auto progress=[&](uint8_t &phase){
        auto result=check();bool set=false;
        if(result==S3EntropyStatus::PublicDraw)result=o.completion(o.context,false,&set);
        if(result==S3EntropyStatus::PublicDraw){phase=ProgressRead|(set?ProgressInitialSet:0);result=check();}
        if(result==S3EntropyStatus::PublicDraw)result=o.timer(o.context,false);
        if(result==S3EntropyStatus::PublicDraw)result=check();
        if(result==S3EntropyStatus::PublicDraw)result=o.completion(o.context,true,&set);
        if(result==S3EntropyStatus::PublicDraw)result=check();
        if(result==S3EntropyStatus::PublicDraw){
            if(set)result=S3EntropyStatus::Readback;
            else phase|=ProgressClearZero;
        }
        if(result==S3EntropyStatus::PublicDraw)result=o.timer(o.context,true);
        if(result==S3EntropyStatus::PublicDraw)result=check();
        for(unsigned poll=0;poll<256&&result==S3EntropyStatus::PublicDraw;++poll){
            result=o.completion(o.context,false,&set);
            if(result==S3EntropyStatus::PublicDraw)result=check();
            if(result!=S3EntropyStatus::PublicDraw)break;
            if(set){phase|=ProgressFresh;break;}
            o.pause(o.context);
        }
        // Completion after an observed0 can be from an in-flight conversion.
        // It is a liveness witness, not a guarantee about ADC2 or noise quality.
        if(result==S3EntropyStatus::PublicDraw&&!(phase&ProgressFresh))result=S3EntropyStatus::Timeout;
        return result;
    };
    if(state.poisoned)status=S3EntropyStatus::Unavailable;
    else status=check();
    if(status==S3EntropyStatus::PublicDraw){attempted=true;status=o.enable(o.context);}
    if(status==S3EntropyStatus::PublicDraw)status=check();
    if(status==S3EntropyStatus::PublicDraw)status=o.snapshot(o.context,&report.enabled);
    if(status==S3EntropyStatus::PublicDraw&&!s3_entropy_active(report.enabled))status=S3EntropyStatus::Readback;
    // Nominal settle window only, finite polls and the same real monotonic clock.
    bool settled=false;
    if(status==S3EntropyStatus::PublicDraw){
        const int64_t settle_start=last;
        for(unsigned poll=0;poll<256;++poll){
            status=check();if(status!=S3EntropyStatus::PublicDraw)break;
            if(last-settle_start>=2000){settled=true;break;}o.pause(o.context);
        }
        if(status==S3EntropyStatus::PublicDraw&&!settled)status=S3EntropyStatus::Timeout;
    }
    if(status==S3EntropyStatus::PublicDraw)status=progress(report.progress_before);
    for(unsigned i=0;i<8&&status==S3EntropyStatus::PublicDraw;++i){
        status=check();if(status!=S3EntropyStatus::PublicDraw)break;
        S3EntropySnapshot current;status=o.snapshot(o.context,&current);
        if(status!=S3EntropyStatus::PublicDraw)break;
        if(!s3_entropy_active(current)){status=S3EntropyStatus::Readback;break;}
        status=check();if(status!=S3EntropyStatus::PublicDraw)break;
        uint32_t word=0;size_t got=0;status=o.word(o.context,&word,&got);
        if(status!=S3EntropyStatus::PublicDraw){s3_entropy_wipe(reinterpret_cast<uint8_t*>(&word),4);break;}
        if(got!=4){s3_entropy_wipe(reinterpret_cast<uint8_t*>(&word),4);status=S3EntropyStatus::Provider;break;}
        std::memcpy(staging+4*i,&word,4);s3_entropy_wipe(reinterpret_cast<uint8_t*>(&word),4);++report.words;
        status=check();
    }
    if(status==S3EntropyStatus::PublicDraw)status=progress(report.progress_after);
    if(status==S3EntropyStatus::PublicDraw)status=o.snapshot(o.context,&report.after);
    if(status==S3EntropyStatus::PublicDraw&&!s3_entropy_active(report.after))status=S3EntropyStatus::Readback;
    if(status==S3EntropyStatus::PublicDraw){
        bool repeated_word=true,zero=true,ones=true;
        for(unsigned i=0;i<32;++i){zero=zero&&staging[i]==0;ones=ones&&staging[i]==255;
            if(i>=4&&staging[i]!=staging[i%4])repeated_word=false;}
        if(zero||ones||repeated_word||(state.have_previous&&std::memcmp(staging,state.previous,32)==0))status=S3EntropyStatus::Health;
    }
    if(owned){
        const auto cleanup=o.cleanup(o.context,attempted,&report.rest);
        if(cleanup!=S3EntropyStatus::PublicDraw||!s3_entropy_rest(report.rest)){
            status=S3EntropyStatus::Cleanup;state.poisoned=true;
        }
        if(status==S3EntropyStatus::PublicDraw)status=check();
        if(status==S3EntropyStatus::PublicDraw){
            std::memcpy(state.previous,staging,32);state.have_previous=true;
            std::memcpy(destination,staging,32);*written=32;
        }else{s3_entropy_wipe(state.previous,32);state.have_previous=false;}
        s3_entropy_wipe(staging,32);
        const int64_t end=o.now(o.context);report.elapsed_us=start>=0&&end>=start?end-start:-1;
        report.status=status;o.unlock(o.context);
    }
    return status;
}
