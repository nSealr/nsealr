# PCB development and present capability

Reviewed 2026-10-18. There is no frozen nSealr production schematic, routed PCB, verified component inventory or physically qualified assembly recorded in this restart. There is a candidate architecture, a source-based component shortlist and executable CAD tooling evidence. [Validation](validation.md) records earlier electrical/pin/resource studies and unresolved manual access. Exact hardware availability remains unknown in `work-items.json`.

## From user requirement to a manufactured device

```mermaid
flowchart LR
    R[Requirements and threats] --> C[Exact parts, manuals and budgets]
    C --> B[Evaluation-board experiments]
    B --> S[Reviewed schematic and libraries]
    S --> L[Factory rules, stackup and layout]
    L --> M[Reviewed manufacturing package]
    M --> E[First-article measurements]
    E --> D[Corrected design and qualification]
    D --> P[Small production lot and unit tests]
    P --> Release[Reproducible developer/product release]
```

| Gate | Required artifact and actual check | Owner in roadmap |
| --- | --- | --- |
| Requirements | Use cases, adversaries, active interfaces, custody, trusted UI, owner/developer lifecycle, environmental and mechanical envelope. Derive measurable limits. | P01, S04, H03 |
| Parts and reference review | Exact ordering codes/package/stepping; dated datasheets, reference manuals and errata; selected sections and unresolved access. Pin/alternate-function allocation, voltage and current margins, RAM/flash, bus pullups, reset/startup and debug limits. | H01 |
| Bench feasibility | Real MCU/SE commands, selected display/input path, resource usage, entropy/fault behavior, power sequencing and allowed ownership transitions on identified kits. Evaluation-board radios/package/supply differences remain explicit. | H02, H02S, H03; H04 freeze |
| Schematic capture | Native KiCad project with project-local reviewed symbols/footprints, exact pin numbers, connector mating view and polarity, rail names and net classes. Independent datasheet-to-symbol-to-footprint checks; ERC and explicit net assertions. | H05 |
| Layout preparation and routing | Selected manufacturer's stackup, copper/clearance/drill/assembly constraints and production-test access before routing. Placement, return paths, decoupling loops, USB geometry, thermal/current paths, sensitive buses, expansion isolation, edge/enclosure clearance. Review copper and mechanical views, not only counts. | H06 |
| Manufacturing package | Matching native sources, BOM with approved substitutions, CPL/placement orientation, Gerber/drill or accepted equivalent, assembly drawings and fabrication notes. Inspect exported CAM and reconcile every fitted/DNP part and orientation. Hash the exact package. | H07 |
| First articles (EVT) | Inspect assembly and shorts; current-limited initial power; rail/reset/clock measurements; flash/debug; interfaces/UI; SE commands; thermal and controlled faults. Record board/silicon IDs, instruments, operator and raw results. | H08 |
| Design verification (DVT) | Apply corrections and repeat affected tests on the intended revision. Power interruption, battery/USB faults, update/recovery, input integrity, manufacturing variability and applicable environmental/ESD/EMC tests. Security testing follows the stated attacker model. | H09, V03, S05 |
| Production validation | Small-lot yield, fixture repeatability, per-unit pass/fail and traceability, protected provisioning/signing roots, shipping state, recovery and support. Generic Board release owns this independently of Nostr. | B03 or R01/R02 |

EVT, DVT and production validation are purposes, not a demand for three different revisions if one revision passes all applicable evidence. A design change reopens its affected tests. An agent can prepare designs, procedures and analyze instrument data; an identified person or genuinely connected bench must perform wiring, inspection and physical measurements. A specialist AI review does not replace required independent electrical/security expertise.

## What the AI tooling has actually demonstrated

The clean October 18 tuple is KiCad 10.0.7, official `kicad-python 0.8.0`, protobuf 5.29.6, MCP 1.30.0 and KiPilot commit `303e62010172bf99c2aa41c10237c18bcabcca7a`. Installation resolved normally and the installed binding matched the official wheel. A three-component resistor-divider board is the tool test fixture; it is not the nSealr design.

