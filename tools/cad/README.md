# Bounded KiCad qualification

Run from this repository using fresh absolute runtime and output paths. This
harness owns one disposable project and display; it must not target a product
CAD directory. The reviewed contract is
[the E01 brief](../../docs/restart/implementation/E01/brief.md).

```sh
python3 tools/cad/qualify.py prepare --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT" --tool-root /home/tux/nsealr/.restart-tools/cad --display :96
python3 tools/cad/qualify.py install --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT" --python /home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3
python3 tools/cad/qualify.py run --runtime "$CAD_E01_RUNTIME" --output "$CAD_E01_OUTPUT"
python3 tools/cad/qualify.py verify --output "$CAD_E01_OUTPUT"
```

Host prerequisites: Linux x86-64, `uv`, the pinned AppImage and source checkout,
Xvfb/xdotool helper installation, ImageMagick `import`/`convert`, and `pdftoppm`.
Preparation re-extracts the verified AppImage, creates isolated KiCad config and
archives the pinned adapter. Installation is normal dependency resolution in a
new Python 3.12.15 venv; it is not a clean operating-system bootstrap. No global
MCP registration occurs. Network installation may fetch pinned packages.

The board is a synthetic resistor divider. Its fixed coordinates, two-layer
stack, front-only placement, zero rotation, straight F.Cu tracks and width/
clearance checks are the entire geometric scope. Only MCP summary, footprint,
pad and board-text reads are promoted after a complete passing run. A rejected
text mutation is a negative test, not a promoted write operation.

The source generator creates new snapshots and refuses an existing fixture
directory. It uses hand-authored schematic S-expressions and the hash-pinned
AppImage's legacy `pcbnew` only for fixture construction. The independent checker
uses native XML, separately parsed PCB data and explicit expected connectivity,
coordinates and routes; it does not use the generator as its expected-value
oracle. New symbols, geometry or export conventions require new review/tests.

The recovery test replaces a closed disposable snapshot with an invalid
candidate, rejects it with native DRC, and restores every snapshot byte. GUI
crashes happen only after native saving completed; no crash-during-save,
unsaved-edit recovery, transactional rollback or multiwriter claim is made.

Each attempt keeps logs, negatives, native snapshots and exports. Never rerun
against existing fixture output or delete a failed attempt to obtain a pass.
A failed campaign may leave GUI recovery files, and cleanup terminates only the
processes that the campaign itself launched. Review the final artifact manifest
and visual output independently before promoting any operation. Default ignored
DRC checks remain listed. CAD tooling evidence cannot close physical release gates.
