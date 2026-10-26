# Frozen normal public P4 C6 guard proof

Compiled product source:33a6b4e3e29c4dd74b8557bc38d1c5b345c07290.
Author:p4_optical_review; distinct reviewer/operator:root.
Current main99332719 was merged in the same worktree before authoring.
The app/core/SDK before/after bindings are in the exact main-merge receipt.

Private artifact packet:apps/p4/evidence/c6-normal-guard/final-packet.
218 members including SHA256SUMS; manifest SHA
56683c7e98615fff0b4ff9634fcb9d63da73ac9a02ce706207c061096e353873.
packet.json SHAc8b155769895ba9c9f3d644b10adccf6f7ef0356c76e1fa4d5b078b6882ea84d.
This directory is a selected public proof projection, not another artifact packet.
Its packet-members.sha256 is the exact private packet manifest; compressed logs
and linker map must decompress to their original raw hashes, without editing.

The source was clean before the one normal configure/build. All124 source inputs,
effective SDK configuration a5d508d7 and Rust static archive7d77596a were checked
unchanged after each stage. Build PASS4.54s; app version33a6b4e3, actual mode0.
Image/ELF/nm/config/offset/Rust-storage checks and11 pinned SDK source hashes are
recorded. Normal app1228304bytes SHA
2a74a35788f438d30427c2d37398f41fdbd9babf322f05ba31374a77471347ee.
P4 offsets:boot0x2000,partition0x8000,app0x20000;DIO80m16MB,no boot_app0.
No SDIO/CIS/Hosted/radio initialization is admitted by this normal path.

Actual helper27cases pass ASan/UBSan with GPIO/register stubs. The first mock's
preliminary GREEN and the corrected actual-reset-model RED are preserved.
The exact final fixture then passes after the OEN fix; source-before snapshot
matches the RED hash. Feed/response-clear hooks have their four exact command
result receipts, all exit0. An initial empty aggregate was a metadata path-filter
bug; it was corrected without source/artifact/test/build changes.
The final native-source-binding SHA is
4dff3b2c79c0d1e329e578de199b9f0755cbe2a53b7e9a9bbc0034321f7ee7b1.

Root's distinct source/packet review is copied byte-exact as root-distinct-review:
SHAcde6155e83709519624b9844326291ba6660e5420a1f8631814559b1ae11eeea.
It admits only this public source/packet and does not turn models/builds into
hardware qualification. Root alone associates/flashes/observes the physical P4.

Previous813/69 source, mode3 causal C6 measurements and prior optical/WDT/crypto
proofs remain on their original sources. No unchanged suite/canary/probe replay.
The old normal's battery/PWR response does not prove CPU continuity; root has
since associated the reconnected USB bridge/path. Current topology is public USB.

Normal guard samples actual GPIO54/config before engine and around critical
boundaries, with sticky failure and best-effort blank/low/reset. Already displayed
QR is not revocable. Reset/panic/WDT can bypass cleanup and release the pin.
No physical C6 pin4 voltage/die/firmware/RF/offline/host-absence/human-consent,
erasure/entropy/custody or release claim. PMIC VBUS could be a future presence
block, not host authentication; current BSP has no exposed status API and no
PMIC/USB driver is added. Future offline battery/physical-USB-unplug precondition
remains a separate operator/hardware gate. Source brief preserves these limits.
