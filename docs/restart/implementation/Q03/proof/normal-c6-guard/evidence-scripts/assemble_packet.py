from pathlib import Path
import json,hashlib,shutil,subprocess,time,datetime,re,gzip
from elftools.elf.elffile import ELFFile
R=Path('/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25');W=R/'p4-session';A=W/'apps/p4';E=A/'evidence/c6-normal-guard';P=E/'final-packet';T=R/'p4-probe';SDK=T/'src/esp-idf'
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def cp(src,rel):
 dest=P/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);return {'file':rel,'bytes':dest.stat().st_size,'sha256':sha(dest)}
source='33a6b4e3e29c4dd74b8557bc38d1c5b345c07290'
assert subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip()==source
assert not subprocess.check_output(['git','-C',str(W),'status','--porcelain=v1','--untracked-files=all'],text=True)
pre=json.loads((P/'source-before-build.json').read_text());packet=json.loads((P/'packet.json').read_text())
assert pre['source']==source
for rel,h in pre['source_inputs'].items():assert sha(W/rel)==h,rel
for rel in pre['source_inputs']:cp(W/rel,'source/'+rel)
cp(W/'LICENSE','source-notices/LICENSE-nsealr')
cp(A/'rust/target/riscv32imafc-unknown-none-elf/release/libnsealr_p4_optical.a','rust-core-reused.a')
files=[]
for rel,name in [('nsealr_p4_public_optical.bin','firmware.bin'),('nsealr_p4_public_optical.elf','firmware.elf'),('nsealr_p4_public_optical.map','firmware.map'),('bootloader/bootloader.bin','bootloader.bin'),('partition_table/partition-table.bin','partitions.bin'),('flasher_args.json','flasher_args.json'),('flash_args','flash_args'),('config/sdkconfig.h','sdkconfig.h'),('config/sdkconfig.json','sdkconfig.json'),('project_description.json','project_description.json'),('compile_commands.json','compile_commands.json'),('CMakeCache.txt','CMakeCache.txt')]:
 info=cp(A/'build'/rel,'normal/'+name);info['file']=name;files.append(info)
cp(A/'sdkconfig','normal/sdkconfig')
packet['normal']={'mode':0,'files':files,'sdkconfig_sha256':sha(P/'normal/sdkconfig')}
for cmd in packet['commands']:
 assert cmd['exit']==0
 for rel in cmd['evidence']:
  folder=W/rel;result=json.loads((folder/'result.json').read_text());assert result['exit']==0
  for f,key in [('stdout.log','stdout.log_sha256'),('stderr.log','stderr.log_sha256')]:assert sha(folder/f)==result[key]
  for f in folder.iterdir():
   if f.is_file():cp(f,'build-evidence/'+folder.name+'/'+f.name)
for folder in sorted(E.glob('native-*')):
 if not folder.is_dir():continue
 for f in sorted(folder.iterdir()):
  if f.is_file() and f.name!='guard-native':cp(f,'native/'+folder.name+'/'+f.name)
cp(E/'native-results.json','native/initial-results.json')
final=json.loads((E/'native-guard-final/result.json').read_text())
for rel,h in final['sources'].items():assert sha(A/rel)==h,rel
initial=json.loads((E/'native-results.json').read_text())
unchanged_native=['main/worker_watchdog.c','tests/worker_watchdog_test.c','main/response_lifetime.c','tests/response_lifetime_test.c','main/local_input.c','main/local_input.h']
for rel in unchanged_native:assert sha(A/rel)==initial['sources']['apps/p4/'+rel],rel
native_binding={'guard_final_result_sha256':sha(E/'native-guard-final/result.json'),'guard_final_sources':final['sources'],'guard_final_case_count':27,'guard_final_commands_exit':[x['exit'] for x in final['commands']],'affected_feed_response_sources':{rel:sha(A/rel) for rel in unchanged_native},'affected_commands_exit':[x['exit'] for x in initial['commands'] if Path(x['argv'][-1]).name in {'watchdog-native','response-native'}],'initial_guard_green':'Historical first mock lacked actual OEN reset default; not final admission. Kept with corrected-model expected RED and exact before-helper snapshot.','RED_source_sha256':sha(E/'native-guard-reset-model-red/c6_guard-before.c'),'RED_fixture_is_final':json.loads((E/'native-guard-reset-model-red/result.json').read_text())['fixture_sha256']==sha(A/'tests/c6_guard_test.c'),'no_unchanged_suite_replay':True}
assert all(x==0 for x in native_binding['guard_final_commands_exit']) and native_binding['RED_fixture_is_final']
native_binding['affected_result_receipts']=[{'path':'native/native-'+name+'-'+stage+'/result.json','sha256':sha(P/('native/native-'+name+'-'+stage+'/result.json')),'exit':0} for name in ['watchdog','response'] for stage in ['compile','run']]
assert len(native_binding['affected_commands_exit'])==4 and all(x==0 for x in native_binding['affected_commands_exit'])
write(P/'native-source-binding.json',native_binding)
for name in ['p4-normal-c6-guard-contract.json','p4-normal-c6-guard-contract-root-review.json','p4-normal-c6-guard-main-merge.json','p4-c6-root-probe-assessment.json']:
 cp(R/'intake'/name,'intake-source/'+name)
