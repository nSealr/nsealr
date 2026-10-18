# S01 provenance follow-up result

Tested repair source: `7a32eed82f542e818fad1c48d6815a38930eac32`.
The corrected current bootstrap and all required local acceptance gates pass.
Distinct final review and final-candidate CI remain required; this report does
not close S01 or authorize a merge.

This supersedes the earlier tooling-gate acceptance at
`ae01a32e8e0aab335115bbd17caad27f29122709`. Independent review found three real
bypasses despite its passing eight suites and integration recipe. The original
75 indexed artifacts, original R00 patch/manifest and S01 v1 patch/manifest are
unchanged. The original observations and failed review remain reproducible.

The [approved addendum](provenance-followup-brief.md), commit
`e4e46cf4abedf45951d33ec915d91de60bcb35ec`, was approved by root in
`4c78218` and imported as `176995fda93dc1a9d1f3db80b07ec06959211b61`.
The [execution record](provenance-followup-execution.json) and
[artifact index](provenance-followup-artifacts.json) bind the following evidence.

## Correction and observed controls

Core provenance is mandatory before iteration, including when required globs
are empty. The complete tracked vector inventory must match source, snapshot
and manifest; hidden files are included. Source bytes must equal the claimed
Git blob, snapshot bytes must equal source, and the recorded SHA-256 must match.
Generic partial consumers retain their required-glob contract; supplied metadata
is validated. A third selected CC0 patch implements this without rewriting the
two existing overlays or modifying fixtures/product code.

The active bootstrap now pins specs `45f8b6ff1123f3f55be4ce457fd1008e91043cc2`
and companion `678796900e462f5504e47fe934e2e5f23d85824f` and applies original
provenance, metadata-v1 and follow-up overlays in that order. All other
repository/runtime pins are unchanged. Patch, source, preimage and postimage
checks are mandatory and recorded separately.

| Check | Observed result |
| --- | --- |
| Preserved independent probe, original two overlays | Expected exit 1: 17 controls pass, three bypasses reproduced |
| Same 20 mutation functions, third overlay added | 20 pass; missing manifest, missing manifest plus vector and forged dotfile digest all reject |
| Direct provenance suite using real Git repositories | 36 tests pass, including simultaneous dirty source/snapshot and forged digest |
| Public bootstrap boundary suite | 11 tests pass, including ordered default application, missing follow-up and pin/preimage/output failures |
| Historical core `9194e292` / specs `8bb8cca7`, original plus follow-up | Six controls pass; 222 complete-core file comparisons; v1 overlay demonstrably absent |
| Fresh current default bootstrap | Exit 0; exact source/runtime versions and all three overlays recorded |
| Fresh core `make -k ci` | Exit 0, including 227 core, four secret-boundary and 20 simulator tests, bootstrap tests and reproducible-build checks |
| Fresh lab `make -k ci` | Exit 0; 169 tests |
| Actual fixture parity and v1 inventory | Both exit 0; 547 comparisons and all three expected v1 negatives selected |
| One uninterrupted fresh lab `make integration` | Exit 0; exact 20-step recipe and all three v1 auth negatives executed |

The count increased from 546 to 547 solely because core `vectors/.gitkeep` is
now compared. The complete 221-file upstream snapshot is unchanged, including
all 22 intended metadata migration paths from the original fixture commit.

## Reproduction and evidence boundaries

The positive bootstrap used the real entry point, with an absent owned
destination and `--mirrors /home/tux/nsealr` solely for authorized Git object
transport. No runtime or dependency cache was copied into this destination.
Its pinned archives/wheels were downloaded and hashed again. Kernel, libc,
compiler, TLS trust, system utilities and HOME remain host inputs; this is not
an OS-isolated build. Earlier targeted controls reused the retained pinned
runtime, explicitly distinguished from the fresh acceptance campaign.

All fresh commands, timestamps, exit codes, environment, source states and raw
logs are under [followup-evidence/fresh](followup-evidence/fresh/). The default
bootstrap invocation is recorded separately under
[fresh-bootstrap-driver](followup-evidence/fresh-bootstrap-driver/).
[run-affected.py](followup-evidence/run-affected.py) records the exact affected
gates without turning earlier failures into successful exits.

Every top-level core object except `docs` and `tools` equals the prior full
eight-suite fixture candidate `41f5d2d193e4a00227737e1f8d71ce57e39ea889`.
The six unchanged sibling suites are reconciled to that existing evidence;
they are not claimed as a second fresh eight-suite run. Only four declared lab
files differ from its pinned source, and tracked diffs remain unchanged after
the campaign. Generated untracked bytecode is preserved in the source-state
record. Source candidate push and PR CI both passed; final evidence publication
starts separate CI that root must verify before integration.

Historical R00 remote refs and input hash remain verified in
[historical-preservation.json](followup-evidence/historical-preservation.json).
The historical control rejects deliberately mismatched current metadata with
old specs. Historical refs retain the original known gate limitations; the new
evidence does not retrospectively repair their observations.

Live relay, installed interactive browsers, identified physical device signing,
camera/GPIO/display approval, secure-element custody, provisioning and physical
entropy/manufacturing remain outside this software acceptance. Safe probes and
simulators do not qualify hardware. A02 must select and review the complete
corrected tooling tuple before replacing these transitional overlays.
