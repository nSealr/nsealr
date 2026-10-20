# QP01 engine-boundary canary component review

**PASS_canary_component_only; no findings.** Exact candidate
`b45812362e2f8340572aaaffd0384a9662fc6fb2`, tree
`bfa3923cbbd79037fd9b2a1ef8105b7935468c10`; author `/root/a02_sol`, independent
boundary reviewer `/root/b01_final_review`, Sol6.1 xhigh. This is a review of
the new fixed-public-fixture C ABI/ctypes canary, not another review of the
unchanged K01 engine or an approval of a product/device adapter. Root separately
reviews the preparation decision, primary sources and global scope.

The actual path is Python `CDLL` → the sole exported fixture function → one
private Rust `AuthorizationSession` → raw `begin_request` → `review_step` →
Python presentation callback → core `LocalInput` transitions → `sign_approved`.
See `probe/src/lib.rs:18–80,83–154,166–210` and `canary.py:42–45,67–163` under
`docs/restart/implementation/QP01/engine-boundary/`. Rust includes only the raw
fixed request, imports original public scalar3, and supplies deterministic public
auxiliary bytes. The signature/expected event is not loaded into Rust or passed
through the ABI. The independent `profile-empty` row and request are exact
pre-implementation inputs from `c9c83bf4`; the executed probe/canary/inputs from
`7c755299` are byte-identical at the reviewed candidate. The accepted unchanged core supplies
parser, ownership, complete inspection, one-use consent and release verification;
its security review is reused rather than self-reviewed here.

The five original build/canary/features/readelf/export command-log pairs and
eight actual execution-context source hashes match. The isolated manifest points
directly to that core with default features disabled; all 31 registry identities
already occur in the existing root lock. The archived x86_64 `.so` is the exact
493,312-byte compiled fixture, SHA-256
`3291c34290ce2a96eb692ee191e976ebf6451221a4a6192e00f7dc09438d7a4c`.
Its single exported symbol and observed host/std/unwind features agree with the
source. The component does not add a second parser, signer or approval mechanism.

One allowed rerun of the **existing** canary from this isolated checkout, using
the archived library and unchanged pinned environment, passed in 0.042 seconds.
It crossed all 33 real frames in order, including the separate decision; every
label/body/position was copied inside the callback. The 344-byte event matches
all independent template/key/ID/signature fields, and the unchanged Python
canonicalizer/libsecp256k1 verifier accepts it. Reject returns−3 after an actual
core post-rejection signing refusal with no provider call; premature approval
returns−4; a caught simulated Python display exception returns−5. Each error
leaves zero written length and all 9,216 caller bytes zero. Actual nested reentry
with separate valid buffers returns Busy−2, zeros its buffer and invokes no nested
UI. A fresh subsequent operation succeeds. All new case/frame/action/output
observations equal the original trace; this is a distinct execution, not a new
build or relabelled author run. See [runtime-canary/command.json](runtime-canary/command.json)
and [comparison.json](runtime-canary/comparison.json).

The unsafe ABI preconditions remain necessary: output and aligned `size_t`
storage must be live, writable, distinct and unaliased for the whole call;
callback pointers must remain valid and not unwind. Rust validates null,
alignment and exact capacity, then creates/zeros the output and length **before**
acquiring the atomic owner guard. Consequently Busy is an owner/reentry refusal,
not protection against invalid or aliased pointers; same-buffer reentry is not a
valid test of this contract. Frame spans are public stack-owned borrows valid
only during the callback; the supplied Python callback copies them and holds
strong `CFUNCTYPE` references. Ordinary error/success paths cancel and lock the
owner. `catch_unwind` contains Rust unwinding inside the export with the guard
released by `Drop`; this branch was not panic-injected. Neither it nor Python's
explicit caught RuntimeError proves recovery from abort, foreign unwind, invalid
memory, a failed exception handler, a panic hook or a panicking payload destructor.

The loop bounds review steps, not native callback duration: the fixture clock is
constant, a callback can block, and no external cancellation API or hard deadline
exists. Python/native components remain trusted and can forge input or retain
memory. This owns a single blocking public-fixture operation, not a persistent
import/session/user-key API. Host glibc2.41 and the library's observed GLIBC symbol
requirements through2.33 do not prove ARM/Pi compatibility. No actual target,
physical UI/QR, entropy/provider health, backend scratch erasure, no-persistence
or resource qualification follows. All three QP01 and all six Q02 criteria remain
incomplete. No product edit, rebuild, full CI, crypto corpus, hosted observation,
new public probe or resource question was performed.
