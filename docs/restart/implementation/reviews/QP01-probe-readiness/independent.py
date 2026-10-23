"""Execute probe classification on synthetic inputs; no target hardware queried."""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / 'apps/pi/app/nsealr_vault/hardware_probe.py'
EXPECTED_SHA = '525734ce67618b59d8f30d2e3fcd5dd74c5e956a259f24419cd82857a7d3d0b8'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
spec = importlib.util.spec_from_file_location('reviewed_probe', SOURCE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

VALID = 'camera_auto_detect=1\ndtparam=spi=on\n'
EXPECTED_CALLS = [('systemctl', action, service) for service in ('ssh', 'sshd')
                  for action in ('is-enabled', 'is-active')]
results = []


def run_case(name, config=VALID, replacement=None, ready=False):
    calls = []
    reads = []

    def read(path):
        reads.append(str(path))
        return {'/proc/device-tree/model': 'Raspberry Pi Zero Rev 1.3\0',
                '/boot/config.txt': config,
                '/proc/swaps': 'Filename Type Size Used Priority\n'}[str(path)]

    def command(args):
        calls.append(args)
        if replacement is not None and args[1:] == replacement[:2]:
            return replacement[2]
        return (1, 'disabled', '') if args[1] == 'is-enabled' else (3, 'inactive', '')

    # Any accidental real OS command, rather than the injected callback, fails.
    with patch.object(probe.subprocess, 'run', side_effect=AssertionError('unexpected OS command')):
        report = probe.run_seed_signer_compatibility_probe(
            read_text=read, find_module=lambda _: True, run_command=command)
    assert report['ready_for_hardware_acceptance'] is ready, (name, report)
    assert calls == EXPECTED_CALLS
    assert set(reads) == {'/proc/device-tree/model', '/boot/config.txt', '/proc/swaps'}
    if not ready:
        assert report['acceptance_blockers']
    results.append({'name': name, 'expected_ready': ready,
                    'observed_ready': report['ready_for_hardware_acceptance'],
                    'boot_camera': next(x['status'] for x in report['checks'] if x['id'] == 'boot_camera_enabled'),
                    'boot_spi': next(x['status'] for x in report['checks'] if x['id'] == 'boot_spi_enabled'),
                    'remote': next(x['status'] for x in report['checks'] if x['id'] == 'remote_access_disabled'),
                    'readonly_query_sequence_exact': True})


for name, config in (
    ('known-auto', VALID),
    ('known-legacy', 'start_x=1\ndtparam=spi=on\n'),
    ('all-and-whitespace', '[all]\n\tstart_x = 1\r\n dtparam = spi = on \n'),
    ('commented-off-does-not-disable', '# camera_auto_detect=0\n' + VALID),
):
    run_case(name, config, ready=True)

for name, config in (
    ('commented-spi', 'camera_auto_detect=1\n#dtparam=spi=on\n'),
    ('commented-camera', '#camera_auto_detect=1\ndtparam=spi=on\n'),
    ('spi-contrary-after', VALID + 'dtparam=spi=off\n'),
    ('spi-contrary-before', 'dtparam=spi=off\n' + VALID),
    ('camera-contrary', VALID + 'camera_auto_detect=0\n'),
    ('substring-is-not-assignment', 'camera_auto_detect=1\nx=dtparam=spi=on\n'),
    ('suffix-is-not-value', 'camera_auto_detect=1\ndtparam=spi=onward\n'),
    ('include-unresolved', VALID + 'include boot-extra.txt\n'),
    ('filter-unresolved', '[pi0]\n' + VALID),
    ('filter-reset-still-unresolved', '[pi0]\n[all]\n' + VALID),
    ('overlay-unresolved', VALID + 'dtoverlay=example\n'),
    ('combined-parameters-unresolved', VALID + 'dtparam=audio=on,spi=on\n'),
    ('unicode-separator', 'camera_auto_detect=1\u2028dtparam=spi=on\n'),
    ('long-entry-unresolved', 'camera_auto_detect=1\n' + ' ' * 68 + 'dtparam=spi=on\n'),
):
    run_case(name, config)

bad = ((1, '', 'Permission denied'), (127, '', 'missing command'),
       (0, 'disabled', ''), (3, 'disabled', ''), (1, 'disabled', 'warning'),
       (3, 'inactive', 'warning'), (4, 'unknown', ''), (0, 'future-state', ''),
       (1, 'disabled\nmasked', ''), (3, 'inactive\nunknown', ''),
       (True, 'disabled', ''), (1, 'disabled\x1b[0m', ''))
for service in ('ssh', 'sshd'):
    for action in ('is-enabled', 'is-active'):
        for index, response in enumerate(bad):
            run_case(f'{service}-{action}-unknown-{index}', replacement=(action, service, response))
        unsafe = 'enabled' if action == 'is-enabled' else 'active'
        run_case(f'{service}-{action}-explicit-unsafe', replacement=(action, service, (0, unsafe, '')))

# Validate the real default runner's missing-command path without executing it.
with patch.object(probe.subprocess, 'run', side_effect=FileNotFoundError('systemctl')) as called:
    value = probe._remote_access_check(probe._default_run_command)
assert value['status'] == 'blocked'
assert [tuple(x.args[0]) for x in called.call_args_list] == EXPECTED_CALLS
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
Path(__file__).with_name('independent-results.json').write_text(json.dumps({
    'candidate': '4ab6e46e3f6e332d38bb049ed4988bec9f3550cf',
    'product_source_sha256': EXPECTED_SHA,
    'proof_kind': 'Actual product function executions with synthetic file/module/command inputs; no Pi, GPIO, service or boot mutation',
    'cases': results, 'case_count': len(results), 'all_passed': True,
    'default_missing_command_path': 'blocked; four exact read-only query argument lists; subprocess mocked',
    'physical_or_global_remote_access_attestation': False
}, indent=2) + '\n')
print(f'PASS independent probe matrix: {len(results)} cases plus default missing-command path. No hardware or OS service command executed.')
