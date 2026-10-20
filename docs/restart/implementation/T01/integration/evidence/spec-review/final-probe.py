#!/usr/bin/env python3
"""Read immutable corrected-spec bindings and existing paired fixture data only."""
import base64,collections,datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
C='cb39bb026d4008b7f3d7abf358b604c79e3b699d';OLD='6324aaa9f71b55c57b076f4d402e8056e8f63488';B='503719d5c607bdbcd1da30a89b0c3c6f5983c01b'
H='03c2616518d6d9a32fe5cc9a945624a72cd32ac0';S='c358229777d2582964a4f326ce8d15709841a395';PREFIX='docs/restart/implementation/T01/integration/'
REPOS={'nSealr/nsealr':ROOT,'nSealr/companion':Path('/home/tux/nsealr/companion'),'nSealr/specs':Path('/home/tux/nsealr/specs'),'nSealr/raspberry':Path('/home/tux/nsealr/raspberry')}
cache={}
def git(*args,repository=ROOT):return subprocess.check_output(['git',*args],cwd=repository)
def body(c,p,repository=ROOT):
 key=(str(repository),c,p)
 if key not in cache:cache[key]=git('show',c+':'+p,repository=repository)
 return cache[key]
def load(c,p,repository=ROOT):return json.loads(body(c,p,repository))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def binding(row,repository=ROOT):
 raw=body(row['commit'],row['path'],repository);mode,kind,blob=git('ls-tree',row['commit'],'--',row['path'],repository=repository).decode().split('\t')[0].split()
 assert (mode,kind,blob)==(row['mode'],'blob',row['blob']) and len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['path']
 return raw
s,a,m=[load(C,PREFIX+p) for p in ['source-reconciliation.json','acceptance-reconciliation.json','consumer-map.json']]
old_s=load(OLD,PREFIX+'source-reconciliation.json');audit=load(H,'docs/restart/implementation/T01/source-audit.json');plan=load(H,'docs/restart/implementation/T01/acceptance-plan.json')
assert git('rev-parse',C+'^{tree}').decode().strip()=='4fa51873b4f77028424850a26bc8b3c1f2ca89ff'
changes=[r.split('\t') for r in git('diff','--name-status',B,C).decode().splitlines()];assert len(changes)==4 and all(st=='A' and p.startswith(PREFIX) for st,p in changes)
assert {p for _,p in changes}=={PREFIX+p for p in ['brief.md','source-reconciliation.json','acceptance-reconciliation.json','consumer-map.json']}
assert set(git('diff','--name-only',OLD,C).decode().splitlines())=={p for _,p in changes}
for p in ['original44_audited_input_reconciliation','current_layout_extra_bindings','proposed_S03_API_and_oracle_bindings','version_map']:
 assert s[p]==old_s[p],p
new_provenance,old_provenance=s['provenance_transition_proposal'],old_s['provenance_transition_proposal']
assert dict(new_provenance,implementation_to_adoption_sequence=old_provenance['implementation_to_adoption_sequence'])==old_provenance
new_sequence,old_sequence=new_provenance['implementation_to_adoption_sequence'],old_provenance['implementation_to_adoption_sequence']
assert len(new_sequence)==len(old_sequence)==4 and all(new_sequence[i]==old_sequence[i] for i in [0,2,3])
assert new_sequence[1]['when']==old_sequence[1]['when']
for row in s['historical_preparation']+[s['distinct_historical_preparation_review']]:binding(row)
original_by_path={}
for group in audit['sources']:
 repo=REPOS[group['repository']]
 assert git('rev-parse',group['commit']+'^{tree}',repository=repo).decode().strip()==group['tree']
 for row in group['inspected_files']:original_by_path[(group['repository'],row['path'])]=(group['commit'],row)
assert len(original_by_path)==44 and len(s['original44_audited_input_reconciliation'])==44
changed_inputs=0
for row in s['original44_audited_input_reconciliation']:
 orig=row['original'];commit,original=original_by_path[(orig['repository'],orig['path'])]
 assert commit==orig['commit'] and orig['blob']==original['git_blob'] and orig['sha256']==original['sha256'] and orig['bytes']==original['bytes']
 old=binding(orig,REPOS[orig['repository']]);current=binding(row['current_main']);proposal=binding(row['proposed_S03'])
 assert row['original_bytes_equal_current']==(old==current) and row['proposed_S03_changes_current_bytes']==(current!=proposal)
 changed_inputs+=old!=current
