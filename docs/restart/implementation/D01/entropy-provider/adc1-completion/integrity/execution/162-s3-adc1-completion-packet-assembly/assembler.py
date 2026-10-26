import pathlib,json,hashlib,shutil,subprocess,re,datetime
from elftools.elf.elffile import ELFFile
R=pathlib.Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25");P=R/"s3-probe";W=R/"s3-session";B=P/"native/build/idf-public";OLD=P/"artifacts/entropy-public";OUT=P/"artifacts/entropy-adc1-completion"
SOURCE="e7f04215fc97808acdafdbf9420f6ef6d0102c5b"
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(["git","-C",str(W),*a],text=True).strip()
def write(path,x):
 p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n")
def cp(src,dest):
 dst=OUT/dest;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);return {"file":str(dest),"bytes":dst.stat().st_size,"sha256":sha(dst)}
assert git("rev-parse","HEAD")==SOURCE and not git("status","--porcelain")
assert not OUT.exists(),OUT
oldmanifest=OLD/"SHA256SUMS";assert sha(oldmanifest)=="fa960732584895f48c6a11092753902d69f7d83b4ec5a569838de4aefc43e702"
oldmembers=0
for line in oldmanifest.read_text().splitlines():
 h,name=line.split("  ",1);assert sha(OLD/name)==h,name;oldmembers+=1
snapshot=json.loads((P/"execution/adc1-progress-source-before-build.json").read_text());assert snapshot["source"]==SOURCE
for item in snapshot["source_inputs"]:
 assert sha(W/item["path"])==item["sha256"],item["path"]
 assert git("rev-parse",SOURCE+":"+item["path"])==item["blob"],item["path"]
assert git("diff","f65e8aa9",SOURCE,"--","crates/nsealr-core","Cargo.lock","vendor/crypto-bigint","apps/s3-session/main/session_buttons.h","apps/s3-session/main/session_input.h","apps/s3-session/main/otg_public_state.h")==""
config=json.loads((B/"config/sdkconfig.json").read_text());prior=json.loads((OLD/"source-and-closure.json").read_text());prior.setdefault("descriptors_from_elf",prior["descriptors_unchanged_from_833"])
assert (B/"compile_commands.json").read_bytes()==(OLD/"compile_commands.json").read_bytes(),"reused macro command must match actual flags"
assert (B/"config/sdkconfig.h").read_bytes()==(OLD/"sdkconfig.h").read_bytes()
expected=prior["generated_config_checked"]
for k,v in expected.items():assert config.get(k,False)==v,(k,v,config.get(k))
for k in ["ESP_WIFI_ENABLED","BT_ENABLED","PM_ENABLE"]:assert not config.get(k,False),k
project=json.loads((B/"project_description.json").read_text());assert project["project_version"]==SOURCE[:8]
assert "espcoredump" not in project["build_components"]
flash=json.loads((B/"flasher_args.json").read_text());assert flash["flash_settings"]=={"flash_mode":"dio","flash_size":"16MB","flash_freq":"80m"}
assert set(flash["flash_files"])=={"0x0","0x8000","0x10000"}
nm=(P/"execution/156-s3-adc1-progress-linked-defined/stdout.log").read_text()
patterns={"named_persistent_writers":r" (?:esp_flash_write|esp_partition_write|nvs_(?:open|set|commit)\w*|esp_ota_(?:write|begin|end)|f_(?:open|write)|wl_write|esp_core_dump_write)$","competing_runtime_clients":r" (?:esp_wifi_init|esp_bt_controller_init|adc_oneshot_\w+|adc_continuous_\w+|i2s_\w+|temperature_sensor_\w+|esp_fill_random|getrandom|getentropy|arc4random\w*)$","obsolete_serial_jtag_or_console":r" (?:usb_serial_jtag_driver_install|usb_serial_jtag_read_bytes|usb_serial_jtag_write_bytes|esp_tusb_init_console|tinyusb_console_init|esp_vfs_tusb_cdc_register)$"}
scans={k:[l for l in nm.splitlines() if re.search(r" [TtWw] ",l) and re.search(p,l)] for k,p in patterns.items()}
assert not any(scans.values()),scans
undefined=(P/"execution/157-s3-adc1-progress-linked-undefined/stdout.log").read_text().splitlines();assert [l.split()[-1] for l in undefined]==["__cxx_fatal_exception","start_app","start_app_other_cores"]
assert "<nsealr_core::authorization::AuthorizationSession>::sign_approved" in nm
assert len(re.findall(r" T tud_event_hook_cb$",nm,re.M))==1
with open(B/"nsealr_s3_native_public.elf","rb") as f:
 elf=ELFFile(f);symtab=elf.get_section_by_name(".symtab")
 def named(n):
  line=next(l for l in nm.splitlines() if l.endswith(" "+n));a,size=line.split()[:2];return int(a,16),int(size,16)
 def getbytes(a,n):
  for s in elf.iter_sections():
   base=s["sh_addr"]
   if base<=a and a+n<=base+s["sh_size"] and s["sh_type"]!="SHT_NOBITS":return s.data()[a-base:a-base+n]
  raise AssertionError((a,n))
 a,n=named("device_descriptor");device=getbytes(a,n);a,n=named("configuration_descriptor");raw=getbytes(a,n)
 assert device.hex()==prior["descriptors_from_elf"]["device_hex"] and raw.hex()==prior["descriptors_from_elf"]["config_hex"]
 retained=[]
 for name in ["ctx","history","owner_lock","last_report","diagnostic_draws"]:
  a,n=named(name);s=next(s for s in symtab.iter_symbols() if s["st_value"]==a and s["st_size"]==n);section=elf.get_section(s["st_shndx"]).name
  assert 0x3fc80000<=a and a+n<0x3fce0000 and section in [".dram0.bss",".dram0.data"],(name,hex(a),section)
  retained.append({"name":name,"address":hex(a),"bytes":n,"section":section})
 assert sum(x["bytes"] for x in retained if x["name"] in ["ctx","history","owner_lock"])<=256
 assert sum(x["bytes"] for x in retained if x["name"] in ["last_report","diagnostic_draws"])==2048
