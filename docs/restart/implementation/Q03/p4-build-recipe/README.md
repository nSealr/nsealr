# Stable P4 build-recipe maintenance proof

The goal remains paused. This is the finite maintainer-requested build
maintenance lot, not a resumption of vault Stage B or a device release.

The full build ran on source c90baa6ba178983fdbbd6a2aaa59e4dac247c8aa with selected
public tools in a new external workspace. Thirty-eight application C/header/
Rust/vendor/consumer-manifest files and the shared core equal stable
b259d416c482569622e6467a121b6c4436e6ac9e byte for byte. Only recipe/build metadata,
config provenance and documentation changed. Paused fb43306 is excluded.

The final admission candidate is3f16bc4189fd11cd8c0881a54c7dabeda59df00e.
Distinct review found that c90 checked the selected Python SHA after its version
command, and authenticated SDK source only in prepare after the python-stage
checker. The known selected providers were already authenticated in the original
setup, so the successful build remains valid historical evidence on those inputs.
The amendment moves SHA admission before execution and reuses one SDK/checker/
requirements/constraints authentication helper before both SDK checker paths.

The targeted executable wrong-provider negative passed: exit1, marker absent,
no bootstrap command started. The affected positive base-version, SDK/submodule,
full-constraint and actual IDF-environment checks passed on the unchanged provider
inputs. Root explicitly authorized reuse of c90 target results: no target command,
flag, application/core or provider content changed. There was no second target,
Rust/configure or full-bootstrap run, and the old build is not relabelled with the
new source identity. recipe-source-bindings.json preserves both input identities.

One fresh Rust RISC-V consumer build passed in3.770s, configure in30.811s and
one normal target build in24.057s (2252Ninja steps,8jobs). No full host suite,
Stage A replay, target fault variant, USB, CI or physical test ran.

The app is1,236,336bytes, SHA256
7fdd674ccb434d1864f8ab7375ffee34d7bd78a8291e96407140fd3ed3df7083.
Readback identifies ELF32 little-endian RISC-V, single-float ABI and16byte stack
alignment. The linked Rust STORAGE is5920bytes at0x4ff57578 in internal DRAM.
This confirms the linked artifact's layout, not physical stack/RAM behavior.

The generated SDK configuration has zero semantic key/value changes against
the historical normal snapshot. Actual app header and flasher args say
DIO/80MHz/16MB; the unchanged QIO selection boolean also remains in sdkconfig.
Use the generated string/header/flash arguments when identifying artifacts.
Offsets are bootloader0x2000, partition table0x8000 and app0x20000; these are
file-analysis results, not authorization or evidence of a flash operation.
C6 guard mode0 and entropyUnavailable0 are recorded in generated CMake inputs.

A Python bootstrap RED is retained. UV0.11.28 --require-hashes rejects broad SDK
range constraints while parsing the same input. The corrected source keeps all
57exact version/input hashes, syncs them, then immediately runs the unchanged
SDK checker with the entire admitted constraint body. uv pip check and actual
IDF environment strict check also pass; no range was relaxed/skipped.

The final Python environment is new and pip-free. esptool5.6.0 was rebuilt
offline from authenticated publisher sdist
86c7249e9cc3a824e032ede9ba20abad057a2c49e231418cc4f02b177bb36f42
using pinned setuptools84.2.1. Its160installed source files checked against the
sdist match exactly. Its original LICENSE is retained. The earlier private wheel
is not required; metadata/wheel byte reproducibility is not asserted. The first
partial bootstrap contained only setuptools; it was retired after preserving its
RED command/result/log and inventory. No SDK/tool/cache input was deleted.

The old private environment scripts, external config baseline and historical
patched component checkout are not normative inputs. The recipe uses explicit
tool/cache/work roots and public pins. The chosen SDK/Rust/Python installations
still physically live in the selected existing tool directories; the
residual-dependencies.json list distinguishes those active installations from
optional download caches and retired dependencies. Moving/deleting an active
installation requires rebinding/recreating its generated environment first.

Results and limits are separate from reproducibility: the previous app was
1,236,368bytes, and the new image has a different identity. Project version,
compile time, paths and source-derived tool metadata can change bytes. Source
and config equivalence plus one successful clean build do not establish
bit-for-bit reproduction or renewed physical qualification.

The proof directory contains original command/results and logs. Larger logs are
deterministic gzip; log-bindings.json records both raw and compressed hashes.
generated/ contains only generated config/lock/flash metadata. Artifacts remain
external and are identified in artifacts.json. No SDK/toolchain/cache/image is
archived in this repository. source-config-equivalence.json binds the unchanged
implementation. The recipe and exact public input/license instructions are in
apps/p4/recipe. Artifact inspection used standard readelf/nm/size/esptool on
files only.

Hardware evidence from b259 remains historical. Entropy health/production,
real identities, custody, offline consent, camera-after-lease, reset/log/RAM and
LCD behavior are not newly qualified. Root reviews this frozen source/proof;
no push/CI/hardware action is part of this maintenance task.
