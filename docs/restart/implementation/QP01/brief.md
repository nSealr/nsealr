# QP01 Pi source and feasibility preparation

Useful Python camera, decoder, framebuffer, GPIO and QR adapters can be retained
as bring-up/reference code. There is no hardware-wired application entry point,
bootable Pi image or Python interface to the shared Rust owner at this source. The first optical probe is
therefore feasible to prepare, but QP01 remains incomplete until the exact kit,
image and physical observations exist. No runtime implementation is admitted by
this document.

Input is `b159425e7fdb0111bed904e69381dafd23ade6e4`, tree
`539db1953555eca4a9cc36c3b636c91d1cbf5d44`: normal Q01 PR39 merge. Root's
[actual-main acceptance b48a3bbd](https://github.com/nSealr/nsealr/blob/b48a3bbdf8738c8b74724d259ab11e1608d304b8/docs/restart/implementation/reviews/Q01-current-delivery/adoption/actual-main-acceptance.json)
now confirms full CI39469150123 and fresh source correspondence, with unchanged
earlier tamper controls reused. The source is unchanged; no rebase or repeated
diagnostic follows. R00/T01/Q01 host proof does not identify a Pi image.
B01's ongoing K01 edits are outside this input and
were not read. [Evidence](evidence.json) binds the unchanged QP01/R00/Q01 criteria,
source paths, four finite diagnostics and explicit remaining inputs; the [sole
graph](../../../../plan/work-items.json) is unchanged. The existing operator/kit identification follow-up remains
pending; no duplicate question is opened.

The implementation rows below refer to [camera/display/GPIO adapters](../../../../apps/pi/app/nsealr_vault/seed_signer_hardware.py),
[composition](../../../../apps/pi/app/nsealr_vault/adapters.py),
[reference flow](../../../../apps/pi/app/nsealr_vault/hardware_flow.py),
[CLI](../../../../apps/pi/app/nsealr_vault/cli.py) and
[setup probe](../../../../apps/pi/app/nsealr_vault/hardware_probe.py).
Their exact input modes/blobs/hashes and existing fake-test sources are bound
in the evidence file; no new physical execution is implied.

| Existing path | Actual callable implementation | Disposition and missing evidence |
| --- | --- | --- |
| `seed_signer_hardware.py:315` `PiCameraJpegFrameSource` | Imports legacy `picamera.PiCamera`, requests 480×480/24fps by default, captures JPEG to BytesIO and closes the camera. | Preserve the frame-source interface. Replace this legacy capture implementation for a supported libcamera/Picamera2 image; an old image is only a separately identified development experiment. No sensor, DMA/native-buffer lifetime, frame-byte/pixel/work bound or target latency is qualified. |
| `:347` `PyzbarQrDecoder`, `:200` `SeedSignerCameraQrScanner` | Optional Pillow JPEG load and native zbar decode via pyzbar; takes the first symbol, preserves bytes, polls static or accumulated animated envelopes. | Retain as a bounded-probe candidate, subject to exact target library/ABI and hostile-image/native-decoder qualification. Optional `max_frames` is not an implemented native-decoder time/memory ceiling; default polling can be unbounded. Framing checks do not authenticate a sender. |
| `:381` Pillow draw target, `:433` review display, `st7789_layout.py` | Produces a 240×240 framebuffer and applies layout commands, then calls injected `present_image`. | Retain pixel/layout transport only. No SPI panel/controller object or CS/DC/reset/backlight/rotation initialization is supplied. Identify and bind a real presenter; verify font metrics, clipping and full Rust-owned inspection before trusting the display. A four-section Python preview is not full S03/K01 review. |
| `:473` response display, `:539` QR matrix renderer | Optional python-qrcode, square-matrix checks, quiet zone, integer module fit and animated display cycles. | Retain for optical measurement. Defaults and mathematical fit do not prove scan-back/readability or freeze single/multipart framing; QH01 owns that comparison. |
| `:140` GPIO adapter and `:93` profile | Configures pull-ups using BOARD numbering; reject precedes approve, waits for release; next37/scroll35/approve33/reject40 are reference physical-pin numbers. | Retain configurable input boundary only after actual HAT wiring/polarity/pin conflicts and stuck/simultaneous-button tests. Timeout parameters exist but defaults do not establish a finite physical fault policy. The kit description does not prove this map fits. |
| `adapters.py`, `hardware_flow.py`, `cli.py:465` | Composed in-process interfaces exist; CLI `flow` actually constructs file adapters and a Python reference signer. `hardware-probe` is callable setup inspection. | Keep file/mocked paths and Python/libsecp256k1 as independent software reference. Q02 replaces production custody, semantic review, consent and signing with the accepted shared engine. There is no hardware-wired CLI entry point. |
| `session_source_qr.py`, import/backup flows | Native nsec, mnemonic and legacy SeedQR parsers and RAM-session reference flows exist. | Preserve reference coverage; do not infer SeedSigner interchange/backup compatibility from a kit or class name. Q01 native original-nsec recovery and actual Python/native copy/persistence limits still need their owning implementation and physical proof. |
| `apps/pi/os/`, hardware `os-profile.json` and `requirements.json` | Requirements/manifests, not an image builder or downloadable image. | Reuse their channel/custody evidence categories with current Q01 requirements. No boot chain, radio isolation, no-secret-write or substitution property is established. |

The camera mismatch is concrete: `hardware_probe.py:192` accepts either
`picamera` or `picamera2` module presence, but the default camera factory at
`seed_signer_hardware.py:568` constructs only the legacy class. Raspberry Pi's
current [camera documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)
marks original Picamera/legacy camera software unsupported and describes
libcamera/rpicam tools. Thus a green module check does not make the existing
factory work on a modern image. No new camera port is written here.

The setup probe is supplementary evidence: model-string matching is not a radio
inspection; boot markers are substring checks, not effective configuration;
module presence is not a native driver call; swap/ssh checks are partial runtime
observations. `persistent_secret_present: false` is a literal report field, not
a storage scan. Its readiness boolean cannot replace any physical criterion.
The historical hardware full-flow template also names old repositories and
compact review concepts: reuse its record categories, not an inherited PASS,
four-page completeness claim or production authorization.

The compiler pin is Rust1.95.0. Its [versioned ARM target source](https://github.com/rust-lang/rust/blob/1.95.0/compiler/rustc_target/src/spec/targets/arm_unknown_linux_gnueabihf.rs)
defines `arm-unknown-linux-gnueabihf` as ARMv6 hard-float, 32-bit, GNU/Linux
with VFP2, and describes kernel3.2/glibc2.17 support. Local `rustc --print cfg`
recognizes that target. This is a supported compiler option, not a compiled Pi
engine. Only x86_64 and the existing RISC-V target libraries are installed in
the pinned environment. No ARM compile/link/run was attempted.

The [Rust ARM guide](https://doc.rust-lang.org/rustc/platform-support/arm-linux.html)
identifies the original Zero's ARM1176/BCM2835 as ARMv6. A possible
[Zero2W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) has a
Cortex-A53 and onboard wireless; this does not identify the maintainer's kit.
Resolve exact board/revision and 32/64-bit userland before selecting target,
sysroot and native libraries. An ARMv7 binary is not a substitute for an ARMv6
build, and an `armhf` package label alone does not settle CPU requirements.
Neither the name Zero nor the setup probe proves radio absence.

R00's [bootstrap](../../../../tools/baseline/bootstrap.py) explicitly requires x86_64/glibc and its [inputs](../../../../tools/baseline/inputs.json) pin x86_64 Python/native
wheels. It is host reproducibility evidence, not a reusable Pi image installer.
The Pi package requires Python>=3.9 and mnemonic/secp256k1; camera/Pillow/zbar/
GPIO/SPI/qrcode are optional and unpinned there. Exact ARM-compatible versions,
sources, licenses, native builds and linked dependencies remain image inputs.
Current [diagnostics](checks/commands.json) show a Rust `lib`, no cdylib/staticlib/Python module;
there are no PyO3/CFFI/ctypes calls to this core in the Pi path. CFFI used by the
independent Python crypto package is not a shared-engine binding.

For Q02, retain Python camera/display/GPIO plumbing where measured parity holds
and keep one actual K01 Rust owner for secrets, parser, complete inspection,
consent and verified output. A single measured in-process boundary is the
minimal candidate to compare; no public raw-secret getter or Python re-creation
of authority follows. Its concrete ABI is not selected here. It must bind target
CPU/float ABI, libc/loader, Python ABI and native libraries; define buffer and
opaque-owner lifetimes, fresh clock/provider/display failures, exception/panic
containment and cleanup. Rust rlib/no_std or RISC-V final-link evidence alone
does not supply that boundary or prove Pi execution. Q02 also owns actual peak
RAM/stack, latency, entropy invocation/failure and source-to-binary evidence.

[The minimal physical procedure](physical-probe.md) starts without identity or
signing, records exact image/channel/hardware facts, then measures camera/decode/
display/buttons and optical scan-back using public fixtures. Full shared-engine
signing waits the actual accepted K01 tuple and Q02 admission. No product, graph,
dependency, CI, lock, hardware manifest or prior proof is changed; no purchase,
new harness, broad suite or hosted-CI observation is performed.
