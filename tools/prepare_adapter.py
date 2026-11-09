#!/usr/bin/env python3
"""Fetch the pinned LVGL adapter, then apply the narrow public-header fix."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PIN = '5d75f3f0dc499d9ed4b69284a3741187c2b75a70'
ARCHIVE_SHA256 = 'a3701e3853f62803475cf7864e3c62e9f58d277175beab6c557aea1ad6ed74ae'
PATCHED_SHA256 = '4190a9f84693b2cc4a902f1b0f766f4f10e960736daadb8b7e3f6b036ddc6008'


def prepare(directory, archive=None):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / 'esp_lvgl_adapter'
    patched = target / 'src/display/bridge/v9/lvgl_ppa_accel_v9.c'
    if target.exists():
        if patched.is_file() and hashlib.sha256(patched.read_bytes()).hexdigest() == PATCHED_SHA256:
            return target
        raise SystemExit('Existing adapter differs; choose an empty component directory')
    archive = Path(archive).resolve() if archive else directory / 'adapter-source.tar.gz'
    if not archive.exists():
        urllib.request.urlretrieve(f'https://codeload.github.com/espressif/esp-iot-solution/tar.gz/{PIN}', archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise SystemExit('Adapter source archive hash differs')
    prefix = f'esp-iot-solution-{PIN}/components/display/tools/esp_lvgl_adapter/'
    with tarfile.open(archive, 'r:gz') as source:
        for member in source:
            if not member.name.startswith(prefix) or not member.isfile():
                continue
            relative = Path(member.name[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts:
                raise SystemExit('Unsafe source archive path')
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as src, path.open('wb') as dst:
                shutil.copyfileobj(src, dst)
    subprocess.run(['patch', '-p1', '-i', str(ROOT / 'firmware/p4/adapter.patch')], cwd=target, check=True)
    if hashlib.sha256(patched.read_bytes()).hexdigest() != PATCHED_SHA256:
        raise SystemExit('Adapter patch output differs')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=ROOT / '.cache/p4/components')
    parser.add_argument('--archive', type=Path, help='Optional already downloaded exact source archive')
    args = parser.parse_args()
    print(prepare(args.directory, args.archive))
