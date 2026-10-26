// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <limits.h>
// All methods and field reads require the caller's ISR/task-safe spinlock.
// No clearable pending bit: grants bind an immutable generation. Saturation poisons
// the instance until CPU restart, so no event can be hidden by wrap or acknowledgement.
enum class OtgEvent : unsigned { BusReset, Attached, Detached, Suspend, Resume, LineState, LineCoding, Count };
struct OtgState {
    uint32_t epoch=0, counts[unsigned(OtgEvent::Count)]={}, baud=0;
    bool configured=false, suspended=true, dtr=false, rts=false, poisoned=false, reset_pending=false;
    void increment(uint32_t &value) {
        if(value==UINT32_MAX) poisoned=true;
        else ++value;
    }
    void event(OtgEvent kind,bool a=false,bool b=false,uint32_t rate=0) {
        const unsigned index=unsigned(kind);
        if(index>=unsigned(OtgEvent::Count)){poisoned=true;return;}
        increment(counts[index]);
        bool revoke=false;
        switch(kind){
        case OtgEvent::BusReset: configured=false;dtr=false;suspended=true;reset_pending=true;revoke=true;break;
        case OtgEvent::Attached: configured=true;suspended=false;break;
        case OtgEvent::Detached: configured=false;dtr=false;suspended=true;revoke=true;break;
        case OtgEvent::Suspend: suspended=true;revoke=true;break;
        case OtgEvent::Resume: suspended=false;break;
        case OtgEvent::LineState: dtr=a;rts=b;revoke=!a;break;
        case OtgEvent::LineCoding: baud=rate;break;
        case OtgEvent::Count: poisoned=true;return;
        }
        if(revoke)increment(epoch);
    }
    // Called by a FIFO barrier after the corresponding stack reset, never by Enable.
    // Older callbacks cannot reopen the transport while reset is still queued.
    void reset_processed(uint32_t ticket) {
        if(poisoned||counts[unsigned(OtgEvent::BusReset)]!=ticket)return;
        configured=false;dtr=false;suspended=true;reset_pending=false;
    }
    bool usable() const {return configured&&!suspended&&dtr&&!poisoned&&!reset_pending;}
    bool current(uint32_t grant) const {return usable()&&grant==epoch;}
};
