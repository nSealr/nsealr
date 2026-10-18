"""Single disposable campaign; every failed invocation remains in its output."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from common import HERE, digest, environment, now, output, require, run, runtime, write_json
from checks import checks

base,out=runtime(),output()
env=environment(base)
session=json.loads((base/'session.json').read_text())
env.update(CAD_TOOLS_ROOT=str(base),CAD_QUAL_ROOT=str(out),DISPLAY=session['display'])
app=base/'squashfs-root/AppRun'
python=base/'venv/bin/python'
xd=base/'sysroot/usr/bin/xdotool'
xd_env=dict(env,LD_LIBRARY_PATH=str(base/'sysroot/usr/lib/x86_64-linux-gnu'))
processes=[]
gui_events=[]


def execute(name,argv,expected=0,timeout=90,custom_env=None):
    return run(name,argv,env=custom_env or env,expected=expected,timeout=timeout)

def native(name,args,expected=0):
    return execute(name,[app,'kicad-cli',*args],expected)

def gates(v):
    project=out/'fixtures'/v;export=out/'exports'/v;export.mkdir(parents=True,exist_ok=True)
    native(v+'-erc',['sch','erc','--format','json','--severity-all','--exit-code-violations','-o',export/'erc.json',project/'canary.kicad_sch'],5 if v=='bad' else 0)
    native(v+'-drc',['pcb','drc','--format','json','--all-track-errors','--schematic-parity','--severity-all','--exit-code-violations','-o',export/'drc.json',project/'canary.kicad_pcb'],0 if v in ['fixed','roundtrip'] else 5)
    native(v+'-netlist',['sch','export','netlist','--format','kicadxml','-o',export/'netlist.xml',project/'canary.kicad_sch'])

def exports(v):
    d=out/'fixtures'/v;e=out/'exports'/v
    cmds=[('pdf',['sch','export','pdf','-o',e/'schematic.pdf',d/'canary.kicad_sch']),
      ('bom',['sch','export','bom','--fields','Reference,Value,Footprint','--labels','Reference,Value,Footprint','-o',e/'bom.csv',d/'canary.kicad_sch']),
      ('gerbers',['pcb','export','gerbers','-l','F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts','-o',str(e/'gerbers')+'/',d/'canary.kicad_pcb']),
      ('drill',['pcb','export','drill','--format','excellon','--generate-map','--map-format','svg','--generate-report','--report-path',e/'drill-report.txt','-o',str(e/'drill')+'/',d/'canary.kicad_pcb']),
      ('placement',['pcb','export','pos','--format','csv','--units','mm','-o',e/'placement.csv',d/'canary.kicad_pcb']),
      ('svg',['pcb','export','svg','-l','F.Cu,F.Silkscreen,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','-o',e/'board.svg',d/'canary.kicad_pcb'])]
    for name,args in cmds:native(v+'-'+name,args)
    write_json(e/'source-hashes.json',{p.name:digest(p) for p in d.iterdir() if p.suffix in ['.kicad_sch','.kicad_pcb','.kicad_pro']})

def launch(name,args):
    log=(out/'logs'/f'{name}.log').open('x')
    p=subprocess.Popen(list(map(str,args)),env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    log.close();processes.append(p)
    gui_events.append({'event':'launch','name':name,'argv':list(map(str,args)),'pid':p.pid,'utc':now()})
    write_json(out/'gui-events.json',gui_events)
    return p

def window(p,pattern):
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        require(p.poll() is None,'Editor exited before ready')
        r=subprocess.run([str(xd),'search','--onlyvisible','--pid',str(p.pid),'--name',pattern],env=xd_env,capture_output=True,text=True)
        ids=r.stdout.split()
        if len(ids)==1:
            time.sleep(.4)
            return ids[0]
        time.sleep(.2)
    execute('blocked-gui-'+str(p.pid),['import','-window','root',out/f'visuals/blocked-{p.pid}.png'])
    raise RuntimeError('GUI not ready; inspect preserved screenshot')

def key(name,w,*keys):
    execute(name,[xd,'windowfocus',w,'key','--clearmodifiers',*keys],custom_env=xd_env)

def edit_session(appname,ext,sequence,crash=False):
    target=out/'fixtures/roundtrip'/('canary.'+ext)
    before=digest(target);mtime=target.stat().st_mtime_ns
    p=launch(appname+'-'+sequence,[app,appname,target])
    w=window(p,'canary.*'+('PCB Editor' if appname=='pcbnew' else 'Schematic Editor'))
    execute('size-'+sequence,[xd,'windowsize',w,'1400','1000'],custom_env=xd_env)
    if appname=='pcbnew':
        from kipy import KiCad
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                b=KiCad(socket_path='ipc://'+str(base/'runtime/kicad/api.sock'),timeout_ms=500).get_board()
                require(len(b.get_footprints())==3,'Wrong open PCB')
                break
            except Exception:
                time.sleep(.2)
        else:raise RuntimeError('IPC not ready')
        if sequence=='first':execute('mcp-read',[python,HERE/'mcp_read.py'])
    key('save-'+appname+'-'+sequence,w,'ctrl+s')
    deadline=time.monotonic()+5
    while target.stat().st_mtime_ns==mtime and time.monotonic()<deadline:time.sleep(.1)
    require(target.stat().st_mtime_ns!=mtime,'Native save did not write the file')
    key('fit-'+appname+'-'+sequence,w,'Home')
    time.sleep(.4)
    execute('image-'+appname+'-'+sequence,['import','-window','root',out/f'visuals/{appname}-{sequence}.png'])
    saved=digest(target)
    if crash:
        p.kill();p.wait(timeout=5)
        gui_events.append({'event':'SIGKILL-after-completed-save','pid':p.pid,'utc':now(),'sha256':saved})
    else:
        key('close-'+appname+'-'+sequence,w,'ctrl+q')
        p.wait(timeout=10)
        require(p.returncode==0,'Native close failed')
    require(digest(target)==saved,'Process stop changed saved source')
    gui_events.append({'event':'saved-and-stopped','app':appname,'sequence':sequence,'utc':now(),
                       'before_sha256':before,'saved_sha256':saved,'save_wrote_file':True,'crash_after_save':crash})
    write_json(out/'gui-events.json',gui_events)

try:
    native('version',['version','--format','about'])
    execute('generate',[app,'python3.11',HERE/'generate.py'])
    # Refusing a second generation must leave every native snapshot untouched.
    before={str(p.relative_to(out)):digest(p) for p in (out/'fixtures').rglob('*') if p.is_file()}
    execute('reject-overwrite',[app,'python3.11',HERE/'generate.py'],expected=1)
    require(before=={str(p.relative_to(out)):digest(p) for p in (out/'fixtures').rglob('*') if p.is_file()},'Rejected generation changed files')
    for v in ['bad','fixed','width','clearance']:gates(v)
    exports('fixed')
    # Staged replacement is performed only while no editor is running, then rolled back.
    stage=out/'recovery';shutil.copytree(out/'fixtures/fixed',stage)
    snapshot={str(p.relative_to(stage)):p.read_bytes() for p in stage.rglob('*') if p.is_file()}
    (stage/'canary.kicad_pcb').write_bytes((out/'fixtures/bad/canary.kicad_pcb').read_bytes())
    native('reject-staged-candidate',['pcb','drc','--format','json','--exit-code-violations','-o',out/'staged-rejected-drc.json',stage/'canary.kicad_pcb'],5)
    for name,data in snapshot.items():(stage/name).write_bytes(data)
    require(all((stage/name).read_bytes()==data for name,data in snapshot.items()),'Snapshot restoration failed')
    write_json(out/'recovery.json',{'refused_overwrite_unchanged':True,'staged_candidate_rejected':True,
      'snapshot_restored_byte_identical':True,'source_hashes':before})
    shutil.copytree(out/'fixtures/fixed',out/'fixtures/roundtrip')
    require(not Path('/tmp/.X11-unix/X'+session['display'][1:]).exists(),'Display occupied')
    xvfb=launch('xvfb',[base/'sysroot/usr/bin/Xvfb',session['display'],'-screen','0','1440x1080x24','-nolisten','tcp'])
    time.sleep(.5);require(xvfb.poll() is None,'Xvfb failed')
    edit_session('eeschema','kicad_sch','first')
    edit_session('eeschema','kicad_sch','reopened',crash=True)
    edit_session('eeschema','kicad_sch','after-crash')
    edit_session('pcbnew','kicad_pcb','first')
    edit_session('pcbnew','kicad_pcb','reopened',crash=True)
    edit_session('pcbnew','kicad_pcb','after-crash')
    gates('roundtrip');exports('roundtrip')
    result=checks(out)
    execute('render-schematic',['pdftoppm','-singlefile','-png','-r','110',out/'exports/roundtrip/schematic.pdf',out/'visuals/schematic'])
    execute('render-board',['convert','-background','white',out/'exports/roundtrip/board.svg',out/'visuals/board.png'])
    result.update(passed=True,completed_utc=now(),scope='bounded synthetic tooling qualification; no electrical or production release claim')
    write_json(out/'results.json',result)
finally:
    for p in reversed(processes):
        if p.poll() is None:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            gui_events.append({'event':'owned-process-cleanup','pid':p.pid,'returncode':p.returncode,'utc':now()})
    write_json(out/'gui-events.json',gui_events)
    # Campaign stdout is appended by the parent after exit, so only internal immutable files.
    excluded={'manifest.json'}
    write_json(out/'manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*'))
      if p.is_file() and p.name not in excluded and not p.name.endswith('.lck') and p.name!='commands.jsonl'})
