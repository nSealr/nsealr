This is the experiment's C ABI, not a new nSealr wire contract or stable product
API. Numeric request wire2 remains distinct from the internal authorization-v1
domain and the historical inventory-v1 directory. Before any product adoption,
the actual selected interface needs a versioned ABI and reviewed Q02 source;
this preparation does not prescribe a second contract registry.

The single exported `qp01_public_fixture_run` takes a nullable presentation
callback, a caller-owned9,216-byte output buffer, its exact capacity and a
distinct writable `size_t *written`. It accepts no key or request input. The
callback uses C integers and byte spans only:

```c
typedef int32_t (*present_callback)(
    uint32_t kind, uint32_t index, uint32_t total,
    const uint8_t *label, size_t label_bytes,
    const uint8_t *body, size_t body_bytes,
    const uint8_t *position, size_t position_bytes);
int32_t qp01_public_fixture_run(present_callback present,
                                uint8_t *output, size_t capacity,
                                size_t *written);
```

`kind`0 is Data and1 is Decision. Action0 is Next,1 Approve,2 Reject and3 Back;
other values are a display error. Rust maps these into actual `LocalInput` and
`review_step`, which alone decides whether consent exists. No approval boolean,
digest or copied diagnostic state can bypass this. The static32×8 geometry is a
conformance fixture, not a measured240×240 renderer.

One non-copyable `AuthorizationSession` is private to the synchronous call. The
fixed public scalar3 is consumed/wiped from its input array; Rust selects the
original scalar and uses the accepted backend. It cancels and locks the owner
on the ordinary result/error paths, and ordinary Rust destruction owns cleanup
on an unwinding panic. Neither Python nor the ABI receives an owner, key pointer,
Rust struct layout or generic secret-loading API. This is not persistent custody;
the experiment constructs a fresh public owner per call.

Label/body/position pointers borrow a public Rust frame only during that callback.
Python copies them before returning and holds a strong `CFUNCTYPE` reference for
the full call. There are no asynchronous callbacks or retained frame pointers.
The returned event is copied from the core's private public-result staging into
the caller's buffer only after signing verification/completion. Python owns the
public result copy; that allocation must remain live and unaliased, as must the
distinct aligned length pointer. Null/alignment/capacity checks cannot prove
arbitrary raw pointer validity. Invalid caller pointers or aliasing remain
undefined behavior, not a safe error channel.

Success is0. With valid supplied buffers, Busy−2, local Reject−3, invalid review−4,
display failure−5, caught unwind−6 and other engine failure−7 return zero length
and a fully zero output. Argument error−1 may occur before buffers can be safely
written; callers must ignore output then. The canary actually exercises Busy,
Reject, invalid review and display failure. Reject additionally invokes the
engine signing API and checks that its provider is uncalled and output is wiped.
It does not inject a Rust panic or invalid pointer.

A nonblocking atomic guard refuses concurrent/reentrant calls, including actual
nested ctypes reentry during a presentation. It is released only after the outer
call settles. Python's GIL is not an owner lock: CDLL calls release it. Python
callbacks catch `BaseException` themselves and return the explicit failure value;
they must not depend on ctypes' handling of an uncaught exception. A callback may
still block indefinitely, and the fixture clock is constant. No bounded native
call time, asynchronous cancellation, hard deadline or GUI scheduler is proven.
User rejection/display failure ends this operation; a later call is a fresh owner,
not a retry of old consent.

The wrapper uses `panic="unwind"` and `catch_unwind` inside `extern "C"`; no Rust
unwind is permitted through Python/C frames. Rust's
[FFI guidance](https://doc.rust-lang.org/nomicon/ffi.html#ffi-and-unwinding) and
[catch_unwind documentation](https://doc.rust-lang.org/std/panic/fn.catch_unwind.html)
distinguish caught unwinding from process abort. This cannot recover an abort,
segfault, invalid-pointer fault, foreign exception or necessarily a panicking
payload destructor; a panic hook can also run. No process-wide secret cleanup
follows from this code. The versioned1.95 web page was unavailable in this
session; actual1.95 compilation confirms the API is present, without treating
the newer online standard-library version as the observed compiler.

Python and every camera/decoder/presenter/GPIO/native component remain in the
trusted computing base. They can forge local actions, read process memory or
retain camera/import buffers. The ABI keeps semantic ownership in Rust but
provides no hostile-Python isolation. The provider and clock here are explicit
deterministic public fixtures. Production entropy, native-buffer quiescence,
imports/recovery, swap/dumps/logs/image writes, physical display/input binding,
backend scratch/compiler moves and target resource measurements remain open.

Reproduction uses the unchanged pinned environment source in
`docs/restart/implementation/R00/evidence/final/environment.json`, with only a
task-local `CARGO_TARGET_DIR`, then the recorded `cargo build --locked --offline
--release --manifest-path .../probe/Cargo.toml` and
`python3 .../canary.py <built-so> <public-result.json>`.
[Actual argv/environment/source bindings](checks/host-01/context.json) and
[raw command receipts](checks/host-01/commands.json) are authoritative; no root
build recipe, package installer or physical runner was introduced.
