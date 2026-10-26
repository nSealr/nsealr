// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
enum class SessionDrain { Empty, Limit, Error };
// RX ring is 2048 bytes. A wrapped byte ring needs two contiguous reads;
// a third bounded read may establish empty. Future arrivals are not attested.
template<class Reader>
SessionDrain session_discard(Reader read) {
    uint8_t scratch[2048];
    size_t total=0;
    for(unsigned call=0;call<3 && total<sizeof(scratch);++call) {
        const int n=read(scratch,sizeof(scratch)-total);
        if(n<0)return SessionDrain::Error;
        if(n==0)return SessionDrain::Empty;
        if(size_t(n)>sizeof(scratch)-total)return SessionDrain::Error;
        total+=size_t(n);
    }
    return SessionDrain::Limit;
}
