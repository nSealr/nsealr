The smallest useful in-process candidate is a Rust `cdylib` with a narrow C ABI,
loaded by Python `ctypes`. Rust owns the operation, original key, raw parser,
complete inspection, consent, signing and verified output. Python supplies
trusted display/input callbacks and copies public results. This is a preparation
decision with an executed fixed-public-identity host canary, not an admitted
product API, Pi build/image or physical result.

Input is actual main `5d047b5d3150d58a1a45caf00c8946b7f18364bb`, tree
`87a54f18d45591c21bd97c24a1f3e47b64f77777`. Root accepted K01 source through
`4c0d43ba83a029b23c3ba0771f4bd4d64697c2ed`; PR40/full CI39478676631 passed.
Actual-main CI39480230426 was pending when this assignment was issued. Root now
accepts the same source after full main CI/verify118826559634 and fresh main-only
source checks, with [receipt74ab189f](https://github.com/nSealr/nsealr/blob/74ab189f49ec2d0e09f4049d26f55d082338f49d/docs/restart/implementation/reviews/K01-current-delivery/adoption/actual-main-acceptance.json).
This is later integration evidence, not a source/environment change or a reason
to repeat the canary. QP01's prior
[source preparation3330972](https://github.com/nSealr/nsealr/blob/3330972dd7cc4f36be2622cdafdcfbe8c81adec4/docs/restart/implementation/QP01/brief.md)
and [distinct reviewb0cbd1f](https://github.com/nSealr/nsealr/blob/b0cbd1f69caeb7f26a97c61bb657f9adc501e97d/docs/restart/implementation/reviews/QP01-source-preparation/report.md)
remain exact historical inputs. Their camera/presenter/image and unidentified-kit
limits still apply; no hardware survey or repeated diagnostic was needed.

An existing command does not supply this boundary. Pi `cli.py` calls the Python
reference signer; `hardware_flow.py` accepts Python secret strings, builds its own
review and passes an approval digest to that signer. The desktop Rust CLI is a
vector replayer, not an interactive shared owner or in-process API. Core is a
Rust library with no C/Python exports. The old `QrReviewFlow` wraps a diagnostic
`TrustedReviewSession`; its preview boolean cannot create K01 consent. These
paths are bound to the input commit in [evidence.json](evidence.json), not
inferred from names or a successful build.

Only two concrete modes were compared:

| Mode | Relevant cost | Decision |
| --- | --- | --- |
| Rust C ABI `cdylib` + Python `ctypes` callbacks | Explicit integer/pointer/length signatures, manual lifetimes/errors, target C ABI and libffi availability must be qualified. No new project dependency or Python header build is needed on the observed host. | Selected for this finite experiment. |
| CPython extension using the C API | Adds CPython object/reference/error handling and a `Python.h`/extension-build interface before it solves this same narrow callback exchange. | Deferred; no need demonstrated by this operation. |

Python documents shared-library loading, explicit signatures, callbacks and their
required lifetime in [ctypes3.12](https://docs.python.org/3.12/library/ctypes.html).
Its [extension guide](https://docs.python.org/3.12/extending/extending.html)
describes the CPython-specific C API and recommends considering ctypes for
calling C libraries. Rust documents `cdylib` as the artifact for another language
in [linkage](https://doc.rust-lang.org/reference/linkage.html). The selection is
an engineering inference from those interfaces and the actual canary, not a
claim that either mode isolates Python or automatically supports ARM.

[canary.py](canary.py) loads [probe/src/lib.rs](probe/src/lib.rs) through a real
C function pointer. Independent expectations were committed first at `c9c83bf4`:
one exact pre-runtime K01 `profile-empty` row under public scalar3, zero public
auxiliary bytes, and a fixed numeric-wire2 request. No caller-selected key,
request, provider or device route exists. Executed source is `7c755299`; the
actual [raw commands](checks/host-01/commands.json) and
[callback/output trace](checks/host-01/result.json) show:

- All 33 actual core frames cross into Python in order, including full
  label/body/position/index/total and the separate decision. Python returns Next
  and then Approve; the core produces a 344-byte signed event.
- Every event field, ID and signature matches the old independent row. The
  unchanged Python `crypto.event_id` and libsecp256k1 verifier independently
  accept this single output. This does not rerun the K01 corpus.
- Python Reject reaches the owner; an actual subsequent `sign_approved` refuses
  `InvalidState`, with provider invocation count0 and all9,216 output bytes zero.
  Premature Approve on a Data frame also refuses. A caught Python display
  exception returns an explicit error, producing zero output.
- A nested FFI call inside the callback is refused Busy before a second owner
  or callback is created. After the failure cases, a fresh fixed-fixture call
  succeeds. The original owner never crosses the ABI.

The isolated probe lock contains the same31 registry package/version/checksum
identities as the root lock; only the probe package is new. Core default features
remain disabled; no root/host/historical lock, vendor, feature, CI or runtime file
changes. The wrapper intentionally links host `std` for unwind containment;
this is not another no_std claim. Actual tools are Rust1.95.0 and Python3.12.15
on x86_64/glibc2.41. ELF inspection records libc/libgcc/loader dependencies and
GLIBC symbols through2.33, and exactly one exported fixture entry point. This
particular `.so` is not usable on ARM. Its exact hash/copy, source bindings,
environment and feature output are recorded in the evidence.

For a later admitted Q02 adapter, retain measured camera/decoder, pixel presenter
and button plumbing; replace Python semantic review, key custody, approval-digest
authority and signing orchestration with the Rust owner. Forward exact bounded
scanned envelope/request bytes: do not deserialize to a Python dictionary and
reserialize before the core parser. Existing Rust envelope decode functions can
retain those bytes; the diagnostic QR preview is not an authorization bridge.
Python's existing renderer can be reused only if it displays every Rust-owned
label, value and position completely before returning a fresh local action.
Its four-section preview and existing default button-step bound are not parity
proof for these33 frames. No production flow is connected by this canary.

[The ABI/lifetime contract](abi.md) identifies the remaining adapter obligations.
The canary owns one operation inside one blocking call; it does not implement a
persistent import/session/opaque-handle API. Q02 must keep its eventual owner
inside Rust for the full intended session, bind trusted clock/provider/display
lifetimes and prove cleanup across that actual lifetime. No additional engine,
semantic parser or generic driver framework is indicated by this experiment.

The exact Pi model/revision, ARMv6 Zero versus a possible Zero2 variant, userland,
sysroot, Python/libffi/native-library ABI, camera/panel/wiring, operator/access,
image integrity/channels and persistence facts remain unknown as already
recorded. No new resource question is opened. This host result is not an ARM
compile/link/run, optical probe, secret-persistence test, entropy/provider health
or physical consent proof. All three QP01 and all six Q02 criteria remain
incomplete; future product work requires its actual source/admission and device
evidence. The sole graph and existing physical procedure are unchanged.
