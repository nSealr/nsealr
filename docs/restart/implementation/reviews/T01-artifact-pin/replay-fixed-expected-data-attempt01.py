"""Re-execute the read author transform in isolated output, never product files."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
REL = Path('protocols/contracts/v1')
TRANSFORM = ROOT / 'docs/restart/implementation/T01/integration/evidence/independent-wire2-transform.py'
EXPECTED = TRANSFORM.with_suffix('.json')
namespace = {'__file__':str(TRANSFORM),'__name__':'reviewed_fixed_input_transform'}
exec(compile(TRANSFORM.read_bytes(), str(TRANSFORM), 'exec'), namespace)
historical = namespace['SOURCE']
with tempfile.TemporaryDirectory(prefix='review-fixed-expectations-') as directory:
    output = Path(directory)
    shutil.copytree(ROOT / REL, output / REL)
    proof = output / 'proof'
    proof.mkdir()
    # Only the output directory and fixed Git reader differ from the exact read
    # transform. Expected algorithms/inputs remain unchanged; no runtime imports.
    namespace.update(ROOT=output, ARTIFACT=output / REL,
                     __file__=str(proof / TRANSFORM.name))
    namespace['original'] = lambda path: subprocess.check_output(
        ['git','--no-replace-objects','-C',str(ROOT),'show',historical+':'+path])
    namespace['main']()
    observed = json.loads((proof / EXPECTED.name).read_bytes())
    expected = json.loads(EXPECTED.read_bytes())
    assert observed == expected, 'Fixed-preimage derivation differs from retained independent proof'
    bindings = []
    for row in observed['changed_sources']:
        actual = (ROOT / row['path']).read_bytes()
        replay = (output / row['path']).read_bytes()
        assert replay == actual, row['path']
        assert hashlib.sha256(actual).hexdigest() == row['current_sha256'], row['path']
        bindings.append({'path':row['path'],'sha256':row['current_sha256']})
    print(json.dumps({'source':historical,'exact_source_transform_sha256':hashlib.sha256(TRANSFORM.read_bytes()).hexdigest(),
                      'transform_output_exact':True,'92_actual_postimages_match':len(bindings)==92,
                      'six_diagnostic_pairs_exact':len(observed['diagnostic_digest_map'])==6,
                      'runtime_oracle_imported':False,'product_files_written':False,
                      'bindings':bindings},indent=2))