| Operation | Evidence and present limit |
| --- | --- |
| Create native schematic/PCB and local libraries | The schematic was generated as native S-expressions; the fixture PCB used the AppImage's bundled legacy `pcbnew`/SWIG API. KiCad accepted the files and expected components/nets were checked. This is not MCP board creation/placement, interactive schematic IPC or a qualified security-device circuit. |
| Detect intentional faults | Disconnected schematic pin/label and PCB short/connectivity/parity faults produced failing checks; corrected inputs passed. Five default ignored DRC rule classes are recorded, so this is not “every possible rule enabled.” Production needs its own reviewed rules. |
| Read a live PCB through MCP | Board summary, footprints, pads and text actually exercised. Tool discovery alone is not evidence. |
| Modify through MCP | Text edit/save exercised with disabled-mutation rejection, dry run, stale-value rejection, editor restart persistence, restoration and second restart verification. One writer owned the project. |
| Export and reconcile | Schematic PDF/netlist, board SVG, three-row BOM/CPL, nine Gerbers and drill output with three holes; independently asserted three nets, seven pads and thirteen tracks. Counts accompany semantic checks; they are not physical compatibility proof. |
| General placement, routing, zones and rule changes through MCP | Not qualified by a text-edit canary. Each operation needed for H05/H06 must be demonstrated and reviewed before use on the real design. |
| Native schematic IPC, headless IPC, full 3D/mechanical and SPICE workflow | Not demonstrated. Stable IPC scope and binding availability constrain these; use explicit native/CLI workflows where qualified. |
| Electrical correctness, manufacturability and security | Not established by the canary. These need the design-specific analysis and physical gates above. |

Two compatibility limits remain visible. The binding's API source is 10.0.6; its direct `check_version()` raises `FutureVersionError` for live 10.0.7 because it compares the complete version tuple, without capability negotiation. KiPilot exposes this mismatch as a warning; the six operations above passed despite it. Separately, fresh-process imports of `board_jobs`, `board_rules`, `schematic` and `schematic_types` fail in this binding. There is no blanket compatibility or 135-tool qualification claim.

