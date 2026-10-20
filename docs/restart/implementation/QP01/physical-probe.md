# Minimal identified-kit optical probe

This is a ready procedure with missing prerequisites, not an executed report.
QP01's three physical criteria remain open. Keep the maintainer's existing
identification/operator follow-up pending; do not substitute a model, image,
driver or tester. Record each missing command/library/connection as blocked.
Only an admitted disposable public-fixture session is contemplated. No real
identity, production signer, purchase, flash or provisioning happens here.

Before execution, the single kit record needs exact board/revision and header
population; camera sensor/module/CSI cable/connector; display controller/HAT
revision/rotation/power and SPI pins; all button/joystick pins and active levels;
power source, USB data wiring and attached storage; microSD/image origin and
hash; kernel/firmware/boot configuration; Python/native library versions; operator,
access, recording equipment and environmental conditions. All are currently
unverified. Record source URLs/commit/package hashes with the actual sample.

1. Identify and inspect without signing. Photograph labels and cable/header
   orientation, reconcile the manufacturer's exact pinout and inspect radio,
   USB/serial/debug/auxiliary paths. On the actual image capture model/CPU,
   kernel, userland width, OS/libc and Python ABI, for example:

   ```sh
   tr -d '\0' </proc/device-tree/model
   uname -a
   getconf LONG_BIT
   getconf GNU_LIBC_VERSION
   cat /etc/os-release
   python3 -c 'import platform,sys,sysconfig; print(platform.machine(),sys.version,sysconfig.get_config_var("SOABI"))'
   ```

   No model string proves absent radios. Record physical circuitry and actual
   radio/interface/service observations separately; blocked/disabled/absent are
   different claims. Determine ARMv6 versus Zero2-class and 32/64-bit userland
   before choosing a Rust/native-library target. Preserve failed discovery.

2. Bind the image and setup evidence. Hash the supplied image/source manifest
   before use; inspect boot-media mutability, overlays, effective camera/SPI
   config and all remote/gadget/console paths. Capture swap, mount and dump/log
   settings, not only ssh state. If the reference package and its native ABI
   dependencies are installed, run the existing setup command with output on
   a verified RAM filesystem:

   ```sh
   nsealr-vault hardware-probe --out /run/qp01/hardware-probe.json
   cat /proc/swaps
   ulimit -c
   ```

   First verify `/run/qp01` exists on the intended RAM mount. Record exact argv,
   exit/stdout/stderr and file hashes. A probe's `ready` or literal
   `persistent_secret_present` flag is not acceptance. An unsigned image hash
   does not prevent substitution of the microSD, camera, display or controls;
   record inspection/seal/supervision assumptions and any unproved boot trust.

3. Prove capture and decode with a public static request, without importing a
   secret. For a supported rpicam image, [official camera diagnostics](https://www.raspberrypi.com/documentation/computers/camera_software.html#list-cameras) include
   `rpicam-hello --version` and `rpicam-hello --list-cameras`. A finite example is
   `rpicam-jpeg --nopreview --timeout 1000 --width 480 --height 480 --output /run/qp01/public-qr.jpg`.
   These settings are diagnostic examples, not product bounds. Record the
   detected sensor/modes, actual image dimensions/size and capture time. Pass
   those bytes to existing `PyzbarQrDecoder.decode_qr`; compare decoded raw
   bytes with the independently retained public input, then use the existing
   strict envelope decoder. Blank, unrelated and malformed inputs must not
   become accepted requests. Set a finite frame limit for scanner experiments
   and stop on native timeout/resource failure. Record frame/native decode
   time and memory separately from envelope/reassembly limits. The official
   diagnostic bypasses the legacy factory for this one-shot feasibility test;
   it does not implement a modern continuous camera adapter.

   Reuse `protocols/contracts/v1/vectors/transports/qr-envelope-kind-1-basic.json`'s
   exact `envelope` as the retained input and its `decoded` object as the
   independent decode expectation. Its numeric signing version is2; neither
   the inventory directory `v1` nor container name `qr-envelope-v0` changes it.
   Existing `vectors/invalid/qr-envelope-malformed.json`, padded/invalid-UTF8/
   oversized cases and the long-event envelope supply retained hostile/boundary
   inputs; do not regenerate expectations from the photographed output.

4. Prove display and input through real drivers. Identify and bind a concrete
   SPI presenter to `PillowSt7789DrawTarget`/the existing review display; if none
   exists, this step is blocked rather than replaced by a fake target. Inspect
   rotation, colors, glyph bounds, edge clipping, every page/index and visible
   final values on the actual 240×240 panel. Exercise the existing GPIO adapter
   only after verified wiring: next, scroll, distinct approve/reject, held key,
   simultaneous reject+approve and stuck release. Capture observed pin/action
   traces and finite recovery behavior. No action here authorizes signing.
   The direct constructor exposes `release_timeout_polls`, and
   `read_review_button` exposes `max_polls`: choose and record finite diagnostic
   values before running rather than inheriting the factory's unlimited waits.
   A desktop screenshot, four compact sections or a layout-command list cannot
   prove complete trusted engine inspection or physical consent.

5. Prove the optical return using a public fixture response, not a newly signed
   event. Feed it through the existing QR matrix and response-display adapters,
   scan it back using an independently identified receiver and compare exact
   bytes/correlation. Record module scale, quiet zone, brightness, distance,
   angle, lighting and success/failure conditions. Compare bounded static and
   multipart behavior on this actual pair before QH01 framing selection; record
   missing/mixed/repeated/over-limit/timeout cases. Existing fit checks/default
   repetition counts are not measured scan reliability or authentication.
   The existing `vectors/transports/qr-animated-response-kind-1-basic.json`
   supplies fixed public return frames; use its actual records without
   inferring a fresh signature or full client workflow. The fake 2×2 QR matrix
   in the adapter unit test proves plumbing only and is not a physical QR input.

6. Inspect persistence and interruption on disposable public data. Record
   normal/cancel/decode-fault/restart/power-loss observations, boot-media writes,
   swap/crash/core/journal/application logs and native buffers/copy lifetimes.
   Establish detector sensitivity with a deliberately persisted labeled public
   canary, then compare normal/fault runs and offline media inspection. State
   the limits of byte/pattern searches and Python/native/OS copies; a negative
   search is not physical erasure or compiler-proof zeroization. Do not fill a
   historical smoke template with inferred outcomes. Store actual source,
   image/binary/library hashes, sample/operator/instruments, raw outputs,
   photos/traces, expected/observed results and remaining risks together.

These steps establish identified-kit optical feasibility only when actually
executed and independently reviewed. They do not close Q02. After an actual
accepted K01 tuple and Q02 admission, the separate engine round trip must use
the real Rust owner: local public identity import, complete inspection,
consume-first approval/rejection, qualified entropy, verified signature and
independent response verification, plus target ABI/stack/RAM/timing and
session-only custody proof. Existing file/approved-boolean Python flows cannot
stand in for that test. Pi feasibility stays independent of P4 and custom PCB.
