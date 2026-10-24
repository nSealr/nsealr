import os,sys,json,pathlib,subprocess,time,datetime,hashlib
P=pathlib.Path('/home/tux/nsealr/.restart-tools/goal/r00-crypto-bigint-remediation')
R=pathlib.Path('/home/tux/nsealr/.restart-tools/goal/r00-crypto-bigint-remediation-runtime')
D=R/'checks';D.mkdir(exist_ok=False)
source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip();assert source=='7badfdc93fcb1654e97943204b7b854113c21120'
E=json.loads((P/'docs/restart/implementation/R00/crypto-bigint-remediation/resolution/environment.json').read_text())
E['CARGO_NET_OFFLINE']='true';(D/'environment.json').write_text(json.dumps(E,indent=2)+'\n');eh=hashlib.sha256((D/'environment.json').read_bytes()).hexdigest();rows=[]
def run(name,argv,overrides=None,cwd=P):
 overrides=overrides or {};env=E|overrides
 t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('START',name,flush=True);error=None
 with (D/f'{name}.stdout').open('wb') as out,(D/f'{name}.stderr').open('wb') as err:
  try:r=subprocess.run(argv,cwd=cwd,env=env,stdout=out,stderr=err,check=True);code=0
  except subprocess.CalledProcessError as ex:code=ex.returncode;error=ex
 row={'id':name,'argv':argv,'cwd':str(cwd),'source_commit':source,'environment_sha256':eh,'overrides':overrides,'started_utc':start,'elapsed_seconds':time.monotonic()-t,'exit':code,'stdout_sha256':hashlib.sha256((D/f'{name}.stdout').read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256((D/f'{name}.stderr').read_bytes()).hexdigest()};rows.append(row);(D/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print('DONE',name,code,round(row['elapsed_seconds'],3),flush=True)
 if error:raise error
run('rust-version',['rustc','-vV']);run('python-version',['python3','--version']);run('root-reverse-graph',['cargo','tree','--locked','--offline','-i','crypto-bigint']);run('host-reverse-graph',['cargo','tree','--manifest-path','apps/desktop-simulator/Cargo.toml','--locked','--offline','-i','crypto-bigint']);run('ctutils-feature-graph',['cargo','tree','--locked','--offline','-e','features','-i','ctutils'])
run('workspace-default',['cargo','test','--locked','--offline','--workspace'])
obs=D/'observed';obs.mkdir()
keys={'S03_OBSERVED':'s03-events','K01_OBSERVED':'k01-events','K01_IDENTITIES':'k01-identities','K01_IDENTITY_OPERATIONS':'k01-identity-operations','K01_REJECTIONS':'k01-rejections','K01_MATRIX_OBSERVED':'k01-matrix','K01_PREFIX_OBSERVED':'k01-prefixes'}
overrides={k:str(obs/(v+'.json')) for k,v in keys.items()}
run('workspace-all-features',['cargo','test','--locked','--offline','--workspace','--all-features'],overrides)
run('core-no-default-riscv32',['cargo','build','--locked','--offline','--release','-p','nsealr-core','--no-default-features','--target','riscv32imafc-unknown-none-elf'])
run('host-vector-harness',['cargo','test','--manifest-path','apps/desktop-simulator/Cargo.toml','--locked','--offline'])
run('s03-independent-output',['python3','-B','docs/restart/implementation/S03/oracle.py','--check','--fixtures','docs/restart/implementation/S03/vectors.json','--observed',str(obs/'s03-events.json')])
run('k01-independent-output',['python3','-B','docs/restart/implementation/K01/check_observed.py','--fixtures','docs/restart/implementation/K01/independent-inputs.json','--observed',str(obs/'k01-events.json'),'--identities',str(obs/'k01-identities.json'),'--rejections',str(obs/'k01-rejections.json')])
run('workspace-clippy',['cargo','clippy','--locked','--offline','--workspace','--all-targets','--all-features','--','-D','warnings','-D','dead_code'])
run('host-clippy',['cargo','clippy','--manifest-path','apps/desktop-simulator/Cargo.toml','--locked','--offline','--all-targets','--all-features','--','-D','warnings','-D','dead_code'])
deps=R/'target/debug/deps';cmov=list(deps.glob('libcmov-*.rlib'));subtle=list(deps.glob('libsubtle-*.rlib'));assert len(cmov)==len(subtle)==1,(cmov,subtle)
run('official-ctutils-unit-build',['rustc','--edition=2024','--crate-name','ctutils','--test','vendor/ctutils/src/lib.rs','--cfg','feature="subtle"','--extern','cmov='+str(cmov[0]),'--extern','subtle='+str(subtle[0]),'-L','dependency='+str(deps),'-o',str(R/'upstream-ctutils-tests')])
run('official-ctutils-unit-tests',[str(R/'upstream-ctutils-tests')])
run('core-coverage',['cargo','llvm-cov','--locked','--offline','--workspace','--all-features','--summary-only','--json','--output-path',str(D/'core-coverage.json')])
run('host-coverage',['cargo','llvm-cov','--manifest-path','apps/desktop-simulator/Cargo.toml','--locked','--offline','--workspace','--all-features','--summary-only','--json','--output-path',str(D/'host-coverage.json')])
run('unchanged-coverage-ratchet',['python3','ci/check_coverage_ratchet.py',str(D/'core-coverage.json'),'ci/ratchet.json',str(D/'host-coverage.json')])
run('c-abi-release-build',['cargo','build','--locked','--offline','--release','-p','nsealr-pi-engine-fixture','--message-format=json'])
artifacts=[r for s in (D/'c-abi-release-build.stdout').read_text().splitlines() if (r:=json.loads(s)).get('reason')=='compiler-artifact' and r['target']['name']=='nsealr_pi_engine_fixture']
assert len(artifacts)==1,artifacts
libs=[pathlib.Path(x) for x in artifacts[0]['filenames'] if x.endswith('.so')];assert len(libs)==1;lib=libs[0];sha=hashlib.sha256(lib.read_bytes()).hexdigest()
(D/'c-abi-artifact.json').write_text(json.dumps({'source_commit':source,'compiler_artifact':artifacts[0],'actual_path':str(lib),'sha256':sha,'bytes':lib.stat().st_size,'runtime_role':'new release ELF from changed authenticated dependency closure; no reproducibility claim'},indent=2)+'\n')
run('c-abi-elf-header',['readelf','-h',str(lib)]);run('c-abi-elf-dynamic',['readelf','-d',str(lib)])
run('c-abi-engine-adapter-tests',['python3','-B','-m','unittest','-v','test_engine_adapter.EngineAdapterTests'],{'NSEALR_QP01_LIBRARY':str(lib),'NSEALR_QP01_LIBRARY_SHA256':sha},cwd=P/'apps/pi/tests')
# The unchanged gate intentionally obtains fresh official data in its own temporary cache.
run('fresh-three-graph-audit',['make','cargo-deny'],{'CARGO_NET_OFFLINE':'false'})
print('ALL_CHECKS_COMPLETE',len(rows),flush=True)
