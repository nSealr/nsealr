#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    errors=[]
    if not (ROOT/'LICENSE').is_file() or 'Creative Commons CC0' not in (ROOT/'LICENSE').read_text():errors.append('LICENSE does not contain expected marker: '+'Creative Commons CC0')
    for name in ['protocols', 'schemas', 'vectors', 'examples', 'scripts']:
        if not (ROOT/name).is_dir():errors.append('missing required directory: '+name)
    for error in errors:print('ERROR:',error)
    if not errors:print('Component structure and license verified independently of checkout name')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
