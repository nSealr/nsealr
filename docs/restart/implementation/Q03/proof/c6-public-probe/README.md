# Frozen public C6 probe packet

Product source:813e98cc7eade910b52e37ebd690be5280404aaf, phase1_scope.
Continuation author:s3_native_finish. This delivery adds proof/metadata only.
Distinct reviewer:p4_optical_review; coordinator/operator:root.

External packet:apps/p4/evidence/c6-public-probe/final-packet.
225 members, SHA256SUMS6fa1fe95731c154954c0cf7529b2a76fa23dc3e865ce211ffcf5fbd28b46de46.
packet.json SHAeea2ec53d78f30a25d4a396825154472822560267be94a7f57b3aa20107f1719.
Integrity receipt in integrity/ validates all members and final image/receipt
bindings. This directory retains compressed exact raw logs and maps: decompression
must reproduce the original result/artifact hash; no whitespace normalization.

The last historical build130942 was preserved before the same builddir was
reconfigured. It lacked the complete pre-build snapshot and retained dirty Git
version867. Final mode builds bind115 source inputs before execution and verify
unchanged SDK config and Rust staticlib after each command. Both have version813.
Native-stable source hashes match exactly; the existing20case CIS/sequence model
ASan/UBSan proof was reused. No unchanged Rust/crypto/quirc/WDT canary replay.
Earlier native and target receipts remain historical and attributed to phase1_scope.

Final app files are in c6-reset/ and normal/, respectively1275360 and1225776bytes.
Their SHA values and raw bootloader/partition hashes/offsets are in packet.json.
P4 offsets are0x2000 boot,0x8000 partition,0x20000 app; DIO/80m/16MB.
No boot_app0. The same builddir is restored to normal.

Only mode3 admits the bounded public probe before engine/key init and then never
returns to Nostr. Normal has only the2byte fatal-cleanup stub and the new explicit
HOLD1.5..5s/RELEASE decision text. Worker96KiB internal, real100tick deadline,
WDT5s, SDK6.0.2, core/crypto/vendor and C6 firmware remain unchanged.

This source/proof is not physical evidence. Root alone reviews/flashes/observes
one operation or UNAVAILABLE, restores the new normal image and reads the actual
HOLD/RELEASE page. Generic CIS0092:6666 and SDIO timeout/recovery do not establish
C6 die/revision/firmware, pin4 voltage, RF-off, offline or custody. Best-effort low
on returning/task-fatal paths never proves continuity through SDK panic/WDT/reset.
Historical WDT register label is not a general register dump; tasknames and ROM
SavedPC remain. No keys, entropy/recovery, eFuse or H01/C01 closure is admitted.
