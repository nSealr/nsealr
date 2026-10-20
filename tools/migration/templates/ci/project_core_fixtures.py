#!/usr/bin/env python3
"""Extract committed contract fields into Cargo OUT_DIR for tests only.

This script performs data projection. It does not call a signer, parser, review
renderer, hash implementation or expected-value generator.
"""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=ROOT/'protocols/contracts/v1'

def load(path):return json.loads((ARTIFACT/path).read_bytes())
def quote(value):return 'r'+('#'*8)+'"'+value+'"'+('#'*8)
def action(value):return {'next':'ReviewPageAction::Next','approve_or_reject':'ReviewPageAction::ApproveOrReject'}[value]
def strings(values):return '['+','.join(quote(v) for v in values)+']'
def limits(value):return 'ReviewDisplayLimits {'+','.join(key+':'+str(value[key]) for key in ['max_title_chars','max_body_lines','max_line_chars','max_compact_body_lines','max_compact_line_chars'])+'}'
def pages(value):return '['+','.join('('+quote(p['title'])+',&'+strings(p['lines'])+','+action(p['action'])+')' for p in value)+']'

def project(output):
    output.mkdir(parents=True,exist_ok=True)
    for row in json.loads((ROOT/'ci/core-test-projections.json').read_bytes()):
        value=load(row['artifact_path'])
        for part in row['pointer']:value=value[int(part)] if isinstance(value,list) else value[part]
        data=value if row['encoding']=='string' else json.dumps(value,ensure_ascii=False,separators=(',',':'))
        (output/row['output']).write_text(data,encoding='utf-8')
    functions=[]
    for name,source in [('basic','kind-1-basic'),('tagged','kind-1-tags')]:
        review=load('vectors/review-screens/'+source+'.json')['screen_review']
        functions.append('pub fn '+name+'_trusted_review_request() -> TrustedReviewRequest { trusted_review_request('+quote(review['request_id'])+','+name.upper()+'_REVIEW_SCREEN_APPROVAL_DIGEST,&'+pages(review['pages'])+') }')
    first=load('vectors/review-detail-pages/kind-1-control-escapes-t-display-s3.json')
    functions.append('pub fn t_display_s3_review_limits() -> crate::review::display::ReviewDisplayLimits { crate::review::display::'+limits(first['limits'])+' }')
    (output/'review-fixtures.rs').write_text('\n'.join(functions))
    details=[]
    for path in sorted((ARTIFACT/'vectors/review-detail-pages').glob('*.json')):
        data=json.loads(path.read_bytes());request=load('vectors/review/'+data['source_review_vector']+'.json')['request']
        expected=[]
        for p in data['pages']:
            fields=[key+':'+quote(p[key]) for key in ['title','page_indicator','logical_page_id']]
            fields+=['action:'+action(p['action']),'lines:vec!'+strings(p['lines']),
                     'body_line_styles:vec!['+','.join({'meta':'ReviewBodyLineStyle::Meta','value':'ReviewBodyLineStyle::Value','normal':'ReviewBodyLineStyle::Normal'}[s] for s in p['body_line_styles'])+']']
            expected.append('ExpectedDetailPage {'+','.join(fields)+'}')
        details.append('ReviewDetailPageVector {name:'+quote(data['name'])+',request_json:'+quote(json.dumps(request,ensure_ascii=False,separators=(',',':')))+',approval_digest:'+quote(data['approval_digest'])+',limits:'+limits(data['limits'])+',pages:vec!['+','.join(expected)+']}')
    (output/'detail-fixtures.rs').write_text('fn review_detail_page_vectors() -> Vec<ReviewDetailPageVector> { vec!['+','.join(details)+'] }')
    policies=[]
    for name,file in [('esp32_usb_fixture','esp32-usb-enable-kind-1-automation'),('custom_hardware_wallet_fixture','custom-hardware-wallet-enable-kind-1-automation')]:
        data=load('vectors/policy-changes/'+file+'.json');proposal=data['proposal'];review=data['review'];requester=proposal['requested_by']
        fields=[key+':'+quote(proposal[key])+'.parse().unwrap()' for key in ['proposal_id','account_id','route_type','action','current_policy_id','proposed_policy_id']]
        fields+=['proposed_grant_ids','requested_by:PolicyChangeRequester {surface:'+quote(requester['surface'])+'.parse().unwrap(),client_pubkey:'+quote(requester['client_pubkey'])+'.parse().unwrap(),label:'+('Some('+quote(requester['label'])+'.parse().unwrap())' if requester.get('label') is not None else 'None')+'}', 'created_at:'+str(proposal['created_at'])]
        fields+=[key+':'+str(proposal[key]).lower() for key in ['device_review_required','physical_approval_required','companion_authoritative','contains_secret_material']]
        policies.append('fn '+name+'() -> PolicyChangeFixture { let mut proposed_grant_ids=PolicyChangeGrantIds::new(); '+''.join('proposed_grant_ids.try_push('+quote(grant)+').unwrap();' for grant in proposal['proposed_grant_ids'])+' PolicyChangeFixture { proposal:PolicyChangeProposal {'+','.join(fields)+'},proposal_id:'+quote(review['proposal_id'])+',approval_digest:'+quote(review['approval_digest'])+',pages:'+pages(review['pages'])+'} }')
    (output/'policy-fixtures.rs').write_text('\n'.join(policies))

if __name__=='__main__':project(Path(sys.argv[1]))
