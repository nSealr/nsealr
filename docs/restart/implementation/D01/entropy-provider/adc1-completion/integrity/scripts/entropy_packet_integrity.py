from pathlib import Path
import hashlib,json,subprocess
P=Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/s3-probe");O=P/"artifacts/entropy-adc1-completion";W=P.parent/"s3-session";B=P/"native/build/idf-public"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/"SHA256SUMS")=="28bf4e20449d02ab0241e7db7e9bb7cd9cba9753e33b7d7dd7d4d0d2136d5e56"
listed={}
for line in (O/"SHA256SUMS").read_text().splitlines():
 h,n=line.split("  ",1);assert n not in listed and sha(O/n)==h,n;listed[n]=h
assert set(listed)=={str(x.relative_to(O)) for x in O.rglob("*") if x.is_file() and x.name!="SHA256SUMS"}
p=json.loads((O/"packet.json").read_text());c=json.loads((O/"source-and-closure.json").read_text());source=p["source_commit"]
assert source==c["source_commit"]==subprocess.check_output(["git","-C",str(W),"rev-parse","HEAD"],text=True).strip()
assert not subprocess.check_output(["git","-C",str(W),"status","--porcelain"],text=True).strip()
for item in c["source_inputs"]:
 n=item["path"];assert sha(W/n)==sha(O/"source"/n)==item["sha256"],n
 assert subprocess.check_output(["git","-C",str(W),"rev-parse",source+":"+n],text=True).strip()==item["blob"]
for item in c["compiled_sources"]:assert sha(Path(item["source"]))==item["sha256"],item["source"]
for name,r in p["receipts"].items():
 d=O/"evidence/execution"/name;assert sha(d/"result.json")==r["result_sha256"]
 rr=json.loads((d/"result.json").read_text());assert rr["exit"]==r["exit"]
 for n,k in [("stdout.log","stdout_sha256"),("stderr.log","stderr_sha256")]:assert sha(d/n)==r[k]==rr[k]
for x in p["files"]:assert sha(O/x["file"])==x["sha256"] and (O/x["file"]).stat().st_size==x["bytes"]
for src,name in [(B/"nsealr_s3_native_public.bin","firmware.bin"),(B/"nsealr_s3_native_public.elf","firmware.elf"),(B/"nsealr_s3_native_public.map","firmware.map"),(P/"native/build/rust-core/xtensa-esp32s3-none-elf/release/libnsealr_s3_native_core.a","rust-core.a"),(B/"bootloader/bootloader.bin","bootloader.bin"),(B/"partition_table/partition-table.bin","partitions.bin")]:assert sha(src)==sha(O/name)
assert p["compiled_source_commit"]==json.loads((O/"project_description.json").read_text())["project_version"] or p["compiled_source_commit"][:8]==json.loads((O/"project_description.json").read_text())["project_version"]
print(json.dumps({"result":"PASS_SOURCE_BUILD_PACKET_BINDINGS_ONLY","source":source,"members":len(listed),"source_inputs":len(c["source_inputs"]),"compiled_sources":len(c["compiled_sources"]),"receipts":len(p["receipts"]),"manifest_sha256":sha(O/"SHA256SUMS"),"closure_sha256":sha(O/"source-and-closure.json"),"packet_sha256":sha(O/"packet.json"),"app_sha256":sha(O/"firmware.bin"),"hardware":"NOT RUN by implementer; root distinct review/finite public diagnostic pending"},indent=2))
