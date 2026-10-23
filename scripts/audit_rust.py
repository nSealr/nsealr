#!/usr/bin/env python3
"""Fetch current audit data separately from the unchanged vendored build graphs."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ('Cargo.toml', 'apps/desktop-simulator/Cargo.toml')


def audit(root=ROOT):
    channel = tomllib.loads((root / 'rust-toolchain.toml').read_text())['toolchain']['channel']
    # TMPDIR may itself be inside the workspace. Cargo config discovery for data
    # acquisition must start outside it so source replacement cannot hide index data.
    with tempfile.TemporaryDirectory(prefix='nsealr-rust-audit-', dir='/tmp') as temporary:
        data = Path(temporary)
        env = dict(os.environ, CARGO_HOME=str(data / 'cargo'),
                   CARGO_REGISTRIES_CRATES_IO_PROTOCOL='sparse', RUSTUP_TOOLCHAIN=channel)
        common = ['cargo', 'deny', '--locked', '--config', str(root / 'deny.toml')]
        # Fresh cache each time: fetch failures cannot be hidden by stale data.
        for index, manifest in enumerate(MANIFESTS):
            command = common + ['--manifest-path', str(root / manifest), 'fetch', 'index']
            if index == 0:
                command.append('db')
            print(shlex.join(command), flush=True)
            result = subprocess.run(command, cwd=data, env=env)
            if result.returncode:
                return result.returncode
        for manifest in MANIFESTS:
            command = common + ['--manifest-path', str(root / manifest), '--offline',
                                'check', '--deny', 'index-failure']
            print(shlex.join(command), flush=True)
            result = subprocess.run(command, cwd=root, env=env)
            if result.returncode:
                return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(audit())
