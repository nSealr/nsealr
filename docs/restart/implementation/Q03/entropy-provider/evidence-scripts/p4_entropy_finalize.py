
from pathlib import Path
import json,hashlib,shutil,re,subprocess,datetime,gzip
R=Path('/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25');P=R/'p4-probe';W=R/'p4-session';A=W/'apps/p4';S=P/'src/esp-idf';O=A/'evidence/entropy-public';F=O/'final-packet'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cp(s,d):
 d.parent.mkdir(parents=True,exist_ok=True)
 if d.exists():assert sha(s)==sha(d)
 else:shutil.copy2(s,d)
def wr(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def tree(s,d):
 for p in sorted(s.rglob('*')):
  if p.is_file():cp(p,d/p.relative_to(s))
assert not (F/'SHA256SUMS').exists()
tree(P/'execution/p4-entropy-24-packet-stage',F/'execution/p4-entropy-24-packet-stage')
cp(P/'scripts/p4_entropy_finalize.py',F/'evidence-scripts/p4_entropy_finalize.py')
# Preserve the exact host request and byte-equality expected response used by run08, not a guessed fixture.
cp(A/'evidence/request.qr',F/'host-proof/request.qr')
expected=A/'evidence/final-response-request.qr'
assert sha(expected)==sha(F/'host-proof/host-response.qr')
cp(expected,F/'host-proof/expected-historical-response.qr')
wr(F/'host-proof/fixture-binding.json',{'request_sha256':sha(F/'host-proof/request.qr'),'response_bytes':602,'response_sha256':sha(F/'host-proof/host-response.qr'),'expected':str(expected.relative_to(W)),'expected_sha256':sha(expected),'run':'p4-entropy-08-ffi-positive','auxiliary':'synthetic0x22 HOST ONLY; no new oracle/cryptography suite or human observation'})
closure=json.loads((F/'source-and-closure.json').read_text())
for n in ['components/esp_hal_clock/esp32p4/include/hal/clk_tree_ll.h','components/soc/esp32p4/register/hw_ver3/soc/trng_struct.h','components/heap/tlsf/README.md','components/heap/tlsf/include/tlsf.h']:
 cp(S/n,F/'sdk-sources'/n)
 closure['SDK_sources'].append({'path':n,'sha256':sha(S/n)})
wr(F/'source-and-closure.json',closure)
# The original primary PDF stays in its existing intake; bind/excerpt the reviewed text without new research.
primary=R/'intake/p4-orientation-primary'
cp(primary/'trm-source.json',F/'primary/trm-source.json')
t=(primary/'trm.txt').read_text()
pages=t.split('\f')
excerpts=[]
for i,page in enumerate(pages):
 if any(('\n'+str(n)+'\n') in page for n in [1698,1789,2052,2053,2054,2055]):excerpts.append({'pdf_text_page_index0':i,'text':page})
# Printed page parsing is not used as a source of facts; complete text remains bound at its original path.
wr(F/'primary/collected-TRM-binding.json',{'original':str(primary/'trm.txt'),'text_sha256':sha(primary/'trm.txt'),'pdf_sha256':'622fe9625d19cf00bd7aa49e65f0b5dd6ef2197f83cb7a88b4405078d6a957d4','contract_printed_pages':[1698,1789,2052,2053,2054,2055],'exact_page_excerpts_if_plain_number_detected':excerpts,'limit':'Preliminary older register mapping; no new fact/revision assurance inferred from numeric text parsing.'})
x=(F/'artifact-checks/normal/selected-functions.txt').read_text()
frames={}
for b in x.split('FUNCTION ')[1:]:
 name=b.splitlines()[0].split()[0];frames[name]=[int(n) for n in re.findall(r'addi\s+sp,sp,-(\d+)',b)]
wr(F/'artifact-checks/selected-static-frames.json',{'source':'b259d416','mode':'normal','prologue_bytes':frames,'own_nested_collection_chain_bytes':96+208+16,'with_selected_helper32_bytes':96+208+16+32,'limit':'Selected actual prologues only; no bound on entire SDK/ROM/logging/transitive call chain, interrupts or physical watermark. Additional stack budget2048 is an engineering cap pending affected hardware>=4096free, not a measured bound.'})
p=json.loads((F/'packet.json').read_text())
d=P/'execution/p4-entropy-24-packet-stage';r=json.loads((d/'result.json').read_text())
p['records'].append({'record':d.name,'exit':r['exit'],'expected':r.get('expected_exit'),'seconds':r['seconds'],'result_sha256':sha(d/'result.json')})
p['SDK_source_snapshot_count']=len(closure['SDK_sources']);p['finalized_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();p['source_and_closure_sha256']=sha(F/'source-and-closure.json')
wr(F/'packet.json',p)
# Integrity of frozen source plus captured images before manifest. No build/retest/hardware.
b=json.loads((F/'source-before-build.json').read_text())
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==b['source']
for n,h in b['source_inputs'].items():assert sha(W/n)==h and sha(F/'source'/n)==h,n
for mode in ['normal','fixed-unavailable']:
 for i in json.loads((F/mode/'variant.json').read_text())['files']:assert sha(F/mode/i['file'])==i['sha256']
for n,pth in [('target',A/'rust/target/riscv32imafc-unknown-none-elf/release/libnsealr_p4_optical.a'),('host',A/'rust/target/x86_64-unknown-linux-gnu/release/libnsealr_p4_optical.a')]:
 assert sha(pth)==sha(F/('rust-'+n+'.a'))==b['Rust_'+n+'_sha256']
for d in (F/'execution').iterdir():
 if not d.is_dir():continue
 r=json.loads((d/'result.json').read_text())
 assert sha(d/'stdout.log')==r['stdout_sha256'];assert sha(d/'stderr.log')==r['stderr_sha256']
for d in (F/'build-evidence').iterdir():
 r=json.loads((d/'result.json').read_text())
 assert sha(d/'stdout.log')==r['stdout.log_sha256'];assert sha(d/'stderr.log')==r['stderr.log_sha256']
files=[p for p in sorted(F.rglob('*')) if p.is_file()]
(F/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(F))+'\n' for p in files))
# Version the bounded metadata and exact compressed raw proof, not firmware/ELF/tool caches.
D=W/'docs/restart/implementation/Q03/entropy-provider'
D.mkdir(exist_ok=False)
for n in ['README.md','SHA256SUMS','packet.json','source-before-build.json','source-and-closure.json','allocator-and-resources.json']:
 cp(F/n,D/n)
