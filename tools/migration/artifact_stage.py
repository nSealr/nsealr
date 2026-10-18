#!/usr/bin/env python3
"""Consolidate contract ownership and preserve independent Python/Pi verification."""
import argparse
import ast
import json
from pathlib import Path
import re
from rehearse import canonical,digest
from transforms import Changes


RETIRED={'smartcard','smartcard_apdu','external_review_acknowledgement','card_persistent','display_less','nfc'}


def drop_nodes(text,names):
    lines=text.splitlines(True);spans=[]
    for node in ast.walk(ast.parse(text)):
        name=getattr(node,'name',None)
        if isinstance(node,ast.Assign):name=next((t.id for t in node.targets if isinstance(t,ast.Name)),None)
        if name in names:spans.append((node.lineno-1,node.end_lineno))
    for start,end in sorted(spans,reverse=True):lines[start:end]=[]
    return ''.join(lines)


def replace_function(text,name,new):
    node=next(n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=text.splitlines(True);lines[node.lineno-1:node.end_lineno]=[new+'\n'];return ''.join(lines)


def adapt_schema(value):
    if isinstance(value,list):
        result=[]
        for item in value:
            if isinstance(item,str) and item in RETIRED:continue
            if isinstance(item,dict) and 'if' in item and '"smartcard"' in json.dumps(item['if']):continue
            transformed=adapt_schema(item)
            if transformed not in result:result.append(transformed)
        return result
    if isinstance(value,dict):
        out={key:adapt_schema(v) for key,v in value.items()}
        # repository ownership is integration source ownership, not a claim that
        # custom hardware or any signer is qualified.
        if 'repository' in out.get('properties',{}):
            property=out['properties']['repository']
            if 'enum' in property:property['enum']=['nsealr']
            if 'const' in property:property['const']='nsealr'
        return out
    return value


def owner_values(value):
    if isinstance(value,dict):return {k:('nsealr' if k=='repository' and v in {'raspberry','firmware','hardware'} else owner_values(v)) for k,v in value.items()}
    if isinstance(value,list):return [owner_values(v) for v in value]
    return value


def apply(target:Path,author:Path,output:Path):
    c=Changes(target); artifact=target/'protocols/contracts/v1'; records=[];leaf_changes=[]
    c.put('.gitignore',(target/'.gitignore').read_bytes()+b'\n# Consolidated component build outputs\n.venv/\nnode_modules/\ndist/\n*.egg-info/\n*.tgz\n/apps/desktop-simulator/target/\n')
    for directory in ['protocols','schemas','vectors','examples']:
        for path in sorted((artifact/directory).rglob('*')):
            if not path.is_file():continue
            rel=path.relative_to(artifact).as_posix();before=path.read_bytes();after=before;reason=None
            if path.suffix=='.json':
                data=json.loads(before);original=json.loads(before)
                if directory=='schemas':data=adapt_schema(data)
                else:data=owner_values(data)
                if rel=='vectors/features/signer-feature-matrix-v0.json':
                    data['features']=[r for r in data['features'] if r['id'] not in RETIRED]
                    data['solutions'].pop('smartcard')
                    for solution in data['solutions'].values():
                        for key in RETIRED:solution['features'].pop(key,None)
                if rel=='vectors/route-refusals/signer-route-refusals-v0.json':
                    data['cases']=[row for row in data['cases'] if row['route_type']!='smartcard']
                if rel=='vectors/policy-decisions/policy-route-mismatch-manual-review.json':
                    data['policy_profile_id']='policy-manual-only-qr-vault';reason='retain-policy-mismatch-with-active-policy'
                if data!=original:
                    after=canonical(data);reason=reason or 'retire-card-members-and-reconcile-current-owner'
                    leaf_changes.append({'path':rel,'reason':reason,'before_sha256':digest(before),'after_sha256':digest(after)})
                    c.put(str(path.relative_to(target)),after)
            records.append({'path':rel,'original_sha256':digest(before),'sha256':digest(after),'adaptation':reason})
    for path in list(c.original):
        if path.startswith('tests/fixtures/specs/'):c.remove(path)
    manifest={'artifact_format':1,'artifact_id':'nsealr-contracts-v1','wire_versions':'Existing explicitly named wire versions retained; artifact format is not a wire version.',
              'source_commit':'45f8b6ff1123f3f55be4ce457fd1008e91043cc2','initial_import_commit':'86569e073da4faec0811d67137bbb0fd4f74c7c6',
              'files':records,'consumer_coverage':{'rust':'apps/desktop-simulator in-scope/excluded category and invalid-prefix lists; core test projections reference these same files',
                                               'python':'independent verify_specs.py verifies all retained fixtures; Pi compares its own signing/review/crypto results',
                                               'typescript':'packages/fixtures loader and all retained Bridge suites; declared per-feature subsets retain explicit completeness'},
              'retirement':'Only the declared card directory, three card-only descriptors and card members retire. General policy mismatch remains with active QR policy.',
              'generation':'No pre-test expected-value regeneration. verify_specs.py remains an independent Python/libsecp256k1 oracle.'}
    c.put('protocols/contracts/v1/manifest.json',canonical(manifest));c.put('scripts/verify_contracts.py',(author/'tools/migration/templates/scripts/verify_contracts.py').read_bytes())
    # Preserve all independent Pi assertions, changing only their source root.
    path='apps/pi/tests/test_vault_core.py';text=(target/path).read_text();text=replace_function(text,'specs_dir','def specs_dir() -> Path:\n    return ROOT.parents[1] / "protocols/contracts/v1"');c.put(path,text.encode())
    path='apps/pi/tests/test_seed_signer_hardware.py';text=(target/path).read_text().replace('Path(__file__).resolve().parent / "fixtures/specs"','Path(__file__).resolve().parents[3] / "protocols/contracts/v1"');c.put(path,text.encode())
    # Preserve standalone structure negatives; obsolete repository-wide file
    # lists no longer describe a component inside the integrated tree.
    for root,marker,dirs in [('protocols/contracts/v1','Creative Commons CC0',['protocols','schemas','vectors','examples','scripts']),('apps/pi','MIT License',['app','os','docs','scripts','tests'])]:
        checker='''#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    errors=[]
    if not (ROOT/'LICENSE').is_file() or MARKER not in (ROOT/'LICENSE').read_text():errors.append('LICENSE does not contain expected marker: '+MARKER)
    for name in DIRECTORIES:
        if not (ROOT/name).is_dir():errors.append('missing required directory: '+name)
    for error in errors:print('ERROR:',error)
    if not errors:print('Component structure and license verified independently of checkout name')
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
'''.replace('MARKER',repr(marker)).replace('DIRECTORIES',repr(dirs))
        c.put(root+'/scripts/verify_repo.py',checker.encode())
    # Keep active route/policy checks and replace card support by rejection.
    path='protocols/contracts/v1/scripts/verify_specs.py';text=(target/path).read_text()
    text=drop_nodes(text,{'APDU_HEX_RE','SMARTCARD_APDU_EXPECTATIONS','smartcard_apdu_vector_names','expected_apdu_value','apdu_vector_status_word','check_smartcard_apdu_vector'})
    text=text.replace('    "smartcard",\n','').replace('    "smartcard_apdu",\n','').replace('    "external_review_acknowledgement",\n','').replace('    "card_persistent",\n','')
    text=text.replace('    "smartcard": "smartcard",\n','')
    text=text.replace('"raspberry_qr_vault": "raspberry"','"raspberry_qr_vault": "nsealr"').replace('"esp32_qr_vault": "firmware"','"esp32_qr_vault": "nsealr"').replace('"esp32_usb_nip46": "firmware"','"esp32_usb_nip46": "nsealr"').replace('"custom_hardware_wallet": "hardware"','"custom_hardware_wallet": "nsealr"')
    text=text.replace('"qr", "usb", "smartcard", "nfc", "nip46_relay", "embedded"','"qr", "usb", "nip46_relay", "embedded"').replace('"external_policy", "display_less"','"external_policy"').replace('"esp32_usb_nip46", "smartcard", "custom_hardware_wallet"','"esp32_usb_nip46", "custom_hardware_wallet"')
    text=re.sub(r'    elif route_type == "smartcard":\n.*?(?=    elif route_type == "custom_hardware_wallet":)', '',text,flags=re.S)
    text=re.sub(r'    if "smartcard" in route_types.*?\n        errors.append\(.*?\)\n','',text)
    text=text.replace('    for rel in smartcard_apdu_vector_names():\n        check_smartcard_apdu_vector(rel, errors)\n\n','')
    c.put(path,text.encode())
    path='protocols/contracts/v1/tests/test_verify_specs.py';text=(target/path).read_text();text=drop_nodes(text,{'test_smartcard_apdu_vectors_are_discovered_from_directory','test_smartcard_apdu_vectors_validate_commands_and_status_words'})
    text=text.replace('    check_smartcard_apdu_vector,\n','').replace('    smartcard_apdu_vector_names,\n','')
    text=text.replace('self.assertIn("smartcard-slot-0",','self.assertNotIn("smartcard-slot-0",').replace('self.assertIn("manual-only-displayless-smartcard",','self.assertNotIn("manual-only-displayless-smartcard",')
    text=replace_function(text,'test_policy_profiles_reject_automation_for_display_less_smartcard_routes','''    def test_policy_profiles_reject_automation_for_display_less_smartcard_routes(self) -> None:
        policy = deepcopy(load_json("vectors/policies/manual-only-qr-vault.json"))
        policy["route_types"] = ["smartcard"]
        policy["mode"] = "scoped_automation"
        policy["grants_allowed"] = True
        errors: list[str] = []
        verify_specs.check_policy_profile_shape("retired-card-policy", policy, errors)
        self.assertIn("route_types contain unknown routes", "\\n".join(errors))''')
    text=replace_function(text,'test_account_descriptors_reject_display_less_smartcard_trusted_review_claims','''    def test_account_descriptors_reject_display_less_smartcard_trusted_review_claims(self) -> None:
        account = deepcopy(load_json("vectors/accounts/esp32-usb-device-slot-0.json"))
        account["signer_route"]["type"] = "smartcard"
        account["signer_route"]["trusted_review"] = "device_display"
        account["signer_route"]["policy_support"] = "scoped_automation"
        account["capabilities"]["physical_review"] = True
        account["capabilities"]["persistent_grants"] = True
        errors: list[str] = []
        verify_specs.check_account_descriptor_shape("retired-card-trust-claim", account, errors)
        self.assertIn("signer_route.type", "\\n".join(errors))''')
    text=text.replace('load_json("vectors/accounts/smartcard-slot-0.json")','load_json("vectors/accounts/esp32-qr-nip06-account-0.json")').replace('mutated-smartcard-policy-route','mutated-qr-policy-route').replace('policy_profile_id does not include signer route type smartcard','policy_profile_id does not include signer route type esp32_qr_vault')
    c.put(path,text.encode())
    write=canonical(leaf_changes);c.put('protocols/contracts/v1/adaptation.json',write)
    # Rust replay is independent and consumes the same artifact directly.
    path='apps/desktop-simulator/src/lib.rs';text=(target/path).read_text().replace('.join("tests")\n        .join("fixtures")\n        .join("specs")','.join("protocols")\n        .join("contracts")\n        .join("v1")');text=text.replace('    "smartcard",        // solution-3 applet contract (smartcard/companion, Phase 06).\n','');text=text.replace('complete pinned snapshot','authoritative contract artifact').replace('`tests/fixtures/specs/vectors`','`protocols/contracts/v1/vectors`').replace('`tests/fixtures/specs/SOURCE.json`','`protocols/contracts/v1/manifest.json`');c.put(path,text.encode())
    path='apps/desktop-simulator/src/replay/policies.rs';text=(target/path).read_text().replace('    "smartcard",\n','').replace('The frozen family ids (cross-repo test contract — never rename)','The retained route ids (versioned contract artifact)');c.put(path,text.encode())
    return c.apply(output,'Use one authoritative contract artifact and retire card-only semantics')


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output))
