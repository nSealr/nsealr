"""Compare one fixed public account's supported and retired recovery forms."""
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
ARTIFACT = ROOT / 'protocols/contracts/v1'
spec = importlib.util.spec_from_file_location('reference', ARTIFACT / 'scripts/verify_specs.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
account = json.loads((ARTIFACT / 'vectors/accounts/esp32-usb-device-slot-0.json').read_bytes())
probe = """
import fs from 'node:fs';
import {parseAccountDescriptor} from './packages/policy/dist/index.js';
const account = JSON.parse(fs.readFileSync(0, 'utf8'));
try { parseAccountDescriptor(account); console.log(JSON.stringify({accepted:true})); }
catch (error) { console.log(JSON.stringify({accepted:false,error:String(error.message)})); }
"""
observations = []
for control in ['original_public_device_slot', 'retired_card_slot']:
    value = json.loads(json.dumps(account))
    if control == 'retired_card_slot':
        value['recovery'] = {'type':'card_slot','card_id':'public-test-card',
                             'slot_id':'public-test-slot','backup_required':True}
    errors = []
    reference.check_account_descriptor_shape('public-review-account', value, errors)
    child = subprocess.run(['node','--input-type=module','-e',probe], cwd=ROOT,
                           input=json.dumps(value), capture_output=True, text=True, check=True)
    observations.append({'control':control,'independent_reference_accepted':not errors,
                         'reference_errors':errors,'runtime':json.loads(child.stdout)})
assert observations[0]['independent_reference_accepted'] and observations[0]['runtime']['accepted']
assert observations[1]['independent_reference_accepted'] and not observations[1]['runtime']['accepted']
schema = json.loads((ARTIFACT / 'schemas/account-v1.schema.json').read_bytes())
forms = [v['properties']['type']['const'] for v in schema['$defs']['recovery']['oneOf']]
assert 'card_slot' in forms
print(json.dumps({'actual_observations':observations,'schema_declared_recovery_forms':forms,
                  'schema_engine_run':False,'conclusion':'Retired card recovery remains in new schema/reference but current runtime rejects it.'},indent=2))
