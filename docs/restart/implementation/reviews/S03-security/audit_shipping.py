#!/usr/bin/env python3
"""Limited artifact/source controls; not a final-link or absence-of-all-code proof."""
import hashlib,json,pathlib
OWN=pathlib.Path(__file__).resolve().parent
ROOT=OWN.parents[4]
lib=OWN/'build/riscv32imafc-unknown-none-elf/release/libnsealr_core.rlib'
data=lib.read_bytes()
markers=[b'S03_OBSERVED',b's03_independent_event_id_and_signature_agree',b's03_first_attempt_is_irrevocable']
for marker in markers:assert marker not in data,marker
source=(ROOT/'crates/nsealr-core/src/authorization.rs').read_text()
assert '#[cfg(test)]\nmod tests;' in source
assert all('pub fn '+n not in source for n in ['execute','start_execution','finish_execution'])
assert 'sign_raw(' not in source
features=(OWN/'evidence/runtime-features.log').read_text()
assert all('feature "'+n+'"' not in features for n in ['alloc','std','serde','ecdh','getrandom','algorithm'])
print(json.dumps({'library':str(lib.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'fixture_markers_absent':[x.decode() for x in markers],'raw_signing_call_absent_from_product_source':True,'test_module_cfg_test_only':True,'execution_functions_private':True,'prohibited_runtime_features_absent':True,'limit':'Marker absence corroborates source inspection only; artifact is a library build without reproducibility remapping, not final firmware or an entropy/physical erasure qualification.'},indent=2))
