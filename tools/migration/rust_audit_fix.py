#!/usr/bin/env python3
"""Place the host cargo-deny config option at its supported global position."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 c=Changes(a.target);path='Makefile';text=(a.target/path).read_text().replace('cargo deny --manifest-path $(HOST_MANIFEST) check --config deny.toml','cargo deny --manifest-path $(HOST_MANIFEST) --config deny.toml check');c.put(path,text.encode());print(c.apply(a.output,'Use supported cargo-deny option ordering for the independent host graph'))
