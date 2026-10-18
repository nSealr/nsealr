# Architecture decisions

## Product and platform

**nSealr** is the project. **nSealr Signer** is the Nostr signing application. **nSealr Bridge** connects Nostr clients to devices. **nSealr Board** is the programmable hardware, and **nSealr Board SDK** supports firmware authors. These descriptive names avoid maintaining a separate brand for each chip. They are project naming decisions, not trademark clearance.

Connected and Offline are interaction modes, not a user-controlled switch that automatically preserves custody or security. Every supported artifact has an exact device profile. A commercial ESP32 without SE, a Pi QR kit, a P4 QR kit and the custom board have separate qualification and release paths.

## One engine, appropriate adapters

Use a Rust portable engine for canonical Nostr operations, bounded parsing, review content, one-use operation authorization and output verification. Separate platform adapters own entropy, time, storage, display/input and transports. Build distinct embedded applications and a Linux application; sharing source does not require one universal binary.

Use maintained cryptographic implementations after target qualification. Do not preserve custom hash code, freely cloned/debug-printed secret objects, reusable boolean approval or unbound identity merely because older tests pass. Tests must assert the corrected security property.

Bridge is TypeScript where browser/Node integration needs it. Prefer one coherent public SDK with explicit browser/Node entry points and internal modules, rather than publishing internal package boundaries. NIP-07 and NIP-46 integration must route through actual device approval; a NIP-46 client is not a hardware-backed signing server. Enforce origin/session/peer/user identity and queue/time bounds at the boundary that owns them.

Do not elevate host labels into hardware-authenticated identity. A browser extension can authenticate an origin within its browser boundary; a device cannot infer it from an untrusted label. A host-terminated encrypted NIP-46 request also does not authenticate the forwarded plaintext to the device. Stronger provenance requires a concrete device-verifiable protocol; local consent must bind the actual operation regardless. See [client qualification](../product/client-qualification.md) for encryption-context and DM-review requirements.

Pi adapters may remain Python where that is the simplest maintained integration, using one defined engine boundary. The existing Python signer can serve as a differential test oracle; it is not a reason to maintain two permanent normative engines. A narrow vendor C adapter for camera or USB is acceptable when measured support warrants it; it must have explicit ownership, version pinning and boundary tests.

## Custody and trusted review

Define boot trust, active interfaces, storage/SE behavior, physical attacker assumptions, display ownership, input ownership and recovery for each profile. Display pixels are trusted only if the executing firmware and the relevant peripherals, buses and DMA paths are controlled as required by that profile. A secure element cannot make a hostile display honest.

Approval consumes a grant bound to canonical operation, account, policy version, request/session and expiry. Cancellation, replay, power interruption and malformed requests are negative test cases. The host cannot assert that approval occurred. Capabilities describe supported operations; they are not attestation or proof of readiness.

## Generic board boundary

Board SDK owns generic MCU/peripheral support, secure-element drivers, boot/update/recovery hooks, owner lifecycle and examples. It has no Nostr event semantics. One trusted firmware image is the initial model; ordinary linked libraries do not isolate mutually hostile applications.

The owner-controlled development lifecycle and a qualified Signer lifecycle need explicit roots of trust and transitions. Replacing firmware must not leave privileged MCU or SE state accessible to a new image unexpectedly. Test reset, re-enrollment, rollback and post-provisioning recovery on sacrificial hardware before irreversible settings.

Board selection remains an evidence gate. MCU, SE count/model, display connector, power and NFC are not frozen by the old BOM. More components do not automatically yield independent trust domains. Native BIP340/secp256k1 capability must be demonstrated on the exact selected command set; generic ECC or an internal X25519 channel does not establish it.

Expose documented standard interfaces where they serve concrete uses: USB-C, debug, GPIO buses and selected display/expansion connectors. Define voltage, power budget, pin ownership, safe startup and isolation. There is no universal display FPC pinout. Sensitive SE buses and trusted review paths must not be exposed as unrestricted maker GPIO.
