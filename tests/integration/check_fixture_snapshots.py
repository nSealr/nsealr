#!/usr/bin/env python3
"""Invoke the sole authoritative contract provenance/completeness gate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_contracts import validate
if __name__=='__main__':
    print(validate())
