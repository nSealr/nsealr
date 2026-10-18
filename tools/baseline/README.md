# Pinned product bootstrap

From a clean committed nsealr checkout on Linux x86_64/glibc:

```sh
python3 tools/baseline/bootstrap.py /absolute/absent/runtime
python3 /absolute/absent/runtime/nsealr/tools/baseline/run.py /absolute/absent/runtime
```

The existing installer pins downloadable Python, Node, pnpm, cargo tools and
wheels by version and SHA-256. Rustup installs the declared Rust version and
targets. It fetches only the exact current product commit, with its reachable
history for immutable contract/evidence checks. No sibling or private repository
is fetched. The caller's HOME remains unchanged; caches/configuration belong to
the new runtime. Destination reuse, archive hash failures, dirty source and
source drift are rejected. The full run records commands, outputs and failures.

The host OS, libc, compiler, Git, make, rsync and hosted runner are not hermetic.
Downloaded Rust toolchain manifests use the existing rustup trust boundary.
Actual installed browser, live relay, attached hardware and physical security
qualification require separate evidence. Historical R00/S01 multi-repository
inputs and overlay tools are preserved in original Git history and reviewed
restart evidence; they are no longer the active product bootstrap.
