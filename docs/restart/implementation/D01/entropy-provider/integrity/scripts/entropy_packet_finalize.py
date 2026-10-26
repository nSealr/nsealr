from pathlib import Path
import hashlib,json,shutil
P=Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/s3-probe");O=P/"artifacts/entropy-public"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
d=P/"execution/150-s3-entropy-packet-corrected-header-path";r=json.loads((d/"result.json").read_text());assert r["exit"]==0
for n,k in [("stdout.log","stdout_sha256"),("stderr.log","stderr_sha256")]:assert sha(d/n)==r[k]
for src in d.iterdir():
 if src.is_file():
  dst=O/"evidence/execution"/d.name/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
f=O/"packet.json";j=json.loads(f.read_text());j["receipts"][d.name]={"exit":0,"seconds":r["seconds"],"result_sha256":sha(d/"result.json"),"stdout_sha256":r["stdout_sha256"],"stderr_sha256":r["stderr_sha256"]};f.write_text(json.dumps(j,indent=2,ensure_ascii=False)+"\n")
(O/"README.md").write_text("""# S3 fallible SARADC public experiment

Compiled source08d919c31cff329f14809cc8c3ed2f26cd8454c5, SDK5.3 e0991fac,
esp_tinyusb3.0.0 pinned68bf7f/af8bc85b. Public scalar3 only. No secret endpoint,
identity import/generation, production entropy_ok or ADC183 exemption.

The final image is firmware.bin448928bytes SHA256
0825678c8981aaabbf36be9377112905d8f2ea4cd6f06e010b6ef42045b9c969.
Actual generated flasher_args: boot0x0, partition0x8000, app0x10000;
DIO80m16MB, no boot_app0. Root alone may flash after distinct review.
No USB, device access, flash, CI, push or merge by the implementation author.

Finite physical observation: keep a single CDC handle open through local actions.
At the public entropy screen use fresh GPIO0 Skip or GPIO14 Run as labelled.
Run permits at most4 diagnostic32byte attempts this CPU boot and stops at the
first failure; acknowledge with a fresh gesture. Capture public RNG status,
words/supplied/elapsed, bank tags, reference counts and enabled register summary.
Four complete snapshots per draw are retained internally; compact serial output
logs all four bank/reference tags, enabled/after/rest flags, and selected enabled
registers plus after SAR data. It does not dump every field of every snapshot.
A sample line is public-not-identity and appears only after successful cleanup.
Then at most1 new auxiliary attempt may serve an existing scalar3 request; pass
explicit expectedPublicKey on the host. AUX failure requires CPU restart before
another attempt. No retry-until-green or second campaign is authorized here.
Measure affected main>=4096byte and USB>=512byte free watermarks and confirm
LCD/buttons/CDC remain functional. An Unavailable/Readback/Health result is a
bounded public negative to preserve, never a justification to change expectations.

Provider status:0PublicDraw,-1Argument,-2Unavailable,-3Ownership,-4Readback,
-5Timeout,-6Health,-7Interrupted,-8Provider,-9Cleanup. Each returning owned error
wipes destination/staging and supplies0, with no signature/fallback. SDK word API
has no per-call health error; word/short/failure injections are focused host tests.
50ms checks apply between calls; they cannot interrupt a stuck SDK/ROM call.
Queue acceptance is not host delivery and already queued bytes cannot be recalled.

Source-before-build binds94 inputs to final Git blobs and hashes.665 compiled
sources, generated config/macros, ELF symbols/sections/descriptors, target
references and selected function bodies are included. RCC policies tested are the
same template functions used by the target adapter. Busy claim leaves foreign
counts untouched; corrupted counts fail terminally with balanced locks. Owned
post-helper APB gate restore is explicit, without a reset pulse/vendor patch.
Post-disable DIG/data banks are gated and UNKNOWN; only SYSTEM/SENS/analog are
read then. S3 WIFI/BT enable masks are zero and never used as an RF-health bool.
Configured clocks and gross activity/repetition checks are not entropy measures.
No executable competing ADC/I2S/temperature/RF/RNG initializer or nominal persistent
writer matched the closed application scan. Direct/indirect ROM and bootloader
activity are not exhaustively ruled out by that scan. ADC183 remains unresolved
for production; varied output cannot prove source health or fault tolerance.

14 focused Rust tests and1818 provider checks passed.133/134 repeat128/129 and
add no coverage.135 compiler RED is preserved with corrected target-format cause;
136 is a historical earlier build,139 the sole final flash candidate.146 objdump
kept only its last repeated selector;147 selects each body in a separate invocation.
149 packet path assertion is a packaging failure only;150 corrected the actual
platform_port header path. Existing SDK Python is used for ELF parsing after an
outer system-Python import error, with no failed target/build replay. Existing
114 TinyUSB439member preflight and116/117 gesture/epoch84checks are reused; all352
old OTG packet members were checked unchanged. Core/oracle/host suites unchanged
and not rerun. Licenses, dependency archive, source notices and exact primary
source ledger are preserved with their historical attribution.

Static retained provider state is242bytes INTERNAL and diagnostics2048bytes.
No new heap/task/DMA; main98304/USB4096 stacks remain internal. Selected largest
new function frame464bytes and collector224bytes are supporting static evidence,
not a complete indirect/ROM call-chain bound; root watermarks remain pending.

Power amendment uses its own distinct root review, preserves historical reviews,
and changes only the S3 USB-only profile/current bindings. No battery, supercap
or independent power is required. Future real session terminates on power loss
and requires local reload; the auto scalar3 fixture proves neither that behavior
nor whole-memory erasure. E5 powered data-only unplug is not applicable. DTR,
bus-reset/suspend while powered and existing ROM/reset/RAM gates still apply.
No readiness, custody, C01/H01 closure or secret admission is declared.
""")
shutil.copy2(__file__,O/"evidence/scripts/entropy_packet_finalize.py")
files=sorted(x for x in O.rglob("*") if x.is_file() and x.name!="SHA256SUMS")
(O/"SHA256SUMS").write_text("".join(sha(x)+"  "+str(x.relative_to(O))+"\n" for x in files))
print(json.dumps({"members":len(files),"manifest_sha256":sha(O/"SHA256SUMS"),"packet_sha256":sha(O/"packet.json"),"closure_sha256":sha(O/"source-and-closure.json")},indent=2))
