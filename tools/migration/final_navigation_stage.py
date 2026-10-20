#!/usr/bin/env python3
"""Declare current guide cleanup and byte-exact accepted A02 record additions."""
import argparse,json
from pathlib import Path
from assemble import read_git
from rehearse import canonical,digest
from transforms import Changes


def apply(target,author,output):
 c=Changes(target)
 guides={
 'docs/architecture.md':'''# Product implementation

The [product requirements](product/README.md) establish correctness; this page
describes the selected implementation. The [task graph](../plan/work-items.json)
alone records task status. Historical all-Rust phase plans remain in Git history.

- `crates/nsealr-core` owns portable Rust protocol, transport, review, policy,
  session and cryptographic primitives. Its embedded workspace and target
  toolchain are separate from the host workspace. The current device dispatcher
  still refuses real signing; compiled primitives do not qualify device custody.
- `apps/desktop-simulator` is the independent host Cargo workspace and vector
  replay harness, with its own lockfile and pinned toolchain.
- `apps/bridge`, `packages` and `tools/bridge` own the host applications, private
  modules and sole public TypeScript SDK. See [Bridge boundaries](bridge/architecture.md).
- `apps/pi` retains the independently implemented Python QR/application oracle.
  Its software signing harness is not evidence of physical Pi qualification.
- `protocols/contracts/v1` is the sole authoritative contract artifact. Its
  version is the artifact inventory version, not a new wire-protocol version.
  Python, Rust and TypeScript consumers keep independent implementations.
- `boards` contains experimental profiles, not qualified hardware claims.

Generic board software remains in the separate Nostr-free Board SDK. Hardware,
website and organization metadata retain their separate repository owners.
Custom board availability is not a prerequisite for the product software build.
Retired smartcard implementations and original source identities remain in their
public source histories; they are outside the active product.

Current requirements and navigation are editable at their declared owners.
`plan/evidence-index.json` binds original closed-task evidence byte-for-byte;
the original reviews do not cover later substantive changes to current contracts.
See [testing](testing.md), [reproducibility](reproducible-build.md) and the
[execution handoff](restart/implementation/handoff.md).
''',
 'docs/testing.md':'''# Product verification

Use the [pinned cold bootstrap](../tools/baseline/README.md), then run `make ci`.
The full gate executes source/evidence integrity and the complete task validator,
contract inventory tamper controls, independent Python contract tests, Rust
formatting/clippy/default and std tests/device-target compilation, the separate
host oracle, dependency audit, both coverage floors and reproducible builds.
It also executes Bridge build/type/unit and packed Node/browser/type consumers,
Pi checks, selected integration helper tests, replacement product guardrails and
one uninterrupted seventeen-step product integration.

`make rust-ci`, `make bridge-ci`, `make pi-ci`, `make contract-ci` and
`make integration` expose the same gates for focused work. Host Rust commands
use `--manifest-path apps/desktop-simulator/Cargo.toml`; the root workspace is
the embedded graph. Both read the authoritative `protocols/contracts/v1`
artifact. No sibling repository or copied fixture fallback is required.

The generated Rust fixture projections preserve input values and expected
answers from the artifact; they do not compute the expected result with the
implementation under test. Python contract/Pi implementations stay independent.
Every retained consumer scope is checked; an unclassified artifact category
fails the applicable coverage check. The historical before/after case ledger
accounts explicitly for retired card cases and adapted layout/guardrail cases.

The default live-relay test remains visibly skipped. Installed Chromium/Firefox,
attached boards, camera/display/GPIO, real review/approval, provisioning and
physical security need separate evidence. Optional browser/serial helper unit
tests run in normal CI; their success does not claim those resources were used.
External hardware repository regression is separate from product CI. See
[Bridge testing](bridge/testing.md) for the packed SDK boundary.
''',
 'docs/roadmap.md':'''# Work and qualification

Read the [single task graph](../plan/work-items.json) and
[restart execution rules](restart/execution.md) for dependencies, ownership,
resources and acceptance. This page is navigation, not another status ledger.

The accepted architecture consolidates product software while keeping the
generic Board SDK and hardware independent. [Current requirements](product/README.md)
define the product and security boundaries. [Architecture](architecture.md)
describes the selected implementation and [testing](testing.md) its gates.

Physical releases still require their exact device, review/authorization,
custody, entropy, recovery and platform-security evidence. Software conformance
cannot close those gates. Old fixed-family and mandatory-all-Rust phase plans
remain historical source evidence; they do not schedule current work.
''',
 'docs/audit-checklist.md':'''# Software and release evidence

Use the [task graph](../plan/work-items.json) for accepted results and the
[product requirements](product/README.md) for release criteria. This checklist
is a review aid; it makes no completion or device-qualification claim.

- Bind the exact source, licenses, public ancestry, dependency locks and tool
  versions. Keep excluded private histories and credentials outside public Git.
- Run the complete [product gates](testing.md), preserving failures and skips.
  Verify independent contract consumers and actual packed SDK consumers.
- Keep the two Rust workspaces separate, preserve coverage floors and reproduce
  device and host artifacts from independent clean builds.
- Preserve immutable historical evidence and the sole task graph. Declare
  substantive current-contract changes and obtain their own review.
- Verify production source boundaries, request-bound response checks, rejected
  host approval shortcuts and disabled unqualified signing paths.
- Qualify actual browser/relay/device behavior separately. Bind physical review,
  one-use authorization, key custody, provisioning, entropy, update/debug policy
  and recovery to concrete measurements before a profile can claim support.

The host OS and hosted runner are not immutable or OS-hermetic. Dependency audit
warnings and unavailable index coverage must remain visible in execution evidence.
'''}
 frozen={r['path'] for r in json.loads((target/'plan/evidence-index.json').read_bytes())['artifacts']}
 for path,text in guides.items():
  if path in frozen:raise ValueError('cannot rewrite immutable evidence')
  c.put(path,text.encode())
 # These are exact historical approvals, not approval of this later candidate.
 selections=[('732f742422cb26e7f215613f56a6c90acc6f73dc','docs/restart/implementation/A02/'),
 ('a6756825ed39ad39e33fa5f1917b6ac4f7c70538','docs/restart/implementation/reviews/A02-spec/'),
 ('b9d5d96e22fb6a1a60b379a2e04061f2bdce23b7','docs/restart/implementation/reviews/A02-admission/'),
 ('0a8bb620fa635bf1d1721c707957563df456fc9c','docs/restart/implementation/reviews/A02-admission-coordinator.json')]
 records=[]
 for commit,prefix in selections:
  for path in read_git(author,'ls-tree','-r','--name-only',commit,'--',prefix).decode().splitlines():
   data=read_git(author,'show',commit+':'+path)
   if path in frozen and (target/path).read_bytes()!=data:raise ValueError('record copy would mutate closed evidence')
   c.put(path,data);records.append(dict(source_commit=commit,source_path=path,target_path=path,sha256=digest(data),byte_exact=True))
 c.put('docs/restart/implementation/A02/migration-record-provenance.json',canonical({'purpose':'Exact historical preparation and admission; later source changes and acceptance need their own review.','files':records}))
 return c.apply(output,'Reconcile current product guides and preserve exact A02 preparation review and admission records')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output))
