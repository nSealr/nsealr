#!/usr/bin/env python3
"""Record actual unittest outcomes and source hashes for exact case reconciliation."""
import argparse,hashlib,inspect,json,os,sys,unittest
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--start',required=True);p.add_argument('--pattern',default='test*.py');p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();os.chdir(root);sys.path.insert(0,str(root));sys.path.insert(0,str(root/a.start));rows=[];original={}
 suite=unittest.TestLoader().discover(a.start,pattern=a.pattern)
 def walk(node):
  if isinstance(node,unittest.TestSuite):
   for child in node:walk(child)
  else:
   if type(node).__name__=='_FailedTest':raise ValueError('failed case collection')
   path=Path(inspect.getfile(type(node))).resolve();original[path]=hashlib.sha256(path.read_bytes()).hexdigest()
 walk(suite)
 class Result(unittest.TextTestResult):
  def addSuccess(self,test):
   super().addSuccess(test);path=Path(inspect.getfile(type(test))).resolve();rows.append(dict(case_id=test.id(),path=path.relative_to(root).as_posix(),sha256=original[path],status='passed'))
  def addSkip(self,test,reason):
   super().addSkip(test,reason);rows.append(dict(case_id=test.id(),status='skipped',reason=reason))
 result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
 if any(hashlib.sha256(p.read_bytes()).hexdigest()!=value for p,value in original.items()):raise ValueError('case source changed during execution')
 if len({r['case_id'] for r in rows})!=len(rows):raise ValueError('ambiguous case IDs')
 a.output.write_text(json.dumps(dict(tests_run=result.testsRun,successful=result.wasSuccessful(),rows=rows),indent=2)+'\n')
 return not result.wasSuccessful()

if __name__=='__main__':raise SystemExit(main())