macros=(P/"execution/145-s3-entropy-final-actual-macros/stdout.log").read_text()
for value in ["#define CONFIG_ESP_MAIN_TASK_STACK_SIZE 98304","#define CONFIG_TINYUSB_CDC_COUNT 1","#define CONFIG_TINYUSB_DEBUG_LEVEL 0","#define SYSTEM_WIFI_CLK_WIFI_EN 0","#define SYSTEM_WIFI_CLK_BT_EN 0"]:assert value in macros,value
compiled=[]
for entry in json.loads((B/"compile_commands.json").read_text()):
 p=pathlib.Path(entry["file"]);compiled.append({"source":str(p),"resolved":str(p.resolve()),"sha256":sha(p)})
OUT.mkdir()
files=[]
for src,name in [(B/"bootloader/bootloader.bin","bootloader.bin"),(B/"partition_table/partition-table.bin","partitions.bin"),(B/"nsealr_s3_native_public.bin","firmware.bin"),(B/"nsealr_s3_native_public.elf","firmware.elf"),(B/"nsealr_s3_native_public.map","firmware.map"),(B/"flasher_args.json","flasher_args.json"),(B/"flash_args","flash_args"),(P/"native/sdkconfig.otg-public","sdkconfig"),(B/"config/sdkconfig.h","sdkconfig.h"),(B/"config/sdkconfig.json","sdkconfig.json"),(B/"config/sdkconfig.cmake","sdkconfig.cmake"),(B/"project_description.json","project_description.json"),(B/"compile_commands.json","compile_commands.json"),(B/"CMakeCache.txt","CMakeCache.txt"),(P/"native/build/rust-core/xtensa-esp32s3-none-elf/release/libnsealr_s3_native_core.a","rust-core.a"),(B/"esp-idf/esp_tinyusb/libesp_tinyusb.a","esp_tinyusb.a")]:files.append(cp(src,name))
assert sha(OUT/"rust-core.a")==snapshot["Rust_archive_sha256"]
for item in snapshot["source_inputs"]:cp(W/item["path"],"source/"+item["path"])
for folder in ["licenses","source-notices","dependencies"]:
 for src in (OLD/folder).rglob("*"):
  if src.is_file():cp(src,str(src.relative_to(OLD)))
