#!/usr/bin/env python3
"""Run host vectors and target library builds without parent Cargo config."""
import datetime
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

with tempfile.TemporaryDirectory(prefix='nsealr-crypto-cargo-', dir='/tmp') as cargo_cwd:
    def run(name, command, overrides=None):
        command = list(command)
        overrides = dict(overrides or {})
        cwd = root
        if command[0] == 'cargo':
            # [workspace] isolates workspace membership, not Cargo's config lookup.
            # Cargo discovers repository config from cwd, not --manifest-path.
            cwd = pathlib.Path(cargo_cwd)
            command[3:3] = ['--manifest-path', str(root / 'Cargo.toml')]
            overrides['CARGO_TARGET_DIR'] = str(root / 'target')
        try:
            result = subprocess.run(command, cwd=cwd, env=os.environ | overrides,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output, code = result.stdout, result.returncode
        except OSError as error:
            output, code = str(error) + '\n', 127
        log = out / (name + '.log')
        log.write_text(output)
        rows.append(dict(name=name, command=command, cwd=str(cwd), env=overrides,
                         exit_code=code, log=log.name,
                         sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
        (out / 'runs.json').write_text(json.dumps({
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'project_dir': str(root), 'runs': rows,
        }, indent=2) + '\n')
        print(name, code, flush=True)

    run('fixtures', ['python3', 'fetch_vectors.py'])
    run('rustc', ['rustc', '+1.95.0', '-vV'])
    run('targets', ['rustup', 'target', 'list', '--installed', '--toolchain', '1.95.0'])
    run('clang', ['clang', '--version'])
    run('vectors', ['cargo', '+1.95.0', 'test', '--locked', '--test', 'vectors', '--', '--nocapture'])
    for backend in ['rustcrypto', 'libsecp']:
        run('features-' + backend, ['cargo', '+1.95.0', 'tree', '--locked',
                                   '--no-default-features', '--features', backend, '-e', 'features'])
        for target in ['thumbv8m.main-none-eabihf', 'riscv32imafc-unknown-none-elf']:
            env = {'CC_' + target.replace('-', '_').replace('.', '_'): 'clang'}
            run(backend + '-' + target, ['cargo', '+1.95.0', 'build', '--locked', '--release',
                                        '--lib', '--no-default-features', '--features', backend,
                                        '--target', target], env)

raise SystemExit(1 if any(row['exit_code'] != 0 for row in rows) else 0)
