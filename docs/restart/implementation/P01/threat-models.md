# Per-profile threat models — specification candidate

Read with [requirements](requirements.md). Status: candidate for independent review; no profile is qualified. The controls below are required behaviors with acceptance owners, not claims about current code or assemblies.

## Common assets, actors and trust

Assets: the user identity scalar and derived shared secrets; correct operation/recipient/plaintext; selected public identity; one-use local authority; PIN/storage/update roots where present; availability and recoverability. Transport identities are separate assets and do not substitute for user identity.

The host client, Bridge inputs, relay, USB/QR bytes, labels, timestamps and operation previews are potentially hostile. A compromised host may alter requests, reorder/delay/replay results, flood memory, lie about app identity and publication, or read plaintext deliberately returned to it. No signer protects confidentiality of a message already shown to a compromised client. The screen/control path, executing trusted firmware and qualified custody implementation form the operation-authority boundary; host assertions cannot enter it as approval.

People can misread prompts, lose backups, reveal them to a camera, install modified firmware or replace devices. The design must make supported decisions inspectable and recovery understandable. Usability testing is part of the gate, while user scores cannot waive a security failure. The supply chain, vendor SE authority and independent review limits are documented; no device is promised resistant to every physical or invasive attack.

## Commercial ESP32 without SE

| Boundary | Required design and limits | Evidence owner |
| --- | --- | --- |
| Local user / host | MCU owns screen and physical confirmation. USB carries bounded requests/results, never user nsec or approval booleans. Check per-request identity and complete reviewed action. | D01/V01, S03/K01/C01 |
| Firmware / debug | Exact SoC/SDK, boot enforcement, update/recovery and debug lifecycle. Development mode is distinct from admitted persistent use. Locking flags are tested on hardware. | D01/D02/D03 |
| Persistent custody | Storage wrapping/PIN design must withstand the declared host/flash/rollback threat. No SE protection is claimed. Extraction, fault, silicon and PIN enforcement limits are explicit. | D02 and independent admission |
| Interfaces / memory | Identify radios and enabled channels; control secret placement and driver exposure. No claim of a physical air gap. Measure entropy, stack, RAM and timing on actual binary. | D01/V01/D02 |
| Loss / recovery | Local backup and same-key restore; interrupted storage/update and reset failures cannot expose state or bypass the declared unlock model. | D02/D03 |

## Raspberry Pi QR

| Boundary | Required design and limits | Evidence owner |
| --- | --- | --- |
| Optical / local user | Bound frames and reassembly before parser/crypto work; separate recovery import from event QR. Screen and GPIO input are actual trusted-path dependencies. QR is hostile input. | Q01/QH01/QP01/Q02 |
| Linux image / adapters | Kernel, boot media, camera/display drivers and retained Python/FFI code remain trusted. Rust does not isolate a hostile Python caller or modified kernel. Determine actual image integrity and boot enforcement; do not call signed downloads enforced secure boot. | QP01/Q02/Q04 |
| Session custody | No persistent identity storage, swap, recovery frames, thumbnails, diagnostic logs or dumps containing secrets. Account for caller/interpreter/camera copies. Power-off/Drop are not proofs of instant physical RAM erasure. | Q02/Q04 |
| Physical access | Inspect exact model for absent versus disabled radios, USB/data paths and removable-media/substitution risks. A radio-absent Pi is still susceptible to substituted image/peripheral or invasive physical access under declared limits. | QP01/Q02/Q04 |
| Recovery | Reload locally each session; verify checksum, selected identity and full output. Loss of kit should not require surrendering the backup to a desktop helper. | Q02/Q04 |

## ESP32-P4 QR

| Boundary | Required design and limits | Evidence owner |
| --- | --- | --- |
| Optical / local user | Same manual QR semantics as Pi; actual camera, screen and physical consent path measured independently. A P4-family name does not prove a supported sensor or control. | QP02/Q03/Q05 |
| MCU / companion | Inspect exact silicon, SDK, camera DMA, secret-memory placement, debug and update behavior. List companion chips and their connections; a disabled ESP32-C6 is not physically absent. | QP02/Q03 |
| Custody / faults | Session-only identity, no persistent secret copies. Trace actual entropy invocation; handle reset/power interruption and update recovery without resurrecting authorization. | Q03/Q05 |
| Physical access | No SE non-exportability claim. Declare physical substitution, memory access and fault limits; optical operation is not universal extraction resistance. | Q03/Q05 |

## Custom Board running Signer

| Boundary | Required design and limits | Evidence owner |
| --- | --- | --- |
| Trusted UI | MCU owns display/input and relevant buses/DMA. Expansion does not expose unrestricted SE buses or the trusted-review path. A secure element cannot authenticate pixels it does not control. | H02/H03/H04/H05/H08, V02/V03 |
| SE / MCU custody | Define exact stored objects, wrapping, PIN counters, reset/reconfiguration, channel enrollment, host-binding secrets and exposure in MCU RAM. Never infer native BIP340/non-exportability from generic ECC. Address exact vendor advisories. | S04/H01/H02S/V02/V03 |
| Firmware ownership | Distinguish owner firmware roots from vendor SE applet/update authority. Test erasure/re-enrollment, unsigned/rollback images, recovery and transitions using identified sacrificial units before irreversible settings. | S04/H02/H02S/B02/V02/V03 |
| Power / state | Electrical protection and persistence survive declared brownout/reset/update failure cases. Pre-layout calculations and bench probes are repeated on assemblies. | H03/H04/H08/H09/V03 |
| Actual assembly / production | Bind source, SDK, bootloader, silicon, SE configuration and board revision to measurements. Close independent findings before pilot identities and requalify final production changes. | V03/S05/P03/R01/R02 |

## Generic Board + SDK

The initial developer owns one trusted firmware image. Linked SDK components do not isolate hostile applications. Driver primitives are not complete SSH/FIDO/wallet products. APIs name actual custody location, algorithms and supported/unsupported lifecycle operations; unsupported properties produce explicit errors. Developer mode, owner-secured mode and product-qualified Signer state have different admissible secrets and ownership transitions.

B01 specifies APIs; B02 proves services on evaluation hardware; H08/H09 repeat board electrical/service behavior; B03 independently qualifies intended assemblies, developer reproduction, small-lot testing/provisioning, release entropy/update/recovery and shipping state. None of these inherits Nostr pilot evidence or requires Nostr semantic code. A new firmware author must know which state survives reset, recovery and reprogramming.

## Required hostile scenario families

1. Wrong expected user; valid foreign transport/user signatures; account change; mixed-session and stale result.
2. Duplicate/trailing JSON; hidden field/tag; hostile Unicode; unsupported kind; size/depth/queue flood; indefinite pending work.
3. Replay/race of approval; cancel/lock/expiry/reset during operation; mutated review or response.
4. Malformed/mixed QR frames; secret-import QR presented as an operation; camera/log/dump persistence.
5. Message recipient/plaintext/ciphertext/seal substitution; missing outer context; unsupported NIP-04 or opaque signing.
6. Failed/stuck entropy or unintended provider; stack/RAM overflow; unqualified runtime/FFI fallback.
7. Interrupted vault write/update; PIN-counter rollback; partial reset or permissive SE object read; firmware-owner transition retaining privileged state.
8. Wrong part/footprint/rail, backfeed and USB-power entitlement, thermal faults, manufacturing substitution and insufficient unit-test coverage.

Each family needs its own independent expected result and exact candidate/resource record. Structural validator success, simulated signing, a source audit or AI agreement cannot replace a physical result at the boundary being claimed.
