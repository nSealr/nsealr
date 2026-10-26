# S3 public functional packet

Compiled C/UI source: a0ea67e090a891e89877e67b8933186e28491b9d.
Native Rust receipt80 compiled a8b4a49f; all production Rust sources, manifests,
locks, core and vendor are byte-identical at the final source. Host test-only
reentry delta b1dc5723 passed receipt88. Old foundation packet bcad/a159 is immutable.

This is the actual request -> complete Rust review -> local physical input ->
Rust sign_approved -> framed response consumer. It accepts only already-public
scalar3. No real key, entropy generation, nsec import/export, vault, host approval
or default product readiness is exposed. Generated config and linked closure
remain part of the source-bound evidence, not secret-session admission.

Exact flash settings are from flasher_args.json: DIO/80MHz/16MB, boot0x0,
partition0x8000, app0x10000. No boot_app0. Verify SHA256SUMS after Linux->Mac
transfer and bind current private S3 inventory. Root alone flashes; no eFuse writes.

Finite reused/new proof:
- 77:11 focused adapter host tests; 88:one additional callback-reentry test.
- 78/79 and83/84:gesture/menu tests with ASan+UBSan, including stale Both cannot
  become menu Rotate and raw Left blocks final Right approval.
- 80:native Xtensa public adapter build.
- 81:independent S03 Python/hashlib/hash-pinned official BIP340 reference verifies
  exact fixture3 identity, canonical ID and signature; three cryptographic negatives.
- 87:existing product TypeScript build; 90:actual Rust response passes existing
  serial transport and paired-client verifier, with request-ID/content/wrong-key/
  signature mutations rejected. This is host replay, not physical USB/Nostr-client
  qualification.
- 105:final changed C/UI/TX/RX SDK build; 106–109:exact final image/nm/export readback.
  Intermediate82/86 are preserved with their own source, not relabelled final.
- Driver RX is2048 bounded bytes, read quantum64; parsed state owns one request.
  This permits one full frame burst and does not promise lossless hostile flooding.
  103/104 verify wrapped segments and explicit Empty/Limit/Error outcomes: at most
  three nonblocking reads, cumulative2048bytes. Enable is permitted only after an
  observed empty read. Limit/error keeps Locked/INPUT BUSY until a new gesture.
  Distinct review found and closed the prior one-read wrap gap. The source200
  candidate packet is preserved separately and is not the admitted final source.

Use one serial handle throughout a physical run: opening/reopening Serial/JTAG
can alter reset/line-control behavior. Root's prior observed rst0x15 belongs to
its separate source/capture, with no universal cause or RAM-erasure conclusion.

Physical positive:
1. Reset defaults to buttons-left orientation, as observed on foundation. Full
   fixture public key and PUBLIC TEST KEY banner must be readable. In the idle
   menu, GPIO0 short press/release rotates180degrees and remains locked. Observe
   both views, actual edge caption/legend and stable GPIO functions; do not guess
   upper/lower button positions. Choice is RAM only.
2. GPIO14 short press/release locally enables the public-test request path.
   Send request.serial after READY on the same open handle. During each complete
   data page, GPIO14 Next and GPIO0 Back. All labels/body/page-position must fit
   and be legible; escaped text is literal. Orientation cannot change here.
3. On the distinct final page, hold GPIO14 alone1.5real seconds to Approve.
   Both has priority and locks after1.5seconds; GPIO0 rejects. Initial-held and
   carried gestures cannot authorize the new page.
4. Capture the actual complete response and verify under the exact public key/
   event ID/signature in packet.json using the existing oracle/client. A queued
   driver return is not receipt: only the captured complete host frame supplies it.
   The screen says RESULT QUEUED. A new request always needs a fresh local enable.
5. Capture bounded s3-public-result-v1 telemetry if delivered. tx_report is a
   queue API return, frames counts DMA commits, elapsed_us includes human wait,
   stack_min_free_bytes is the main-stack minimum free space since boot.
   Missing diagnostics with a non-reading host are not fabricated as zeros.

Physical negatives needed: Back and Reject; held-start/old final gesture;
Both->Lock->release must not Rotate; fresh Rotate only in menu; expiry at the
100-second boundary; malformed/checksum/base64/duplicate/oversized inputs; host
flood while reviewing; unplug/reset; host not reading and finite TX queue failure.
Queue failure is terminal until reset, with no automatic retransmit/sign retry.
Already accepted public bytes in the FIFO/ring cannot be recalled by Lock or
disconnect and may later be read. That limitation remains explicit; future CDC/
secret-session work must qualify its actual lifecycle separately.

Read docs/restart/implementation/D01/native-session-contract.md at sourcea0ea67e0
for the full contract and later OTG/SARADC/internalRAM/panic/recovery gates.
This packet completes no product criterion and is not a real-identity release.
