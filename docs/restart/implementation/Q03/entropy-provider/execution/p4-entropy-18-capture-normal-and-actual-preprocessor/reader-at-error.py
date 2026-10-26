import pathlib,json,hashlib,shutil,subprocess,shlex,re,sys
from elftools.elf.elffile import ELFFile
R=pathlib.Path('/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25')
A=R/'p4-session/apps/p4';B=A/'build';O=A/'evidence/entropy-public'
mode=sys.argv[1];assert mode in ['normal','fixed-unavailable']
D=O/mode;assert not D.exists();D.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cp(src,name):
 d=D/name;shutil.copy2(src,d);return {'file':name,'bytes':d.stat().st_size,'sha256':sha(d)}
files=[]
for src,name in [(B/'nsealr_p4_public_optical.bin','firmware.bin'),(B/'nsealr_p4_public_optical.elf','firmware.elf'),(B/'nsealr_p4_public_optical.map','firmware.map'),(B/'bootloader/bootloader.bin','bootloader.bin'),(B/'partition_table/partition-table.bin','partitions.bin'),(B/'flasher_args.json','flasher_args.json'),(B/'flash_args','flash_args'),(A/'sdkconfig','sdkconfig'),(B/'config/sdkconfig.h','sdkconfig.h'),(B/'config/sdkconfig.json','sdkconfig.json'),(B/'config/sdkconfig.cmake','sdkconfig.cmake'),(B/'project_description.json','project_description.json'),(B/'compile_commands.json','compile_commands.json'),(B/'CMakeCache.txt','CMakeCache.txt')]:files.append(cp(src,name))
c=json.loads((D/'compile_commands.json').read_text());flags={}
for name in ['p4_entropy.c','c6_guard.c','main.c','worker_watchdog.c']:
 e=next(x for x in c if x['file'].endswith('/main/'+name));f=[x for x in shlex.split(e['command']) if x.startswith('-DP4_')];flags[name]=f
 assert '-DP4_WDT_PROBE_MODE=0' in f
 if name=='p4_entropy.c':assert '-DP4_ENTROPY_FIXED_UNAVAILABLE='+str(int(mode!='normal')) in f
config=json.loads((D/'sdkconfig.json').read_text())
assert config['ESP32P4_REV_MIN_FULL']==300 and not config.get('PM_ENABLE',False)
assert config['ESP_TASK_WDT_PANIC'] and config['ESP_SYSTEM_PANIC_SILENT_REBOOT']
assert sha(D/'sdkconfig')=='a5d508d745eff91de953d6e6f5d48f384f130dd6e1cd8ee13422440862cb494d'
flash=json.loads((D/'flasher_args.json').read_text());assert set(flash['flash_files'])=={'0x2000','0x8000','0x20000'}
assert flash['flash_settings']=={'flash_mode':'dio','flash_size':'16MB','flash_freq':'80m'}
with open(D/'firmware.elf','rb') as f:
 elf=ELFFile(f);assert elf.elfclass==32 and elf['e_flags']==3
 dwarf=elf.get_dwarf_info();sizes={}
 for cu in dwarf.iter_CUs():
  top=cu.get_top_DIE();name=top.attributes.get('DW_AT_name')
  if name and name.value.decode().endswith('/p4_entropy.c'):
   for die in cu.iter_DIEs():
    n=die.attributes.get('DW_AT_name')
    if n and n.value in [b'StaticSemaphore_t',b'p4_entropy_report_t']:
     typed=die
     while 'DW_AT_type' in typed.attributes and 'DW_AT_byte_size' not in typed.attributes:typed=typed.get_DIE_from_attribute('DW_AT_type')
     if 'DW_AT_byte_size' in typed.attributes:sizes[n.value.decode()]=typed.attributes['DW_AT_byte_size'].value
 assert 'StaticSemaphore_t' in sizes and 2*sizes['StaticSemaphore_t']<=512,sizes
 assert sizes.get('p4_entropy_report_t',513)<=512,sizes
if mode=='normal':
 e=next(x for x in c if x['file'].endswith('/esp_hw_support/hw_random.c'))
 args=shlex.split(e['command']);base=[];skip=False
 for arg in args:
  if skip:skip=False;continue
  if arg in ['-o','-MF','-MT','-MQ']:skip=True;continue
  if arg in ['-c','-MD','-MMD','-MP']:continue
  base.append(arg)
 commands=[]
 for extra,name in [(['-dM','-E'],'hw_random.macros'),(['-E','-P'],'hw_random.i')]:
  argv=base+extra
  with open(D/name,'w') as out:subprocess.run(argv,cwd=e['directory'],stdout=out,check=True)
  commands.append({'argv':argv,'cwd':e['directory'],'file':name,'sha256':sha(D/name)})
 macros={}
 for line in (D/'hw_random.macros').read_text().splitlines():
  m=re.match(r'#define (\w+)\s*(.*)',line)
  if m:macros[m.group(1)]=m.group(2)
 selected={k:macros.get(k) for k in ['SOC_RNG_CLOCK_IS_INDEPENDENT','SOC_RNG_BUF_CHAIN_ENTROPY_SOURCE','SOC_RNG_RTC_TIMER_ENTROPY_SOURCE','SOC_RTC_TIMER_SUPPORTED','WDEV_RND_REG','RNG_DATA_REG','DR_REG_LP_TRNG_BASE','CONFIG_ESP32P4_REV_MIN_FULL','ANA_I2C_MST_CLK_HAS_ROOT_GATING']}
 expanded=(D/'hw_random.i').read_text()
 assert 'init_rng(' not in expanded
 (D/'rng-preprocessor.json').write_text(json.dumps({'commands':commands,'selected_macros':selected,'init_rng_body_present':False,'meaning':'Undefined RNG_CLOCK/BUF_CHAIN/RTC entropy condition macros compile as0; no ignored SDK init_rng branch may be cited as foreign active TRNG cause. RTC_TIMER_SUPPORTED mixing remains distinct.'},indent=2)+'\n')
j={'mode':mode,'source':subprocess.check_output(['git','-C',str(A.parent.parent),'rev-parse','HEAD'],text=True).strip(),'project_version':json.loads((D/'project_description.json').read_text())['project_version'],'files':files,'actual_flags':flags,'ABI':'ELF32 RISC-V RVC single-float flags3','DWARF_type_bytes':sizes,'SDK_mutex_payload_bytes':2*sizes['StaticSemaphore_t'],'allocator_overhead':'separate; no isolated concurrent heap-delta claim','hardware':'NOT RUN'}
(D/'variant.json').write_text(json.dumps(j,indent=2)+'\n')
print(json.dumps(j,indent=2))
