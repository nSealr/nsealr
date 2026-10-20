#!/usr/bin/env python3
"""Four public fixture images + blank: native HOST feasibility, never optical qualification."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig
import time
import traceback

HERE = Path(__file__).resolve().parent
REPO = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=HERE, text=True).strip())

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_record(path: Path) -> dict:
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': digest(data)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite a previous observation.
    report = {'scope': 'Host-native fixed public images only', 'cases': [], 'blank': None,
              'source': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
              'python': sys.version, 'executable': file_record(Path(sys.executable).resolve()),
              'SOABI': sysconfig.get_config_var('SOABI'), 'host': platform.platform(),
              'machine': platform.machine(), 'libc': platform.libc_ver(),
              'physical_camera_ARM_native_hostile_bounds_qualified': False}
    try:
        for binding in json.loads((HERE / 'source-bindings.json').read_text())['bindings']:
            assert digest((REPO / binding['path']).read_bytes()) == binding['sha256'], binding['path']
        sys.path.insert(0, str(REPO / 'apps/pi/app'))
        from nsealr_vault.seed_signer_hardware import (
            PythonQrcodeMatrixRenderer, PillowSt7789DrawTarget,
            SeedSignerSt7789ResponseQrDisplay, PyzbarQrDecoder)
        from PIL import Image
        import qrcode
        import pyzbar.pyzbar
        report['packages'] = {name: importlib.metadata.version(name) for name in
                              ('qrcode', 'Pillow', 'pyzbar', 'mnemonic', 'secp256k1', 'cffi', 'pycparser')}
        report['default_ECC'] = qrcode.QRCode(border=0).error_correction
        assert report['default_ECC'] == qrcode.constants.ERROR_CORRECT_M
        decoder = PyzbarQrDecoder()  # Real default pyzbar loader and native ZBar.
        frozen = json.loads((HERE / 'expectations.json').read_text())
        for case in frozen['cases']:
            row = {'name': case['name']}
            report['cases'].append(row)
            envelope = (REPO / case['envelope_path']).read_bytes()
            assert digest(envelope) == case['envelope_sha256']
            row['envelope_bytes'] = len(envelope)
            row['expected_envelope_sha256'] = digest(envelope)
            actual_renderer = PythonQrcodeMatrixRenderer()
            matrices, frames = [], []
            render_ns = []
            class MeasuredRenderer:
                def render_qr_matrix(self, text):
                    start = time.perf_counter_ns()
                    matrix = actual_renderer.render_qr_matrix(text)
                    render_ns.append(time.perf_counter_ns() - start)
                    matrices.append(matrix)
                    return matrix
            target = PillowSt7789DrawTarget(present_image=lambda image: frames.append(image.copy()))
            display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=MeasuredRenderer())
            start = time.perf_counter_ns()
            display.emit_response_qr(envelope.decode('ascii'))
            row['render_and_present_ns'] = time.perf_counter_ns() - start
            row['matrix_render_ns'] = render_ns
            assert len(matrices) == len(frames) == 1
            matrix, image = matrices[0], frames[0]
            n = len(matrix); modules = n + 8; scale = 240 // modules
            assert scale > 0  # Existing fit criterion only, not a new2px threshold.
            size = modules * scale; origin = (240 - size) // 2
            row.update({'matrix_modules': n, 'qr_version': (n - 17) // 4,
                        'quiet_zone_modules_per_side': 4, 'quiet_zone_pixels_per_side': 4 * scale,
                        'total_modules': modules, 'module_size_pixels': scale,
                        'qr_square_pixels': size, 'origin_xy': [origin, origin],
                        'framebuffer_mode': image.mode, 'framebuffer_size': list(image.size),
                        'matrix_sha256': digest(bytes(int(v) for line in matrix for v in line))})
            assert image.mode == 'RGB' and image.size == (240, 240)
            # Independently apply the frozen integer geometry to every pixel.
            for y in range(240):
                for x in range(240):
                    expected = (0, 0, 0)
                    if origin <= x < origin + size and origin <= y < origin + size:
                        expected = (255, 255, 255)
                        mx, my = (x - origin) // scale - 4, (y - origin) // scale - 4
                        if 0 <= mx < n and 0 <= my < n and matrix[my][mx]: expected = (0, 0, 0)
                    assert image.getpixel((x, y)) == expected, (case['name'], x, y)
            rgb, png = out / (case['name'] + '.rgb'), out / (case['name'] + '.png')
            rgb.write_bytes(image.tobytes()); image.save(png, format='PNG')
            row['framebuffer'] = file_record(rgb); row['PNG'] = file_record(png)
            start = time.perf_counter_ns(); decoded = decoder.decode_qr(image)
            row['framebuffer_native_decode_ns'] = time.perf_counter_ns() - start
            assert isinstance(decoded, bytes), type(decoded).__name__
            (out / (case['name'] + '.decoded')).write_bytes(decoded)
            row['decoded_envelope_sha256'] = digest(decoded)
            assert decoded == envelope  # Exact ORIGINAL bytes; no parse/reserialize.
            with Image.open(png) as reopened:
                reopened.load()
                assert reopened.mode == 'RGB' and reopened.size == (240, 240)
                assert reopened.tobytes() == rgb.read_bytes()
                start = time.perf_counter_ns(); png_decoded = decoder.decode_qr(reopened)
                row['PNG_native_decode_ns'] = time.perf_counter_ns() - start
                assert isinstance(png_decoded, bytes) and png_decoded == envelope
            row['status'] = 'PASS_FIXED_HOST_IMAGE_BYTES'
        blank = Image.new('RGB', (240, 240), 'white')
        blank.save(out / 'blank.png', format='PNG'); (out / 'blank.rgb').write_bytes(blank.tobytes())
        start = time.perf_counter_ns(); result = decoder.decode_qr(blank)
        report['blank'] = {'native_decode_ns': time.perf_counter_ns() - start,
                           'decoded': result, 'PNG': file_record(out / 'blank.png'),
                           'framebuffer': file_record(out / 'blank.rgb')}
        assert result is None
        report['status'] = 'PASS_HOST_FIXED_IMAGE_FEASIBILITY_ONLY'
    except Exception as exc:
        report['status'] = 'BLOCKED_NATIVE_OR_GEOMETRY'
        report['blocker'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
        print(traceback.format_exc(), file=sys.stderr)
    finally:
        loaded = sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                         if '.so' in line and line.split()[-1].startswith('/')})
        report['loaded_ELF_files'] = [file_record(Path(p)) for p in loaded if Path(p).is_file()]
        (out / 'observations.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status': report['status'], 'cases': len(report['cases']), 'blank': report['blank'] is not None}))
    return 0 if report['status'] == 'PASS_HOST_FIXED_IMAGE_FEASIBILITY_ONLY' else 1

if __name__ == '__main__':
    raise SystemExit(main())
