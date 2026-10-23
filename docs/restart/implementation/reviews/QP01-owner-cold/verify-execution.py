"""Read this review's six existing receipts; perform no build or runtime replay."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = HERE / '.runtime/source'
CANDIDATE = '9d39469209afc8e35535cf8ba58dbe668a3f3224'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def records(raw):
    decoder = json.JSONDecoder()
    result = []
    while raw.strip():
        raw = raw.lstrip()
        value, length = decoder.raw_decode(raw)
        result.append(value)
        raw = raw[length:]
    return result


receipts = {}
for name in ['provision-01', 'node-install-01', 'node-build-01',
             'owner-matrix-01', 'producer-controls-01', 'audit-controls-01']:
    receipt = read(name + '/receipt.json')
    assert receipt['candidate'] == CANDIDATE and receipt['exit'] == 0, name
    for filename, expected in receipt['outputs'].items():
        assert sha((HERE / name / filename).read_bytes()) == expected
    receipts[name] = {'sha256': sha((HERE / name / 'receipt.json').read_bytes()),
                      'exit': receipt['exit'], 'seconds': receipt['duration_seconds']}

# Compare every exported tracked blob and executable bit, including old evidence.
tree = subprocess.check_output(['git', 'ls-tree', '--full-tree', '-rz', CANDIDATE], cwd=HERE)
assert tree.strip(b'\0'), 'empty tracked-source inventory'
inventory = []
for item in tree.split(b'\0'):
    if not item:
        continue
    metadata, raw_path = item.split(b'\t', 1)
    mode, kind, blob = metadata.decode().split()
    path = raw_path.decode()
    exported = SOURCE / path
    assert kind == 'blob'
    raw = os.readlink(exported).encode() if mode == '120000' else exported.read_bytes()
    actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert actual_blob == blob, path
    if mode != '120000':
        assert bool(exported.stat().st_mode & 0o111) == (mode == '100755'), path
    inventory.append({'path': path, 'mode': mode, 'sha256': sha(raw)})

identities = read('provision-01/identities.json')
artifacts = []
for number, name, kind, relative_source, relative_manifest, variable in [
    (1, 'nsealr_pi_engine_fixture', 'cdylib', 'crates/nsealr-pi-engine-fixture/src/lib.rs',
     'crates/nsealr-pi-engine-fixture/Cargo.toml', 'NSEALR_QP01_LIBRARY'),
    (2, 'nsealr-qr-worker', 'bin', 'apps/pi/qr-worker/src/main.rs',
     'apps/pi/qr-worker/Cargo.toml', 'NSEALR_QP01_QR_WORKER')]:
    cargo = records((HERE / f'provision-01/cargo-{number}.stdout.jsonl').read_text())
    selected = [r for r in cargo if r['reason'] == 'compiler-artifact'
                and r['target']['name'] == name and kind in r['target']['kind']]
    assert len(selected) == 1
    row = selected[0]
    assert row['fresh'] is False and row['profile']['opt_level'] == '3'
    assert Path(row['manifest_path']) == SOURCE / relative_manifest
    assert Path(row['target']['src_path']) == SOURCE / relative_source
    elf = Path(identities[variable])
    assert str(elf) in row['filenames']
    if kind == 'bin':
        assert row['executable'] == str(elf) and os.access(elf, os.X_OK)
    raw = elf.read_bytes()
    assert raw[:4] == b'\x7fELF' and sha(raw) == identities[variable + '_SHA256']
    details = subprocess.run(['readelf', '-h', '-l', '-d', str(elf)],
                             capture_output=True, check=True)
    detail_name = f'provision-01/elf-{number}.txt'
    (HERE / detail_name).write_bytes(details.stdout + details.stderr)
    artifacts.append({'compiler_artifact': row, 'path': str(elf), 'bytes': len(raw),
                      'mode': oct(elf.stat().st_mode & 0o777), 'sha256': sha(raw),
                      'inspection': {'argv': ['readelf', '-h', '-l', '-d', str(elf)],
                                     'exit': details.returncode, 'raw': detail_name,
                                     'sha256': sha(details.stdout + details.stderr)}})

trace = records((HERE / 'owner-matrix-01/stdout.log').read_text())
cases = [r for r in trace if 'case' in r and 'pass' in r]
assert len(cases) == 39 and all(r['pass'] is True for r in cases)
assert len({r['case'] for r in cases}) == 39
owners = [r['owner_settlement'] for r in trace if 'owner_settlement' in r]
real_owners = [r for r in owners if not r['synthetic_no_W_helper']]
helpers = [r for r in owners if r['synthetic_no_W_helper']]
cs = [r['first_owner_child_settlement'] for r in trace if 'first_owner_child_settlement' in r]
phases = [r['owner_phase'] for r in trace if 'owner_phase' in r]
assert len(real_owners) == 21 and len(helpers) == 11 and len(cs) == 21 and len(phases) == 11
assert sum(bool(r['synthetic_handshake_control']) for r in cs) == 1
worker_statuses = []
for owner in real_owners:
    terminal = owner['terminal']
    assert owner['signal'] is None and owner['code'] in (0, 2)
    assert owner['statusEOF'] and owner['outEOF'] and owner['errEOF']
    assert terminal['ownership'] == 'settled' and terminal['worker_io']['owned_fds_closed']
    if terminal['worker_pid'] is not None:
        phase = [r for r in phases if r['worker_pid'] == terminal['worker_pid']]
        assert len(phase) == 1
        phase = phase[0]
        assert phase['owner_pid'] == owner['pid'] == phase['ppid']
        assert phase['worker_pid'] == phase['sid'] == phase['pgid']
        assert phase['exe_sha256'] == identities['NSEALR_QP01_QR_WORKER_SHA256']
        assert phase['G_bytes'] == phase['image_bytes_sent'] == 0
        assert [f['fd'] for f in phase['fds']] == [0, 1, 2]
        assert phase['limits'] == {'AS': [268435456, 268435456], 'CPU': [1, 2], 'CORE': [0, 0]}
        assert all(terminal['worker_io'].values())
        wait = terminal['worker_wait']
        assert wait['collector_pid'] == owner['pid']
        assert (wait['raw_status'], wait['exit_code']) in ((0, 0), (9, -9))
        worker_statuses.append({'pid': terminal['worker_pid'], 'owner_pid': owner['pid'],
                                'wait': wait, 'IO': terminal['worker_io'], 'outcome': terminal['outcome']})
assert len(worker_statuses) == len({r['pid'] for r in worker_statuses}) == 11
all_pids = [r['pid'] for r in owners + cs + worker_statuses]
assert len(all_pids) == len(set(all_pids)) == 64
still_present = [pid for pid in all_pids if Path(f'/proc/{pid}').exists()]
assert not still_present, still_present
native = [r['first_owner_native_observation'] for r in trace if 'first_owner_native_observation' in r]
assert len(native) == 3
for row in native:
    assert row['library'] == identities['NSEALR_QP01_LIBRARY']
    assert row['sha256'] == identities['NSEALR_QP01_LIBRARY_SHA256']
    assert row['input_bytes'] == 259 and row['output_bytes'] == 611
    assert row['input_sha256'] == '88a16190a1b1ed033fc9bebe5452af70e9a9783fd6b92305add2ac7134039ff7'
    assert row['output_sha256'] == '250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded'
guard = [r['synchronous_deadline_guard'] for r in trace if 'synchronous_deadline_guard' in r]
assert len(guard) == 1
assert guard[0]['signal_aborted'] is False and guard[0]['actual_hold_ms'] >= 110
assert guard[0]['W_O_collected'] and guard[0]['private_decoded_bytes'] == 259
assert guard[0]['C_input_bytes'] == 0

result = {'candidate': CANDIDATE, 'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'verifier_sha256': sha(Path(__file__).read_bytes()), 'receipts': receipts,
          'export_post_execution': {'tracked_blobs_exact': len(inventory), 'modes_exact': True,
                                    'inventory_sha256': sha(json.dumps(inventory, sort_keys=True).encode()),
                                    'git_directory_absent': not (SOURCE / '.git').exists(),
                                    'cargo_home_crate_archives': len(list((HERE / '.runtime/cargo-home').rglob('*.crate')))},
          'artifacts': artifacts,
          'matrix': {'cases': [r['case'] for r in cases], 'pass': 39,
                     'kernel_process_roles': {'native_C': 20, 'C_handshake_helper': 1,
                                              'real_O': 21, 'real_W': 11, 'no_W_O_helpers': 11},
                     'unique_descendant_pids': sorted(all_pids), 'unique_descendants': 64,
                     'pure_parser_controls': 9, 'pure_parser_kernel_processes': 0,
                     'worker_terminal_and_IO': worker_statuses,
                     'all_original_pids_absent_at_observation': True,
                     'native_observations': 3, 'synchronous_guard': guard[0]},
          'limits': ['Raw harness scope labels retain author wording; this invocation is independently executed by the reviewer.',
                     'No full Pi/make ci or fresh advisory/index acquisition in this reviewer replay.',
                     'No general ELF reproducibility, physical/ARM/Pi, default route, O-death or unknown-cleanup qualification.']}
(HERE / 'execution-checks.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'pass': True, 'tracked_blobs': len(inventory), 'matrix_cases': 39,
                  'unique_descendants': 64, 'actual_artifacts': [r['sha256'] for r in artifacts]}))
