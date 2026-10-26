import pathlib,json,subprocess,hashlib,re,shlex
from elftools.elf.elffile import ELFFile
R=pathlib.Path('/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25')
A=R/'p4-session/apps/p4';O=A/'evidence/entropy-public';OLD=A/'evidence/c6-normal-guard/final-packet'
nm_old=json.loads((OLD/'artifact-checks/linked-symbols/command.json').read_text())['argv']
nm=pathlib.Path(nm_old[0]);objdump=nm.with_name(nm.name.rsplit('-',1)[0]+'-objdump');readelf=nm.with_name(nm.name.rsplit('-',1)[0]+'-readelf')
records=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(argv,path,cwd=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 with open(path,'w') as out:subprocess.run(list(map(str,argv)),cwd=cwd,stdout=out,check=True)
 records.append({'argv':list(map(str,argv)),'cwd':str(cwd or A),'output':str(path.relative_to(O)),'sha256':sha(path)})
summary={}
for mode in ['normal','fixed-unavailable']:
 D=O/mode;C=O/'artifact-checks'/mode;elf=D/'firmware.elf'
 run([nm,'-S','--defined-only','-C',elf],C/'defined.txt')
 run([nm,'-u',elf],C/'undefined.txt')
 run([readelf,'-SW','-sW',elf],C/'sections-symbols.txt')
 text=(C/'defined.txt').read_text()
 assert re.search(r' T p4_entropy_fill32$',text,re.M)
 assert 'p4_fixture_auxiliary' not in text
 assert not re.search(r' [TtWw] init_rng$',text,re.M)
 for name in ['esp_random','bootloader_random_enable','bootloader_random_disable','p4_entropy_collect']:
  present=bool(re.search(r' [TtWw] '+name+r'$',text,re.M))
  assert present==(mode=='normal'),(mode,name,present)
 undef=[x.split()[-1] for x in (C/'undefined.txt').read_text().splitlines()]
 assert undef==['__cxx_fatal_exception','start_app','start_app_other_cores'],undef
 raw=subprocess.check_output([str(objdump),'-d','-C',str(elf)],text=True)
 targets={x:[] for x in ['p4_entropy_fill32','esp_random','bootloader_random_enable','bootloader_random_disable','adc_lock_try_acquire','adc_lock_release','adc_apb_periph_claim','adc_apb_periph_free']}
 current=None
 for line in raw.splitlines():
  m=re.match(r'^[0-9a-f]+ <(.+)>:$',line)
  if m:current=m.group(1);continue
  for target in targets:
   if '<'+target+'>' in line:targets[target].append({'caller':current,'instruction':line.strip()})
 if mode=='normal':
  assert targets['esp_random'] and all(x['caller']=='word' for x in targets['esp_random'])
  assert targets['bootloader_random_enable'] and all(x['caller']=='source' for x in targets['bootloader_random_enable'])
  assert targets['bootloader_random_disable'] and all(x['caller']=='source' for x in targets['bootloader_random_disable'])
 assert targets['p4_entropy_fill32']
 (C/'direct-calls.json').write_text(json.dumps({'limits':'Direct references only; indirect callbacks and SDK fatal/ROM activity need source analysis','targets':targets},indent=2)+'\n')
 with open(elf,'rb') as f:
  e=ELFFile(f);s=e.get_section_by_name('.symtab');selected=[]
  names={'p4_entropy_fill32','p4_entropy_bind_worker','p4_entropy_collect','p4_entropy_warm_locks','bootloader_random_enable','bootloader_random_disable','esp_random','snapshot','source','bus','try_lock','release_lock','guard'}
  for symbol in s.iter_symbols():
   if symbol['st_info']['type']=='STT_FUNC' and symbol.name in names:selected.append((symbol['st_value'],symbol['st_size'],symbol.name))
  with open(C/'selected-functions.txt','w') as out:
   for address,size,name in sorted(selected):
    out.write('FUNCTION '+name+' '+hex(address)+' '+str(size)+'\n')
    body=subprocess.check_output([str(objdump),'-d','--start-address='+hex(address),'--stop-address='+hex(address+size),str(elf)],text=True)
    assert any(l.startswith(format(address,'x')+':') for l in body.splitlines()),name
    out.write(body)
  objects=[]
  for symbol in s.iter_symbols():
   if symbol['st_info']['type']=='STT_OBJECT' and symbol.name in ['owner','owner_lock','history','last_report']:
    section=e.get_section(symbol['st_shndx']);objects.append({'name':symbol.name,'bytes':symbol['st_size'],'address':hex(symbol['st_value']),'section':section.name})
  for item in objects:assert item['section'] in ['.dram0.bss','.dram0.data'],item
  assert sum(x['bytes'] for x in objects if x['name'] in ['owner','owner_lock','history'])<=256
  assert next(x['bytes'] for x in objects if x['name']=='last_report')==320
 summary[mode]={'undefined_anchors':undef,'objects':objects,'direct_calls':targets,'functions_selected':len(selected)}
# Verify analog refcount macro in the provider TU; it is not included in hw_random TU.
D=O/'normal';commands=json.loads((D/'compile_commands.json').read_text())
entry=next(x for x in commands if x['file'].endswith('/main/p4_entropy.c'))
args=shlex.split(entry['command']);base=[];skip=False
for arg in args:
 if skip:skip=False;continue
 if arg in ['-o','-MF','-MT','-MQ']:skip=True;continue
 if arg in ['-c','-MD','-MMD','-MP']:continue
 base.append(arg)
assert (A/'build/config/sdkconfig.h').read_bytes()==(D/'sdkconfig.h').read_bytes()
run(base+['-dM','-E'],O/'artifact-checks/provider-normal.macros',cwd=entry['directory'])
macros=(O/'artifact-checks/provider-normal.macros').read_text()
assert re.search(r'^#define ANA_I2C_MST_CLK_HAS_ROOT_GATING 1\b',macros,re.M)
assert re.search(r'^#define P4_ENTROPY_FIXED_UNAVAILABLE 0$',macros,re.M)
summary['provider_macro_note']='ANA root gating1 in actual provider TU; undefined in hw_random TU only because that header is not included there. Three SOC_RNG_* conditionals are undefined in actual hw_random CPP and init_rng body/symbol absent.'
(O/'artifact-checks/commands.json').write_text(json.dumps(records,indent=2)+'\n')
(O/'artifact-checks/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'result':'PASS_ARTIFACTS_AND_CLOSED_DIRECT_REFERENCES_ONLY','variants':list(summary)[:2],'mutex_payload_bytes':184,'report_bytes':320},indent=2))
