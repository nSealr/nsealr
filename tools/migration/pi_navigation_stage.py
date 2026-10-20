#!/usr/bin/env python3
"""Give the imported Pi component current navigation and retain its doc guard."""
import argparse
from pathlib import Path
from transforms import Changes


def apply(target, output):
    change = Changes(target)
    change.put('apps/pi/README.md', b'''# Pi QR vault reference and adapters

This component owns the retained Python reference harness, Pi-facing adapters,
and independent signing/review comparisons in the nSealr integration repository.
It is not a qualified Pi image or a second approved production signing engine.
K01 owns the portable engine; QP01 establishes the kit/image feasibility; Q02 owns
shared-engine Pi integration and physical qualification in the [task plan](../../plan/work-items.json).

The `nsealr-account-descriptor-v0` route is `raspberry_qr_vault` with policy
`policy-manual-only-qr-vault` and `persistent_grants: false`. Each signing request
requires local trusted review and physical approval. Imported sources live only
in the current RAM session; Python wiping is best effort and does not establish
physical power-cycle or production secret-custody guarantees.

Run `make -C apps/pi ci` from the repository root using the pinned Python
environment. The component tests consume the single [contract artifact](../../protocols/contracts/v1/)
and exercise independent Python/libsecp256k1 behavior plus injected camera,
display and GPIO boundaries. Optional physical drivers are not a main build
prerequisite. A successful safe probe is setup evidence, not full qualification.

See [architecture](docs/architecture.md), [testing](docs/testing.md), and the
[stateless image profile](os/stateless-qr-vault-profile.md) for retained behavior
and explicit physical limitations. Current requirements are in [docs/product](../../docs/product/).
''')
    path = 'apps/pi/tests/test_vault_core.py'
    text = (target/path).read_text().replace('(ROOT / "docs/roadmap.md").read_text(encoding="utf-8"),',
        '(ROOT.parents[1] / "plan/work-items.json").read_text(encoding="utf-8"),')
    change.put(path, text.encode())
    for path in ['apps/pi/docs/architecture.md', 'apps/pi/docs/testing.md']:
        text = (target/path).read_text().replace('`nSealr/raspberry` is the Raspberry/Pi signer implementation family.',
            '`apps/pi/` in `nSealr/nsealr` contains the Raspberry/Pi reference harness and adapters.')
        text = text.replace('`nSealr/specs`', '`protocols/contracts/v1/`')
        change.put(path, text.encode())
    return change.apply(output, 'Add current Pi component navigation and preserve manual-route documentation guard')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(apply(a.target,a.output))
