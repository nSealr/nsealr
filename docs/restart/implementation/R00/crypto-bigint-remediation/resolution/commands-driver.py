import os,json,pathlib,subprocess,time,datetime,hashlib,shutil
R=pathlib.Path('/home/tux/nsealr/.restart-tools/goal/r00-crypto-bigint-remediation-runtime')
P=pathlib.Path('/home/tux/nsealr/.restart-tools/goal/r00-crypto-bigint-remediation')
D=P/'docs/restart/implementation/R00/crypto-bigint-remediation/resolution';D.mkdir(exist_ok=True)
e=json.loads(pathlib.Path('/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/environment.json').read_text())
for k,v in {'CARGO_HOME':'cargo','CARGO_TARGET_DIR':'target','TMPDIR':'tmp','XDG_CACHE_HOME':'cache','XDG_CONFIG_HOME':'config','XDG_DATA_HOME':'data'}.items():
 e[k]=str(R/v);(R/v).mkdir(exist_ok=True)
e['CARGO_REGISTRIES_CRATES_IO_PROTOCOL']='sparse'
(D/'environment.json').write_text(json.dumps(e,indent=2)+'\n')
refresh=R/'refresh';(refresh/'src').mkdir(parents=True,exist_ok=True)
(refresh/'src/lib.rs').write_text('// Resolution only; never compiled.\n')
(refresh/'Cargo.toml').write_text('''[package]
name = "r00-crypto-bigint-source-resolution"
version = "0.0.0"
edition = "2024"
publish = false
[dependencies]
crypto-bigint = { version = "=0.7.6", default-features = false }
ctutils = { version = "=0.4.5", default-features = false }
cpubits = "=0.1.1"
num-traits = { version = "=0.2.19", default-features = false }
autocfg = "=1.5.1"
cmov = { version = "=0.5.4", default-features = false }
''')
rows=[]
def run(i,a,cwd='/tmp'):
 t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (D/f'{i}.stdout').open('wb') as o,(D/f'{i}.stderr').open('wb') as err:r=subprocess.run(a,cwd=cwd,env=e,stdout=o,stderr=err)
 rows.append({'id':i,'argv':a,'cwd':str(cwd),'started_utc':start,'elapsed_seconds':time.monotonic()-t,'exit':r.returncode,'stdout_sha256':hashlib.sha256((D/f'{i}.stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((D/f'{i}.stderr').read_bytes()).hexdigest()})
 (D/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(i,r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
run('cargo-version',['cargo','--version'])
run('minimal-registry-lock',['cargo','generate-lockfile','--manifest-path',str(refresh/'Cargo.toml')])
run('official-vendor',['cargo','vendor','--locked','--manifest-path',str(refresh/'Cargo.toml'),str(R/'refreshed-vendor')])
for f in ['Cargo.toml','Cargo.lock']:shutil.copyfile(refresh/f,D/('resolution-'+f))
