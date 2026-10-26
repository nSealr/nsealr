# Public C6 link/reset probe and explicit final decision text

Author `/root/phase1_scope`; coordinator/reviewer/operator `/root`. Base867c9fb4.
The root approved the bounded contract in intake/p4-c6-public-probe-contract.json
(SHA10dfb7780b87fd453f3a98b4a623f744ede682cdd594814341bec9d294312827),
with the added requirement that every returning post-low path attempts low again
and reports actual pad state, even when recovery or cleanup fails. Approval receipt
SHA7c009418068a792e52b4fb0d9d31451f42392f97e432e86c129d50fb7460910f.
No core, plan, crypto, quirc, SDK source/configuration or C6 firmware is changed.

## One measurable public operation

The new c6-reset compile mode3 runs before BOOT check and Rust engine/key init,
with USB data connected for observation. It uses existing IDF6.0.2 public SDMMC
host/SDIO APIs, not esp_hosted or a radio API. SDIO support is already enabled.
Slot1 CLK18/CMD19/DAT14..17 follows vendor870588e6 page1 C6 wiring; MicroSD39..44
is not used. GPIO54 reaches C6 CHIP_PU through R54 on that schematic. The sample
PCB revision, actual pin4 voltage, C6 die/revision/firmware and RF remain unknown.

Only a power-on reset permits an attempt. Other reset reasons show UNAVAILABLE,
query existing GPIO configuration without claiming input-disabled reads, and stop
without automatic re-probing. No host command, touch or BOOT supplies approval.
The fixed internal probe adapter is not an external callback/authority interface.

Baseline requires GPIO54 input enabled/output disabled/high, an IO-only SDIO card
with1..7functions, valid CCCR and a bounded CIS. The parser accepts exactly one
MANFID tuple with generic0092:6666, the configurable defaults documented in the
pinned C6 HINF_CFG_DATA0 register (user146/device26214). This is a conservative
supported endpoint signature, shared/configurable and not a silicon identity.
Unknown IDs or missing positive are UNAVAILABLE before any low/release. CIS reads
at most256bytes/64tuples; bounds, duplicates, truncation and the256byte edge are
covered by native fixtures. No arbitrary endpoint text/MAC/serial is logged.

Once admitted, preload GPIO54 output0 then enable input+output. After10ms sample
the real pad through gpio_get_io_config plus gpio_get_level with input confirmed.
One CMD52 to the same CCCR must time out; a valid reply is a failed causal result,
and other errors are inconclusive. Release exactly once to input/high impedance,
wait1500ms with real time and recover the same CIS/CCCR/function signature once.
Reassert low, sample input/output/pad and require one more CMD52 timeout, then stop.
No loop retries or RF scan; card_init's existing finite SDK command retries are
not promoted to a qualified bound.

The same real start establishes one absolute20s deadline in logic and adapter,
checked between callbacks/commands. The host uses explicit100ms command timeout,
400kHz maximum and fixed internal512byte aligned scratch, with no voltage/power
controller. WDT5s is unchanged. No feed occurs inside SDIO init/read or a GPIO API;
feeds occur only between collected phases/committed UI and cooperative waits.
Vendor blocking/overrun can still require reset and is not a hard20s return proof.
No clock freeze/rescale, core100tick extension or new ACTIVE budget API.

Every returning path after low admission makes a best-effort low call, then reads
actual input/output/pad. Cleanup status remains failed if the call/readback fails,
even when a prior low succeeded. After host teardown the adapter reasserts and
samples once more. A teardown error never returns to feed/new work. Task-level
p4_fatal also attempts low when admitted; SDK panic/WDT/hardware reset bypasses
that hook, and GPIO continuity across reset is explicitly unqualified. On a new
non-power-on boot the probe stops. A pull-up may re-enable C6 on reset; no safe
cleanup or physical isolation claim is inferred from a software flag.

The display/log says PUBLIC C6 LINK PROBE / NO KEYS / NOT OFFLINE PROOF and shows
phase, generic IDs, actual pad/input/output and cleanup errors. The strongest
successful result is LINK CAUSALITY OBSERVED on the board-documented endpoint.
USB-UART DTR/RTS→P4 BOOT35 and bridge/C6 power on battery remain open trust gates.
This operation neither qualifies offline custody nor establishes human consent.

## Normal final page and verification scope

The final decision now visibly says:

```text
BOOT: tap = REJECT
HOLD BOOT 1.5..5s
RELEASE to APPROVE
>5s = REJECT
```

Only that text changes. Existing1500..5000ms hold+release, >5000Reject, debounce,
fresh release/frame binding, touch navigation and real100tick deadline remain.
Root reads the actual new screen; no phrase-based checker or unchanged suite replay.
The normal public867 optical roundtrip602bytes already passed the existing client;
it remains evidence on its original source, not a fresh observation of this binary.

Focused native checks cover CIS bounds and20sequence outcomes: no positive/no low,
input-disabled pad, low still responding, wrong recovery, timeout/rollback, a single
release, and cleanup failure/real pad reporting. Models are not physical evidence.
Build only normal and c6-reset in the same admitted build directory; old53094 WDT
probe binaries/results remain preserved, with no WDT/crypto/core/quirc replay.

Root corrected its reading of the original WDT logs: the label Print CPU1 registers
is followed by ROM reset; no MEPC/RA/SP/A* values or register dump were observed.
Task/CPU names and ROM SavedPC remain. Silentpanic is not custody/log qualification;
this change does not patch SDK panic behavior or admit real keys.

Root separately reviews source/artifacts, flashes the public probe and observes
one bounded operation or UNAVAILABLE, then restores the exact new normal image
and reads HOLD/RELEASE on the final page. No C6 flash, eFuse, board opening, added
hardware, CI/push or physical outcome is performed/claimed by this author.


## Frozen source and final packet

The product contribution above was completed by phase1_scope in
813e98cc7eade910b52e37ebd690be5280404aaf. After ownership transfer,
s3_native_finish verified the clean source, inactive jobs and exact existing
native-stable source hashes, retained those results, and completed only the
necessary final source-bound normal/probe builds and packaging. No product code
was changed by the continuation author. No unchanged tests or WDT canaries ran.

The final packet is apps/p4/evidence/c6-public-probe/final-packet:225 members,
SHA256SUMS6fa1fe95731c154954c0cf7529b2a76fa23dc3e865ce211ffcf5fbd28b46de46.
Its manifest, source/closure bindings, source snapshot, native results, exact
compressed linker maps and build/artifact/integrity receipts are retained in
proof/c6-public-probe. The packet itself includes both ELF/bin/map sets and source.
The normal app is1225776bytes, SHA
b19107ecef328911e53cd9f96668780ac40e73895c706a381279426e208271b5;
the c6-reset app is1275360bytes, SHA
908e95aeeea4bda9d9c451d3f014dbd93b088748c1526990b87e908832c52d59.
Both use P4 boot0x2000/partition0x8000/app0x20000, DIO/80m/16MB, no boot_app0.
The same builddir is left in normal. SDK effective hash a5d508d7 and Rust archive
7d77596a remained unchanged through all four configure/build commands.

Distinct final review belongs to p4_optical_review and root. Actual C6 probe
and new normal display observations are NOT RUN by the implementers. Root is
the sole USB/flash operator; all open gates above remain open.
