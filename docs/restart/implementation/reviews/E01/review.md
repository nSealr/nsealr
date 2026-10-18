# E01 independent exact-candidate review

**Verdict: pass for the bounded operations in the reviewed brief and capability
allowlist.** No blocking finding. This review does not close E01's canonical task,
merge PR 14, promote other adapter operations or qualify a product board.

Reviewed candidate: `89943be5a52ce43058d446da640b5fb550a124d3`.
Executed implementation: `1524af02c70ab5e74bd7089d9055b2568e7a2250`.
The `tools/cad` tree is identical at both commits:
`2b0cbab560e56c2494bd11bf43817370e31d0e3d`.
Reviewer: `/root/independent_cad_review`, distinct from author
`/root/cad_execution`. The parent confirmed an accepted spawn with
`gpt-6-astra`, `xhigh`, `fork_turns=none`; this records the assigned runtime
configuration, not independent introspection of hosted model identity.

The parent spec review's two file hashes still match the candidate. I read the
canonical E01 acceptance, brief, inputs, results, capability and failure records,
validation, visual inspection, every `tools/cad` source file, and selected pinned
adapter implementations. The seven contracts adequately bound the minimal native
capture/export and live PCB read path. The independent fixture oracle is separate
from source generation: explicit XML net membership, native PCB poses/pad mapping,
front layers, 13 straight routes, outline, project minimums, CPL convention and
drill coordinates are checked against separately stated expectations. I also
checked the two copper layers directly in both native snapshots.

## Independent execution and evidence integrity

[Reviewer results](evidence-01/results.json) and
[commands](evidence-01/commands.json) record a fresh extraction of the pinned
AppImage into a reviewer-owned runtime, plus native ERC, DRC with schematic parity,
and XML export on reviewer-owned project copies. No GUI or IPC server was launched
by this review; no display or author's live project was used.

The unchanged fixed copy passed ERC/DRC with exit 0 and zero reported findings,
unconnected items or parity violations. For an independent adversarial control,
I changed only R1's X coordinate from 35.0 to 35.1 mm. This remains electrically
connected and passes native ERC/DRC and parity with exit 0, but the contract oracle
rejects it with `Footprint pose mismatch`. The experiment demonstrates why native
checks alone cannot establish the required placement. Both original and mutated
native snapshots, exports and logs are retained under `evidence-01/`.

I recomputed the candidate's full semantic checker against the archived successful
campaign. All 13 executed source hashes, both spec-reviewed file hashes, all 277
attempt-01 archival entries and all 286 attempt-02 archival entries matched.
Both original and round-tripped export source hashes match the corresponding
native schematic, board and project files. The reviewer evidence manifest also
verifies. The original failed attempt remains failed and byte-preserved; its pad
layer-order correction requires exact membership and cardinality, so it does not
accept missing, additional or duplicate layers.

The archived clean installation used a newly created Python 3.12.15 venv and normal
resolver invocation with all 34 dependency pins; it used no `--no-deps`, override
or corrected wheel. Its resolved inventory and successful `uv pip check` are
retained. [Independent provenance results](provenance-results.json) compare all 72
installed binding files against a newly fetched official wheel of the pinned hash,
the adapter archive against commit `303e62010172bf99c2aa41c10237c18bcabcca7a`, all
runtime adapter source files against that archive and 12 installed adapter package
files against their sources. All pins match and a new read-only `uv pip check`
passes. I reused the installed Python environment read-only for review parsing;
I did not claim a second clean installation or a fresh-machine bootstrap.

## Native, GUI and MCP assessment

The native negative reports contain the actual configured rule values: 0.1500 mm
track width violates 0.2000 mm, and 0.0500 mm clearance violates 0.2000 mm. The
disconnected schematic reports `pin_not_connected` and `label_dangling`; the bad
PCB reports a short, mask bridge, unconnected item and parity finding. The
clearance spur's additional dangling endpoint remains visible. Fixed and
round-tripped sources pass the gates. Five default ignored DRC classes remain
explicitly disclosed; `--severity-all` does not enable them.

I reconciled the GUI launch/save/close/kill/reopen events with command logs,
persisted hashes and final native checks. Each editor saved a nonempty project,
was reopened, then was killed after a completed save and opened again. This
supports persisted-source recovery only. It provides no crash-during-write,
unsaved-edit, power-loss or arbitrary transaction rollback guarantee.

I independently viewed the hash-linked `pcbnew-after-crash.png`,
`eeschema-after-crash.png`, `schematic.png` and `board.png` in attempt 02. The PCB
GUI shows J1/R1/R2, seven numbered pads, the VIN/VOUT/GND copper paths, CANARY text,
closed outline, 13 tracks and zero unrouted connections. The schematic GUI and PDF
render show the two 10k resistors and three-pin connector with the intended labels.
The sheet is sparse and the board SVG raster is very small; the native GUI view
supplies the useful board detail. These are tooling observations, not independent
CAM, package, mechanical or electrical qualification.

The archived stdio exchange contains actual calls to all four promoted read tools,
including each component's pads. Board identity, coordinates, front/back pad layer
membership and net assignments agree with native sources. The attempted text
mutation returns the explicit disabled-mutation error; subsequent in-memory text
and disk hash are unchanged. The pinned adapter routes these reads through read
helpers, and the tested write through its mutation guard. This is a bounded tool
allowlist and application control, not a sandbox for arbitrary adapter calls.

## Limits and source checks

The live 10.0.7 versus binding API 10.0.6 `FutureVersionError` remains explicit.
Fresh independent processes reproduced all four unsupported imports:
`board_jobs`, `board_rules`, `schematic`, `schematic_types`. Optional-import handling
does not promote them. There is no inherited qualification from an earlier Python
tuple. Stable IPC is limited to a running PCB GUI; native CLI handles exports and
the reviewed legacy `pcbnew` fallback constructs only this fixed fixture.

The [official Linux release page](https://www.kicad.org/download/linux/) still
listed 10.0.7 when independently checked on 2026-10-18. The
[IPC developer documentation](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
distinguishes KiCad 9/10 GUI PCB support from KiCad 11 schematic, headless and
export support. The [10.0 CLI manual](https://docs.kicad.org/10.0/en/cli/cli.html)
documents the native commands used here. Installed pinned source and observed
outputs establish the actual tested behavior.

MCP writes, bottom placement/flip, arbitrary rotations, vias, zones/fill, general
routing, schematic/headless IPC, IPC export, custom IPC rules, 3D/STEP and SPICE
remain unpromoted. New symbols, footprints, geometry, production rules and
fabrication outputs still need design-specific review and tests. No physical
evidence or manufacturing submission is included.

The full historical `git diff --check` still fails on native SVG/stdout/Xvfb
whitespace. The separate authored-source/document check passes; raw bytes were
not changed to obtain a green full-diff result. Source lint and the restart-plan
validator pass. Exact commands and outputs are in [validation.json](validation.json).

## Replay

Use `replay.py` from this review with `--repo` pointing to a disposable checkout
of the exact candidate above, a fresh absolute `--runtime`, a fresh `--output`,
and the pinned `--image`. Use Python 3.12.15 with the recorded `sexpdata==1.0.2`
environment. `provenance.py` checks the preserved installation read-only and
requires the adapter Git checkout and official wheel URL. The exact executed
invocations are recorded in `review.json`; the commands refuse existing outputs.
The native extraction and reviewer project copies must remain separate from all
live CAD projects. No full GUI campaign was repeated because the selected native
rerun, independently chosen fault control and archived GUI/MCP evidence resolved
the review questions.