assert changed_inputs==19
for row in s['current_layout_extra_bindings']+s['proposed_S03_API_and_oracle_bindings']+m['actual_primary_entrypoints']+m['targeted_symbol_consumer_hits']:binding(row)
assert len(s['current_layout_extra_bindings'])==35 and len(s['proposed_S03_API_and_oracle_bindings'])==12
original_consumers=collections.Counter((g['repository'],p) for g in audit['consumer_inventory'] for p in g['pinned_matched_files'])
actual_consumers=collections.Counter((r['original']['repository'],r['original']['path']) for g in m['original_consumer_inventory'] for r in g['files'])
assert original_consumers==actual_consumers and sum(actual_consumers.values())==135
retired=[];retained=0
for group in m['original_consumer_inventory']:
 for row in group['files']:
  binding(row['original'],REPOS[row['original']['repository']])
  if row['status']=='retained':binding(row['current_binding']);retained+=1
  else:
   assert row['status']=='retired_no_fallback' and row['current_binding'] is None
   assert not git('ls-tree',B,'--',row['current_path']);retired.append(row['current_path'])
assert retained==129 and len(retired)==6 and len(set(retired))==2
assert a['all5_original_criteria']==plan['criteria']
assert [r['acceptance'] for r in a['all5_original_criteria']]==next(t['acceptance'] for t in load(B,'plan/work-items.json')['tasks'] if t['id']=='T01')
assert len(a['all42_original_cases'])==len(plan['suites'])==6
for new,old in zip(a['all42_original_cases'],plan['suites']):
 assert all(new[k]==old[k] for k in ['id','title','criteria','source_gaps','cases'])
assert sum(len(g['cases']) for g in a['all42_original_cases'])==42
rows=s['SSOT_projection_reconciliation'];assert len(rows)==170
old_rows={r['mapping']['output']:r for r in old_s['SSOT_projection_reconciliation']};config={r['output']:r for r in load(B,'ci/core-test-projections.json')}
assert config=={r['mapping']['output']:r['mapping'] for r in rows} and len(config)==170
counts=collections.Counter();groups=s['semantic_cutover_dependency_groups'];affected=0
for row in rows:
 key=row['mapping']['output'];previous=old_rows[key]
 for field in ['mapping','current_projected_sha256','current_projected_bytes','current_source_binding']:assert row[field]==previous[field]
 raw=binding(row['current_source_binding']);value=json.loads(raw)
 for part in row['mapping']['pointer']:value=value[int(part)] if isinstance(value,list) else value[part]
 projected=value if row['mapping']['encoding']=='string' else json.dumps(value,ensure_ascii=False,separators=(',',':'))
 assert isinstance(projected,str) and sha(projected.encode())==row['current_projected_sha256'] and len(projected.encode())==row['current_projected_bytes']
 group=row['semantic_cutover_group'];counts[group]+=1;assert key in groups[group]['mapped_outputs'] and row['projected_value_action']
 affected+=row['potential_wire_status_cutover_collision']
assert dict(sorted(counts.items()))==s['projection_summary']['semantic_group_counts'] and len(counts)==13 and affected==119
assert len(rows)-affected==51
for group,record in groups.items():assert set(record['mapped_outputs'])=={r['mapping']['output'] for r in rows if r['semantic_cutover_group']==group}
resolved_groups={'field-7bc474eb9fd65cd1f1cdfd09.txt':'static_qr_positive',
 'field-b69c96b873204e5c324385c0.txt':'review_container_and_transcript',
 'field-275b00adc2cdd30c17c95c67.txt':'serial_positive'}
for key,group in resolved_groups.items():
 row=next(r for r in rows if r['mapping']['output']==key)
 assert row['potential_wire_status_cutover_collision'] and row['semantic_cutover_group']==group