for name in ["licenses-inherited.json","Cargo.lock","root-Cargo.lock","crypto-bigint-checksum.json","request.json","request.serial"]:cp(OLD/name,name)
for name in ["s3-fallible-sar-entropy-contract.json","s3-fallible-sar-entropy-contract-root-review.json","s3-usb-only-power-amendment-root-review.json","s3-sar-data-status-resolution-contract.json","s3-sar-data-status-resolution-contract-root-review.json","s3-entropy-negative-provider-observation.json","s3-entropy-negative-runtime.log"]:cp(R/"intake"/name,"contract/"+name)
for name in ["s3-usb-only-power-amendment.json","s3-usb-only-power-amendment-root-review.json"]:cp(W/"docs/restart/implementation/P01"/name,"power/"+name)
for name in ["docs/product/requirements.md","docs/product/threat-models.md","docs/restart/implementation/D01/native-session-contract.md","plan/work-items.json","plan/evidence-index.json"]:cp(W/name,"power/source/"+name)
ledger=R/"intake/s3-entropy-primary-sources/exact-source-ledger.json";assert sha(ledger)=="065eaaef10bacb68d10cd2ef40d7468d334d406a6fab3cb9f58f7e306521ed67"
cp(ledger,"primary/exact-source-ledger.json")
critical=set(x["path"] for x in json.loads(ledger.read_text())["sdk_sources"])
critical.update(["components/hal/esp32s3/include/hal/adc_ll.h","components/hal/include/hal/adc_types.h","LICENSE","components/soc/esp32s3/include/soc/syscon_reg.h","components/soc/esp32s3/include/soc/sens_reg.h","components/soc/esp32s3/include/soc/rtc_cntl_reg.h","components/soc/esp32s3/include/soc/io_mux_reg.h","components/soc/esp32s3/include/soc/gpio_reg.h","components/hal/esp32s3/include/hal/regi2c_ctrl_ll.h","components/hal/platform_port/include/hal/regi2c_ctrl.h"])
sdkfiles=[]
for rel in sorted(critical):
 p=P/"native/src/esp-idf"/rel
 assert p.exists(),p
 sdkfiles.append(cp(p,"sdk-critical/"+rel))
for x in json.loads(ledger.read_text())["sdk_sources"]:assert sha(P/"native/src/esp-idf"/x["path"])==x["sha256"]
receipts={}
for folder in sorted((P/"execution").iterdir()):
 if not folder.is_dir() or not folder.name[:3].isdigit():continue
 number=int(folder.name[:3])
 if number not in set(range(128,162))|{114,116,117}:continue
 if not (folder/"result.json").exists():continue
 rec=json.loads((folder/"result.json").read_text());assert rec["exit"]==(2 if number==135 else 1 if number in (149,159) else 0),folder
 for name,key in [("stdout.log","stdout_sha256"),("stderr.log","stderr_sha256")]:assert sha(folder/name)==rec[key]
 for src in folder.iterdir():
  if src.is_file():cp(src,"evidence/execution/"+folder.name+"/"+src.name)
 receipts[folder.name]={"exit":rec["exit"],"seconds":rec["seconds"],"result_sha256":sha(folder/"result.json"),"stdout_sha256":rec["stdout_sha256"],"stderr_sha256":rec["stderr_sha256"]}
for src in (P/"execution/131-entropy-private-host-fixture").iterdir():
 if src.is_file():cp(src,"evidence/host-fake-aux-fixture/"+src.name)
