#!/usr/bin/env python3
"""Independent S03 oracle. No nsealr implementation is imported.

Generate expected values before observing Rust; --check never rewrites them.
Only disposable, explicitly public fixture scalars are used.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate decoded member')
        result[key] = value
    return result


def integer(token):
    if not re.fullmatch(r'0|[1-9][0-9]*', token):
        raise ValueError('noncanonical integer')
    return int(token)


def forbidden(_):
    raise ValueError('unsupported numeric token')


def template(raw):
    if len(raw) > 4096:
        raise ValueError('input limit')
    item = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_int=integer, parse_float=forbidden, parse_constant=forbidden)
    if type(item) is not dict or set(item) != {'created_at', 'kind', 'tags', 'content'}:
        raise ValueError('template members')
    for field, maximum in [('created_at', 2**53-1), ('kind', 65535)]:
        if type(item[field]) is not int or not 0 <= item[field] <= maximum:
            raise ValueError('integer range/type')
    if type(item['content']) is not str or len(item['content'].encode('utf-8')) > 2048:
        raise ValueError('content')
    if type(item['tags']) is not list or len(item['tags']) > 32:
        raise ValueError('tags')
    total = len(item['content'].encode('utf-8'))
    for tag in item['tags']:
        if type(tag) is not list or not 1 <= len(tag) <= 8 or tag[0] == '':
            raise ValueError('tag shape')
        for field in tag:
            if type(field) is not str or len(field.encode('utf-8')) > 256:
                raise ValueError('tag field')
            total += len(field.encode('utf-8'))
    if total > 4096:
        raise ValueError('aggregate')
    return item


def canonical(item, pubkey):
    data = json.dumps([0, pubkey, item['created_at'], item['kind'], item['tags'], item['content']],
                      ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(data) > 8192:
        raise ValueError('canonical limit')
    return data


def reference():
    path = ROOT / 'oracle-source/bip340_reference.py'
    provenance = json.loads((path.parent/'provenance.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == provenance['source_sha256']
    spec = importlib.util.spec_from_file_location('bip340_reference', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generate(destination):
    bip = reference()
    key = (3).to_bytes(32, 'big')
    pubkey = bip.pubkey_gen(key).hex()
    samples = [('', []), ('hello', []), ('"\\/\b\f\n\r\t\0\x01\x1f', []),
               ('caf\u00e9 e\u0301 \U0001f600 \u2028\u2029', []),
               ('U+202E \\u{202E} \u202e \u200d', []),
               ('  leading and trailing  ', [['t', 'x'], ['t', 'x', '', 'extension']]),
               ('quote', [['q', 'a'*64, '', pubkey, 'extension']]),
               ('reply', [['e', 'b'*64, '', 'root', pubkey], ['p', pubkey, '']])]
    rows = []
    for index, (content, tags) in enumerate(samples):
        value = dict(created_at=0 if index==0 else 1710000000+index, kind=1, tags=tags, content=content)
        raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
        parsed = template(raw)
        data = canonical(parsed, pubkey)
        event_id = hashlib.sha256(data).digest()
        signature = bip.schnorr_sign(event_id, key, bytes(32))
        assert bip.schnorr_verify(event_id, bytes.fromhex(pubkey), signature)
        rows.append(dict(id=f'fixture-{index}', template=raw.decode(), public_fixture_scalar=3,
                         aux_hex=bytes(32).hex(), pubkey=pubkey, canonical_hex=data.hex(),
                         event_id=event_id.hex(), signature=signature.hex()))
    value = {'format': 'nsealr.s03-independent-v1', 'provenance': 'Independent Python JSON/hashlib + hash-pinned upstream BIP340 reference; public scalar 3', 'vectors': rows}
    destination.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'generated':len(rows),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}))


def check(fixtures, observed):
    bip = reference()
    official = json.loads((ROOT/'oracle-source/selected-official-vectors.json').read_text())['rows']
    for row in official:
        assert bip.schnorr_verify(bytes.fromhex(row['message']), bytes.fromhex(row['public key']),
                                  bytes.fromhex(row['signature'])) == (row['verification result'] == 'TRUE')
    rows = json.loads(fixtures.read_text())['vectors']
    actual = {row['id']: row for row in json.loads(observed.read_text())}
    assert set(actual) == {row['id'] for row in rows}
    keys = json.loads(observed.with_suffix('.keys.json').read_text())
    assert {row['scalar'] for row in keys} == {'1', '3', 'n-3'}
    for row in keys:
        scalar = bip.n-3 if row['scalar'] == 'n-3' else int(row['scalar'])
        key = scalar.to_bytes(32, 'big')
        assert bip.pubkey_gen(key).hex() == row['pubkey']
        normalized = scalar if bip.has_even_y(bip.point_mul(bip.G, scalar)) else bip.n-scalar
        assert normalized.to_bytes(32, 'big').hex() == row['normalized_backend']
        if row['scalar'] == 'n-3':
            message = bytes.fromhex(rows[0]['event_id'])
            assert bip.schnorr_sign(message, key, bytes(32)).hex() == row['empty_event_signature']
    # Separate parser oracle: expected rejection follows grammar/type/Unicode
    # requirements, never a result copied from the Rust parser.
    good = rows[0]['template']
    negatives = [good.replace('"kind":1', '"kind":1,"k\\u0069nd":1'),
                 good.replace('"kind":1', '"kind":65536'),
                 good.replace('"created_at":0', '"created_at":01'),
                 good.replace('"created_at":0', '"created_at":-0'),
                 good.replace('"kind":1', '"kind":true'),
                 good.replace('"content":""', '"content":"\\ud800"'),
                 good+',', good+'{}']
    for raw in [text.encode() for text in negatives] + [good.encode().replace(b'"content":""', b'"content":"\xc0\x80"')]:
        try:
            template(raw)
        except (ValueError, UnicodeError):
            pass
        else:
            raise AssertionError(('accepted invalid input', raw))
    field_mutations = 0
    for want in rows:
        data = canonical(template(want['template'].encode()), want['pubkey'])
        assert data.hex() == want['canonical_hex']
        assert hashlib.sha256(data).hexdigest() == want['event_id']
        got = actual[want['id']]
        for field in ['pubkey', 'canonical_hex', 'event_id', 'signature']:
            assert got[field] == want[field], (want['id'], field)
        message, public, signature = bytes.fromhex(got['event_id']), bytes.fromhex(got['pubkey']), bytes.fromhex(got['signature'])
        assert bip.schnorr_verify(message, public, signature)
        assert not bip.schnorr_verify(hashlib.sha256(message).digest(), public, signature)
        assert not bip.schnorr_verify(message, bip.pubkey_gen((1).to_bytes(32, 'big')), signature)
        for offset in range(32):
            changed=bytearray(message); changed[offset]^=1
            assert not bip.schnorr_verify(bytes(changed), public, signature)
        for offset in range(64):
            changed=bytearray(signature); changed[offset]^=1
            assert not bip.schnorr_verify(message, public, bytes(changed))
        for field in ['created_at', 'kind', 'tags', 'content']:
            changed = template(want['template'].encode())
            if field == 'content':
                changed[field] += 'changed'
            elif field == 'tags':
                changed[field].append(['t', 'added'])
            else:
                changed[field] ^= 1
            changed_id = hashlib.sha256(canonical(changed, want['pubkey'])).digest()
            assert changed_id != message
            assert not bip.schnorr_verify(changed_id, public, signature)
            field_mutations += 1
    print(json.dumps({'verified_events':len(rows), 'official_verifier_controls':len(official),
                      'actual_key_imports_checked':len(keys), 'strict_parser_negative_controls':len(negatives)+1,
                      'signature_byte_mutations_rejected':64*len(rows), 'event_id_byte_mutations_rejected':32*len(rows),
                      'canonical_field_mutations_rejected':field_mutations, 'wrong_key_mutations_rejected':len(rows),
                      'double_hash_mutations_rejected':len(rows)}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--fixtures', type=Path, default=ROOT/'vectors.json')
    parser.add_argument('--observed', type=Path, default=ROOT/'evidence/observed-events.json')
    args=parser.parse_args()
    if args.generate == args.check:
        parser.error('choose exactly one of --generate or --check')
    generate(args.fixtures) if args.generate else check(args.fixtures, args.observed)
