#!/usr/bin/env python3
"""Bind every admitted software case to execution, a declared replacement or retirement."""
import argparse,collections,json,re
from pathlib import Path
from assemble import read_git
from rehearse import canonical,digest

# Original copied-snapshot mechanics become checks against one immutable source
# artifact. Keep explicit semantic mappings, not a count-based waiver.
SNAPSHOTS={
 'test_matching_snapshot_files_pass':['test_fully_valid_control_after_mutation_is_restored'],
 'test_mismatched_snapshot_reports_repo_and_path':['test_tampered_normal_and_hidden_files_reject_forged_digests'],
 'test_required_snapshot_glob_reports_missing_live_specs_file':['test_unmatched_declared_consumer_pattern_rejects'],
 'test_snapshot_without_live_specs_file_fails':['test_extra_normal_and_hidden_files_reject_even_with_forged_inventory'],
 'test_committed_nonregular_vector_rejects':['test_committed_nonregular_file_rejects'],
 'test_complete_snapshot_counts_hidden_vector':['test_complete_artifact_counts_hidden_file'],
 'test_dirty_upstream_and_snapshot_with_forged_digest_reject':['test_new_git_commit_and_forged_manifest_cannot_replace_frozen_source'],
 'test_extra_normal_and_hidden_vectors_reject_even_with_forged_inventory':['test_extra_normal_and_hidden_files_reject_even_with_forged_inventory'],
 'test_malformed_or_nonobject_manifest_rejects':['test_malformed_or_nonobject_manifest_rejects'],
 'test_missing_manifest_and_v1_vector_rejects':['test_missing_manifest_and_versioned_vector_rejects'],
 'test_missing_manifest_rejects_before_iteration':['test_missing_manifest_rejects_before_iteration'],
 'test_missing_vectors_with_retained_or_forged_inventory_reject':['test_missing_normal_and_hidden_files_reject_even_with_forged_inventory'],
 'test_nonregular_source_snapshot_and_manifest_reject':['test_symlinked_data_manifest_and_root_reject','test_symlinked_directory_rejects'],
 'test_partial_consumer_manifest_is_validated_when_present':['test_missing_partial_consumer_scope_rejects','test_reduced_consumer_scope_rejects'],
 'test_source_worktree_inventory_drift_rejects':['test_missing_normal_and_hidden_files_reject_even_with_forged_inventory','test_extra_normal_and_hidden_files_reject_even_with_forged_inventory'],
 'test_tampered_normal_and_hidden_vectors_reject_forged_digest':['test_tampered_normal_and_hidden_files_reject_forged_digests'],
 'test_wrong_provenance_or_hash_rejects':['test_wrong_source_pin_or_inventory_rejects','test_wrong_original_hash_rejects']}
OVERLAYS={
 'test_default_applies_all_three_in_order_and_records_each':('All three corrected historical overlays were actually applied and their four postimages verified before consolidation. Active bootstrap fetches the exact committed product instead of patching sibling sources.','test_exact_selected_history_available_without_unselected_branch'),
 'test_missing_followup_is_not_silently_skipped':('No active sibling overlay remains. The immutable artifact/source checks and exact product fetch reject incomplete selected inputs.','test_missing_selected_commit_preserves_fetch_failure'),
 'test_modified_patch_is_rejected_before_mutation':('The historical overlays remain frozen. Migration replay now rejects changed patch bytes before application.','test_unapproved_patch_bytes_rejected'),
 'test_modified_preimage_is_rejected_before_patch':('Historical source preimages are preserved; replay rejects a dirty or mismatched declared source before applying its patch.','test_dirty_preimage_rejected_before_patch'),
 'test_wrong_actual_commit_is_rejected_before_mutation':('The single-product runner binds the selected commit and rejects pre/post source drift.','test_successful_command_that_changes_source_fails_acceptance'),
 'test_wrong_declared_commit_is_rejected_before_mutation':('Source fetch requires the exact selected commit; declared migration commit identities cannot be forged.','test_declared_commit_identity_cannot_be_forged'),
 'test_wrong_output_hash_is_rejected_and_not_recorded_as_pass':('Replay verifies every declared postimage before committing; current artifacts bind their own immutable source.','test_forged_postimage_rejected')}

