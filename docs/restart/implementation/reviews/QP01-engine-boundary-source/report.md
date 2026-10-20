# QP01 boundary preparation: source and decision review

**PASS_source_and_decision_preparation_only; no findings.** Candidate
`b45812362e2f8340572aaaffd0384a9662fc6fb2`, tree
`bfa3923cbbd79037fd9b2a1ef8105b7935468c10`, author `/root/a02_sol`;
reviewer `/root`, Sol6.1 xhigh. This accepts a bounded host experiment as useful
preparation, not a product ABI, target implementation or completed physical task.

The finite question was whether Python can drive the accepted Rust owner's real
review/consent/signing path without implementing a second signer. Two concrete
boundaries were compared: `ctypes` with a C ABI, and a native CPython extension.
The former is a reasonable choice for this isolated experiment: the actual
environment already supplies ctypes, the wrapper is a Rust cdylib, and the
isolated 31 registry identities already occur in the root lock. No new registry
or Python dependency, production lock change or generic user-key API is admitted.
This evidence does not choose the final product boundary or prove that an ARM
image supplies compatible Python/libffi/glibc components.

Primary references support the limited mechanism, not its safety by themselves:
[Python ctypes](https://docs.python.org/3.12/library/ctypes.html) documents C
shared-library calls and callback lifetime obligations;
[Python extension guidance](https://docs.python.org/3.12/extending/extending.html)
describes the CPython API alternative;
[Rust linkage](https://doc.rust-lang.org/reference/linkage.html) describes cdylib;
the [Rust FFI guidance](https://doc.rust-lang.org/nomicon/ffi.html#ffi-and-unwinding)
distinguishes supported unwinding from abort and foreign exceptions. Online
reference text is not execution evidence for the exact compiler or a panic path.
The actual host/compiler/native-library identities remain in the original logs.

Root verified all 44 added paths are confined to
`docs/restart/implementation/QP01/engine-boundary/`, with every pre-existing path
and Git mode identical to accepted input `5d047b5d3150d58a1a45caf00c8946b7f18364bb`.
The 43 manifest members, 43 source bindings, 13 original command/raw-log pairs,
eight executed-context source hashes, environment binding and archived library
digest match. Original expectations and raw request were committed at
`c9c83bf45159ac7b3fc32e4657763c2b70a2115e` before the wrapper, and the selected
`profile-empty` row is exactly the independent K01 input. Executed source
`7c755299e27a8affb5defa42fe318dfab4e2ff1c` is unchanged in the final candidate.
See [validation.json](validation.json) for the checked counts and command outcomes.

The separate code component is accepted only within its own verdict:
`cabe9f785957e44d124fc1250505fe0842955312`,
**PASS_canary_component_only**, reviewer `/root/b01_final_review`.
Root verified its eight review-only paths, seven paired artifact hashes and exact
candidate binding. Its separately recorded 0.042-second rerun uses the unchanged
archived x86_64 library, not a new build; actual cases match the original trace.
It observes 33 callbacks, a 344-byte independently verified signed event,
rejection, premature approval, a caught Python display error, nested Busy and
fresh-call recovery. Root did not repeat that code review or execution.

The original recorder setup error and native-metadata AttributeError remain
preserved. The metadata correction follows the observed built-in `_ctypes`
module and records the interpreter/native secp library instead; it changes no
product, expected result or threshold. Raw readelf whitespace is retained rather
than rewriting original evidence. Existing docs validation passed; final bundled
delivery still requires exact affected metadata review and the normal protected
PR and actual-main integration gates.

Python and its native components remain trusted, including their ability to
forge local actions or inspect memory. Pointer validity, alignment, nonaliasing,
callback lifetime and no foreign unwind are caller preconditions. Busy is not
protection against invalid or aliased pointers: zeroing precedes guard acquisition.
The fixed public scalar3 and deterministic auxiliary input are test fixtures,
not production entropy. The constant clock and bounded step loop do not enforce
a hard callback deadline or asynchronous cancellation. Rust panic recovery was
not injected, and abort/foreign faults are not covered. The single blocking call
does not qualify persistent custody, arbitrary user-key import or repeated
product sessions.

All three QP01 and six Q02 acceptance criteria remain incomplete and byte-exact.
Exact kit/image/operator/access, ARM build/link/run and native ABI, physical
camera/QR/display/input, no-persistence, entropy/provider failures, backend scratch
erasure and target resource measurements remain open. No production transport,
provider, real key or physical release is enabled. The accepted unchanged K01
reviews are reused, not reissued. Custom PCB research is independent of this path.
