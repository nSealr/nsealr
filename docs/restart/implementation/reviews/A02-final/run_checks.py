import datetime,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRODUCT=OUT/'replay/initial-import/repository'
PYTHON='/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/python/bin/python3'
env=dict(os.environ,PATH=str(Path(PYTHON).parent)+':'+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1',TZ='UTC',LC_ALL='C.UTF-8')
(OUT/'environment.json').write_text(json.dumps({'python':sys.version,'python_executable':sys.executable,'python_sha256':hashlib.sha256(Path(PYTHON).read_bytes()).hexdigest(),'platform':platform.platform(),'selected_env':{k:env[k] for k in ['PATH','PYTHONDONTWRITEBYTECODE','TZ','LC_ALL']}},indent=2)+'\n')
checks=[('migration-controls',[PYTHON,'-B','-m','unittest','discover','-s','tools/migration','-p','test_*.py','-v'],ROOT),('product-docs-test',['make','docs','test'],PRODUCT)]
rows=[]
for label,argv,cwd in checks:
 log=OUT/(label+'.log');started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with log.open('wb') as f: result=subprocess.run(argv,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 rows.append({'label':label,'argv':argv,'cwd':str(cwd),'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':result.returncode,'log':log.name,'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
 (OUT/'checks.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(label,result.returncode,log.read_text()[-700:],flush=True)
 if result.returncode:sys.exit(result.returncode)