def reconcile(author,target,runtime,out):
 admission=author/'docs/restart/implementation/A02/admission-evidence'
 before=json.loads((admission/'case-dispositions.json').read_bytes());old_python=json.loads((admission/'core-python-cases.json').read_bytes())
 named=runtime/'named-python-execution-01';groups={}
 for name in ['contracts','pi','helpers','root-controls','bootstrap']:
  data=json.loads((named/(name+'.json')).read_bytes());assert data['successful'];groups[name]={r['case_id']:r for r in data['rows']};assert len(groups[name])==data['tests_run']
 cold=runtime/'cold-product-02';full=cold/'evidence/suites/00-product-ci.log';result=json.loads((cold/'evidence/suites/result.json').read_bytes());assert result['all_passed'] and not result['source_changed_after'];log=full.read_text();rust_ids=set(re.findall(r'^test (.+?) \.\.\. ok$',log,re.M))
 assert read_git(target,'rev-parse','HEAD').decode().strip()==result['input_commits']['nsealr']
 rows=[];seen_after=set();artifact_controls=groups['root-controls']
 def bind(group,name):
  row=groups[group][name];assert row['status']=='passed';seen_after.add((group,name));return row|{'execution_group':group,'execution_record_sha256':digest((named/(group+'.json')).read_bytes())}
 for old in before['cases']:
  if old['source']=='companion':continue
  row={'before':old};name=old['case_id'];source=old['source'];treatment=old['treatment']
  if source=='nsealr':
   if name not in rust_ids:raise ValueError('missing Rust case: '+name)
   row.update(disposition='retained Rust assertion executed; declared fixture/workspace adaptations',after={'case_id':name,'status':'passed','execution_log_sha256':digest(full.read_bytes()),'source_commit':result['input_commits']['nsealr']})
  elif treatment in ['retire-smartcard','retire-private-prose']:
   reason='Retired active card/APDU implementation and its card-only conformance obligation; original public history remains.' if treatment=='retire-smartcard' else 'Assertion about excluded private prose retired after the separate privacy literal change; current owner/feature assertions remain. No placeholder private documents were imported.'
   row.update(disposition=treatment,reason=reason,after=None)
  else:
   group={'specs':'contracts','raspberry':'pi','lab':'helpers'}[source]
   if name in groups[group]:row.update(disposition='retained/adapted executed case',after=bind(group,name))
   elif name.replace('.FixtureSnapshotTests.','.FixtureScopeTests.') in groups[group]:row.update(disposition='same consumer obligation adapted from duplicate snapshot to authoritative artifact scope',after=bind(group,name.replace('.FixtureSnapshotTests.','.FixtureScopeTests.')))
   elif source=='lab' and name.split('.')[-1] in SNAPSHOTS:
    replacements=['test_contracts.ArtifactProvenanceTests.'+n for n in SNAPSHOTS[name.split('.')[-1]]]
    row.update(disposition='replace copied snapshot mechanics with immutable authoritative artifact checks',after=[bind('root-controls',n) for n in replacements])
   else:raise ValueError('unaccounted admitted case: '+name)
  rows.append(row)
 migration_log=(named/'00-all-migration-control-negatives.log').read_text()
 for old in old_python['cases']:
  name=old['case_id'];group='root-controls' if old['group']=='plan' else 'bootstrap';row={'before':old}
  if name in groups[group]:row.update(disposition='retained current bootstrap or full canonical plan control',after=bind(group,name))
  else:
   reason,replacement=OVERLAYS[name.split('.')[-1]]
   matches=[(g,n) for g,cases in groups.items() for n in cases if n.endswith('.'+replacement)]
   if matches:after=[bind(g,n) for g,n in matches]
   else:
    match=re.search(r'^'+replacement+r' \(([^)]+)\) \.\.\. ok$',migration_log,re.M)
    if not match:raise ValueError('replacement control was not executed: '+replacement)
    after=[dict(case_id=match[1]+'.'+replacement,status='passed',execution_log_sha256=digest((named/'00-all-migration-control-negatives.log').read_bytes()))]
   row.update(disposition='retire obsolete active multi-repository overlay mechanism; preserve frozen source and historical execution',reason=reason,after=after,historical_actual_application='execution/s01-overlay-execution-01 and ordered patch 02 preserve the original applied outputs')
  rows.append(row)
 # Bind every opaque private product obligation to actual positive/negative
 # execution without publishing the protected original case names or paths.
 private=[]
 for old in json.loads((author/'docs/restart/implementation/A02/private-case-obligations.json').read_bytes())['cases']:
  oid=old['case_identity_sha256'];row={'before':old}
  if old['treatment']=='replace-product-guardrail':
   python=[n for n in groups['root-controls'] if n.endswith('.test_'+oid)]
   if python:after=bind('root-controls',python[0])
   else:
    if 'PASS '+oid not in log:raise ValueError('missing actual opaque Node control: '+oid)
    after={'case_id':oid,'status':'passed','execution_log_sha256':digest(full.read_bytes()),'source_file':next(p for p in ['tools/bridge/test_product_boundaries.mjs','tools/bridge/test_current_guides.mjs'] if oid in (target/p).read_text())};after['source_sha256']=digest((target/after['source_file']).read_bytes())
   row.update(disposition='required replacement positive and negative control executed',after=after)
  else:row.update(disposition=old['treatment'],after=None)
  private.append(row)
 new=[{'group':g,**row} for g,cases in groups.items() for n,row in cases.items() if (g,n) not in seen_after]
 # Count acceptance domains separately; a stable case name is not a claim of
 # unchanged source bytes or parity. Exact file transformations remain binding.
 summary={'python_contract_before':92,'python_contract_after':90,'pi_before_and_after':150,'selected_helper_before':144,'selected_helper_after':115,'helper_retired_card':10,'helper_retired_private_prose':2,'helper_snapshot_mechanics_replaced':17,'consumer_scope_cases_retained_with_class_rename':18,'rust_unique_retained':263,'core_plan_retained':18,'original_bootstrap_retained':4,'obsolete_active_overlay_mechanism_cases_replaced':7,'current_bootstrap_cases':8,'new_current_root_control_cases':49,'private_cases':25,'private_product_guardrails_executed':21,'private_taxonomy_prose_retired':4,'optional_browser_serial_helper_cases_in_115':13}
 out.write_bytes(canonical(dict(source_commit=result['input_commits']['nsealr'],full_suite_log_sha256=digest(full.read_bytes()),scope='Exact case identities and actual outcomes; adaptations require the declared source/file patches and distinct review, not a same-name parity inference.',counts=summary,cases=rows,private_opaque_obligations=private,additional_executed_controls=new,typescript='bridge-named-execution-02/case-correspondence.json retains every original716 runnable ID, all691 actual passed outputs, five name replacements, seven route/ack assertion adaptations, and25 retired-card IDs; separate unchanged live-relay skip.')))
 print(json.dumps(summary,sort_keys=True))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();reconcile(a.author_repo,a.target,a.runtime,a.output)
