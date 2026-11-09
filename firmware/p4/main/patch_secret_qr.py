#!/usr/bin/env python3
"""Preserve bundled QR behavior and wipe its two data-dependent mask histories."""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();raw=a.source.read_bytes()
expected='cdba3a8f78254e6b2427af9a5bd64085e425e6d0e56da8ac1efcc65105276e1c'
if hashlib.sha256(raw).hexdigest()!=expected:
    raise SystemExit('QR encoder input changed; review its memory behavior before updating the pin')
text=raw.decode()
anchor='''        if(hasFinderLikePattern(runHistory))
            result += PENALTY_N3;
    }'''
assert text.count(anchor)==2
replacement='''        if(hasFinderLikePattern(runHistory))
            result += PENALTY_N3;
        // nSealr: run lengths depend on secret QR modules; clear before scope exit.
        volatile unsigned char * wipe = runHistory;
        for(size_t i = 0; i < sizeof(runHistory); ++i) wipe[i] = 0;
#ifdef P4_QR_WIPE_TEST
        p4_qr_stack_wipe_observer(runHistory, sizeof(runHistory));
#endif
    }'''
text=text.replace(anchor,replacement)
text=text.replace('#include "qrcodegen.h"', '#include '+json.dumps(str(a.source.with_name('qrcodegen.h').resolve())))
text=text.replace('#include "../../lvgl_public.h"', '#include '+json.dumps(str((a.source.parent/'../../lvgl_public.h').resolve())))
text=text.replace('#include <string.h>', '''#include <string.h>
#ifdef P4_QR_WIPE_TEST
extern void p4_qr_stack_wipe_observer(const unsigned char *, size_t);
#endif''')
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
print(json.dumps({'input_sha256':expected,'patched_sha256':hashlib.sha256(text.encode()).hexdigest(),'cleared_mask_histories':2}))
