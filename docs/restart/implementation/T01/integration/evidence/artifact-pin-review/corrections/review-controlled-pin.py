"""Exercise the unchanged reviewed checker with the explicitly reviewed literal."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
source = ROOT / 'scripts/verify_contracts.py'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'dc0e13c95be0c522a625955c18f9ca82a88252ac0076c82b2ec761f44d478e90'
namespace = {'__file__':str(source),'__name__':'root_controlled_literal_review'}
exec(compile(raw,str(source),'exec'),namespace)
assert namespace['ARTIFACT_TREE_OID'] is None
namespace['ARTIFACT_TREE_OID'] = 'b629e75d18190ded2403ffabe965b595a9bcf6a6'
print(json.dumps(namespace['validate'](),sort_keys=True))
