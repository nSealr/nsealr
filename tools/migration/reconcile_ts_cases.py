#!/usr/bin/env python3
"""Bind each collected original TS case to actual migrated execution or retirement."""
import argparse,json
from collections import Counter
from pathlib import Path
from rehearse import canonical,digest,git


def reconcile(author,target,report_path,transitions_path):
 before=json.loads((author/'docs/restart/implementation/A02/admission-evidence/case-dispositions.json').read_bytes())
 original=[r for r in before['cases'] if r['source']=='companion'];assert len(original)==716
 report=json.loads(report_path.read_bytes());transitions=json.loads(transitions_path.read_bytes())
 cases={};skips=[]
 for suite in report['testResults']:
  path=Path(suite['name']).relative_to(target).as_posix()
  for test in suite['assertionResults']:
   name=' > '.join([*test['ancestorTitles'],test['title']]);key=(path,name)
   if key in cases:raise ValueError('duplicate case identity')
   cases[key]=test
 rows=[];used=set()
 for old in original:
  row=dict(old);target_file=old['target_file'];name=old['case_id']
  if old['treatment']=='retire-smartcard':
   if target_file is not None:raise ValueError('retired card still has active target')
   row.update(after_case=None,after_status='deliberately-retired',reason='Active card implementation retired by accepted product scope; original public source/history preserved. Active route safety is covered by named rejection/dispatch cases and packed export/command negatives.')
  else:
   matches=[t for t in transitions if t['path']==target_file and name.endswith(' > '+t['before'])]
   if len(matches)>1:raise ValueError('ambiguous transition')
   if matches:
    t=matches[0];name=name[:-len(t['before'])]+t['after'];row.update(executed_treatment='replace-retired-route-rejection',transition_reason=t['disposition'])
   else:row['executed_treatment']='retain-with-declared-path/artifact-adaptations' if old['treatment']=='retain' else old['treatment']
   key=(target_file,name)
   if key not in cases:raise ValueError('missing after case: '+name)
   if cases[key]['status']!='passed':raise ValueError('case did not pass: '+name)
   used.add(key);row.update(after_case=name,after_status='passed',after_file_sha256=digest((target/target_file).read_bytes()))
  row.pop('after_execution',None);rows.append(row)
 for key,test in cases.items():
  if key in used:continue
  path,name=key
  if path!='packages/nip46/src/session-live.e2e.test.ts' or test['status'] not in ['pending','skipped']:raise ValueError('undeclared new/unmapped after case: '+name)
  old=git(target,'show','86569e073da4faec0811d67137bbb0fd4f74c7c6:'+path)
  if old!=(target/path).read_bytes():raise ValueError('live relay skip source changed')
  skips.append(dict(path=path,case_id=name,status=test['status'],source_byte_identical=True,sha256=digest(old),reason='Inherited NSEALR_LIVE_E2E resource gate. Framework list omits it; full run records it. No live relay execution claimed.'))
 assert len(used)==691 and len(skips)==1 and sum(r['after_status']=='deliberately-retired' for r in rows)==25
 return dict(source_commit='678796900e462f5504e47fe934e2e5f23d85824f',target_commit=git(target,'rev-parse','HEAD').decode().strip(),report_sha256=digest(report_path.read_bytes()),counts={'before_collected_runnable':716,'same_named_runnable':686,'named_replacements':5,'retired_card_cases':25,'after_passed_runnable':691,'separate_unchanged_live_relay_skip':1,'after_execution_total':692},case_correspondence=rows,retirement_by_source_file=dict(Counter(r['path'] for r in rows if r['after_status']=='deliberately-retired')),separate_skips=skips,meaning='716 and691 are collected runnable-case counts. Full execution includes one unchanged inherited skip on both sides; 716 minus692 mixes denominators. File transformations and removed data members remain separately declared; names/counts alone are not source equivalence.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['author-repo','target','report','transitions','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();data=reconcile(a.author_repo,a.target,a.report,a.transitions);a.output.write_bytes(canonical(data));print(json.dumps(data['counts'],sort_keys=True))