for name in ["entropy_selected_disassembly.py","entropy_link_calls.py","entropy_packet.py"]:cp(P/"scripts"/name,"evidence/scripts/"+name)
cp(P/"execution/adc1-progress-source-before-build.json","evidence/source-before-build.json")
calls=json.loads((P/"execution/160-s3-adc1-progress-direct-rng-calls/stdout.log").read_text())
closure={"schema":"nsealr.s3-public-fallible-sar-closure.v1","source_commit":SOURCE,"tree":snapshot["tree"],"source_inputs":snapshot["source_inputs"],"source_input_count":len(snapshot["source_inputs"]),"core_unchanged":snapshot["old_core_blobs_unchanged"],"private_adapter_changed":False,"Rust_archive_sha256":snapshot["Rust_archive_sha256"],"generated_config_checked":expected,"RF_PM_config_false":["ESP_WIFI_ENABLED","BT_ENABLED","PM_ENABLE"],"project_version":project["project_version"],"build_components":project["build_components"],"compiled_sources":compiled,"compiled_source_count":len(compiled),"named_executable_scans":scans,"undefined_symbols":undefined,"undefined_note":"Three SDK -u extraction anchors, not an assertion of unresolved runtime imports","rng_direct_target_references":calls,"retained_internal_symbols":retained,"descriptors_unchanged_from_833":prior["descriptors_from_elf"],"sdk_critical_files":sdkfiles,"readback_limits":["Active SYSTEM/SENS/analog/DIG/data bank31, post-disable bank7 only; gated/reset DIG/data fields are UNKNOWN, not zero health","S3 WIFI_EN and BT_EN masks are zero; raw WIFI clock is logged, no RF-off boolean inferred from those masks","Owned post-helper APB gate restore uses existing HAL and no reset pulse; SDK source unchanged","Configured 240MHz CPU/80MHz APB and dividers are not physical calibrated frequencies","TRM doubleSAR RNG path does not establish a per-SAR bypass/fault-tolerance guarantee; rev0.2 ADC183 stays open"],"resource_check":{"main_stack_bytes":98304,"USB_stack_bytes":4096,"new_tasks_heap_DMA":0,"provider_state_cap":256,"diagnostic_retention_bytes":2048,"largest_selected_new_function_frame_bytes":464,"collector_frame_bytes":240,"stack_limit_note":"Selected entry instructions are supporting static evidence, not a complete indirect/ROM stack bound; affected main>=4096 and USB>=512 free watermarks remain root hardware checks"},"scan_limits":"Named linked executable scan and direct-call disassembly do not prove absence of all indirect/ROM activity or initialization outside the application image","historical_previous_entropy_packet_integrity":{"members":oldmembers,"manifest_sha256":sha(oldmanifest),"note":"all old members checked unchanged;439TinyUSB members reuse preflight114,84gesture/epoch checks reuse116/117, no repeated suite"}}
closure.update({"delta_base":"f65e8aa9b8917821e25a80d9d541bba29a9973a7","generated_macro_reuse":"145 reused: exact generated sdkconfig.h and full actual compile_commands bytes unchanged from f65; no macro definitions added by private completion layout","completion_observer":"Two independent initial-read/clear0/fresh1 sequences, timer bit24 only, ADC1_DONE raw/clear bit31; initial1 may clear normally; in-flight completion is a witness only, not exclusive trigger causality or ADC2/noise health","report_layout":"384bytes unchanged: word count uint8<=8, two phase bytes and reserved byte replace old uint32 count; private only, no Rust/wire ABI delta"})
write("source-and-closure.json",closure)
packet={"schema":"nsealr.s3-public-fallible-sar-packet.v1","created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":SOURCE,"compiled_source_commit":SOURCE,"branch":git("branch","--show-current"),"status":"SOURCE/HOST FAULTS/BUILD ONLY; root distinct review and one finite public hardware pass pending","sdk":json.loads((OLD/"packet.json").read_text())["sdk"],"dependencies":json.loads((W/"apps/s3-session/tinyusb-source.json").read_text()),"flash":{"chip":"esp32s3","mode":"dio","frequency":"80m","size":"16MB","files":[{"offset":"0x0","file":"bootloader.bin"},{"offset":"0x8000","file":"partitions.bin"},{"offset":"0x10000","file":"firmware.bin"}],"no_boot_app0":True,"operator":"root only; no USB/flash by author"},"files":files,"receipts":receipts,"tests":{"Rust_private_adapter":14,"provider_checks":1818,"duplicate_receipts":"133/134 repeat unchanged128/129: preserved, no extra coverage claimed","historical_reused":"114 dependency preflight;116/117 gesture+epoch; unchanged core/oracle/host suites not repeated"},"failures_preserved":{"135":"Target code formatting: misleading indentation and Xtensa uint32_t printf type. Fixed9df; final139 passes. No SDK failure.","149":"Packet assembler used nonexistent generic hal/include regi2c path; corrected to actual platform_port/include. No product source or build changed. Original assembler/log retained.","146":"GNU objdump repeated --disassemble options only printed the last target; valid public auxiliary body only.147 invokes each exact mangled function independently and asserts body presence.","packaging_python":"Outer system Python lacked elftools after140–145; no target command failed or was repeated.147 and packet use existing SDK venv with pyelftools0.33."},"hardware_expected":{"boot":"Wait for CDC configured/DTR; fresh GPIO0 Skip / GPIO14 Run. Run once, up to4x32 public draws, stop at first failure; fresh acknowledgement then scalar3 public workflow","draws":"Diagnostic attempt budget4 plus at most1 NEW auxiliary attempt per CPU boot, including failures; no retry-until-green","readbacks":"s3-public-rng-v1 (status/words/supplied/elapsed/banks/refs), s3-public-rng-reg-v1;32byte public-not-identity only on status0","failure":"Typed failure produces no auxiliary/fallback/signature; restart required after auxiliary failure. Nonreturning SDK call is not hard bounded by between-call50ms checks","root_only":"One persistent CDC handle, capture full bounded diagnostic and at most1 public roundtrip with explicit expected key; record main/USB watermarks and display/buttons. Unavailable source is a valid negative, not a reason to repeat"},"not_admitted":["identity import/generation/backup/recovery","entropy_ok/production source qualification from four samples","ADC183 exemption","wholeRAM/register/cache erasure","RF-off measurement or all reset/debug/ROM domains","C01/H01 task closure or device readiness"],"power":"S3 product USB-only, no battery/supercap requirement; E5 not applicable. Future real session ends on power loss and needs local reload; scalar3 auto fixture does not prove that.","transport_limits":"CDC queue acceptance is not host delivery; already queued prefix/full response cannot be recalled. Existing USB event-loss/reset/RAM limits remain; no secret endpoints added.","warnings":"Upstream manager-disabled/component/minimum-CMake/GNU-stack warnings retained in logs; no new SDK/vendor/WDT workaround"}
packet.update({"schema":"nsealr.s3-public-adc1-completion-packet.v1","delta_base":"f65e8aa9b8917821e25a80d9d541bba29a9973a7","tests":{"current_provider_checks":3485,"current_records":[152,153],"reused":"Rust14 from131, USB84 from116/117, dependency439members114, prior validators137/138; core/FFI/USB/SDK unchanged; no repeated campaign or Rust build","duplicate_historical":"133/134 duplicated128/129 and add no coverage"},"current_build":"154 sole affected target build PASS; source e7f04215","historical_negatives":"08d real one-aux Health refusal726b/raw0d575c preserved; no four-draw success, RNG-stuck diagnosis or source-quality conclusion","completion_phases":"progress=pre/post hex:bit0 initial read,bit1 initial1,bit2 observed clear0,bit3 fresh1. Successful d/f; phase0 unknown/unreached. Raw stable14000 alone never replaces both witnesses. Global50ms budget includes claim/settle/both phases/cleanup; finite256polls each, no hard guarantee for a nonreturning SDK call"})
packet["failures_preserved"]["159"]="Inspection selector expected a particular alias name, but compiler folded two lambda symbols to one body/address.161 groups by address/size and retains aliases; no firmware/source/build change. Original selector/log preserved."
packet["hardware_expected"]["readbacks"]+="; progress=pre/post d/f only after independent observed0to1, initial1 permitted after successful clear; prior raw14000 remains diagnostic"
write("packet.json",packet)
print(json.dumps({"packet":str(OUT),"source":SOURCE,"source_inputs":len(snapshot["source_inputs"]),"compiled_sources":len(compiled),"app":next(x for x in files if x["file"]=="firmware.bin"),"retained":retained,"receipts":len(receipts),"closure_sha256":sha(OUT/"source-and-closure.json")},indent=2))