cp(R/'intake/p4-c6-observed-runtime.log','prior-observation/p4-c6-observed-runtime.log')
sdk_paths=['LICENSE','components/esp_driver_gpio/include/driver/gpio.h','components/esp_driver_gpio/src/gpio.c','components/esp_hal_gpio/include/hal/gpio_types.h','components/esp_hal_gpio/include/hal/gpio_hal.h','components/esp_hal_gpio/esp32p4/include/hal/gpio_ll.h','components/soc/esp32p4/register/hw_ver3/soc/gpio_reg.h','components/soc/esp32p4/register/hw_ver3/soc/io_mux_reg.h','components/soc/esp32p4/include/soc/gpio_sig_map.h','components/soc/esp32p4/include/soc/soc.h','components/esp_system/ld/esp32p4/sections.ld.in']
sdk_sources=[]
for rel in sdk_paths:
 original=subprocess.check_output(['git','-C',str(SDK),'show',pre['SDK_commit']+':'+rel])
 assert original==(SDK/rel).read_bytes(),rel
 info=cp(SDK/rel,'sdk-sources/'+rel);info['path']=rel;sdk_sources.append(info)
nmtool=str(T/'tools/tools/riscv32-esp-elf/esp-15.2.0_20251204/riscv32-esp-elf/bin/riscv32-esp-elf-nm')
checks=[('image-info',[str(T/'python-env-uv/bin/python'),'-m','esptool','image-info',str(P/'normal/firmware.bin')]),('linked-symbols',[nmtool,'-S','--defined-only','-C',str(P/'normal/firmware.elf')]),('undefined-symbols',[nmtool,'-u',str(P/'normal/firmware.elf')])]
for label,argv in checks:
 folder=P/'artifact-checks'/label;folder.mkdir(parents=True)
 start=time.monotonic();run=subprocess.run(argv,cwd=W,capture_output=True,timeout=60)
 (folder/'stdout.log').write_bytes(run.stdout);(folder/'stderr.log').write_bytes(run.stderr)
 command={'argv':argv,'cwd':str(W),'role':'read-only artifact inspection; no USB/hardware access'}
 write(folder/'command.json',command)
 write(folder/'result.json',dict(command,exit=run.returncode,seconds=time.monotonic()-start,stdout_sha256=sha(folder/'stdout.log'),stderr_sha256=sha(folder/'stderr.log')))
 assert run.returncode==0
nm=(P/'artifact-checks/linked-symbols/stdout.log').read_text()
for name in ['p4_c6_guard_begin','p4_c6_guard_check','p4_c6_guard_before_abort','p4_engine_init','p4_engine_run','p4_worker_idle','p4_worker_watchdog_start','p4_monotonic_ms','p4_display_ack_complete']:
 assert re.search(r' [TtWw] '+name+'$',nm,re.M),name
forbidden=[s for s in nm.splitlines() if re.search(r' [TtWw] (?:p4_c6_run|p4_c6_public_probe|sdmmc_card_init|sdmmc_io_get_cis_data|esp_hosted.*|esp_wifi_init)$',s)]
assert not forbidden,forbidden
undefined=(P/'artifact-checks/undefined-symbols/stdout.log').read_text().splitlines()
assert [s.strip().split()[-1] for s in undefined]==['__cxx_fatal_exception','start_app','start_app_other_cores']
cmds=json.loads((P/'normal/compile_commands.json').read_text())
actual_flags={}
for name in ['c6_guard.c','worker_watchdog.c','p4_local.c','main.c']:
 c=next(x['command'] for x in cmds if x['file'].endswith('/main/'+name))
 assert '-DP4_WDT_PROBE_MODE=0 ' in c
 assert '/soc/esp32p4/register/hw_ver3 ' in c or '/soc/esp32p4/register/hw_ver3/' in c or '/soc/esp32p4/register/hw_ver3/include' in c
 actual_flags[name]=0
