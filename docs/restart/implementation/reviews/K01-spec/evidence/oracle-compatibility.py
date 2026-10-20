"""Bounded preparation compatibility experiment; NO observed K01 output.

Synthetic witnesses are copied from public prepared expectations solely to reach
the legacy checker's input-validation stage. They cannot count as runtime proof.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
INPUT = ROOT / 'docs/restart/implementation/K01/independent-inputs.json'
d = json.loads(INPUT.read_text())
oracle_path = ROOT / 'docs/restart/implementation/S03/oracle.py'
spec = importlib.util.spec_from_file_location('pinned_s03_oracle', oracle_path)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
bip = oracle.reference()

for row in d['vectors']:
    item = json.loads(row['template'])
    raw = json.dumps([0, row['pubkey'], item['created_at'], item['kind'],
                      item['tags'], item['content']], ensure_ascii=False,
                     separators=(',', ':'), allow_nan=False).encode()
    assert raw.hex() == row['canonical_hex']
    event_id = hashlib.sha256(raw).digest()
    assert event_id.hex() == row['event_id']
    key = row['public_fixture_scalar'].to_bytes(32, 'big')
    assert bip.pubkey_gen(key).hex() == row['pubkey']
    signature = bip.schnorr_sign(event_id, key, bytes.fromhex(row['aux_hex']))
    assert signature.hex() == row['signature']
    assert bip.schnorr_verify(event_id, bytes.fromhex(row['pubkey']), signature)

keys = []
for row in d['identity_expectations']:
    scalar = int(row['original_scalar_hex'], 16)
    normalized = scalar if bip.has_even_y(bip.point_mul(bip.G, scalar)) else bip.n - scalar
    assert normalized.to_bytes(32, 'big').hex() == row['normalized_backend_hex']
    assert bip.pubkey_gen(scalar.to_bytes(32, 'big')).hex() == row['pubkey']
    keys.append(dict(scalar=row['public_fixture_scalar'], pubkey=row['pubkey'],
                     normalized_backend=row['normalized_backend_hex'],
                     empty_event_signature=d['vectors'][0]['signature']))

synthetic = OUT / 'synthetic-witnesses-NOT-runtime.json'
synthetic.write_text(json.dumps(d['vectors'], indent=2) + '\n')
synthetic.with_suffix('.keys.json').write_text(json.dumps(keys, indent=2) + '\n')
argv = [sys.executable, '-B', str(oracle_path), '--check', '--fixtures',
        str(INPUT), '--observed', str(synthetic)]
run = subprocess.run(argv, capture_output=True, text=True)
(OUT / 'oracle-compatibility.stdout.log').write_text(run.stdout)
(OUT / 'oracle-compatibility.stderr.log').write_text(run.stderr)
assert run.returncode != 0
assert 'accepted invalid input' in run.stderr
good = d['vectors'][0]['template']
unchanged_mutation = good.replace('"kind":1', '"kind":1,"k\\u0069nd":1')
assert unchanged_mutation == good
assert oracle.template(unchanged_mutation.encode())['kind'] == 0
result = dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              classification='preimplementation verifier-integration defect; not a product defect',
              candidate='a783fd37033f63d04e27b6855ad064b7402ce428',
              input_sha256=hashlib.sha256(INPUT.read_bytes()).hexdigest(),
              oracle_sha256=hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
              independent_math_rows_recomputed=13, identity_rows_recomputed=3,
              argv=argv, exit_code=run.returncode,
              finding='First kind0 template is unchanged by hardcoded kind1 negative mutation; existing check treats a valid input as a rejection control and fails before observed outputs.',
              synthetic_witnesses_are_runtime_evidence=False,
              no_product_execution=True)
(OUT / 'oracle-compatibility.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