correction=s['encoded_cutover_review_correction']
for row in correction['known_family_source_bindings']+correction['method_source_bindings']:binding(row)
def fixture(path):return load(B,'protocols/contracts/v1/'+path)
def decode(encoded):return base64.urlsafe_b64decode(encoded+'='*((-len(encoded))%4))
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
def digest(request,review,pages):
 payload=dict(version=request['version'],method=request['method'],request_id=request['request_id'],event_template=request['params']['event_template'],review=review,pages=pages)
 return sha(json.dumps(payload,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode())
checks=[]
for name in ['kind-1-basic','kind-1-tags']:
 vector=fixture('vectors/review-screens/'+name+'.json');request=vector['request'];screen=vector['screen_review']
 assert digest(request,vector['review'],screen['pages'])==screen['approval_digest'];checks.append('independent diagnostic digest '+name)
for name in ['kind-1-basic-approve','kind-1-basic-reject','kind-1-long-events-many-tags-detail-scroll-approve']:
 vector=fixture('vectors/review-transcripts/'+name+'.json');assert json.loads(decode(vector['qr_envelope'].split(':',1)[1]))==vector['request']
 if 'screen_review_vector' in vector:assert vector['approval_digest']==fixture('vectors/review-screens/'+vector['screen_review_vector']+'.json')['screen_review']['approval_digest']
 else:assert vector['approval_digest']==fixture('vectors/review-detail-pages/'+vector['detail_review_vector']+'.json')['approval_digest']
 checks.append('transcript request/envelope/digest '+name)
for name in ['qr-envelope-kind-1-basic','qr-envelope-kind-1-long-events-many-tags']:
 vector=fixture('vectors/transports/'+name+'.json');assert vector['envelope']=='nsealr1:'+vector['payload_base64url'] and json.loads(decode(vector['payload_base64url']))==vector['decoded'];checks.append('static QR pairing '+name)
vector=fixture('vectors/transports/qr-animated-response-kind-1-basic.json');decoded=decode(vector['payload_base64url']);assert json.loads(decoded)==vector['decoded'] and sha(decoded)==vector['decoded_json_sha256']
chunks=[]
for frame in vector['frames']:
 prefix,digest_value,position,chunk,checksum=frame.split(':');assert prefix=='nsealr1a' and digest_value==sha(decoded) and sha(frame.rsplit(':',1)[0].encode())[:16]==checksum;chunks.append(chunk)
assert ''.join(chunks)==vector['payload_base64url'];checks.append('animated payload/digest/all3 frame checksums')
vector=fixture('vectors/transports/serial-frame-request-kind-1-basic.json');prefix,kind,payload,checksum=vector['frame'].rstrip('\n').split(':')
assert prefix=='nsealr1f' and kind=='request' and payload==vector['payload_base64url'] and checksum==sha((kind+':'+payload).encode())[:16] and json.loads(decode(payload))==vector['decoded'];checks.append('serial payload/checksum/frame')
vector=fixture('vectors/review/kind-1-basic.json');screen=fixture('vectors/review-screens/kind-1-basic.json');assert vector['request']==screen['request'] and vector['review']==screen['review'];checks.append('basic source review/screen pairing')
assert len(checks)==10
# S03 is not adopted in base503; compare immutable proposal bindings, never invent a base copy.
assert s['S03_proposal']['adopted_main'] is None and s['S03_proposal']['root_approved_T01_tuple'] is None
assert not s['implementation_admitted'] and not a['implementation_admitted'] and s['T01_criteria_closed']==0
bindings=[]
for _,path in changes:
 raw=body(C,path);entry=git('ls-tree',C,'--',path).decode().split('\t')[0].split();bindings.append(dict(path=path,mode=entry[0],blob=entry[2],bytes=len(raw),sha256=sha(raw)))
result=dict(candidate=C,tree=git('rev-parse',C+'^{tree}').decode().strip(),status='PASS_exact_specification_bindings_and_current_data_only',source_bindings=bindings,original_audit_inputs=44,changed_current_postimages=19,extra_current_bindings=35,proposed_S03_bindings=12,consumer_references=135,retained_consumers=129,retired_references=6,retired_paths=sorted(set(retired)),original_criteria=5,original_cases=42,suites=6,projection_mapping_preimages=170,semantic_groups=dict(sorted(counts.items())),affected_contexts=119,independent_contexts=51,current_data_pairing_controls=checks,known_family_sources=len(correction['known_family_source_bindings']),method_source_bindings=len(correction['method_source_bindings']),future_expected_bytes_or_runtime_executed=False,implementation_admitted=False,limits='These are read-only source/data/spec checks; no119runtime successes,final normative transformed values,stable OID or future S03 adopted tuple claimed.',recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'final-probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['source_bindings','current_data_pairing_controls']},sort_keys=True))
