// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
// Additional PUBLIC diagnostic gesture in Locked only. Existing request gestures
// are unchanged. Raw Right cancels until release; Both never becomes Restart.
struct PublicRestart {
    bool armed=false, tracking=false, blocked=false, fired=false;
    uint32_t start=0;
    bool update(uint32_t now,bool l,bool r,bool raw_l,bool raw_r,bool locked) {
        const bool released=!l&&!r&&!raw_l&&!raw_r;
        if(!locked){*this=PublicRestart{};return false;}
        if(!armed){if(released)armed=true;return false;}
        if(released){tracking=blocked=fired=false;return false;}
        if(r||raw_r)blocked=true;
        if(blocked)return false;
        if(l&&raw_l){
            if(!tracking){tracking=true;start=now;}
            if(!fired&&uint32_t(now-start)>=5000){fired=true;return true;}
        }
        return false;
    }
    unsigned countdown(uint32_t now) const {
        if(!tracking||blocked||fired)return 0;
        const uint32_t elapsed=uint32_t(now-start);
        return elapsed<1000?0:elapsed<5000?5-elapsed/1000:0;
    }
};
