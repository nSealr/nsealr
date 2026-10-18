#!/usr/bin/env python3
"""Create a cold, pinned Linux x86_64 software baseline; never reuse a destination."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Recorder:
    def __init__(self, directory: Path, env: dict[str, str]):
        self.directory = directory
        directory.mkdir(parents=True)
        self.env = env
        self.results: list[dict] = []

    def run(self, label: str, argv: list[str], cwd: Path, *, required: bool = True) -> int:
        log = self.directory / f'{len(self.results):02d}-{label}.log'
        result = dict(label=label, argv=argv, cwd=str(cwd), started=utc(), log=log.name)
        print(f'{label}: {argv!r}', flush=True)
        with log.open('w') as stream:
            stream.write(json.dumps(result) + '\n')
            stream.flush()
            code = subprocess.run(argv, cwd=cwd, env=self.env, stdout=stream, stderr=subprocess.STDOUT).returncode
        result.update(ended=utc(), exit_code=code, sha256=sha256(log))
        self.results.append(result)
        write_json(self.directory / 'commands.json', self.results)
        if required and code:
            raise RuntimeError(f'{label} exited {code}; see {log}')
        return code


def environment(destination: Path) -> dict[str, str]:
    """Keep HOME intact; give package managers independent config/cache directories."""
    t = destination / '.tools'
    env = {k: os.environ[k] for k in ('HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if k in os.environ}
    env.update({
        'PATH': os.pathsep.join(str(p) for p in (t/'bin', t/'python/bin', t/'node/bin', t/'cargo/bin')) + ':/usr/bin:/bin',
        'CI': 'true', 'TZ': 'UTC', 'CARGO_HOME': str(t/'cargo'), 'RUSTUP_HOME': str(t/'rustup'),
        'XDG_CACHE_HOME': str(t/'cache'), 'XDG_CONFIG_HOME': str(t/'config'), 'XDG_DATA_HOME': str(t/'data'),
        'npm_config_cache': str(t/'cache/npm'), 'npm_config_store_dir': str(t/'cache/pnpm'),
        'npm_config_userconfig': str(t/'npmrc'), 'npm_config_globalconfig': str(t/'global-npmrc'),
        'npm_config_loglevel': 'error', 'npm_config_update_notifier': 'false',
        'PYTHONUSERBASE': str(t/'python-user'), 'PIP_CONFIG_FILE': '/dev/null',
        'PIP_CACHE_DIR': str(t/'cache/pip'), 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'PIP_NO_INDEX': '1', 'PIP_FIND_LINKS': str(t/'wheels'),
        'PIP_CONSTRAINT': str(t/'constraints.txt'), 'TMPDIR': str(t/'tmp'),
    })
    return env


def download(entry: dict, path: Path) -> None:
    print(f'download {entry["url"]}', flush=True)
    with urllib.request.urlopen(entry['url'], timeout=60) as response, path.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    actual = sha256(path)
    if actual != entry['sha256']:
        raise ValueError(f'SHA256 mismatch for {path.name}: {actual}')


def extract(path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path) as archive:
        archive.extractall(destination, filter='data')


def fetch(recorder: Recorder, name: str, origin: str, commit: str, root: Path) -> None:
    path = root / name
    recorder.run(f'{name}-init', ['git', 'init', str(path)], root)
    recorder.run(f'{name}-fetch', ['git', 'fetch', '--depth=1', origin, commit], path)
    recorder.run(f'{name}-checkout', ['git', 'checkout', '--detach', 'FETCH_HEAD'], path)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=path, text=True).strip()
    if actual != commit or dirty:
        raise ValueError(f'{name}: expected clean checkout of {commit}, got {actual} {dirty}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='must not already exist')
    parser.add_argument('--mirrors', type=Path, help='authorized sibling Git repositories; transport only, pins still verified')
    parser.add_argument('--core-only', action='store_true', help='public core only; no private integration sources')
    args = parser.parse_args()
    root = args.destination.absolute()
    if root.exists() or root.is_symlink():
        parser.error(f'destination already exists: {root}')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or platform.libc_ver()[0] != 'glibc':
        parser.error('this baseline supports Linux x86_64/glibc only')
    for name in ('git', 'make', 'cc', 'rsync'):
        if not shutil.which(name, path='/usr/bin:/bin'):
            parser.error(f'host prerequisite missing: {name}')
    # A source checkout supplies both the bootstrap and the tested core candidate.
    candidate = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=SOURCE, text=True).strip():
        parser.error('commit tracked bootstrap/source changes before creating evidence')
    root.mkdir(parents=True)
    t = root / '.tools'
    for sub in ('bin', 'downloads', 'wheels', 'tmp', 'cache', 'config', 'data'):
        (t/sub).mkdir(parents=True)
    for name in ('npmrc', 'global-npmrc'):
        (t/name).touch()
    lock = json.loads((HERE/'inputs.json').read_text())
    write_json(root/'inputs.json', lock)
    env = environment(root)
    write_json(root/'environment.json', env)
    # Git source retrieval may use the caller's authorized credential setup;
    # execution uses the separate, minimal runtime environment recorded above.
    clones = Recorder(root/'evidence/clones', dict(os.environ))
    fetch(clones, 'firmware', str(SOURCE), candidate, root)
    inputs = {'nsealr': candidate}
    if not args.core_only:
        for name, entry in lock['repositories'].items():
            origin = str(args.mirrors/name) if args.mirrors else entry['url']
            fetch(clones, name, origin, entry['commit'], root)
            inputs[name] = entry['commit']
    write_json(root/'source-commits.json', inputs)
    recorder = Recorder(root/'evidence/bootstrap', env)
    for name, entry in lock['tools'].items():
        asset = t/'downloads'/entry['filename']
        download(entry, asset)
        if name == 'rustup':
            asset.chmod(0o755)
        else:
            extracted = t/'unpack'/name
            extract(asset, extracted)
            if name in ('python', 'node', 'pnpm'):
                children = list(extracted.iterdir())
                if len(children) != 1 or not children[0].is_dir():
                    raise ValueError(f'unexpected archive layout: {name}')
                shutil.move(str(children[0]), t/name)
            else:
                binaries = list(extracted.rglob(name))
                if len(binaries) != 1:
                    raise ValueError(f'unexpected binary archive: {name}')
                shutil.copy2(binaries[0], t/'bin'/name)
    (t/'bin/pnpm').symlink_to(t/'pnpm/bin/pnpm.cjs')
    constraints = []
    wheels = []
    for package in lock['python_packages']:
        wheel = t/'wheels'/package['filename']
        download(package, wheel)
        wheels.append(str(wheel))
        constraints.append(f'{package["name"]}=={package["version"]}')
    (t/'constraints.txt').write_text('\n'.join(constraints)+'\n')
    recorder.run('python-packages', ['python3', '-m', 'pip', 'install', '--no-deps', *wheels], root)
    recorder.run('python-dependency-check', ['python3', '-m', 'pip', 'check'], root)
    recorder.run('rustup-install', [str(t/'downloads'/lock['tools']['rustup']['filename']), '-y', '--no-modify-path', '--profile', 'minimal', '--default-toolchain', 'none'], root)
    recorder.run('rust-toolchain', ['rustup', 'toolchain', 'install', lock['rust_version'], '--profile', 'minimal', '--component', 'rustfmt,clippy,llvm-tools-preview', '--target', 'riscv32imafc-unknown-none-elf'], root)
    recorder.run('rust-default', ['rustup', 'default', lock['rust_version']], root)
    for name in ('companion', 'website'):
        if (root/name).exists():
            recorder.run(f'{name}-frozen-install', ['pnpm', 'install', '--frozen-lockfile'], root/name)
    for name in ('lab', 'raspberry', 'smartcard'):
        if (root/name).exists():
            recorder.run(f'{name}-setup', ['make', 'setup'], root/name)
    versions = {}
    for name, command in {'python':['python3','--version'], 'pip':['python3','-m','pip','--version'], 'node':['node','--version'], 'npm':['npm','--version'], 'pnpm':['pnpm','--version'], 'rust':['rustc','--version'], 'cargo':['cargo','--version'], 'rustup':['rustup','--version'], 'cargo-deny':['cargo','deny','--version'], 'cargo-llvm-cov':['cargo','llvm-cov','--version'], 'cc':['cc','--version'], 'make':['make','--version'], 'git':['git','--version'], 'libc':['ldd','--version']}.items():
        versions[name] = subprocess.check_output(command, cwd=root, env=env, text=True, stderr=subprocess.STDOUT).splitlines()[0]
    write_json(root/'evidence/environment-manifest.json', dict(candidate=candidate, created=utc(), versions=versions, kernel=platform.platform(), os_release=Path('/etc/os-release').read_text(), bootstrap_sha256=sha256(HERE/'bootstrap.py'), inputs_sha256=sha256(HERE/'inputs.json'), cold_destination=True, core_only=args.core_only))
    print(f'Bootstrap complete. Run: python3 {root}/firmware/tools/baseline/run.py {root}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
