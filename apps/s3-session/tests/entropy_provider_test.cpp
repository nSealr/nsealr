// SPDX-License-Identifier: MIT
#include "../main/s3_entropy_logic.h"
#include "../main/s3_entropy_rcc.h"
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
static unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"line %d: %s\n",__LINE__,#x);std::abort();}}while(0)
struct Rcc {
    uint8_t count=0;bool locked=false,on=false;unsigned enters=0,exits=0,writes=0;
    uint8_t acquire_enter(){CHECK(!locked);locked=true;++enters;return count;}
    uint8_t release_enter(){CHECK(!locked);locked=true;++enters;return uint8_t(count-1);}
    void exit(){CHECK(locked);locked=false;++exits;}
    void acquire_exit(uint8_t n){CHECK(locked);count=uint8_t(n+1);exit();}
    void release_exit(uint8_t n){CHECK(locked);count=n;exit();}
    bool inactive(){CHECK(locked);return !on;}
    void enable_clock(){CHECK(locked);on=true;++writes;}
    void disable_clock(){CHECK(locked);on=false;++writes;}
};
static S3EntropySnapshot active(){
    S3EntropySnapshot s;s.readable=31;s.references=1;s.flags=S3_ENTROPY_ACTIVE;s.reference_mask=3;
    s.cpu_hz=240000000;s.apb_hz=80000000;s.clock_select=2;s.clock_div=s.sar_div=3;
    s.timer_target=70;s.pattern1=s.pattern2=0xafffff;s.filter0=s.filter1=13;s.data1=11;s.data2=21;return s;
}
enum class Fault {None,Busy,Error,Short,Oversize,Zero,Ones,Stuck,StableData,Readback,Ownership,ClockBack,Timeout,FrozenClock,Interrupt,Cleanup,Enable,InitialDone,ClearStuckBefore,ClearStuckAfter,MissingBefore,MissingAfter,StopBefore,RestoreBefore,RestoreAfter,OwnerAtClear,InterruptAtClear,ClockBackAtClear,DeadlineAtClear,CumulativeDeadline,FrozenBefore,FrozenAfter,ClaimTimeout,EnableTimeout};
struct Mock {
    Rcc rcc;Fault fault=Fault::None;bool busy=false;unsigned enabled=0,cleaned=0,unlocked=0,words=0,pauses=0,snapshots=0;
    int64_t time=100;uint32_t seed=0;
    bool timer_on=false,done=false,waiting=false,cancel=false;unsigned clears=0,polls=0,timer_writes=0;
    static Mock &m(void *p){return *static_cast<Mock*>(p);}
    static S3EntropyStatus claim(void *p,S3EntropySnapshot *before){auto &s=m(p);
        if(s.busy||s.fault==Fault::Busy)return S3EntropyStatus::Ownership;
        s.busy=true;before->references=s.rcc.count;if(s.fault==Fault::ClaimTimeout)s.time+=50000;
        const auto status=s3_entropy_rcc_claim(s.rcc);if(status!=S3EntropyStatus::PublicDraw)s.busy=false;return status;}
    static S3EntropyStatus enable(void *p){auto &s=m(p);++s.enabled;
        if(s.fault==Fault::Enable)return S3EntropyStatus::Provider;
        s.timer_on=true;s.done=s.fault==Fault::InitialDone;
        if(s.fault==Fault::EnableTimeout)s.time+=50000;
        return s3_entropy_rcc_gate(s.rcc);}
    static S3EntropyStatus snapshot(void *p,S3EntropySnapshot *out){auto &s=m(p);++s.snapshots;
        *out=active();out->references=s.rcc.count;
        if(s.fault==Fault::StableData)out->data1=out->data2=0x14000;
        else{out->data1+=s.words;out->data2+=s.words;}
        if(!s.timer_on)out->flags&=~E_Timer;
        if(s.fault==Fault::Readback&&s.words>=3)out->flags&=~E_Timer;
        return S3EntropyStatus::PublicDraw;}
    static S3EntropyStatus word(void *p,uint32_t *out,size_t *n){auto &s=m(p);CHECK(s.timer_on);CHECK(s.clears==1);++s.words;*n=4;
        *out=0x10203040U+s.seed+s.words*0x01010101U;
        if(s.fault==Fault::Zero)*out=0;
        if(s.fault==Fault::Ones)*out=UINT32_MAX;
        if(s.fault==Fault::Stuck)*out=0x55555555;
        if(s.words==3){
            if(s.fault==Fault::Error)return S3EntropyStatus::Provider;
            if(s.fault==Fault::Short)*n=3;
            if(s.fault==Fault::Oversize)*n=5;
            if(s.fault==Fault::Ownership)s.rcc.count=2;
            if(s.fault==Fault::ClockBack)s.time=0;
            if(s.fault==Fault::Timeout)s.time+=50000;
        }
        return S3EntropyStatus::PublicDraw;}
    static S3EntropyStatus cleanup(void *p,bool,S3EntropySnapshot *rest){auto &s=m(p);++s.cleaned;s.timer_on=false;
        const auto status=s3_entropy_rcc_release(s.rcc);
        *rest=S3EntropySnapshot{};rest->readable=7;rest->references=s.rcc.count;
        if(s.fault==Fault::Cleanup)rest->flags=E_Power;
        return status;}
    static void unlock(void *p){auto &s=m(p);CHECK(s.busy);s.busy=false;++s.unlocked;}
    static int64_t now(void *p){return m(p).time;}
    static bool interrupted(void *p){auto &s=m(p);return s.cancel||(s.fault==Fault::Interrupt&&s.words>=3);}
    static void pause(void *p){auto &s=m(p);++s.pauses;
        if(s.fault!=Fault::FrozenClock&&!(s.fault==Fault::FrozenBefore&&s.clears==1)&&
           !(s.fault==Fault::FrozenAfter&&s.clears==2))s.time+=20;}
    static S3EntropyStatus timer(void *p,bool on){auto &s=m(p);++s.timer_writes;s.timer_on=on;
        if((!on&&s.fault==Fault::StopBefore&&s.clears==0)||
           (on&&s.fault==Fault::RestoreBefore&&s.clears==1)||
           (on&&s.fault==Fault::RestoreAfter&&s.clears==2))return S3EntropyStatus::Readback;
        if(on){s.waiting=true;s.polls=0;}return S3EntropyStatus::PublicDraw;}
    static S3EntropyStatus completion(void *p,bool clear,bool *set){auto &s=m(p);
        if(clear){
            CHECK(!s.timer_on);++s.clears;
            if(s.fault==Fault::OwnerAtClear){s.rcc.count=2;return S3EntropyStatus::Ownership;}
            s.done=(s.fault==Fault::ClearStuckBefore&&s.clears==1)||(s.fault==Fault::ClearStuckAfter&&s.clears==2);
            if(s.fault==Fault::InterruptAtClear)s.cancel=true;
            if(s.fault==Fault::ClockBackAtClear)s.time=0;
            if(s.fault==Fault::DeadlineAtClear)s.time+=50000;
        }else if(s.waiting&&s.timer_on){
            ++s.polls;
            if(s.fault==Fault::CumulativeDeadline&&s.polls==1)s.time+=25000;
            const bool missing=(s.clears==1&&(s.fault==Fault::MissingBefore||s.fault==Fault::FrozenBefore))||
                (s.clears==2&&(s.fault==Fault::MissingAfter||s.fault==Fault::FrozenAfter));
            if(!missing&&s.polls>=2){s.done=true;s.waiting=false;}
        }
        *set=s.done;return S3EntropyStatus::PublicDraw;}

