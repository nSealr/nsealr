# E01 qualified operation path

The bounded native and read-only PCB IPC path passed on implementation commit
`1524af02c70ab5e74bd7089d9055b2568e7a2250`. [Attempt 02](evidence/attempt-02/results.json)
is a complete fresh installation and runtime campaign, not inherited evidence.
The [spec review](../reviews/E01-spec.json) approved the brief before implementation;
a distinct final review of the candidate is still required. Canonical E01 state
is owned by the coordinator and has not been changed here.

## Observed results

| Contract | Actual result and evidence |
| --- | --- |
| CAD-01 toolchain | Python 3.12.15, KiCad 10.0.7, KiPilot 303e620, kicad-python 0.8.0, protobuf 5.29.6 and MCP 1.30.0 installed normally in a new venv; resolver and `uv pip check` exited 0. All 72 installed binding package files match the pinned official wheel. [Inputs](evidence/attempt-02/inputs.json), [package inventory](evidence/attempt-02/requirements-installed.txt), [probe](evidence/attempt-02/binding-probe.json). |
| CAD-02 source generation | Native schematic, board and selected local libraries created. Independent native XML/PCB checks match J1/R1/R2, seven pad identities and the three expected nets. A repeated generation attempt exits 1 and leaves every source byte unchanged. |
| CAD-03 geometry/rules | Three front footprints at explicit coordinates and zero rotation, 13 F.Cu segments, 0.25 mm widths and 27 x 20 mm outline checked. A 0.15 mm segment fails the configured 0.20 mm minimum; 0.05 mm clearance fails the configured 0.20 mm minimum. [Width fault](evidence/attempt-02/exports/width/drc.json), [clearance fault](evidence/attempt-02/exports/clearance/drc.json). The clearance spur also has a dangling endpoint; that extra finding is retained. |
| CAD-04 native gates | Disconnected schematic: exit 5, pin-not-connected and dangling label. Bad PCB: exit 5, short, mask bridge, one unconnected item and one schematic-parity finding. Original and round-tripped corrected sources: ERC/DRC exit 0 with no reported violations, unconnected items or parity findings. [All results](evidence/attempt-02/results.json). |
| CAD-05 native round trip/export | Both actual GUI editors opened and saved nonempty files, closed/reopened and wrote native files again. Save completion required a changed file mtime; semantic checks after reopening match the independent circuit/geometry oracle. PDF, XML netlist, BOM, SVG, CPL, nine Gerbers and three-hole drill output exported from original and round-tripped sources with source hashes. [GUI events](evidence/attempt-02/gui-events.json), [round-trip exports](evidence/attempt-02/exports/roundtrip/source-hashes.json). |
| CAD-06 live read-only MCP | Actual stdio requests verify project identity, footprint/pad coordinates, layers and net assignments. Disabled text mutation rejected with unchanged in-memory text and unchanged board hash. Only four read tools are promoted. [Raw calls](evidence/attempt-02/mcp-read.json). |
| CAD-07 recovery | An invalid closed-project candidate fails DRC; original snapshot restored byte for byte. Each editor was killed only after completed save, reopened, saved and passed semantic/native gates. [Recovery](evidence/attempt-02/recovery.json), [GUI lifecycle](evidence/attempt-02/gui-events.json). |

[Commands](evidence/attempt-02/commands.jsonl) retain UTC times, argv, exit codes,
and separate stdout/stderr. [Manifest](evidence/attempt-02/manifest.json) links
285 artifacts. The [archival manifest](evidence/attempt-02-archive-manifest.json)
also covers the run manifest itself. Public evidence includes only this canary,
selected licensed libraries and authored scripts, with no private Git history.

The native schematic PDF and board GUI were inspected by the author; the
[specific observations](visual-inspection.json) and [images](evidence/attempt-02/visuals/pcbnew-after-crash.png)
remain available for distinct review. Selected export contents are reconciled,
but this is not a complete CAM or manufacturing inspection.

## Failures and promotion limits

[Attempt 01](evidence/attempt-01-archive-manifest.json) remains failed. Its final
checker incorrectly assumed the order of a pad's layer list. The corrected
checker compares exact membership and cardinality, then the complete campaign
was repeated from fresh runtime/evidence directories. The original traceback,
sources and exports remain archived; [failure record](failures.json) identifies
the change and rerun.

The [version probe](evidence/attempt-02/version-probe.json) still raises
`FutureVersionError`: live 10.0.7 versus the binding's 10.0.6 API source. The
binding compares major/minor/patch; it does not negotiate command compatibility.
Fresh-process imports of `board_jobs`, `board_rules`, `schematic` and
`schematic_types` fail. KiPilot's optional-import handling permits server startup
without proving those capabilities. Nothing was patched or suppressed.

Five default ignored DRC classes remain: missing courtyard, track endpoint not
centered on via, tuning-profile geometry, footprint filter mismatch and
footprint type mismatch. `--severity-all` does not enable them. A product and its
factory rules require their own reviewed settings and fault tests.

The [capability allowlist](capabilities.json) deliberately promotes no MCP write
operation. Flip, bottom placement, arbitrary rotations, vias, zones, general
routing, schematic/headless IPC, 3D/STEP, SPICE, crash-during-save, unsaved-edit
recovery and arbitrary transaction rollback remain disabled. A text-write
canary from another tuple cannot qualify these. The bundled legacy `pcbnew`
path constructs the fixed fixture; it is not a stable or general editing API.

This evidence unblocks the described preparation workflow subject to final
review. H05/H06 must qualify new symbols, footprints, rules and operations for
the actual design. No electrical, mechanical, security, manufacturing or
physical release gate is closed.

## Replay

Use the [harness instructions](../../../../tools/cad/README.md) and the exact
commands in the reviewed [brief](brief.md), with fresh absolute runtime/output
paths and exclusive display `:96`. Preparation re-extracts the hash-verified
AppImage. Helper binaries are hash checked; host rendering tools and OS details
are recorded. This is a fresh dependency installation on the recorded host,
not a hermetic or fresh-machine bootstrap. Run `verify` to recheck every archived
hash; a new campaign requires the pinned tools and dependencies.

The [validation record](validation.json) preserves one repository formatting
failure: `git diff --check c06a9e2..HEAD` exits 2 for trailing spaces and EOF blank
lines emitted by native SVG export, native version output and Xvfb. Those raw
bytes remain unchanged and hash linked. A separately scoped authored-source/
document check passes; this is not reported as a full-diff pass. Source lint and
the restart-plan validator pass. No CI configuration or gate was weakened.
