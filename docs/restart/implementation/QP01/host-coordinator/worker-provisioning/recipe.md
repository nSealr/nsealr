Use the selected source tree in this package as the one worker source location for the next separately reviewed host gate: `docs/restart/implementation/QP01/host-coordinator/worker-provisioning/source/{Cargo.toml,Cargo.lock,src/main.rs}`. Preserve the adjacent `LICENSE`. Selection requires these three postimages, not the old RGB branch or a second Git reference. No move into `apps/`, workspace membership, global lock, policy, or CI change is proposed in this probe.

The source export for a checkout containing the package is:

```sh
worker_task_root=$(mktemp -d)
mkdir "$worker_task_root/standalone"
git archive 'HEAD:docs/restart/implementation/QP01/host-coordinator/worker-provisioning/source' | tar -xf - -C "$worker_task_root/standalone"
```

Before compilation, check these exported files against `input-manifest.json`. Provide the exact Rust 1.95.0 x86_64 Linux toolchain and every archive/index record listed in `proof/cache-preflight.json` in a private Cargo home, with checksums checked before use. The concrete probe used the already installed R00 toolchain and copied verified existing local caches; these paths are historical receipts, not availability promises for another machine. Missing tool/archive/checksum is a stop, with no version alternative or download performed by this recipe. A clean checkout alone contains the source and lock, not the external toolchain/registry cache.

Run with the environment and working-directory boundary recorded in `proof/environment.json`: the exported source is its own `[workspace]`, `CARGO_HOME` points to the verified private cache, `CARGO_NET_OFFLINE=true`, the pinned toolchain precedes the observed R00 PATH, and `CARGO_TARGET_DIR` is a new absent task directory. Preserve the firmware workspace configuration as is. The exact build command used here is recorded in `proof/06-build.json`; with those task paths it is:

```sh
cd "$worker_task_root/standalone"
CARGO_HOME="$worker_task_root/cargo-home" \
CARGO_TARGET_DIR="$worker_task_root/target" \
CARGO_NET_OFFLINE=true RUSTUP_TOOLCHAIN=1.95.0 \
cargo build --release --locked --offline \
  --target x86_64-unknown-linux-gnu \
  --message-format=json-render-diagnostics \
  --manifest-path "$worker_task_root/standalone/Cargo.toml"
```

Use Cargo’s successful `compiler-artifact.executable` for the worker binary, require `build-finished.success=true`, then measure the produced file’s bytes and SHA-256. This probe obtained 668,728 bytes and SHA-256 `9f311b6417cc9358c7d9ec89a06edb984799cacc7b49aa815c942596924b11cf`; a later build must record its own actual identity. Do not execute it as a build check. A single matching or differing binary is not a reproducibility result.

For the future caller, require an explicit worker-path/expected-SHA-256 pair supplied from that build receipt as an admitted run input. Neither value may have a default. Require an existing regular executable with the expected identity before any spawn, and preserve the caller’s existing kernel/process identity checks and ownership discipline. A missing receipt, missing argument or identity mismatch stops before spawn. There is no fallback to `1a4…`, `/goal`, another Git reference, another worker, or an unverified cached binary. This is a handoff proposal, not a newly implemented CLI or permission to run this ELF. Selecting a new actual hash requires affected source/input review and real runtime proof; the old `1a4…` ownership contract stays source-specific.

Before this becomes normal provisioning/CI, reconcile the same 11 registry crates with the firmware’s vendored-source guarantee and the actual manifest list in `scripts/audit_rust.py`, then run the unchanged deny policy with mandatory fresh index/advisory acquisition. The local snapshot audit here is only a dated diagnostic. Keep the root manifest’s missing-license warning visible; adding a license field would be a separate input amendment with affected review. Final candidate checks run normally. No CI, existing workspace lock, vendor, policy, graph, caller or operational source change is made by this package.
