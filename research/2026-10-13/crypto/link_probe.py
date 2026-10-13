#!/usr/bin/env python3
"""Link exercised crypto; require the expected ABI failure and inspect each ELF."""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parent
out = pathlib.Path(os.environ.get('NSEALR_SPIKE_EVIDENCE_ROOT', str(root / 'evidence'))).resolve()
out.mkdir(parents=True, exist_ok=True)
rows = []


def execute(command, cwd, overrides=None):
    try:
        result = subprocess.run(command, cwd=cwd, env=os.environ | (overrides or {}),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return result.returncode, result.stdout
    except OSError as error:
        return 127, str(error) + '\n'


with tempfile.TemporaryDirectory(prefix='nsealr-crypto-cargo-', dir='/tmp') as cargo_cwd:
    for backend in ['rustcrypto', 'libsecp']:
        cases = [('thumbv8m.main-none-eabihf', False), ('riscv32imafc-unknown-none-elf', False)]
        if backend == 'libsecp':
            cases.append(('riscv32imafc-unknown-none-elf', True))
        for target, fix_abi in cases:
            name = 'link-' + backend + '-' + target + ('-corrected-abi' if fix_abi else '')
            command = ['cargo', '+1.95.0', 'rustc', '--manifest-path', str(root / 'Cargo.toml'),
                       '--locked', '--release', '--bin', 'freestanding', '--no-default-features',
                       '--features', backend + ',link-probe', '--target', target,
                       '--', '-C', 'link-arg=--entry=_start']
            overrides = {'CC_' + target.replace('-', '_').replace('.', '_'): 'clang',
                         'CARGO_TARGET_DIR': str(root / 'target')}
            if fix_abi:
                overrides['CFLAGS_riscv32imafc_unknown_none_elf'] = '-mabi=ilp32f -march=rv32imafc'
            code, output = execute(command, cargo_cwd, overrides)
            log = out / (name + '.log')
            log.write_text(output)
            row = dict(name=name, command=command, cwd=cargo_cwd, env=overrides, exit_code=code,
                       log=log.name, sha256=hashlib.sha256(log.read_bytes()).hexdigest())
            if code == 0:
                binary = root / 'target' / target / 'release/freestanding'
                dst = out / (name + '.elf')
                dst.write_bytes(binary.read_bytes())
                row['elf_sha256'] = hashlib.sha256(dst.read_bytes()).hexdigest()
                for tool, args in [('readelf', ['-hSW']), ('nm', ['-u']), ('size', ['-A'])]:
                    inspection = [tool, *args, str(binary)]
                    inspect_code, inspect_output = execute(inspection, root)
                    inspect_log = out / (name + '-' + tool + '.log')
                    inspect_log.write_text(inspect_output)
                    row[tool] = dict(command=inspection, exit_code=inspect_code, log=inspect_log.name,
                                     sha256=hashlib.sha256(inspect_log.read_bytes()).hexdigest())
                    if tool == 'nm':
                        row[tool]['no_unresolved_symbols'] = inspect_code == 0 and not inspect_output.strip()
            rows.append(row)
            (out / 'link-runs.json').write_text(json.dumps(rows, indent=2) + '\n')
            print(name, code, flush=True)

failures = []
for row in rows:
    expected_failure = row['name'] == 'link-libsecp-riscv32imafc-unknown-none-elf'
    if expected_failure:
        if row['exit_code'] == 0 or 'different floating-point ABI' not in (out / row['log']).read_text():
            failures.append(row['name'] + ': expected ABI failure was not observed')
    elif row['exit_code'] != 0:
        failures.append(row['name'] + ': link failed')
    if row['exit_code'] == 0:
        for tool in ['readelf', 'nm', 'size']:
            if row[tool]['exit_code'] != 0:
                failures.append(row['name'] + ': ' + tool + ' inspection failed')
        if not row['nm']['no_unresolved_symbols']:
            failures.append(row['name'] + ': unresolved symbols or failed nm inspection')
(out / 'link-verdict.json').write_text(json.dumps({'passed': not failures, 'failures': failures}, indent=2) + '\n')
for failure in failures:
    print(failure, flush=True)
raise SystemExit(1 if failures else 0)
