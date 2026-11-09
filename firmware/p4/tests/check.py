#!/usr/bin/env python3
"""Run board logic checks with the real host core and admitted QR encoder."""
import argparse
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[3]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--components", type=Path, required=True)
p.add_argument("--rust-library", type=Path, required=True)
p.add_argument("--core-root", type=Path, default=root)
p.add_argument("--cc", default="cc")
a = p.parse_args()
out = root / ".cache/p4-check"
out.mkdir(parents=True, exist_ok=True)
main = root / "firmware/p4/main"
lvgl = a.components.resolve() / "lvgl__lvgl"
qr = out / "qrcodegen.c"
subprocess.run([sys.executable, str(main / "patch_secret_qr.py"), "--source",
                str(lvgl / "src/libs/qrcode/qrcodegen.c"), "--output", str(qr)], check=True)
subprocess.run([a.cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-DLV_CONF_SKIP",
                "-DLV_USE_QRCODE=1", "-I" + str(main), "-I" + str(lvgl),
                "-I" + str(a.core_root.resolve() / "core/nsealr-device/include"),
                str(Path(__file__).with_name("signer.c")), str(main / "photo_capture.c"),
                str(main / "secret_qr.c"), str(main / "board_rng_logic.c"), str(qr),
                str(a.rust_library.resolve()), "-o", str(out / "signer")], check=True)
subprocess.run([str(out / "signer")], check=True)
