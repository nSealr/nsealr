#!/usr/bin/env python3
"""Preserve grant/refusal negatives after the declared active-card retirement."""
import argparse
from pathlib import Path
from transforms import Changes


def apply(target, output):
    change = Changes(target)
    path = 'protocols/contracts/v1/tests/test_verify_specs.py'
    text = (target / path).read_text()
    text = text.replace('vector["cases"][-1]["without_dispatcher"] = {',
                        'vector["cases"][-1]["without_dispatcher_after_ack"] = {')
    text = text.replace('"message": "bad display-less shortcut",',
                        '"message": "unexpected host acknowledgement shortcut",')
    text = text.replace('display-less route must not bypass acknowledgement before dispatcher',
                        'trusted-review route must use without_dispatcher')
    old = '            self.assertIn("grant route_type must be a nSealr persistent policy route", "\\n".join(errors))'
    new = '''            expected = ("route_type is unknown" if route_type == "smartcard"
                        else "grant route_type must be a nSealr persistent policy route")
            self.assertIn(expected, "\\n".join(errors))'''
    if text.count(old) != 1:
        raise ValueError('grant rejection assertion preimage changed')
    text = text.replace(old, new)
    change.put(path, text.encode())
    path = 'protocols/contracts/v1/scripts/verify_specs.py'
    text = (target / path).read_text()
    start = text.index('        if selection.get("trusted_review") == "display_less":')
    stop = text.index('\n    if seen_route_vectors', start)
    branch = text.index('        else:\n', start, stop)
    # The retained route contract has no host-acknowledged signer. Preserve all
    # refusal-field/error checks while removing the retired compatibility arm.
    replacement = text[branch + len('        else:\n'):stop]
    replacement = '\n'.join(line[4:] if line.startswith('    ') else line
                            for line in replacement.split('\n'))
    text = text[:start] + replacement + text[stop:]
    change.put(path, text.encode())
    return change.apply(output, 'Retain active grant and acknowledgement rejection controls after card retirement')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(apply(args.target, args.output))
