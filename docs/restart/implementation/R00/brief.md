# R00 implementation brief: isolated software baseline

Parent: R00, acceptance as recorded in `docs/restart/work-items.json` at
`768e8a35ae541f53f5da9c7bea7bf5c577fb474d`. Author: `baseline_execution`.
Independent specification and final-candidate reviewer: assigned by coordinator;
the author cannot approve either review. This brief precedes implementation.

## Purpose, authority and inputs

Provide one reproducible software bootstrap and evidence procedure without
changing signer semantics or claiming product/security/physical qualification.
The three stable local acceptance IDs below map in order to R00 acceptance:

- R00-A1: a fresh isolated checkout installs pinned Python, Node/pnpm and Rust.
- R00-A2: explicitly resolve sibling/nested layout and classify API generation
  drift and launcher noise while preserving behavioral assertions.
- R00-A3: execute relevant suites and complete integration, retaining failures,
  exact inputs and explicit live/physical skips.

Source inputs inspected on 2026-10-18:

| Repository | Commit | Use |
| --- | --- | --- |
| nsealr | `768e8a35ae541f53f5da9c7bea7bf5c577fb474d` | Candidate parent, Rust workspace and restart authority |
| companion | `13414320537d0208fc3ef8e43bd0723c98c1d5e0` | Node build/test/API and host integration |
| raspberry | `d1534d9dcfba8fe4a35cea2ed3529e32a5003dc6` | Python adapter tests and simulated integration |
| specs | `8bb8cca71355bcf8d81a093bcee9f3fe6915b121` | Existing fixture oracle and validators |
| lab | `3303ab17a28ed32419576627d5abb93db3999635` | Full existing integration program and helper tests |
| hardware | `340697d6713a671e9e01b0dc874ec999ab071601` | Existing hardware-document validator/fixtures only |
| smartcard | `ec5da94a05882122e8a794f55f1af3f96a95c696` | Archived software/protocol baseline |
| website | `9cec39a89d6a2d2cc5747b8aae9d4b47a52eb7cd` | Existing site build and tests |
| workspace | `e7d3a2654973628d040354805370f6520e3704ad` | Historical bootstrap audit only |

No private history or audit report is imported into public Git. The published
bootstrap may fetch pinned private migration inputs only for a caller already
having access; this prerequisite must be explicit. Public core reproduction is
independent of private access. Full-program public source migration belongs to
A01/A02. Tool version selection must be recorded with exact upstream URLs and
content hashes; Node/pnpm is coordinated with S01. The existing Rust pin is
1.95.0, with cargo-deny 0.20.2 and cargo-llvm-cov 0.9.1 from current CI.

## Observable contract and owned boundary

New tooling lives under `tools/baseline/`; explanation and selected bounded
public evidence live under `docs/restart/implementation/R00/`. Root Makefile
and CI may gain a thin documented entry point or consistent exact Python pin.
No task graph, product-contract, security implementation, CAD or private source
checkout is edited. Any necessary helper fix is delivered as an explicit
hash-bound overlay applied only to isolated baseline source copies; its source
provenance and diff remain reviewable. Runtime source behavior and assertions
must not change. New product/security defects are reported to their owners.

Bootstrap takes an absent destination, a committed nsealr candidate and pinned
source/tool manifests. It creates a sibling layout inside that destination:
`firmware/` (nsealr compatibility folder), `companion/`, `raspberry/`, `specs/`,
`lab/`, `hardware/`, `smartcard/`, `website/` plus `.tools/` and `evidence/`.
The nsealr folder name is explicitly a legacy integration alias, not repository
identity. Bootstrap must reject an occupied destination rather than silently
reuse or mutate it. Caller-supplied local Git mirrors may replace transport
only; requested commit and clean checkout are verified. Existing global
Python/Node/Rust, package stores, target directories and virtualenvs are not
reused. Lockfiles, exact runtime versions and hashed Python dependency inputs
are preserved. Failure exits nonzero and retains partial diagnostic evidence.

A Linux x86_64/glibc host with Python3 for the driver, Git, curl, tar/xz, make,
and a C toolchain is the initial supported target. Kernel, libc, compiler,
network trust roots and system libraries are host inputs, recorded rather than
container-isolated. This proves clean user-space installs, not a hermetic OS,
bit-identical downloaded registries, Windows/macOS or physical devices.

The runner records argv, cwd, effective nonsecret environment overrides, UTC
start/end, exit status, logs and SHA-256. It attempts every declared software
suite even if an earlier independent suite fails. The complete unchanged lab
integration recipe must run in one invocation; a tail rerun never substitutes
for that result. Inherited failures remain visible and cannot become passes.
A selected correction must have an independent negative check where relevant.
No real keys, relays, cards, USB device approval, camera/display/GPIO checks,
flashing or provisioning are authorized by this software experiment.

## Evidence plan and independent oracles

1. Save pre-change audit: compare old bootstrap and layout paths; reproduce
   companion API drift and strict quiet-stdin failure where the pinned host
   tuple still triggers it. Historical logs are context, not fresh proof.
2. Verify frozen Node installs, hash-locked Python dependencies, pinned Rust
   toolchain/components/target and locked cargo utility installs. Record host
   prerequisites and every version. Empty destination/caches are the oracle
   for cold install; existing canonical caches cannot count as this evidence.
3. Execute core `make ci`, companion `make ci` (plus individual later gates if
   its API freshness check stops CI), Python/specs/hardware/site suites, lab
   tests and the full lab `make integration` recipe. Keep native assertions.
   Capture source statuses before and after each run; generated output drift
   is classified, never silently accepted.
4. Isolate npm launcher diagnostics from application stderr by using the
   pinned launcher/environment, not by filtering stderr or disabling an
   assertion. Demonstrate empty input stays quiet and malformed input still
   fails noisily. Prevent make override leakage by selecting environment
   paths rather than recursive command-line `PYTHON`/`VENV` overrides.
5. Regenerate API output in a disposable copy solely to expose/hash the
   difference and show the freshness check passes there. Do not fabricate
   API-review approval or incorporate unreconciled generated API semantics.
6. Replay documented bootstrap from a fresh Git checkout into another absent
   destination with separate caches; execute version/layout/negative checks
   and affected smoke checks. Preserve full first-run integration evidence.
7. Explicitly list skipped live-relay tests, real browser-session tests and
   absent physical resources; simulated or safe probe checks retain their
   limited names. Hash public artifacts and obtain distinct exact-candidate
   final review before integration. Metadata may follow the reviewed code
   candidate to avoid self-referential commit hashes.

Network failure, unavailable pinned distribution, missing authorized source
access or a host prerequisite makes the affected experiment inconclusive.
A behavioral failure is a failure, not an environment skip. Keep its test
and route repair to the owning task unless an agreed bounded tooling defect.

## Alternatives and delivery

Rejected: reusing `.restart-tools` caches (not a fresh install), editing the
private workspace in place (wrong owner and publication boundary), suppressing
all stderr or relaxing tests (weakens the oracle), updating moving branches
instead of pins (invalidates the input), and importing all private history to
make bootstrap public (violates source disposition and confidentiality).

Deliver brief/spec review, separate tooling candidate, fresh execution logs
and manifest, independent final review, then coordinator-controlled
integration. No old CI result closes this task. Remaining decisions are exact
Node/Python distributions and whether any freshly observed tooling failure
requires a narrowly reviewed overlay; all choices are documented in the
implementation and result, without expanding into S01/S02 fixes.