    S3EntropyOps ops(){return {this,claim,enable,snapshot,word,cleanup,unlock,now,interrupted,pause,timer,completion};}
};
struct Guarded {uint8_t before[16],data[32],after[16];};
static Guarded guarded(){Guarded g;std::memset(&g,0xa7,sizeof(g));return g;}
static void guards(const Guarded &g){for(auto b:g.before)CHECK(b==0xa7);for(auto b:g.after)CHECK(b==0xa7);}
int main(){
    CHECK(sizeof(S3EntropyReport)==384);CHECK(sizeof(S3EntropyReport)*5+32*4==2048);
    auto s=active();CHECK(s3_entropy_active(s));
    for(unsigned bit=0;bit<16;++bit){auto invalid=s;invalid.flags^=1U<<bit;CHECK(!s3_entropy_active(invalid));}
    for(auto field:{&S3EntropySnapshot::readable,&S3EntropySnapshot::references,&S3EntropySnapshot::reference_mask,
       &S3EntropySnapshot::cpu_hz,&S3EntropySnapshot::apb_hz,&S3EntropySnapshot::clock_select,&S3EntropySnapshot::clock_div,
       &S3EntropySnapshot::sar_div,&S3EntropySnapshot::timer_target,&S3EntropySnapshot::pattern1,&S3EntropySnapshot::pattern2,
       &S3EntropySnapshot::filter0,&S3EntropySnapshot::filter1}){auto invalid=s;invalid.*field^=1;CHECK(!s3_entropy_active(invalid));}
    for(unsigned foreign:{1U,2U,254U,255U}){
        Rcc r;r.count=foreign;CHECK(s3_entropy_rcc_claim(r)==S3EntropyStatus::Ownership);
        CHECK(r.count==foreign&&!r.on&&!r.writes&&!r.locked&&r.enters==r.exits);
        CHECK(s3_entropy_rcc_gate(r)==(foreign==1?S3EntropyStatus::PublicDraw:S3EntropyStatus::Ownership));
        CHECK(r.count==foreign&&!r.locked&&r.enters==r.exits);
    }
    for(unsigned foreign:{0U,2U,255U}){
        Rcc r;r.count=foreign;CHECK(s3_entropy_rcc_release(r)==S3EntropyStatus::Cleanup);
        CHECK(r.count==foreign&&!r.locked&&!r.writes&&r.enters==r.exits);
    }
    S3EntropyBudget budget;
    for(unsigned i=0;i<4;++i)CHECK(budget.take(true));
    CHECK(!budget.take(true)&&budget.diagnostic==4);
    CHECK(budget.take(false));CHECK(!budget.take(false)&&budget.auxiliary==1);
    for(auto fault:{Fault::None,Fault::Busy,Fault::Error,Fault::Short,Fault::Oversize,Fault::Zero,Fault::Ones,
        Fault::Stuck,Fault::StableData,Fault::Readback,Fault::Ownership,Fault::ClockBack,Fault::Timeout,
        Fault::FrozenClock,Fault::Interrupt,Fault::Cleanup,Fault::Enable,Fault::InitialDone,
        Fault::ClearStuckBefore,Fault::ClearStuckAfter,Fault::MissingBefore,Fault::MissingAfter,Fault::StopBefore,
        Fault::RestoreBefore,Fault::RestoreAfter,Fault::OwnerAtClear,Fault::InterruptAtClear,Fault::ClockBackAtClear,
        Fault::DeadlineAtClear,Fault::CumulativeDeadline,Fault::FrozenBefore,Fault::FrozenAfter,Fault::ClaimTimeout,Fault::EnableTimeout}){
        Mock m;m.fault=fault;S3EntropyState state;auto g=guarded();size_t written=999;S3EntropyReport report;
        const auto status=s3_entropy_collect(state,m.ops(),g.data,32,&written,report);
        guards(g);CHECK(!m.busy&&!m.rcc.locked&&m.rcc.enters==m.rcc.exits);
        if(fault==Fault::None||fault==Fault::StableData||fault==Fault::InitialDone){
            CHECK(status==S3EntropyStatus::PublicDraw&&written==32&&m.words==8&&state.have_previous);
            CHECK(m.clears==2&&!m.timer_on&&m.timer_writes==4);
            CHECK(report.progress_before==(ProgressRead|ProgressClearZero|ProgressFresh|(fault==Fault::InitialDone?ProgressInitialSet:0)));
            CHECK(report.progress_after==(ProgressRead|ProgressInitialSet|ProgressClearZero|ProgressFresh));
            if(fault==Fault::StableData)CHECK(report.enabled.data1==0x14000&&report.after.data1==0x14000&&report.enabled.data2==0x14000&&report.after.data2==0x14000);
        }
        else{CHECK(status!=S3EntropyStatus::PublicDraw&&written==0&&!state.have_previous);for(auto b:g.data)CHECK(b==0);}
        if(fault==Fault::Busy)CHECK(!m.enabled&&!m.cleaned&&!m.unlocked&&!m.rcc.writes);
        else CHECK(m.enabled==(fault==Fault::ClaimTimeout?0U:1U)&&m.cleaned==1&&m.unlocked==1);
        if(fault==Fault::Ownership||fault==Fault::OwnerAtClear)CHECK(state.poisoned&&m.rcc.count==2);
        else CHECK(m.rcc.count==0);
        if(fault==Fault::Cleanup)CHECK(state.poisoned&&status==S3EntropyStatus::Cleanup);
        if(fault==Fault::FrozenClock)CHECK(m.words==0&&m.pauses==256&&status==S3EntropyStatus::Timeout);
        if(fault==Fault::MissingBefore||fault==Fault::FrozenBefore)CHECK(m.words==0&&m.polls==256&&status==S3EntropyStatus::Timeout);
        if(fault==Fault::MissingAfter||fault==Fault::FrozenAfter)CHECK(m.words==8&&m.polls==256&&status==S3EntropyStatus::Timeout);
        if(fault==Fault::ClearStuckBefore||fault==Fault::ClearStuckAfter)CHECK(status==S3EntropyStatus::Readback);
        if(fault==Fault::CumulativeDeadline)CHECK(m.words==8&&report.elapsed_us>=50000&&status==S3EntropyStatus::Timeout);
        if(fault==Fault::ClaimTimeout)CHECK(!m.enabled&&!m.words&&status==S3EntropyStatus::Timeout);
        if(fault==Fault::RestoreBefore||fault==Fault::StopBefore||fault==Fault::DeadlineAtClear||fault==Fault::InterruptAtClear||fault==Fault::ClockBackAtClear)CHECK(m.words==0);

    }
    S3EntropyState history;Mock first;auto g=guarded();size_t written=0;S3EntropyReport report;
    CHECK(s3_entropy_collect(history,first.ops(),g.data,32,&written,report)==S3EntropyStatus::PublicDraw);
    Mock same;CHECK(s3_entropy_collect(history,same.ops(),g.data,32,&written,report)==S3EntropyStatus::Health);
    CHECK(written==0&&!history.have_previous);for(auto b:g.data)CHECK(b==0);guards(g);
    Mock fresh;fresh.seed=9;CHECK(s3_entropy_collect(history,fresh.ops(),g.data,32,&written,report)==S3EntropyStatus::PublicDraw);
    Mock busy;busy.rcc.count=3;g=guarded();
    CHECK(s3_entropy_collect(history,busy.ops(),g.data,32,&written,report)==S3EntropyStatus::Ownership);
    CHECK(busy.rcc.count==3&&!busy.enabled&&!busy.cleaned&&!busy.rcc.writes);for(auto b:g.data)CHECK(b==0);
    for(size_t cap:{0U,31U,33U}){
        Mock m;g=guarded();written=777;
        CHECK(s3_entropy_collect(history,m.ops(),g.data,cap,&written,report)==S3EntropyStatus::Argument);
        CHECK(written==777&&!m.enabled&&!m.rcc.writes);for(auto b:g.data)CHECK(b==0xa7);guards(g);
    }
    // Software owner held by an outstanding call: a reentrant request has no RCC effect.
    Mock reentrant;reentrant.busy=true;g=guarded();
    CHECK(s3_entropy_collect(history,reentrant.ops(),g.data,32,&written,report)==S3EntropyStatus::Ownership);
    CHECK(reentrant.busy&&!reentrant.rcc.enters&&!reentrant.cleaned);guards(g);for(auto b:g.data)CHECK(b==0);
    std::printf("PASS S3 experimental entropy: %u checks; RCC ownership, fresh ADC1 completion phases, bounded failures, full buffers/guards; not physical entropy evidence\n",checks);
}
