// SPDX-License-Identifier: MIT
#include "../main/otg_state.h"
#include "../main/public_marker.h"
#include "../main/public_restart.h"
#include "../main/session_buttons.h"
#include <cstdio>
#include <initializer_list>
#include <cstdlib>
static unsigned checks=0;
#define CHECK(expr) do{++checks;if(!(expr)){std::fprintf(stderr,"line %d: %s\n",__LINE__,#expr);std::abort();}}while(0)
static OtgState ready(){OtgState s;s.event(OtgEvent::Attached);s.event(OtgEvent::LineState,true,false);return s;}
int main(){
    OtgState s;CHECK(!s.usable());s.event(OtgEvent::Attached);CHECK(!s.usable());
    s.event(OtgEvent::LineState,true,false);CHECK(s.usable());
    const uint32_t grant=s.epoch;CHECK(s.current(grant));
    s.event(OtgEvent::LineCoding,false,false,1200);CHECK(s.current(grant)&&s.baud==1200);
    s.event(OtgEvent::LineState,true,true);CHECK(s.current(grant));
    s.event(OtgEvent::LineState,false,true);CHECK(!s.current(grant));
    s.event(OtgEvent::LineState,true,false);CHECK(s.usable()&&!s.current(grant));
    for(auto event:{OtgEvent::BusReset,OtgEvent::Detached,OtgEvent::Suspend,OtgEvent::LineState}){
        s=ready();const auto before_drain=s.epoch;
        s.event(event);CHECK(!s.current(before_drain));
        // Restore every operational flag: the old Enable still cannot acknowledge
        // the intervening event by reading a newer state after a blocking drain.
        s.event(OtgEvent::Attached);s.event(OtgEvent::Resume);s.event(OtgEvent::LineState,true,false);
        CHECK(s.usable()&&!s.current(before_drain));
        const auto fresh_local_grant=s.epoch;CHECK(s.current(fresh_local_grant));
        s.event(event);CHECK(!s.current(fresh_local_grant));
    }
    s=ready();s.epoch=UINT32_MAX;CHECK(s.current(UINT32_MAX));
    s.event(OtgEvent::Suspend);s.event(OtgEvent::Resume);CHECK(s.poisoned&&!s.usable());
    s.event(OtgEvent::Attached);s.event(OtgEvent::LineState,true,true);CHECK(!s.current(UINT32_MAX));
    s=ready();s.counts[unsigned(OtgEvent::LineCoding)]=UINT32_MAX;
    s.event(OtgEvent::LineCoding,false,false,115200);CHECK(s.poisoned&&!s.usable());
    s=ready();s.event(OtgEvent::Count);CHECK(s.poisoned&&!s.usable());
    const auto marker=public_marker(9);CHECK(marker_valid(marker));
    CHECK(!marker_valid(PublicMarker{}));CHECK(!marker_valid(public_marker(0)));
    for(unsigned i=0;i<16;++i){auto broken=marker;broken.words[i]^=1U<<i;CHECK(!marker_valid(broken));}
    PublicRestart restart;
    CHECK(!restart.update(0,true,false,true,false,true));
    CHECK(!restart.update(6000,true,false,true,false,true)); // held from preceding request cannot restart
    CHECK(!restart.update(6001,false,false,false,false,true));
    CHECK(!restart.update(6100,true,false,true,false,true));
    CHECK(restart.countdown(7100)==4);
    CHECK(!restart.update(11099,true,false,true,false,true));
    CHECK(restart.update(11100,true,false,true,false,true));
    CHECK(!restart.update(12000,true,false,true,false,true));
    CHECK(!restart.update(12001,false,false,false,false,true));
    CHECK(!restart.update(12100,true,false,true,false,true));
    CHECK(!restart.update(17100,true,false,true,false,false)); // Ready/review: no diagnostic restart
    CHECK(!restart.update(24000,true,false,true,false,true)); // must release after returning Locked
    CHECK(!restart.update(24001,false,false,false,false,true));
    CHECK(!restart.update(25000,true,false,true,false,true));
    CHECK(!restart.update(26000,true,false,true,true,true)); // raw Right alone blocks
    CHECK(!restart.update(35000,true,false,true,false,true));
    CHECK(restart.countdown(35000)==0);
    CHECK(!restart.update(35001,false,false,false,false,true));
    CHECK(!restart.update(UINT32_MAX-1000,true,false,true,false,true));
    CHECK(restart.update(3999,true,false,true,false,true)); // bounded unsigned timer wrap
    restart=PublicRestart{};
    SessionGesture both;SessionMenu menu;
    CHECK(!restart.update(0,false,false,false,false,true));
    CHECK(both.update(0,false,false,false,false,false)==SessionAction::None);
    CHECK(!restart.update(10,true,true,true,true,true));
    CHECK(both.update(10,true,true,true,true,false)==SessionAction::None);
    CHECK(!restart.update(1510,true,true,true,true,true));
    CHECK(menu.apply(both.update(1510,true,true,true,true,false))==SessionMenuChange::Lock);
    restart=PublicRestart{}; // same reset performed by owner after commit/Lock
    CHECK(!restart.update(9000,true,false,true,false,true));
    CHECK(!restart.update(15000,true,false,true,false,true));
    CHECK(!restart.update(15001,false,false,false,false,true));
    CHECK(!restart.update(16000,true,false,true,false,true));
    CHECK(restart.update(21000,true,false,true,false,true));
    std::printf("PASS public OTG state/epochs/saturation/marker/restart: %u checks\n",checks);
}
