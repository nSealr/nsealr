# Pinned software baseline

From a clean committed checkout of `nSealr/nsealr` on Linux x86_64/glibc:

```sh
python3 tools/baseline/bootstrap.py /absolute/new/baseline
python3 /absolute/new/baseline/firmware/tools/baseline/run.py /absolute/new/baseline
```

`bootstrap.py` is the single installation entry point. The destination must not
exist. It fetches the current committed core candidate and the exact companion,
Raspberry, specs, lab, hardware, smartcard and website commits in `inputs.json`.
Some legacy migration sources require authorized GitHub access. Supply
`--mirrors /path/to/authorized/sibling/repos` to use existing Git repositories
**only as source transport**; each is freshly fetched with its commit verified.
No existing dependency cache, working tree content or tool installation is
copied. No private source history is imported into the public core repository.

For public core reproduction without migration-source access, add `--core-only`.
It still installs all pinned runtimes and runs the complete core `make ci`, but
cannot claim multi-repository integration. The caller's committed nsealr tree is
the source; fetch/checkout the intended candidate before invoking this command.
Uncommitted tracked changes are rejected. Each run needs a new destination.

The directory layout is intentionally **siblings inside one isolated root**:

```text
baseline/
  firmware/   # nSealr/nsealr; legacy name required by integration consumers
  companion/ raspberry/ specs/ lab/ hardware/ smartcard/ website/
  .tools/     # runtimes, wheelhouse, caches, config, temporary outputs
  evidence/   # commands, UTC timestamps, logs, status and SHA-256
```

This supersedes the old private `workspace/scripts/bootstrap.py` behavior that
created nested repositories under its own checkout while its consumers assumed
siblings. It does not reorganize the maintainer's current checkout or decide
future A01/A02 source disposition.

Host prerequisites: Python 3.12+ for this driver, Git, make, rsync, a C compiler,
Linux x86_64/glibc, trusted TLS roots and network access to GitHub, Node, Rust,
PyPI and npm. No sudo is required. The kernel, libc, C compiler, TLS trust roots
and system utilities remain host inputs, recorded in the environment manifest.
This is a cold user-space bootstrap, not a container or hermetic OS build.
Source retrieval uses the caller's authorized Git credential configuration;
subsequent commands use a minimal recorded environment. HOME is unchanged;
package caches/config and Python user installations point under `.tools/`.

Runtime pins: Python 3.12.15 (standalone build 20261013), Node 24.22.0 (bundled
npm 11.19.1), pnpm 10.33.4, rustup 1.29.1 and Rust 1.95.0 with rustfmt, clippy,
llvm-tools-preview and `riscv32imafc-unknown-none-elf`. cargo-deny 0.20.2 and
cargo-llvm-cov 0.9.1 use **prebuilt official release binaries**, with URLs and
SHA-256 in the manifest. Rustup verifies its downloaded component checksums.
Python wheels, runtime archives and pnpm archive are hash checked before use;
Node workspaces use their existing frozen lockfiles. Repeated Python Makefile
setup uses an offline wheelhouse and exact constraints, including build tools.
The core's actual Rust CI still compiles and tests source.

Python 3.12.15 is the September 30, 2026 security release, selected after checking
[Python's release page](https://www.python.org/downloads/release/python-31215/).
Its standalone archive hash comes from the
[20261013 upstream release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261013).
Other hash authorities are [Node checksums](https://nodejs.org/dist/v24.22.0/SHASUMS256.txt),
[npm package metadata](https://registry.npmjs.org/pnpm/10.33.4),
[rustup checksum](https://static.rust-lang.org/rustup/archive/1.29.1/x86_64-unknown-linux-gnu/rustup-init.sha256),
[cargo-deny release](https://github.com/EmbarkStudios/cargo-deny/releases/tag/0.20.2),
[cargo-llvm-cov release](https://github.com/taiki-e/cargo-llvm-cov/releases/tag/v0.9.1)
and each pinned wheel's PyPI version metadata. Pinning does not certify these
tools or legacy dependencies safe; audits and new patches still need review.

`run.py` uses `make -k ci` to retain independent later gate results when an earlier
gate fails. The exit remains nonzero. Full integration runs the unchanged lab
`make integration` recipe in one invocation. It does not pass command-line
PYTHON/VENV overrides (which would leak through recursive make into Raspberry
setup). npm launcher logging is set to `error`; application stderr is neither
filtered nor discarded. All existing quiet-input/error assertions remain active.

The inherited companion generated API document may fail freshness. Preserve
that failure and inspect a disposable regeneration; do not change the generated
API-review acceptance merely to turn CI green. Live relay tests are disabled;
real browser sessions and physical devices require separate acceptance. Safe
hardware-probe and simulator tests do not establish real hardware operation.
The runner writes these explicit skips even if all executed software gates pass.

For an independent replay, checkout the same tooling candidate into a new Git
clone and run bootstrap into another absent destination. Use `run.py --smoke`
for the second installation's version/layout/core/fixture smoke only; it cannot
substitute for the first complete suite run. Inspect `commands.json` and
`environment-manifest.json`, preserve logs and hashes, and obtain an independent
review of the exact candidate before closing R00. No previous CI run counts.

Tool boundary checks: `python3 -m unittest discover -s tools/baseline -p 'test_*.py'`.

The isolated lab checkout receives the declared `overlays/lab-provenance.patch`
against exact preimage hashes. Its original checker mistakes core `SOURCE.json`
for an upstream vector. The overlay validates that one metadata file's pinned
upstream commit, complete source/snapshot vector inventory and hashes before
excluding it from byte comparison. All real fixture assertions remain active;
new regression cases reject bad provenance, missing/extra inventory, changed
hashes and changed real vectors. Bootstrap records the patch and output hashes;
the runner rejects any undeclared source delta. Original failed baseline logs
remain evidence, and successful integration applies only to this overlay tuple.
