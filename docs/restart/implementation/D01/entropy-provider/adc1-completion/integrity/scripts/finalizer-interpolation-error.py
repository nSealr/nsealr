from pathlib import Path
import hashlib,json,shutil
P=Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/s3-probe");O=P/"artifacts/entropy-adc1-completion"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
d=P/"execution/163-s3-adc1-completion-packet-version-binding";r=json.loads((d/"result.json").read_text());assert r["exit"]==0
for n,k in [("stdout.log","stdout_sha256"),("stderr.log","stderr_sha256")]:assert sha(d/n)==r[k]
for src in d.iterdir():
 if src.is_file():
  dst=O/"evidence/execution"/d.name/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
f=O/"packet.json";j=json.loads(f.read_text());j["receipts"][d.name]={"exit":0,"seconds":r["seconds"],"result_sha256":sha(d/"result.json"),"stdout_sha256":r["stdout_sha256"],"stderr_sha256":r["stderr_sha256"]};f.write_text(json.dumps(j,indent=2,ensure_ascii=False)+"\n")
app=next(x for x in j["files"] if x["file"]=="firmware.bin")
(O/"README.md").write_text(f"""# S3 public ADC1 completion observer

Compiled source e7f04215fc97808acdafdbf9420f6ef6d0102c5b, base f65e8aa9/08d919c3.
The base source, packet436 and its single physical negative remain immutable.
Same SDK5.3 e099, TinyUSB3.0.0, Rust archive and core, host, USB and50ms policy.
No real identity, source-quality/entropy admission, ADC1-only/RTC switch or SDK edit.

Only4 source files changed: S3 provider, private logic/test and app README.
ADC1_DONE raw bit31 and clear bit31 replace the unsupported last-value-equality
proxy. Two separate observed clear0->fresh1 sequences bracket8SDK RNG words.
Only timer-enable bit24 is paused/restored, with full unrelated-field readback;
no interrupt-enable/handler or DMA. Initial DONE1 is allowed if it clears to0
and is followed by1. Stale1, missing pre/post completion, ownership/deadline loss
or failed timer restore refuses, supplies0 and wipes. The timer is checked active
before each word. All word0/FF/repeated/duplicate-block screens remain mandatory.
The one real50ms budget includes claim, settle, both phases and cleanup; finite
256poll caps apply, including frozen-clock negatives. No hard guarantee during
a nonreturning SDK/ROM call. An in-flight conversion can complete after observed0:
this is only a completion witness, not exclusive post-trigger causality, ADC2
activity, source-health or RNG quality. ADC183 remains unresolved for production.

Private report384bytes: uint8 word count<=8 and pre/post phase bytes reuse the
old4byte count slot. Retained state242bytes and diagnostics2048bytes INTERNAL
remain fixed; no new heap/task/DMA. Main98304/USB4096 stacks unchanged. Selected
auxiliary frame464bytes, collector240bytes and witness48bytes are supporting
static evidence, not a complete ROM/indirect stack bound. Root must observe
affected main>=4096/USB>=512bytes free. Progress is appended to the existing
bounded diagnostic: progress=pre/post hex, bit0 initial read,bit1 initial1,
bit2 clear0 observed,bit3 fresh1. Successful phases d/f;0 means not reached.
Core/Rust/C public request-response ABI and protocol versions are unchanged.

One target build154 PASS4.08s; app{app[bytes]}bytes SHA256
{app[sha256]}.
Actual flasher_args: boot0x0,partition0x8000,app0x10000,DIO80m16MB,no boot_app0.
Boot and partitions are unchanged.94 inputs/665 compiled sources, actual config,
ELF/staticlib/map/descriptors and direct references are bound. Macro145 is reused:
actual provider/main commands and sdkconfig.h are byte identical, and all665
commands match except the expected esp_app_desc PROJECT_VER08d->e7 token.
No unaffected Rust/core/USB suite or Rust build was repeated.

Focused host152/153 PASS3485ASan/UBSan checks, preserving negative intent and
covering initial1 clearing, sticky/missing pre/post, timer restoration, cumulative
budget/claim time, raw14000 plus real witnesses, foreign ownership and full buffers.
The host fixtures are not hardware/source qualification. Original08d physical
Health-6 was caused by unchanged DATA_STATUS before its word screens:8words,
0supplied,2653us,refs0/1/1/0,no signature. It is not a RNG-stuck diagnosis and
no draw1..4 was observed/passed. That exact receipt/raw is in contract/.

159 inspection failed on compiler-folded lambda aliases at one address;161
selects bounded address/size groups and retains all aliases.162 packet matcher
expected entire compile_commands equality, but app_desc correctly changed only
PROJECT_VER;163 checks all records and permits only that exact expected token.
Original failed selectors/assembler and logs are preserved. Neither is a target
or runtime failure. Earlier135/149 and duplicate133/134 remain historical,
without new coverage claims. Existing dependency/gesture/Rust/validator receipts
are reused on their unchanged inputs. Previous436 packet members checked intact.
Licenses, notices, pinned archive/ledger and explicit root contracts are included.

Root distinct source/config/closure/packet review precedes any USB/flash. One
finite followup: keep one CDC handle, fresh GPIO0Skip or GPIO14Run as labelled;
Run<=4public32byte diagnostic attempts, stop first failure, then a fresh local
acknowledgement. At most1new scalar3 auxiliary attempt this CPU boot, with explicit
host expectedPublicKey. Never retry until green. Capture progress/status/readbacks,
LCD/buttons and watermarks. Missing observation remains UNKNOWN/NOT RUN; an
Unavailable/Readback/Timeout is a bounded public result to preserve.

S3 product remains USB-only, without battery/supercap requirement; future real
power loss needs local reload, not proved by the auto scalar3 fixture. E5 powered
data-only unplug remains inapplicable. Other reset/ROM/RAM/host gates remain open.
Queue acceptance is not host delivery; no erasure/readiness/C01/H01/custody claim.
No USB/flash/CI/push/merge/eFuse or additional hardware sampling by author.
""")
shutil.copy2(__file__,O/"evidence/scripts/entropy_packet_finalize.py")
files=sorted(x for x in O.rglob("*") if x.is_file() and x.name!="SHA256SUMS")
(O/"SHA256SUMS").write_text("".join(sha(x)+"  "+str(x.relative_to(O))+"\n" for x in files))
print(json.dumps({"members":len(files),"manifest_sha256":sha(O/"SHA256SUMS"),"packet_sha256":sha(O/"packet.json"),"closure_sha256":sha(O/"source-and-closure.json"),"app":app},indent=2))
