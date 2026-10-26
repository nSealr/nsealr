// SPDX-License-Identifier: MIT
#include "../main/session_buttons.h"
#include <cassert>
int main(){
    using A=SessionAction;
    SessionGesture held;
    assert(held.update(0,false,true,false,true,true)==A::None);
    assert(held.update(5000,false,true,false,true,true)==A::None);
    assert(held.update(5010,false,false,false,false,true)==A::None);
    assert(held.update(5020,false,true,false,true,true)==A::None);
    assert(held.update(6519,false,true,false,true,true)==A::None);
    assert(held.update(6520,false,true,false,true,true)==A::Approve);
    SessionGesture both;both.update(0,false,false,false,false,true);
    both.update(1,false,true,false,true,true);
    assert(both.update(1501,false,true,true,true,true)==A::None); // raw Left blocks approval
    assert(both.update(1541,true,true,true,true,true)==A::None);
    assert(both.update(3040,true,true,true,true,true)==A::None);
    assert(both.update(3041,true,true,true,true,true)==A::Lock);
    SessionGesture data;data.update(0,false,false,false,false,false);
    assert(data.update(10,false,true,false,true,false)==A::None);
    assert(data.update(80,false,false,false,false,false)==A::Next);
    assert(data.update(100,true,false,true,false,false)==A::None);
    assert(data.update(180,false,false,false,false,false)==A::Back);
    SessionGesture final;final.update(0,false,false,false,false,true);
    final.update(10,true,false,true,false,true);
    assert(final.update(80,false,false,false,false,true)==A::Reject);
    SessionGesture carry;carry.update(0,false,true,false,true,true);
    assert(carry.update(4000,false,true,false,true,true)==A::None);
    carry.update(4010,false,false,false,false,true);
    carry.update(4020,false,true,false,true,true);
    assert(carry.update(5520,false,true,false,true,true)==A::Approve);
    SessionGesture bounce;bounce.update(0,false,false,false,false,false);
    bounce.update(1,false,false,false,true,false); // raw-only bounce is not a debounced press
    assert(bounce.update(2,false,false,false,false,false)==A::None);
}
