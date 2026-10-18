# E01 — minimal stable CAD path

Parent: E01 at input commit `c06a9e242f2387e1ecc1467116ebef2dff805a9c`.
Author: coordinator-assigned CAD agent, exclusive writer of disposable projects.
Scope: `tools/cad/` and `docs/restart/implementation/E01/`. No production design,
canonical graph, hardware release or manufacturing submission is changed.

## Purpose and inputs

Make the first schematic/PCB preparation path reproducible and reviewable without
requiring the adapter's entire catalog. Promote only executed operations. Exact
pins and source input hashes are in [inputs.json](inputs.json). The toolchain is
KiCad 10.0.7 Lite AppImage, KiPilot 0.3.0 at
`303e62010172bf99c2aa41c10237c18bcabcca7a`, official `kicad-python==0.8.0`,
`protobuf==5.29.6`, `mcp==1.30.0`, Python 3.12.13 and pinned transitive packages.
The AppImage's bundled Python/legacy `pcbnew` is only the disposable board
construction fallback, independently reviewed as source; it is not stable IPC.

Current primary sources checked 2026-10-18:

- [Official Linux release](https://www.kicad.org/download/linux/) lists 10.0.7.
- [IPC scope](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/)
  restricts KiCad 9/10 to GUI PCB IPC; schematic IPC, headless IPC and IPC export
  begin in 11. Binding documentation defaults to development, so installed source
  and stable CLI behavior must be checked directly.
- [10.0 CLI manual](https://docs.kicad.org/10.0/en/cli/cli.html) defines ERC/DRC,
  netlist, PDF, SVG, BOM, positions, Gerber and drill export.
- [Pinned official binding](https://pypi.org/project/kicad-python/0.8.0/) and
  [adapter source](https://github.com/belaszalontai/kipilot-mcp/tree/303e62010172bf99c2aa41c10237c18bcabcca7a)
  define the installed tuple. Probe, retain and report version/import failures;
  neither optional imports nor tool enumeration establishes support.

Earlier private experiments supply selected authored scripts and input hashes,
not evidence for this candidate. Native KiCad library content is selected with
upstream attribution/license, never private repository history. No credentials,
IPC tokens or full environment dump enter public evidence.

## Observable contract and operation matrix

All promotion is bounded to the exact tuple and a three-component synthetic
10k/10k divider. It enables preparation subject to design-specific review; it
cannot certify a new symbol, package, electrical design or fabrication package.

| ID | Required operation and path | Independent acceptance / failure |
| --- | --- | --- |
| CAD-01 | Fresh pinned normal dependency installation; reuse hash-checked AppImage and isolated helpers | Clean venv, resolver and `uv pip check` pass; package inventory and official wheel comparison; preserve expected binding version/import gaps. No `--no-deps`, dependency overrides or patched wheel. |
| CAD-02 | Create native connected schematic, local libraries and fixture PCB from reviewed source | Assert explicit J1/R1/R2 values and all seven pad-to-net mappings from KiCad XML and separately parsed board; no generator-derived oracle. Fresh output directory only; refuse overwrite. |
| CAD-03 | Front-side placement, 0-degree orientation, straight F.Cu tracks, closed Edge.Cuts, project minimum width/clearance | Assert mm coordinates, layers, pad numbers, 13 track widths and geometry, and 27 x 20 mm outline. Dedicated too-narrow track and too-close copper produce corresponding DRC failures under the configured rules. Check top-side CPL sign/origin convention and drill coordinates independently. |
| CAD-04 | Native ERC/DRC including schematic parity | Disconnected schematic pin/label and short/disconnected/parity PCB yield exit 5 and expected classes; corrected fixture yields exit 0 and no reported findings. Record all ignored rule classes without concealing defaults. |
| CAD-05 | Native schematic and PCB open/save/reopen; export | Open nonempty projects in isolated actual GUI; save, close, reopen and rerun semantic/net/check oracles. Native PDF, XML, SVG, BOM, CPL, Gerber/drill outputs link to exact input hashes. Inspect schematic and board render plus GUI. |
| CAD-06 | Read-only live PCB MCP: summary, footprints, pads, text | Actual stdio requests verify expected project identity, components, coordinates/layers and connectivity; mutation disabled. Rejected text edit must leave memory and disk unchanged. No MCP write tool is promoted. |
| CAD-07 | Safe staged workflow and recovery | Refuse existing output, preserve approved snapshot, reject negative candidate, restore exact snapshot hash. Force-stop only owned GUI after a completed save, reopen and verify persisted semantics. Crash during save, unsaved-edit recovery and arbitrary transaction rollback remain unsupported. |

Only the four CAD-06 read tools are enabled in this qualification harness; the
adapter remains unregistered globally. Mutation flags are application controls,
not a sandbox against arbitrary adapter calls. New output paths, one writer,
project identity checks and explicit commands enforce the operating workflow.

Disabled: live MCP writes (including previously tested text edit/save), live
placement/move/rotation/flip, bottom-side assembly, vias, zones/fill, differential
routing, interactive schematic IPC, headless IPC, custom rules/netclasses through
IPC, 3D/STEP fit, SPICE, general autorouting and other catalog operations. Their
coordinate/layer/flip/zone/rollback/crash cases must be qualified when introduced
for H05/H06. Existing front-side fixture geometry does not qualify those cases.

## Evidence and acceptance commands

Implementation will provide these commands; a missing command or failed oracle
keeps the operation unpromoted. Runtime and evidence paths must be fresh and
outside any live product CAD directory. Display `:96` is reserved exclusively
for this author; preparation must reject an occupied display. Mutable config,
cache, documents and IPC runtime are isolated below the fresh runtime root.

```sh
python3 tools/cad/qualify.py prepare --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT" --tool-root /home/tux/nsealr/.restart-tools/cad --display :96
python3 tools/cad/qualify.py install --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT" --python /home/tux/nsealr/.restart-tools/validation4/engineering/binding-0.8.0/bin/python
python3 tools/cad/qualify.py run --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT"
python3 tools/cad/qualify.py verify --output "$CAD_E01_OUTPUT"
python3 scripts/validate_restart_plan.py
git diff --check
```

Each invocation records UTC start/end, sanitized explicit environment, argv,
return code, stdout/stderr, source hashes and native/output hashes. Evidence is
append-only per attempt; failed attempts survive separately. Assertions must be
active checks, not dependent on Python optimization mode. The installed package
inventory, important upstream file hashes and CLI build information accompany
the logs. Runtime files and dependencies stay outside Git; selected native
snapshots, required exports/logs, manifest and concise results enter this scope.

Use one clean fresh install and one complete run, then rerun affected steps for
changes. GUI screenshots/PDF/SVG receive author inspection and distinct final
review; export counts alone are insufficient. Environmental failure (display,
missing helper, dialog blocking, unavailable pinned package) is inconclusive,
retained and diagnosed, never turned into a passing skip.

## Review and delivery

This brief must receive a distinct spec review before implementation. The root
coordinator assigns the reviewer, and later a distinct exact-candidate final
review. Final evidence records that review and candidate, unresolved limits and
replay instructions. Commit/push a scoped draft PR after local checks and review;
normal protected CI remains required. No task status or physical gate is closed
by this brief or by the canary alone.
