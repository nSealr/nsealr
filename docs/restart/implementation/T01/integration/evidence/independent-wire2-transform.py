"""One-time deterministic expected-data derivation from fixed admitted preimages.

No product parser, renderer, signer, codec or generated helper is imported.
Only JSON/UTF8/Base64URL/SHA256 and the previously specified diagnostic payload
formula are used. This is author evidence, not a build/projector/runtime oracle.
"""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = 'dbad656997ad8cf9024ca1489291f5f1d4d3094a'
ROOT = Path(__file__).resolve().parents[6]
ARTIFACT = ROOT / 'protocols/contracts/v1'
SCOPE = json.loads((Path(__file__).parent / 'admission/source-edit-set.json').read_text())


def compact(value, sort=False):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=sort)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def original(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{SOURCE}:{path}'])


def payload(value):
    try:
        decoded = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
        parsed = json.loads(decoded)
        changed = walk(parsed)
        return encode(compact(changed).encode()) if parsed != changed else value
    except (ValueError, UnicodeError):
        return value


def text(value):
    if value.startswith('nsealr1:'):
        return 'nsealr1:' + payload(value[8:])
    if value.startswith('nsealr1f:'):
        pieces = value.rstrip('\n').split(':')
        if len(pieces) != 4:
            return value
        prefix, kind, old, checksum = pieces
        new = payload(old)
        if checksum == sha(f'{kind}:{old}'.encode())[:16]:
            checksum = sha(f'{kind}:{new}'.encode())[:16]
        return f'{prefix}:{kind}:{new}:{checksum}' + ('\n' if value.endswith('\n') else '')
    if value.startswith('{'):
        try:
            parsed = json.loads(value)
            updated = walk(parsed)
            if updated != parsed:
                # Replace only the outer numeric token in raw JSON strings;
                # preserve intentional whitespace and every unrelated byte.
                import re
                return re.sub(r'("version"\s*:\s*)1(?=\s*[,}])', r'\g<1>2', value)
        except ValueError:
            pass
    return value


def walk(value):
    if isinstance(value, list):
        return [walk(item) for item in value]
    if isinstance(value, str):
        return text(value)
    if not isinstance(value, dict):
        return value
    result = {key: walk(item) for key, item in value.items()}
    if 'request_id' in value and ('method' in value or 'ok' in value) and value.get('version') == 1:
        result['version'] = 2
    if 'payload_base64url' in value:
        result['payload_base64url'] = payload(value['payload_base64url'])
        new = result['payload_base64url']
        if value.get('format') == 'serial-frame-v0':
            result['checksum'] = sha(f"{value['type']}:{new}".encode())[:16]
        if value.get('format') == 'qr-animated-envelope-v0':
            decoded = base64.urlsafe_b64decode(new + '=' * (-len(new) % 4))
            digest = sha(decoded)
            result['decoded_json_sha256'] = digest
            size = value['chunk_size_chars']
            chunks = [new[i:i + size] for i in range(0, len(new), size)]
            result['frames'] = []
            for i, chunk in enumerate(chunks, 1):
                frame = f'nsealr1a:{digest}:{i}/{len(chunks)}:{chunk}'
                result['frames'].append(frame + ':' + sha(frame.encode())[:16])
    return result


def pages(review):
    tag_lines = ['No tags'] if review['tag_count'] == 0 else []
    for i, tag in enumerate(review['tags'], 1):
        tag_lines.append(f"Tag {i}/{review['tag_count']}")
        tag_lines.extend(tag or ['empty tag'])
    return [
        {'title': 'Event', 'lines': [f"Kind {review['kind']}", f"Created {review['created_at']}", 'Author', review['author_pubkey']], 'action': 'next'},
        {'title': 'Content', 'lines': [review['content']], 'action': 'next'},
        {'title': 'Tags', 'lines': tag_lines, 'action': 'next'},
        {'title': 'Decision', 'lines': ['Approve signing only if all pages match.'], 'action': 'approve_or_reject'},
    ]


def diagnostic(request, review, summary_pages):
    fixed = {'version': request['version'], 'method': request['method'],
             'request_id': request['request_id'], 'event_template': request['params']['event_template'],
             'review': review, 'pages': summary_pages}
    return sha(compact(fixed, sort=True).encode())


def main():
    originals, updated = {}, {}
    for row in SCOPE['existing']:
        path = row['path']
        if path.startswith('protocols/contracts/v1/') and path.endswith('.json') and '/schemas/' not in path and path.rsplit('/', 1)[-1] not in ['manifest.json', 'consumers.json', 'adaptation.json']:
            data = original(path)
            value = json.loads(data)
            originals[path] = value
            updated[path] = walk(value)

    # Update request-bound diagnostic digests from independently fixed source
    # review values/pages. No production renderer is evaluated.
    digests = {}
    for path, value in updated.items():
        if '/vectors/review/' in path:
            before = originals[path]
            review_pages = pages(value['review'])
            old = diagnostic(before['request'], before['review'], review_pages)
            new = diagnostic(value['request'], value['review'], review_pages)
            digests[old] = new

    def replace_digests(value):
        if isinstance(value, str):
            return digests.get(value, value)
        if isinstance(value, list):
            return [replace_digests(item) for item in value]
        if isinstance(value, dict):
            return {key: replace_digests(item) for key, item in value.items()}
        return value

    for path in updated:
        updated[path] = replace_digests(updated[path])

    profile_by_route = {'raspberry_qr_vault': 'pi_qr', 'esp32_qr_vault': 'p4_qr',
                        'esp32_usb_nip46': 'esp32_no_se', 'custom_hardware_wallet': 'custom_board'}
    custody_by_profile = {'pi_qr': 'volatile_session', 'p4_qr': 'volatile_session',
                          'esp32_no_se': 'mcu_wrapped_persistent', 'custom_board': 'custom_se_assisted_persistent'}
    accounts = {}
    for path, value in updated.items():
        if '/vectors/accounts/' not in path:
            continue
        value['format'] = 'nsealr.account.v1'
        profile = profile_by_route.get(value['signer_route']['type'])
        value['profile'] = profile
        value['implementation_id'] = f'nsealr.conformance.{profile}.v1' if profile else None
        value['limits_id'] = 'nsealr.limits.conformance.v1' if profile else None
        value['capabilities'] = {'methods': [m for m in value['capabilities']['methods'] if m != 'get_signing_status']}
        if profile:
            value['capabilities']['methods'] = ['get_capabilities', 'get_public_key', 'sign_event']
            value['signer_route']['custody'] = custody_by_profile[profile]
            value['signer_route']['policy_support'] = 'manual_only'
            value['signer_route']['trusted_review'] = 'device_display'
        accounts[value['account_id']] = value

    for path, value in updated.items():
        if '/vectors/route-selections/' not in path:
            continue
        # Route vectors wrap the route selection with its expected request.
        def route(item):
            if isinstance(item, dict) and item.get('format') == 'nsealr-route-selection-v0':
                account = accounts[item['account_id']]
                local = account['profile'] is not None
                for key in ['physical_review', 'physical_approval', 'persistent_grants']:
                    item.pop(key, None)
                item.update({'format': 'nsealr.route-selection.v1', 'profile': account['profile'],
                             'implementation_id': account['implementation_id'], 'limits_id': account['limits_id'],
                             'contract': 'nsealr.signing.v2' if local else 'nip46', 'method': 'sign_event',
                             'method_revision': 1, 'operation_id': 'nostr.sign-event.v1',
                             'algorithm_id': 'bip340.secp256k1.v1',
                             'codec_id': 'nsealr.qr-envelope.v0' if item['transport'] == 'qr' else 'nsealr.serial-frame.v0' if local else 'nip46',
                             'custody': account['signer_route']['custody'], 'policy_support': account['signer_route']['policy_support']})
            elif isinstance(item, dict):
                for child in item.values():
                    route(child)
            elif isinstance(item, list):
                for child in item:
                    route(child)
        route(value)

    # A bounded reference describes the generic disabled development protocol.
    # The independent full conformance record still does not qualify hardware.
    runtime = [{'method_id': 'get_capabilities', 'configuration': 'configured', 'availability': 'available', 'reason': None},
               {'method_id': 'get_public_key', 'configuration': 'configured', 'availability': 'available', 'reason': None}]
    reference = {'format': 'nsealr.capabilities.v1', 'form': 'reference', 'profile': 'esp32_no_se',
                 'implementation_id': 'nsealr.conformance.esp32_no_se.v1', 'runtime': runtime}
    for path, value in updated.items():
        if path.endswith(('response-get-capabilities-esp32-s3-scaffold.json', 'response-get-capabilities-esp32-s3-enabled.json')):
            value['result'] = {'capabilities': reference}

    assert len(digests) == 6, 'Expected the six admitted diagnostic source reviews'
    assert len(accounts) == 5, 'Expected the five admitted account preimages'
    records = []
    for path, value in updated.items():
        if value == originals[path]:
            continue
        before = original(path)
        after = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
        (ROOT / path).write_bytes(after)
        records.append({'path': path, 'source_commit': SOURCE, 'source_sha256': sha(before), 'current_sha256': sha(after)})
    assert records, 'An empty transform is not successful expected-data derivation'
    result = {'task': 'T01', 'role': 'Independent fixed-preimage transformation, before corresponding wire/runtime edits',
              'source': SOURCE, 'algorithm': 'stdlib JSON/UTF8/Base64URL/SHA256; diagnostic version-bound canonical payload from fixed review/page inputs; no production code',
              'original170_mappings': 'Preserved in exact preparation; no projected source retired', 'diagnostic_digest_map': digests,
              'changed_sources': records, 'production_output_used': False}
    (Path(__file__).parent / 'independent-wire2-transform.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Independent expected sources transformed: {len(records)}; diagnostic digest pairs: {len(digests)}')


if __name__ == '__main__':
    main()
