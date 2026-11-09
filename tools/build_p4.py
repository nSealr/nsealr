#!/usr/bin/env python3
"""Build the one P4 application with explicit SDK/tool/cache roots; never flash."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from prepare_adapter import prepare

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--tools',type=Path,required=True)
    p.add_argument('--python-env',type=Path,required=True)
    p.add_argument('--reuse-components',type=Path,help='Optional previously downloaded component store')
    p.add_argument('--core-root',type=Path,default=ROOT)
    p.add_argument('--rust-library',type=Path,required=True)
    p.add_argument('--work-dir',type=Path,default=ROOT/'.cache/p4')
    p.add_argument('--seed-config',type=Path,help='Initial measured board config; unnecessary once defaults are saved')
    a=p.parse_args()
    work=a.work_dir.resolve();work.mkdir(parents=True,exist_ok=True)
    for name in ('tmp','cache','idf-tools','components','managed_components'):(work/name).mkdir(exist_ok=True)
    sdk=a.sdk.resolve();tools=a.tools.resolve();python=a.python_env.resolve()
    head=subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()
    if head!='7101770dc6db2667b3c477cc31365dd1acd6db4e':raise SystemExit('Expected ESP-IDF 6.0.2 at its pinned source commit')
    cmake=next(path for path in (tools/'tools/cmake/4.0.3/bin/cmake',tools/'tools/cmake/4.0.3/CMake.app/Contents/bin/cmake') if path.exists())
    gcc=tools/'tools/riscv32-esp-elf/esp-15.2.0_20251204/riscv32-esp-elf/bin'
    ninja=tools/'tools/ninja/1.12.1'
    env=os.environ.copy();env.update(IDF_PATH=str(sdk),IDF_TOOLS_PATH=str(work/'idf-tools'),IDF_PYTHON_ENV_PATH=str(python),VIRTUAL_ENV=str(python),PYTHON=str(python/'bin/python'),ESP_IDF_VERSION='6.0',ESP_ROM_ELF_DIR=str(tools/'tools/esp-rom-elfs/20241011'),NSEALR_COMPONENT_ROOT=str(work/'components'),IDF_COMPONENT_CACHE_PATH=str(work/'cache/components'),TMPDIR=str(work/'tmp'),CCACHE_DISABLE='1',PYTHONNOUSERSITE='1')
    env['PATH']=os.pathsep.join(str(x) for x in (python/'bin',gcc,cmake.parent,ninja,sdk/'tools'))+os.pathsep+env.get('PATH','')
    if a.reuse_components:
        for name in ('components','managed_components'):
            shutil.copytree(a.reuse_components/name,work/name,dirs_exist_ok=True)
        constraints=a.reuse_components/'idf-tools/espidf.constraints.v6.0.txt'
        if constraints.exists():shutil.copy2(constraints,work/'idf-tools'/constraints.name)
    adapter=work/'components/esp_lvgl_adapter'
    if not adapter.exists():
        prepare(work/'components')
    patched=adapter/'src/display/bridge/v9/lvgl_ppa_accel_v9.c'
    expected='4190a9f84693b2cc4a902f1b0f766f4f10e960736daadb8b7e3f6b036ddc6008'
    if hashlib.sha256(patched.read_bytes()).hexdigest()!=expected:raise SystemExit('Adapter public-header patch differs')
    managed=ROOT/'firmware/p4/managed_components'
    selected = work/'managed_components'
    if managed.is_symlink() and managed.resolve()!=selected:
        previous = managed.resolve()
        if previous.name!='managed_components' or not previous.is_relative_to(ROOT/'.cache'):
            raise SystemExit('Refusing to replace an external component binding')
        managed.unlink()
    if not managed.exists():managed.symlink_to(selected,target_is_directory=True)
    if managed.resolve()!=selected:raise SystemExit('Refusing to replace a real component directory')
    # Use the environment's pinned YAML reader without importing arbitrary host packages.
    lock_script="import yaml,sys; p=yaml.safe_load(open(sys.argv[1])); p['dependencies']['espressif/esp_lvgl_adapter']['source']['path']=sys.argv[3]; yaml.safe_dump(p,open(sys.argv[2],'w'),sort_keys=False); print(';'.join(k+'=='+v['version'] for k,v in p['dependencies'].items() if v['source']['type']=='service'))"
    env['IDF_COMPONENT_CONSTRAINTS']=subprocess.check_output([env['PYTHON'],'-c',lock_script,str(ROOT/'firmware/p4/dependencies.lock'),str(work/'dependencies.lock'),str(adapter)],text=True,env=env).strip()
    if a.seed_config and not (work/'sdkconfig').exists():
        lines=a.seed_config.read_text().splitlines()
        override={'CONFIG_LV_FONT_UNSCII_16':'n','CONFIG_LV_FONT_MONTSERRAT_16':'y','CONFIG_ESP_SYSTEM_PANIC_SILENT_REBOOT':'y','CONFIG_ESP_COREDUMP_ENABLE_TO_NONE':'y'}
        for i,line in enumerate(lines):
            key=line.removeprefix('# ').split('=',1)[0].split(' ',1)[0]
            if key in override:
                value=override.pop(key);lines[i]=f'{key}={value}' if value!='n' else f'# {key} is not set'
        lines.extend(f'{k}={v}' for k,v in override.items());(work/'sdkconfig').write_text('\n'.join(lines)+'\n')
    commands=[[str(cmake),'-S',str(ROOT/'firmware/p4'),'-B',str(work/'build'),'-G','Ninja','-DIDF_TARGET=esp32p4','-DSDKCONFIG='+str(work/'sdkconfig'),'-DPYTHON='+env['PYTHON'],'-DNSEALR_COMPONENT_LOCK='+str(work/'dependencies.lock'),'-DNSEALR_CORE_ROOT='+str(a.core_root.resolve()),'-DRUST_LIBRARY='+str(a.rust_library.resolve())],[str(cmake),'--build',str(work/'build'),'--parallel','8']]
    for i,command in enumerate(commands):
        path=work/f'build-{i}.log'
        with path.open('w') as log:result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:print(path.read_text()[-7000:]);raise SystemExit(result.returncode)
    image=work/'build/nsealr.bin'
    report={'source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),'idf':head,'bytes':image.stat().st_size,'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'image':str(image)}
    (work/'build-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
