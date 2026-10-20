#!/usr/bin/env python3
"""Correct the current reproduction recipe for separate embedded and host graphs."""
import argparse
from pathlib import Path
from transforms import Changes

DOCUMENT='''# Reproduce the Rust artifacts

Run `make repro-build` with the [pinned product tools](../tools/baseline/README.md).
The gate performs two clean release builds of the embedded and host workspaces,
then builds from another filesystem path. It compares the core device library
across both runs and both paths, and the host executable across the same-tree
runs. A mismatch fails the gate. Actual hashes belong to the exact source,
toolchain, host and command evidence, not to a permanent value in this guide.

The root `Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml` define the embedded
graph. `apps/desktop-simulator` has its own workspace, lock and toolchain file.
Both pin Rust 1.95.0 and use the committed vendored sources through Cargo source
replacement. Offline/locked builds must preserve both dependency closures.
Python 3.12.15 projects committed contract values into Rust build output;
it does not calculate expected cryptographic or behavioral answers.

From a clean product checkout with the pinned tools installed:

```sh
make repro-build
```

The [actual recipe](../ci/repro_build.sh) uses separate output directories:

| Artifact | First build output | Comparison |
| --- | --- | --- |
| Core device library | `target/repro-a/core/riscv32imafc-unknown-none-elf/release/libnsealr_core.rlib` | Same tree and different checkout path |
| Host oracle | `target/repro-a/host/release/desktop-simulator` | Same tree |

To build each separately, using the same path remapping as the gate:

```sh
NSEALR_SOURCE_ROOT="$(pwd -P)"
RUSTFLAGS="--remap-path-prefix=${NSEALR_SOURCE_ROOT}=/nsealr" \\
  cargo build --release --offline --locked -p nsealr-core \\
  --target riscv32imafc-unknown-none-elf --target-dir target/manual/core
RUSTFLAGS="--remap-path-prefix=${NSEALR_SOURCE_ROOT}=/nsealr" \\
  cargo build --release --offline --locked \\
  --manifest-path apps/desktop-simulator/Cargo.toml --target-dir target/manual/host
```

The host oracle embeds its source directory to locate the authoritative
`protocols/contracts/v1/vectors` artifact. `NSEALR_VECTORS_ROOT` changes its
runtime input location, not its embedded bytes; no cross-path executable
identity is claimed. The core comparison qualifies this library build, not a
finished device application or a cross-host/compiler guarantee.

When either lockfile changes, refresh the vendor set for both exact locked
graphs, preserve licenses, run both dependency audits and rerun the complete
coverage and reproduction gates. The current recipe uses stable path remapping;
it does not introduce a nightly toolchain. The OS, system compiler, linker and
hosted runner remain recorded environmental boundaries. Reproducing artifacts
does not qualify release-signing keys, physical devices or production custody.
'''

def apply(target,output):
 c=Changes(target);c.put('docs/reproducible-build.md',DOCUMENT.encode());return c.apply(output,'Document exact separate-workspace reproduction commands paths and measured scope')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