The stable [KiCad IPC documentation](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/) and [CLI manual](https://docs.kicad.org/10.0/en/cli/cli.html) define different surfaces. MCP is an adapter for issuing operations, not the design authority. Keep native KiCad files, semantic net checks, visual reviews and independently inspected manufacturing exports as the durable artifacts.

## Reference designs: what can actually be learned

The following findings come from selected schematic pages and source paths. They are not complete audits of the referenced products or permission to reuse their code/designs without license review.

| Reference and pinned source | Useful finding | Consequence for nSealr |
| --- | --- | --- |
| [Trezor Safe 7 hardware](https://github.com/trezor/trezor-hardware/tree/f469f4ca0bed731f505f270636a3a459d2f3b931/electronics/trezor_safe_7) | Public Rev D schematics cover main, UI FPC and antenna FPC; selected pages show STM32U5G9ZJ and the SE/UI/power organization. No native Safe 7 PCB/BOM was found in the inspected tree. | Study domain and peripheral ownership. Its larger MCU and different feature set do not validate the U585 memory/pin budget. A custom UI flex is not a universal display connector. |
| [Trezor firmware storage](https://github.com/trezor/trezor-firmware/blob/5fdc180b99bd763c3d18411bba686909875eb337/storage/storage.c) | The implementation combines TROPIC/OPTIGA-related protection and caches storage encryption/authentication keys in MCU memory. | Two SEs can strengthen a particular at-rest/PIN protocol; this source does not support a blanket “the MCU never holds secrets” claim. Analyze active-use exposure and common failure domains. |
| [TROPIC USB Devkit](https://github.com/tropicsquare/devboards/tree/5457ca1e0534df59e5587dba332f30014d7874dc/TROPIC01_USB_Devkit) | TS1303 schematics/native files expose MCU–SPI–SE wiring, GPO and SE power gating. Firmware B documents raw USB–SPI bridging and host-side key handling. | Useful electrical/command bench, not a self-contained trusted signer. Its USB-C plug/Rd arrangement must not be copied as a two-orientation receptacle design. Match product revision, fitted TROPIC part and received configuration. |
| [TROPIC shields and mini boards](https://github.com/tropicsquare/devboards/tree/5457ca1e0534df59e5587dba332f30014d7874dc) | Native schematics/BOMs provide smaller SPI/voltage/connector reference circuits and host-specific shield connections. | Useful for isolated component experiments. An exposed SE bus is a development convenience, not a production security boundary. Connector compatibility needs exact pin, power and level checks. |
| [TROPIC security advisories](https://github.com/tropicsquare/tropic01/tree/90747cac7c0261408c0ca767d272894f481f2cf2/doc/security_advisories) | Physical fault advisory `ODR_TR01_SA_2026012900`, public v1.0 dated June 3, 2026, records a January 27 report (`TR01_CVD_2026012900`). The inspected source did not establish a qualified remediation for our intended part/threat. | Keep the candidate conditional. Do not infer immunity from openness, product adoption or a newer-looking part number. Recheck advisory applicability at procurement and freeze. |
| [BitBox02 Nova January 2026 disclosure](https://blog.bitbox.swiss/en/bitbox-01-2026-marmorera-update/) | The manufacturer reports two OPTIGA configuration-related issues and a firmware correction. Its account distinguishes a retry-limit bypass from seed exposure because the reset destroys the seed-decryption key. | H02S must negatively test object access, partial reset, surviving secrets and counters. A configured “not readable” property requires observed enforcement. This is a vendor incident report, not our exploit reproduction. |
| [COLDCARD security status](https://coldcard.com/security/status) | The manufacturer's October 2026 page describes the earlier RNG incident, corrected generation paths and the fact that firmware updates do not repair previously weak seeds. | Device gates must trace the entropy provider through the actual binary/runtime and exercise failures. Incident recovery must distinguish a repaired implementation from already compromised identities. We have not independently audited the incident. |

A source review can invalidate a proposed guarantee before buying hardware. It cannot measure a side channel, prove a complete product exploitable or transfer another manufacturer's qualification to nSealr.

Graph revision 5 makes these lessons explicit: S02 defines the entropy boundary/provenance contract, H02S tests SE object/reset enforcement, and V01/V02/V03/Q02/Q03 verify actual entropy-provider invocation and failures. B02/B03 independently verify the generic SDK entropy service and its release binary/assemblies, without a Nostr prerequisite. None of those acceptance criteria is closed by this research.

## Component decisions still to earn

| Block | Working shortlist/direction | Required decision evidence |
| --- | --- | --- |
| Main MCU | U585VI candidate; U5A5VJ if measured internal memory requires it; S3 comparator | Actual firmware resource and UI/driver support, lifecycle/debug, exact package/power option and current manual/errata. Safe 7's U5G9 is reference evidence, not a mandatory migration. |
| Secure element | One SE first; SE051C2, Trust M or TROPIC only if the required operations, lifecycle and threat fit | Exact configured part and accessible complete mandatory command/security documentation, actual bench command proof and advisory closure. These are not algorithm-equivalent alternatives. Native BIP-340 is unproven. |
| Display and local input | Direct MCU-controlled display/input; exact module plus adapter | Review readability, memory/bandwidth/latency, reset and DMA ownership, connector/voltage and mechanical fit. No universal FPC assumption. |
| Power and battery | USB-C 5 V sink baseline; charger/regulator shortlist from prior study | Current entitlement and reset defaults, cell protection/NTC, polarity, charge/thermal limits, power-cut behavior and off-state backfeed. No frozen BOM or assumed USB-PD support. |
| Expansion/debug | Documented voltage and power, private SE buses, protected maker buses | Per-pin mux and ownership, safe startup/disconnect, lifecycle access and clear separation of trusted UI from general expansion. |
| Camera/NFC/radios | Profile-specific or removable where justified | A concrete user operation, independent bus/resource/RF/power budget and security analysis. Camera for QR and NFC reader/mailbox/card emulation are different requirements. |

The aim is a useful programmable security board with explicit guarantees. It does not require every peripheral on revision one or simultaneous mutually untrusted firmware applications. New firmware authors get the generic Board SDK; complete SSH/FIDO/wallet applications and any multi-application isolation need their own specifications and qualification.
