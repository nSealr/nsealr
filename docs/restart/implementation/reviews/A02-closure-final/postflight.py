from pathlib import Path
import json,subprocess,hashlib,sys
p=Path(sys.argv[1]).resolve();out=Path(__file__).resolve().parent;base='b1c90139a651895284b2624da7d12903cf16bc9d';candidate='bbccf25897bda8121244c0138d129ae9683177e8';prefix='docs/restart/implementation/A02/closure/'
def git(*a):return subprocess.check_output(['git','-C',str(p),*a])
old=json.loads(git('show',base+':plan/work-items.json'));new=json.loads((p/'plan/work-items.json').read_text());assert len(old['tasks'])==len(new['tasks'])==47 and [t['id'] for t in old['tasks']]==[t['id'] for t in new['tasks']]
tree={}
for row in git('ls-tree','-r','-z',candidate).split(b'\0'):
 if not row:continue
 left,name=row.split(b'\t',1);mode,kind,blob=left.decode().split();tree[name.decode()]={'mode':mode,'kind':kind,'blob':blob}
changes=git('diff','--name-only',base,candidate).decode().splitlines();assert all(tree[n]['mode']=='100644' and tree[n]['kind']=='blob' for n in changes)
inv=json.loads((p/prefix/'copy-inventory.json').read_text());gitcopies=[r for r in inv['copies'] if 'commit' in r['source']]
closure=[]
for commit,sourceprefix,expected in [('249d2cf85b2c69276174f32dc6d24c092e290a67','docs/restart/implementation/reviews/A02-adoption/',9),('5f3714dc55ab99d41352cc7ad33fa3630b2f0a29','docs/restart/implementation/reviews/A02-contract-repair/',11),('d280bfdc33c88a5e49e24659894f1a4ce7af6ea1','docs/restart/implementation/reviews/A02-source-closure/',17)]:
 rows=[r for r in gitcopies if r['source']['commit']==commit];names=set(git('ls-tree','-r','--name-only',commit,'--',sourceprefix).decode().splitlines());assert len(names)==len(rows)==expected and {r['source']['path'] for r in rows}==names
 for r in rows:
  sourceentry=git('ls-tree',commit,'--',r['source']['path']).decode().split('\t')[0].split();dest=tree[r['copied_path']];assert sourceentry[0]==r['mode']==dest['mode'] and sourceentry[2]==r['source']['blob']==dest['blob']
 closure.append({'commit':commit,'members':len(rows),'full_source_closure_and_modes_blobs':'PASS'})
commands=0
for name in ['controls/commands.json','final-checks/commands.json']:
 root=p/prefix/Path(name).parent
 for r in json.loads((p/prefix/name).read_text()):
  assert hashlib.sha256((root/r['log']).read_bytes()).hexdigest()==r['sha256'];commands+=1
checks={'outcome':'PASS','task_count':47,'task_order_exact':True,'all_candidate_delta_files_regular_Git100644':len(changes),'full_review_artifact_closures':closure,'actual_author_control_final_command_logs_verified':commands,'script_scope':'Supplements exact candidate probe with explicit task cardinality and Git mode/blob/full paired-copy closure. No product mutation or repeated suite.'}
(out/'postflight-result.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks))