cfg=json.loads((P/'normal/sdkconfig.json').read_text())
assert cfg['ESP_TASK_WDT_TIMEOUT_S']==5 and cfg['ESP_TASK_WDT_PANIC'] and cfg['ESP_SYSTEM_PANIC_SILENT_REBOOT'] and cfg['ESP_COREDUMP_ENABLE_TO_NONE'] and cfg['FREERTOS_HZ']==1000
assert sha(P/'normal/sdkconfig')==pre['effective_sdkconfig_sha256']
flash=json.loads((P/'normal/flasher_args.json').read_text())
assert flash['flash_settings']=={'flash_mode':'dio','flash_size':'16MB','flash_freq':'80m'}
assert set(flash['flash_files'])=={'0x2000','0x8000','0x20000'}
assert json.loads((P/'normal/project_description.json').read_text())['project_version']==source[:8]
with (P/'normal/firmware.elf').open('rb') as f:
 elf=ELFFile(f);assert elf['e_machine']=='EM_RISCV' and elf['e_flags']==3
 line=next(s for s in nm.splitlines() if s.endswith(' nsealr_p4_optical::STORAGE'))
 addr,size=[int(x,16) for x in line.split()[:2]]
 assert size==5920 and 0x4ff00000<=addr<0x50000000
 section=next(s for s in elf.iter_sections() if s['sh_addr']<=addr and addr+size<=s['sh_addr']+s['sh_size'])
 storage={'address':hex(addr),'bytes':size,'section':section.name,'meaning':'internal HP SRAM by unchanged SDK linker and runtime check; no physical margin/erasure/custody claim'}
audit={'source':source,'app_tree':pre['app_tree'],'source_inputs':len(pre['source_inputs']),'SDK_commit':pre['SDK_commit'],'SDK_sources':sdk_sources,'actual_mode_flags':actual_flags,'SDK_and_Rust_unchanged':True,'ABI':'ELF32 RISC-V RVC single-float e_flags3','Rust_storage':storage,'worker_stack_bytes':96*1024,'undefined_anchors':undefined,'normal_forbidden_linked_names':forbidden,'flash_settings':flash['flash_settings'],'flash_offsets':flash['flash_files'],'project_version':source[:8],'native_source_binding':'native-source-binding.json','OE_adaptation':'Only documented GPIO54 OEN_SEL/OEN_INV_SEL after latch0, before INPUT_OUTPUT; SDK hw_ver3 source and no-disable sequence retained. Root approved this concrete adaptation. No private HAL API/SDK edit.','author_hardware':'NOT RUN; root alone reviews/flashes','not_qualified':['RF/offline/data-host absence','human consent over USB','C6 die/firmware/pin4 voltage/PCB revision','reset hold/erasure/panic/log/entropy/custody','revocation of already displayed/scanned QR']}
write(P/'source-and-closure.json',audit)
packet.update(source_closure='source-and-closure.json',native_source_binding='native-source-binding.json',native_source_binding_sha256=sha(P/'native-source-binding.json'),ABI=audit['ABI'],normal_builddir_restored=True,SDK_sources_count=len(sdk_sources),root_review_sha256=pre['root_review_sha256'],root_OE_followup='Root explicitly approved normalization of the two documented OE bits with real reset model/RED/readback, no private HAL or SDK edit.',current_topology='Root associated reconnected P4 USB bridge/path; public USB connected. Prior battery/PWR observation retained without CPU continuity inference.',finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(P/'packet.json',packet)
cp(E/'assemble_packet.py','evidence-scripts/assemble_packet.py')
(P/'README.md').write_text('Frozen normal public C6 guard source '+source+'; author p4_optical_review; distinct reviewer/operator root.\nOne normal configure/build; no USB/probe/canary/core/crypto replay.\nSource/SDK/native/ABI/offset binding and limitations are in packet.json and source-and-closure.json.\nHistorical first-mock GREEN and actual-reset-model RED remain with the exact final fixture and before-helper snapshot.\nNo hardware/RF/offline/custody qualification.\n')
lines=[sha(f)+'  '+str(f.relative_to(P)) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='SHA256SUMS']
(P/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
names=set()
for line in (P/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);assert n not in names and sha(P/n)==h;names.add(n)
actual={str(f.relative_to(P)) for f in P.rglob('*') if f.is_file() and f.name!='SHA256SUMS'}
assert names==actual
print(json.dumps({'verdict':'PASS_AUTHOR_SOURCE_ARTIFACT_READBACK_PENDING_DISTINCT_ROOT_REVIEW','source':source,'packet':str(P),'members':len(names)+1,'manifest_sha256':sha(P/'SHA256SUMS'),'packet_json_sha256':sha(P/'packet.json'),'app_bin_bytes':(P/'normal/firmware.bin').stat().st_size,'app_bin_sha256':sha(P/'normal/firmware.bin'),'app_elf_sha256':sha(P/'normal/firmware.elf'),'source_inputs':len(pre['source_inputs']),'SDK_sources':len(sdk_sources),'storage':storage},indent=2))
