
from pathlib import Path
import json,hashlib,shutil,subprocess,tomllib,re,datetime
R=Path('/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25')
P=R/'p4-probe';W=R/'p4-session';A=W/'apps/p4';S=P/'src/esp-idf';O=A/'evidence/entropy-public';F=O/'final-packet'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def wr(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def cp(s,d):
 assert Path(s).is_file(),str(s)
 Path(d).parent.mkdir(parents=True,exist_ok=True)
 if Path(d).exists(): assert sha(s)==sha(d),(str(s),str(d))
 else: shutil.copy2(s,d)
def tree(s,d):
 for p in sorted(Path(s).rglob('*')):
  if p.is_file():cp(p,Path(d)/p.relative_to(s))
def git(*args):return subprocess.check_output(['git',*args],cwd=W,text=True).strip()
B=json.loads((O/'source-before-build.json').read_text())
assert git('rev-parse','HEAD')==B['source']=='b259d416c482569622e6467a121b6c4436e6ac9e'
assert git('status','--porcelain')==''
for n,h in B['source_inputs'].items(): assert sha(W/n)==h,n
for n,blob in B['source_blobs'].items(): assert git('rev-parse','HEAD:'+n)==blob,n
old=A/'evidence/c6-normal-guard/final-packet'
assert sha(old/'SHA256SUMS')=='56683c7e98615fff0b4ff9634fcb9d63da73ac9a02ce706207c061096e353873'
oldlines=(old/'SHA256SUMS').read_text().splitlines()
for line in oldlines:
 h,n=line.split('  ',1);assert sha(old/n)==h,n
assert len(oldlines)==217
F.mkdir(exist_ok=False)
for mode in ['normal','fixed-unavailable']:
 v=json.loads((O/mode/'variant.json').read_text())
 for i in v['files']:assert sha(O/mode/i['file'])==i['sha256']
 tree(O/mode,F/mode)
tree(O/'artifact-checks',F/'artifact-checks')
cp(O/'source-before-build.json',F/'source-before-build.json')
for n in B['source_inputs']:cp(W/n,F/'source'/n)
rust={'target':A/'rust/target/riscv32imafc-unknown-none-elf/release/libnsealr_p4_optical.a','host':A/'rust/target/x86_64-unknown-linux-gnu/release/libnsealr_p4_optical.a'}
for n,p in rust.items():
 assert sha(p)==B['Rust_'+n+'_sha256']
 cp(p,F/('rust-'+n+'.a'))
for p in ['provider-test','engine-host','host-response.qr']:cp(O/p,F/'host-proof'/p)
cp(A/'tests/fixtures/final-request.qr',F/'host-proof/final-request.qr') if (A/'tests/fixtures/final-request.qr').exists() else None
# Preserve every outer execution record, including the two explained REDs and absent-provider negative.
records=[]
for d in sorted((P/'execution').glob('p4-entropy-*')):
 if not d.is_dir() or not (d/'result.json').exists():continue
 tree(d,F/'execution'/d.name)
 x=json.loads((d/'result.json').read_text())
 assert sha(d/'stdout.log')==x['stdout_sha256'];assert sha(d/'stderr.log')==x['stderr_sha256']
 records.append({'record':d.name,'exit':x['exit'],'expected':x.get('expected_exit'),'seconds':x['seconds'],'result_sha256':sha(d/'result.json')})
 for child in re.findall(r'START (?:rust|configure|app) (\S+)',(d/'stdout.log').read_text()):
  c=Path(child); tree(c,F/'build-evidence'/c.name)
for name in ['p4-fallible-entropy-contract.json','p4-fallible-entropy-contract-root-review.json','p4-entropy-first-host-compile-stop.json','p4-entropy-sdk-lock-resource-amendment.json']:
 cp(R/'intake'/name,F/'intake-source'/name)
for name in ['active_environment.py','common.py','p4_entropy_capture.py','p4_entropy_inspect.py','p4_entropy_package.py']:
 cp(P/'scripts'/name,F/'evidence-scripts'/name)
# Reuse source-bound prior proof, not its hardware or entropy claims.
for n in ['SHA256SUMS','source-and-closure.json','source-before-build.json','native-source-binding.json','packet.json']:
 cp(old/n,F/'prior-proof'/n)
tree(old/'native',F/'prior-proof/native')
# Primary SDK source snapshots, license texts and exact source-bound helper/header paths.
contract=json.loads((R/'intake/p4-fallible-entropy-contract.json').read_text())
amend=json.loads((R/'intake/p4-entropy-sdk-lock-resource-amendment.json').read_text())
sdk=set(x['path'] for x in contract['primary_bindings']['SDK_sources'])
sdk.update(x['path'] for x in amend['source_bindings'])
sdk.update(str(x.relative_to(old/'sdk-sources')) for x in (old/'sdk-sources').rglob('*') if x.is_file())
sdk.update([
 'components/freertos/FreeRTOS-Kernel/include/freertos/queue.h',
 'components/freertos/FreeRTOS-Kernel/include/freertos/FreeRTOS.h',
 'components/freertos/FreeRTOS-Kernel/LICENSE.md',
 'components/heap/heap_caps_base.c','components/heap/heap_caps.c','components/heap/multi_heap.c',
 'components/heap/multi_heap_platform.h','components/heap/tlsf/tlsf.c',
 'components/heap/tlsf/tlsf_block_functions.h','components/heap/tlsf/tlsf_control_functions.h',
 'components/esp_hw_support/heap_align_hw.c',
 'components/esp_hw_support/port/include/esp_private/periph_ctrl.h',
 'components/esp_hw_support/include/esp_private/periph_ctrl.h',
 'components/hal/esp32p4/include/hal/clk_tree_ll.h',
 'components/soc/esp32p4/register/hw_ver3/soc/hp_sys_clkrst_reg.h',
 'components/soc/esp32p4/register/hw_ver3/soc/adc_reg.h',
 'components/soc/esp32p4/register/hw_ver3/soc/adc_struct.h',
 'components/soc/esp32p4/register/hw_ver3/soc/soc.h',
 'components/soc/esp32p4/include/soc/soc_caps.h'])
# Some exact SDK headers moved between components; only optional supplemental entries can be absent.
required=set(x['path'] for x in contract['primary_bindings']['SDK_sources'])|set(x['path'] for x in amend['source_bindings'])
missing=[]
sdk_records=[]
for n in sorted(sdk):
 if not (S/n).is_file():
  assert n not in required,n
  missing.append(n);continue
 cp(S/n,F/'sdk-sources'/n)
 sdk_records.append({'path':n,'sha256':sha(S/n)})
for x in contract['primary_bindings']['SDK_sources']+amend['source_bindings']:assert sha(S/x['path'])==x['sha256']
# Source notices for the actual tools, root-vendored Rust consumer, managed components, SDK and app vendors.
notices=[]
def notice(s,d,origin,role):
 cp(s,F/'licenses'/d);notices.append({'file':str(Path('licenses')/d),'origin':str(origin),'role':role,'sha256':sha(s)})
notice(W/'LICENSE',Path('nsealr/LICENSE'),'source b259','product source')
tool=P/'tools/tools/riscv32-esp-elf/esp-15.2.0_20251204/riscv32-esp-elf/share/licenses'
for p in sorted(tool.rglob('*')):
 if p.is_file() and p.suffix not in ['.gif','.css']:notice(p,Path('gcc-15.2.0')/p.relative_to(tool),'installed esp-15.2.0_20251204 toolchain','tool/runtime attribution; inclusion is not a linked-code claim')
rb=Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final-replay/.tools/rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/share/doc/rust')
for p in [rb/'COPYRIGHT.html',rb/'COPYRIGHT-library.html',*sorted((rb/'licenses').rglob('*'))]:
 if p.is_file():notice(p,Path('rust-1.95.0')/p.relative_to(rb),'installed rust1.95.0','tool and standard-library attribution')
for pkg in tomllib.loads((A/'rust/Cargo.lock').read_text())['package']:
 if pkg['name'] in ['nsealr-core','nsealr-p4-optical']:continue
 base=W/'vendor'/pkg['name'];meta=tomllib.loads((base/'Cargo.toml').read_text())['package'];assert meta['version']==pkg['version'],pkg
 matches=[p for p in base.rglob('*') if p.is_file() and ('LICENSE' in p.name.upper() or p.name.upper().startswith('COPYING') or p.name.upper().startswith('NOTICE'))]
 assert matches,pkg
 for p in matches:notice(p,Path('rust-vendor')/base.name/p.relative_to(base),str(base.relative_to(W))+'@'+pkg['version'],'locked consumer dependency; target/host/build-only usage distinguished by build metadata')
for label,base in [('app-vendor',A/'vendor'),('managed-components',A/'managed_components')]:
 for p in sorted(base.rglob('*')):
  if p.is_file() and ('LICENSE' in p.name.upper() or p.name.upper().startswith(('COPYING','NOTICE'))):
   notice(p,Path(label)/p.relative_to(base),str(p.resolve()),'retained peripheral/QR closure attribution')
notice(S/'LICENSE',Path('esp-idf/LICENSE'),'SDK7101770','SDK Apache2.0')
notice(S/'components/freertos/FreeRTOS-Kernel/LICENSE.md',Path('esp-idf/FreeRTOS-LICENSE.md'),'SDK7101770 submodule','FreeRTOS kernel')
# TLSF SPDX license header remains in full source snapshot.
wr(F/'licenses/index.json',{'notices':notices,'limit':'Not a relicensing statement. Original in-source SPDX/copyright notices remain in source snapshots. The retained managed-component lock and historical peripheral provenance remain unchanged. Tool license inventory is broader than the set of runtime symbols linked.'})
# Collect read-only image info, not device interaction.
for mode in ['normal','fixed-unavailable']:
 argv=[str(P/'python-env-uv/bin/python'),'-m','esptool','--chip','esp32p4','image-info',str(F/mode/'firmware.bin')]
 r=subprocess.run(argv,cwd=W,capture_output=True,text=True);assert r.returncode==0,r.stderr
 out=F/'artifact-checks'/mode/'image-info';out.mkdir()
 (out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr)
 wr(out/'command.json',{'argv':argv,'exit':r.returncode,'device':'NONE; offline file inspection'})
# Scope executable-name scan correctly: no claim from component inclusion or ROM anchors.
scan={}
for mode in ['normal','fixed-unavailable']:
 lines=(F/'artifact-checks'/mode/'defined.txt').read_text().splitlines()
 hits=[x for x in lines if re.search(r' [TtWw] ',x) and re.search(r'(?i)(random|entropy|adc_|i2s_|temperature_sensor|pmic|nvs_|spiffs|fatfs|ota_|spi_flash_write|esp_partition_write)',x)]
 scan[mode]=hits
 forbidden=[x for x in hits if re.search(r'(?i)(p4_fixture_auxiliary|esp_fill_random|i2s_|temperature_sensor|pmic|nvs_open|nvs_set|nvs_commit|spiffs|fatfs|esp_ota_(begin|write|end)|spi_flash_write|esp_partition_write)',x)]
 assert not forbidden,forbidden
wr(F/'artifact-checks/executable-name-scan.json',{'hits':scan,'interpretation':'esp_ota_get_running_partition is read-only metadata; two 2byte esp_libc_include_getentropy_impl/nvs_sec_provider_include_impl anchors are not consumers/writers. No target0x22 or extra matched RNG/ADC driver/I2S/temperature/PMIC/persistent writer body. Symbol/name scan plus selected direct calls is not exhaustive against indirect,ROM or concurrent foreign activity.'})
# Derive mutex heap overhead from actual ABI and SDK, not a running heap subtraction.
wr(F/'allocator-and-resources.json',{
 'source':B['source'],'SDK':B['SDK'],'target_ABI':'32bit sizeof(size_t)=4; ELF32',
 'DWARF_StaticSemaphore_t':92,'SDK_mutex_count_max':2,'SDK_mutex_payload_INTERNAL_bytes':184,'payload_compile_cap':512,
 'when':'one bind warm-up before engine/key; SDK handles retained; failed second acquire releases only acquired first; no close/replacement',
 'heap_caps':'pvPortMalloc INTERNAL|8BIT; no DMA/cache/SIMD caps, heap_align_hw returns before extra alignment',
 'actual_config':{'LIBC_PICOLIBC':True,'FREERTOS_USE_TRACE_FACILITY':True,'HEAP_POISONING_DISABLED':True,'HEAP_TASK_TRACKING':False,'HEAP_TRACING_OFF':True,'HEAP_USE_HOOKS':False},
 'derivation':{'TLSF_alignment_bytes':4,'payload_rounding_for92':0,'block_size_min_bytes':12,'block_header_overhead_each':4,'split_threshold_header_bytes':16,'nominal_two_block_bytes':192,'possible_unsplit_tail_each_bytes':[0,4,8,12],'two_allocation_blocks_bound_bytes_in_this_TLSF_path':[192,216]},
 'derivation_limit':'Allocator block accounting only from pinned 32bit nonpoisoned/no-tracking path. No isolated concurrent heap measurement, no new heap arena/control allocation charged to the provider, no hardware watermark yet; external fragmentation/overall free heap is not a payload sum.',
 'other_lazy_audit':'The two ADC SDK lock handles are warmed with true try-lock/release before authority. Collection returning paths use already-initialized handles; ADC APB/RCC/regi2c use static refcounts/portMUX. No new task/DMA/per-draw app allocation. SDK abort/error logging/UI and concurrent camera/USB tasks are not claimed universally heap-free; SDK OOM assert/reset is not a typed fallible allocation result.',
 'INTERNAL_static_objects':'actual sizes/addresses/sections in artifact-checks/summary.json; provider owner28+history34+lock8=70bytes (second name owner4 is a different SDK/static object); last_report320bytes separate',
 'stack':'existing worker98304 INTERNAL unchanged; 32byte C staging+32byte Rust destination. Selected machine bodies retained for review; complete SDK/ROM/concurrent stack cost not claimed as measured. New hardware minimum free>=4096 required; old45756 historical only.',
 'new_hardware':'NOT RUN'
})
wr(F/'source-and-closure.json',{
 'source':B['source'],'tree':B['tree'],'app_tree':B['app_tree'],'source_inputs':len(B['source_inputs']),
 'Rust_compiled_source':B['Rust_compiled_source'],'Rust_inputs_unchanged_to_final':True,'Rust_archives':{n:sha(p) for n,p in rust.items()},
 'SDK_commit':B['SDK'],'SDK_sources':sdk_records,'optional_supplemental_missing_paths':missing,
 'SDK_core_vendor_lock_unchanged':True,'ABI':'ELF32 RISC-V RVC single-float e_flags3',
 'generated_config':{'min_rev':300,'max_rev':399,'CPU_MHz':400,'XTAL_MHz':40,'PM':False,'WDT_seconds':5,'WDT_probe_mode':0,'panic':'silent reboot; not ROM/taskname/log qualification','coredump':'NONE','worker_stack_INTERNAL_bytes':98304,'SDKconfig_sha256':B['sdkconfig_sha256']},
 'modes':{'normal':0,'fixed-unavailable':1},'flash_mode_freq_size':'DIO/80m/16MB','offsets':{'bootloader.bin':'0x2000','partitions.bin':'0x8000','firmware.bin':'0x20000'},'boot_app0':'NONE',
 'RNG_preprocessor':'Three SOC_RNG_* conditions undefined in actual hw_randomTU; init_rng absent from CPP and ELF. Hardware startup active TRNG is not attributed to absent constructor. Actual providerTU ANA_I2C_MST_CLK_HAS_ROOT_GATING=1.',
 'source_contract_and_gap':'Exact SDK ADC1+rev3 LP_TRNG helper and esp_random retained. Preliminary TRM/SDK rev3 physical interconnect mapping incomplete. Samplecnt8bit diagnostic only; no DONE/DATA_STATUS/freshness or quality predicate copied from S3.',
 'public_limit':'published11 identity only; metadata no raw aux/keys/request; one attempt perCPUboot including failure; no import/generation/recovery/custody/offline/RF/entropyhealth/realidentity/USER/task closure',
 'prior_proof_reused':{'source':'33a6b4e3e29c4dd74b8557bc38d1c5b345c07290','packet_members':217,'manifest_sha256':sha(old/'SHA256SUMS'),'all_old_members_reverified':True,'no_historical_hardware_result_promoted_to_new_image':True},
 'author_hardware':'NOT RUN; root distinct source/artifact review before USB'
})
wr(F/'packet.json',{
 'source':B['source'],'author':'/root/s3_native_finish','reviewer_operator':'/root','contract_sha256':B['root_contract_sha256'],'root_review_sha256':B['root_review_sha256'],'resource_amendment_sha256':B['resource_amendment_sha256'],
 'source_prebuild_sha256':sha(F/'source-before-build.json'),'source_inputs_verified_after_final_build':len(B['source_inputs']),
 'normal':json.loads((F/'normal/variant.json').read_text()),'fixed_unavailable':json.loads((F/'fixed-unavailable/variant.json').read_text()),
 'records':records,'unexplained_failures':[],
 'explained_RED':{'01':'Host test source formatting split CHECK macro and misleading if/return; fixed only formatting; exact RED source retained, no runtime/firmware had run.','06':'Expected missing strong provider host link failure, no fallback.','18':'Packaging DWARF reader looked for sizeof-only uninstantiated type in providerCU; corrected reader uses actual instantiated SDK locks.c type, no source/rebuild change.'},
 'proof':'6244 ASan/UBSan checks; actual shared admission/warm/collector policy. One Cargo consumer invocation for both targets; positive602 host synthetic byteequal historical expected; aux0/31/33/error each one call after31synthetic reviews, return-11/output0; no human or hardware inference.',
 'build_dir_left':'fixed-unavailable1; normal captured independently; no third rebuild to reset cache',
 'no_unchanged_core_campaign':True,'hardware':'NOT RUN','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()
})
readme="""# P4 public fallible RNG experiment — source b259d416

Only the published 11x32 fixture identity is permitted. This packet does not admit production entropy, private identities, offline/RF absence, USB human-origin, custody, erasure, panic/ROM safety or task closure. Root alone reviews and operates hardware. No USB/flash was performed by the author.

The unchanged SDK6.0.2 commit7101770 helper enables its ADC1 internal path and, for minrev300, LP_TRNG. The exact rev3 physical source mapping remains incomplete in the collected preliminary TRM. Readbacks/locks/finite calls and gross screens cannot establish entropy quality. Sample count is diagnostic only. Both real SDK ADC locks are initialized once before engine/key under the approved resource amendment; payload184 INTERNAL bytes, allocator accounting is separate in allocator-and-resources.json. SDK OOM may assert/reset; between-call50ms checks cannot cancel a hung SDK call.

There are two independent image sets: normal and fixed-unavailable. Both keep normal C6 guard mode0 and unchanged5sWDT. Fixed mode has no source helper/esp_random/collector executable body; it still binds the real SDK mutexes and refuses with typed Unavailable after the existing full local review/BOOT confirmation. One auxiliary attempt per CPU boot, including failure; no scan/retry-until-green. Failure supplies0, wipes buffers and cannot emit a response QR. Success has a terminal public-test screen after the response lifetime.

Frozen source is b259d416c482569622e6467a121b6c4436e6ac9e; app tree a28abb7ec022b2bd646b668fdae2fb96609acacb. Rust was compiled exactly once from f6f08824cf70186cdf472531f0b1863df8036048 in one Cargo call for host and RISC-V targets. Its Rust/core/ABI inputs are identical at b259; the later change only warms real SDK locks before authority. The historical33 packet and source remain unchanged and are source-bound under prior-proof; its hardware observations do not qualify these images.

Review source-before-build.json, source-and-closure.json, generated config, variant.json, selected machine bodies/direct calls, actual TU preprocessor files and licenses/index.json. Three SOC_RNG_* conditions are absent in the actual hw_randomTU, so init_rng is neither compiled nor linked. ANA root gating is1 in the providerTU; an unrelated macro absent from hw_randomTU is not a global0 claim. The executable-name scan distinguishes two link anchors and the read-only running-partition metadata call from consumers/persistent writers; it is not an exhaustive proof against indirect/ROM/concurrent activity.

Offline tests:6244 checks with ASan/UBSan on actual shared admission/warm/collection policies; expected absent-provider linkRED; real Rust hostFFI normal602B and error/0/31/33 all after31synthetic presentations. Target normal and fixed each built once and passed. Test-formatRED01 and packaging-readerRED18 are preserved with exact inputs and explained in packet.json. No unchanged core/QR/gesture/WDT/C6 suite was replayed.

Root procedure after distinct source/artifact approval:
1. Verify SHA256SUMS; select fixed-unavailable for one negative boot. Use that directory's files only. Actual generated settings are DIO80m16MB, bootloader.bin at0x2000, partitions.bin at0x8000, firmware.bin at0x20000; no boot_app0. Root may use its already reviewed erase/flash/readback method; generated reset arguments are recorded, not a promise about board behavior.
2. Capture one fresh full local request review and BOOT hold/release. Expected: one typed Unavailable, no source-helper calls, supplied0, no QR/signature, terminal PUBLIC AUX STOPPED. Guard54 stays ACTIVE/pad0. Stop on unexpected outcome; do not repeat to obtain green.
3. In a separate normal boot, use a new public request and fresh complete review. At most one auxiliary attempt. Require entropy-before/after GPIO54 config/pad0, own lock/ref cleanup, expected active clock/source flags, helper1/1,8words/32supplied, elapsed<=50ms if success, worker free stack>=4096, continuing display/camera/touch and no raw auxiliary output. If successful, scan response and verify explicit11 identity with actual client plus independent BIP340 oracle. Stop on first unexpected failure; retain UNKNOWN if not observed. No additional four-draw/statistical screen.
4. Keep the normal/fixed captures separate with image identities and CPU boots. No production entropy/identity admission follows from a successful public signature. SDK hangs/fatal paths and foreign concurrent violations are outside hard cancellation/heap-free guarantees.

Reproduction uses the existing app build.py, pinned inputs/locks and recorded environment only: one rust --host-proof invocation as necessary, configure/app --probe-mode normal --entropy-mode normal, then configure/app --probe-mode normal --entropy-mode fixed-unavailable. The current shared build directory is intentionally left fixed-unavailable; this packet holds both independent captures. No SDK/vendor/core patch, alternative MCU, eFuse or persistent secret endpoint is introduced.
"""
(F/'README.md').write_text(readme)
print(json.dumps({'packet':str(F),'source_inputs':len(B['source_inputs']),'records':len(records),'SDK_sources':len(sdk_records),'licenses':len(notices),'files':sum(p.is_file() for p in F.rglob('*')),'source':git('rev-parse','HEAD')},indent=2))