for dirn in ['intake-source','primary']:
 for p in (F/dirn).rglob('*.json'):cp(p,D/dirn/p.relative_to(F/dirn))
for mode in ['normal','fixed-unavailable']:
 cp(F/mode/'variant.json',D/mode/'variant.json')
 for p in (F/'artifact-checks'/mode/'image-info').iterdir():cp(p,D/'artifact-checks'/mode/'image-info'/p.name)
for n in ['summary.json','commands.json','executable-name-scan.json','selected-static-frames.json']:
 cp(F/'artifact-checks'/n,D/'artifact-checks'/n)
cp(F/'host-proof/fixture-binding.json',D/'host-proof/fixture-binding.json')
for p in (F/'host-proof').glob('*.qr'):cp(p,D/'host-proof'/p.name)
cp(F/'licenses/index.json',D/'licenses/index.json')
compressed=[]
for dirname in ['execution','build-evidence','evidence-scripts']:
 for p in sorted((F/dirname).rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(F)
  if p.suffix in ['.json','.py','.c','.h']:cp(p,D/rel)
  else:
   dest=D/(str(rel)+'.gz');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(gzip.compress(p.read_bytes(),mtime=0))
   assert gzip.decompress(dest.read_bytes())==p.read_bytes()
   compressed.append({'packet_file':str(rel),'gzip_file':str(rel)+'.gz','raw_sha256':sha(p),'gzip_sha256':sha(dest)})
wr(D/'compressed-proof-bindings.json',compressed)
wr(D/'delivery-binding.json',{'compiled_source':b['source'],'compiled_Rust_source':b['Rust_compiled_source'],'packet_path':str(F),'packet_members':len(files),'manifest_sha256':sha(F/'SHA256SUMS'),'packet_json_sha256':sha(F/'packet.json'),'closure_sha256':sha(F/'source-and-closure.json'),'versioned_gzip_count':len(compressed),'hardware':'NOT RUN by author; root distinct review required','no_product_edits_after_build':True,'no_Q03_state_plan_change':True})
print(json.dumps(json.loads((D/'delivery-binding.json').read_text()),indent=2))
