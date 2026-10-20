#!/usr/bin/env python3
"""Strict offline comparison of real K01 observations to pre-runtime inputs.

No product code supplies expectations. This helper cannot prove execution
provenance; source-bound test commands/logs and distinct review do that.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
S03 = HERE.parent / 'S03'
EXPECTED_SHA = '887ee851eac781f3014db68db79148d63e339c65efa057b89db7b5bec4c29b29'
ORACLE_SHA = 'f69bd3446fd4dce92106d29a0dfb13bf9fbdf447cbfdcae1b2dcf9e6c0f1cda5'
PROVENANCE_SHA = 'cac4f93d9dd399f6f010cf5f4db6d53bd9668af9da0499620db48a5cb9360f0d'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate decoded member')
        result[key] = value
    return result


def integer(token):
    require(re.fullmatch(r'0|[1-9][0-9]*', token) is not None, 'noncanonical integer')
    return int(token)


def forbidden(_):
    raise ValueError('noninteger or nonfinite token')


def strict(raw):
    def scalars(value):
        if type(value) is str:
            value.encode('utf-8', errors='strict')
        elif type(value) is list:
            for child in value:
                scalars(child)
        elif type(value) is dict:
            for key, child in value.items():
                scalars(key)
                scalars(child)
    value = json.loads(raw, object_pairs_hook=unique, parse_int=integer,
                       parse_float=forbidden, parse_constant=forbidden)
    scalars(value)
    return value


def exact(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'exact record fields')


def hex_bytes(value, length):
    require(type(value) is str and re.fullmatch('[0-9a-f]{' + str(2*length) + '}', value) is not None,
            'lowercase hex length/spelling')
    return bytes.fromhex(value)


def rows(value, fields, ids):
    require(type(value) is list and len(value) == len(ids), 'exact row count')
    result = {}
    for row in value:
        exact(row, fields)
        require(type(row['id']) is str and row['id'] in ids and row['id'] not in result,
                'unknown/duplicate row ID')
        result[row['id']] = row
    require(set(result) == set(ids), 'missing row ID')
    return result


def load_oracle():
    for path, expected in [(S03/'oracle.py', ORACLE_SHA),
                           (S03/'oracle-source/provenance.json', PROVENANCE_SHA)]:
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, 'pinned independent source')
    spec = importlib.util.spec_from_file_location('k01_independent_s03_primitives', S03/'oracle.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    return oracle.template, oracle.canonical, oracle.reference()


def check(fixtures, observed, identities, rejections):
    require(hashlib.sha256(fixtures.read_bytes()).hexdigest() == EXPECTED_SHA,
            'immutable accepted822c independent inputs')
    expected = strict(fixtures.read_text())
    template, canonical, bip = load_oracle()
    official = strict((S03/'oracle-source/selected-official-vectors.json').read_text())['rows']
    for row in official:
        require(bip.schnorr_verify(bytes.fromhex(row['message']), bytes.fromhex(row['public key']),
                                  bytes.fromhex(row['signature'])) == (row['verification result'] == 'TRUE'),
                'official reference sanity')
    vectors = expected['vectors']
    ids = [v['id'] for v in vectors]
    require(len(ids) == len(set(ids)) == 13, 'exact13 prepared cases')
    actual = rows(strict(observed.read_text()),
                  ['id','pubkey','canonical_hex','event_id','signature','signed_event_json'], ids)
    mutations = 0
    for row in vectors:
        item = template(row['template'].encode('utf-8'))
        secret = row['public_fixture_scalar'].to_bytes(32, 'big')
        key = bip.pubkey_gen(secret)
        require(key.hex() == row['pubkey'], 'expected public key recomputation')
        data = canonical(item, key.hex())
        require(data.hex() == row['canonical_hex'], 'expected canonical recomputation')
        digest = hashlib.sha256(data).digest()
        require(digest.hex() == row['event_id'], 'expected raw ID recomputation')
        aux = hex_bytes(row['aux_hex'], 32)
        signature = bip.schnorr_sign(digest, secret, aux)
        require(signature.hex() == row['signature'], 'expected exact auxiliary/signature recomputation')
        got = actual[row['id']]
        actual_key = hex_bytes(got['pubkey'], 32)
        actual_digest = hex_bytes(got['event_id'], 32)
        actual_signature = hex_bytes(got['signature'], 64)
        require(type(got['canonical_hex']) is str and got['canonical_hex'] == data.hex(), 'actual canonical bytes')
        require(actual_key == key and actual_digest == digest and actual_signature == signature,
                'actual identity/ID/raw signature')
        require(type(got['signed_event_json']) is str and len(got['signed_event_json'].encode()) <= 9216,
                'complete bounded serialized event')
        signed = strict(got['signed_event_json'])
        exact(signed, ['pubkey','created_at','kind','tags','content','id','sig'])
        reconstructed = {field:signed[field] for field in ['created_at','kind','tags','content']}
        # Reapply independent grammar/type/bounds to the final serialized values.
        final_item = template(json.dumps(reconstructed, ensure_ascii=False, separators=(',', ':')).encode())
        require(final_item == item and canonical(final_item, signed['pubkey']) == data, 'all actual signed fields')
        require(signed['pubkey'] == key.hex() and signed['id'] == digest.hex() and signed['sig'] == signature.hex(),
                'serialized key/ID/signature')
        require(bip.schnorr_verify(digest, key, signature), 'raw ID verification')
        require(not bip.schnorr_verify(hashlib.sha256(digest).digest(), key, signature), 'double-hash rejection')
        wrong_key = bip.pubkey_gen((1).to_bytes(32, 'big'))
        require(not bip.schnorr_verify(digest, wrong_key, signature), 'wrong-key rejection')
        for source, length in [(signature,64),(digest,32)]:
            for index in range(length):
                changed = bytearray(source); changed[index] ^= 1
                require(not bip.schnorr_verify(digest if length == 64 else bytes(changed), key,
                                              bytes(changed) if length == 64 else signature), 'every-byte mutation')
                mutations += 1
        for field in ['created_at','kind','tags','content','pubkey']:
            changed = dict(item); changed_key = key.hex()
            if field in ['created_at','kind']:
                changed[field] += 1
            elif field == 'tags':
                changed[field] = changed[field] + [['unknown','independent mutation']]
            elif field == 'content':
                changed[field] += 'x'
            else:
                changed_key = wrong_key.hex()
            changed_id = hashlib.sha256(canonical(changed, changed_key)).digest()
            require(changed_id != digest and not bip.schnorr_verify(changed_id, key, signature),
                    'each canonical field mutation')
            mutations += 1
    same_id = [v for v in vectors if v['event_id'] == vectors[0]['event_id']]
    require(len(same_id) == 2 and same_id[0]['aux_hex'] != same_id[1]['aux_hex']
            and same_id[0]['signature'] != same_id[1]['signature'], 'independent auxiliary-use control')
    identity_rows = strict(identities.read_text())
    require(type(identity_rows) is list and len(identity_rows) == 3, 'three original identity rows')
    seen = set()
    for row in identity_rows:
        exact(row, ['scalar','original_scalar','normalized_backend','pubkey'])
        require(type(row['scalar']) is str and row['scalar'] not in seen, 'unique scalar identity')
        seen.add(row['scalar'])
        prepared = next((v for v in expected['identity_expectations'] if v['public_fixture_scalar'] == row['scalar']), None)
        require(prepared is not None, 'known identity')
        n = bip.n-3 if row['scalar'] == 'n-3' else int(row['scalar'])
        original = n.to_bytes(32,'big')
        normalized = n if bip.has_even_y(bip.point_mul(bip.G,n)) else bip.n-n
        require(hex_bytes(row['original_scalar'],32) == original
                and row['original_scalar'] == prepared['original_scalar_hex'], 'actual original recovery scalar')
        require(hex_bytes(row['normalized_backend'],32) == normalized.to_bytes(32,'big')
                and row['normalized_backend'] == prepared['normalized_backend_hex'], 'scoped normalized witness')
        require(hex_bytes(row['pubkey'],32) == bip.pubkey_gen(original)
                and row['pubkey'] == prepared['pubkey'], 'identity derivation')
    require(seen == {'1','3','n-3'}, 'all identity cases')
    negatives = expected['negative_expectations']
    actual_negative = rows(strict(rejections.read_text()),
                           ['id','layer','error','approval_calls','entropy_calls','sign_calls','output'],
                           [v['id'] for v in negatives])
    for row in negatives:
        got = actual_negative[row['id']]
        require(got['layer'] == row['layer'], 'actual expected rejection layer')
        require(type(got['error']) is str and got['error'].startswith('Parse(' if row['layer'] == 'parser' else 'Inspection('),
                'bounded actual rejection')
        for field in ['approval_calls','entropy_calls','sign_calls']:
            require(type(got[field]) is int and got[field] == 0, 'rejected input caused effects')
        require(got['output'] is False, 'rejected input released output')
        if row['layer'] == 'parser':
            try:
                template(row['template'].encode('utf-8'))
            except (ValueError,UnicodeError):
                pass
            else:
                raise ValueError('parser-negative expectation accidentally valid')
    return {'independent_vectors':13,'identities':3,'preflight_rejections':len(negatives),
            'official_controls':len(official),'per_byte_and_canonical_mutations_rejected':mutations,
            'limits':'source-bound observations only; no execution provenance, hardware or provider qualification from data comparison'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['fixtures','observed','identities','rejections']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.fixtures,args.observed,args.identities,args.rejections),sort_keys=True))


if __name__ == '__main__':
    main()
