// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
// Gesture classification only; the Rust owner owns authorization.
enum class SessionAction { None=0, Next=1, Back=2, Approve=3, Reject=4, Lock=5 };
struct SessionGesture {
    bool armed=false, left=false, right=false, combo=false, right_timed=false, both_timed=false;
    uint32_t right_start=0,both_start=0;
    SessionAction update(uint32_t now,bool l,bool r,bool raw_l,bool raw_r,bool decision) {
        const bool released=!l&&!r&&!raw_l&&!raw_r;
        if(!armed){if(released)armed=true;return SessionAction::None;}
        if((raw_l&&(raw_r||r))||(l&&raw_r))combo=true;
        left=left||l;right=right||r;
        if(left&&right)combo=true;
        if(combo){
            if(l&&r){if(!both_timed){both_timed=true;both_start=now;}
                if(uint32_t(now-both_start)>=1500)return SessionAction::Lock;
            } else both_timed=false;
            if(released){left=right=combo=right_timed=both_timed=false;}
            return SessionAction::None;
        }
        if(r){
            if(!right_timed){right_timed=true;right_start=now;}
            if(decision&&!l&&!raw_l&&uint32_t(now-right_start)>=1500)return SessionAction::Approve;
        }
        if(released){
            const auto a=left?(decision?SessionAction::Reject:SessionAction::Back):
                right&&!decision?SessionAction::Next:SessionAction::None;
            left=right=right_timed=both_timed=false;return a;
        }
        return SessionAction::None;
    }
};
