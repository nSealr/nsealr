# P4 build recipe (Linux x86_64)

This builds the stable public optical/auxiliary fixture, not the paused volatile
vault WIP. It is not a release, custody, entropy-health or device qualification.
The C/Rust application, SDK and dependency versions are unchanged.

All maintained inputs are in this repository: application and shared Rust core,
Cargo vendor/locks, this config baseline, the explicit public overrides, the
component lock and the admitted four-header LVGL patch. Output and caches belong
to the directory you select. No script, config or component in a private intake,
old worktree or coordinator tool scope is required.

## Exact public tools

Choose existing installations or obtain the following under your own tool root:

* ESP-IDF6.0.2 commit7101770dc6db2667b3c477cc31365dd1acd6db4e and its recursive
  pinned submodules from https://github.com/espressif/esp-idf.git.
* The Linux x86_64 GCC15.2.0_20251204, CMake4.0.3, Ninja1.12.1 and ROM ELF20241011
  archives listed with URL/size/SHA256 in pins.json. The pinned SDK tools.json
  contains the same identities. Its idf_tools.py install command validates the
  downloaded archives. Build needs no OpenOCD/GDB installation or device.
* Python3.12.15 from the pinned Astral standalone archive, uv0.11.28 and Rustup1.29.1
  from pins.json. Verify each archive/executable SHA256 before extracting/running.
  Install Rust1.95.0 minimal plus target riscv32imafc-unknown-none-elf using Rustup
  in directories you choose. The exact installed binary hashes are checked before their execution.
  The official version-specific Rust distribution manifest authenticates its
  component downloads through Rustup; no RustR00 path is assumed.

For a fresh SDK installation (these are user setup commands, not executed by
build.py), use:

```sh
git clone https://github.com/espressif/esp-idf.git "$TASK_SDK"
git -C "$TASK_SDK" checkout --detach 7101770dc6db2667b3c477cc31365dd1acd6db4e
git -C "$TASK_SDK" submodule update --init --recursive
IDF_PATH="$TASK_SDK" IDF_TOOLS_PATH="$TASK_IDF_TOOLS" \
  "$TASK_BASE_PYTHON" "$TASK_SDK/tools/idf_tools.py" install \
  riscv32-esp-elf cmake ninja esp-rom-elfs

RUSTUP_HOME="$TASK_RUSTUP" CARGO_HOME="$TASK_CARGO" \
  "$TASK_RUSTUP_INIT" -y --no-modify-path --profile minimal --default-toolchain 1.95.0
RUSTUP_HOME="$TASK_RUSTUP" CARGO_HOME="$TASK_CARGO" \
  "$TASK_CARGO/bin/rustup" target add --toolchain 1.95.0 riscv32imafc-unknown-none-elf
```

This qualification reuses already verified SDK/tools instead of cloning them
again. The command above is for a contributor who does not have those inputs.

## Fresh Python and one normal build

Run from the repository root. TASK_WORK must be a new directory outside apps/p4.
Set every TASK_* path yourself; no historical path is a default. TASK_RUST is
the actual installed toolchain directory containing bin/ and lib/, for example
TASK_RUSTUP/toolchains/1.95.0-x86_64-unknown-linux-gnu.

```sh
python3 apps/p4/build.py python --work-dir "$TASK_WORK" \
  --base-python "$TASK_BASE_PYTHON" --uv "$TASK_UV" --sdk "$TASK_SDK"

"$TASK_WORK/python/bin/python" apps/p4/build.py all \
  --work-dir "$TASK_WORK" --sdk "$TASK_SDK" --idf-tools "$TASK_IDF_TOOLS" \
  --rust-toolchain "$TASK_RUST" --jobs 8
```

The base Python SHA is checked before its version command. The same SDK/checker/
constraints admission helper is used before executing SDK Python in both python
and prepare stages; the source commit, bodies and recursive gitlinks must match.

The python stage fetches only the exact public inputs in python-sources.json.
Optionally repeat --download-cache DIR to reuse authenticated downloads. It
creates an unseeded environment with uv, installs pinned setuptools84.2.1, then
the exact57-version/hash closure. The unchanged SDK checker then enforces the full
admitted range-constraint file immediately; passing ranges to uv hash-file parsing
is unsupported. No constraint is skipped or relaxed. esptool5.6.0 is
built from its authenticated public sdist, without isolation/network for the
backend. The previous privately derived wheel hash remains history in pins.json;
it is not an installation prerequisite or an asserted bit-reproduction target.
No pip is installed. uv pip check and the unchanged SDK strict checker run.

The all stage is prepare → Rust → configure → target app, once each. The Rust
build is locked/offline using this repository's vendored dependencies, with a
new external target directory. prepare verifies SDK commit/submodules/clean
tracked sources, Python closure and tool executables, obtains and checks the
original public esp_lvgl_adapter0.6.4, then applies only the versioned patch.
The patched whole-component hash is checked separately from the registry hash;
the original registry integrity markers are removed from the patched copy.
Other components are resolved from the versioned lock through the official
manager; any component set/version/hash change stops the recipe after configure,
before target build. --component-cache DIR selects an optional existing official
manager cache, which remains an input cache, not a normative historical checkout.

The recipe copies the lock and config into TASK_WORK and points the app's ignored
managed_components symlink at TASK_WORK/managed_components. It refuses to replace
an existing store or a link belonging to another workspace. When migrating an
old workspace, explicitly unlink that ignored link only after confirming no build
uses it; do not delete its destination. There is one editable app checkout.

You can run prepare, rust, configure and app separately with the same explicit
arguments. Existing --probe-mode normal|busy-cpu|blocking-wait|c6-reset and
--entropy-mode normal|fixed-unavailable remain available; this maintenance lot
qualifies only the default normal target. --host-proof also builds the same
Rust consumer for the existing Linux proof, but is not used in this lot.

## Outputs and limits

TASK_WORK/logs contains exact argv, selected environment, source HEAD, exit,
elapsed time and log hashes. Generated sdkconfig, lock, CMake config, Rust
archive and target ELF/BIN/flash arguments remain in TASK_WORK. No SDK, compiler,
cache, environment or compiled image is committed. The own IDF-tools environment
uses the versioned constraints and the selected tools' absolute paths; it does
not import active_environment.py or a private admission file.

Source equivalence, effective configuration/ABI and image identity are separate
from bit reproducibility. Paths, project version/time and source-derived tool
wheel metadata may alter bytes; one clean build does not establish byte-for-byte
reproducibility. Historical b259 runtime evidence is not rerun or relabelled.
Hardware, usability, reset/log/RAM, offline/custody and secret-admission gates
remain unchanged. Stage B remains paused, uncompiled and untested.

See THIRD_PARTY.md and source-provenance.json. This recipe does not redistribute
downloaded SDK/tool/component binaries and does not supersede their licenses.
