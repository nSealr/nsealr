#!/usr/bin/env python3
"""Build/test/render native LVGL screens; optionally serve their framebuffer."""

import argparse
import html
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]
LVGL_COMMIT = "60b614c23c816ca5edc5f2840c9945eff7da0ad4"


def png_from_ppm(path):
    data = path.read_bytes()
    header, width_height, maximum, pixels = data.split(b"\n", 3)
    width, height = map(int, width_height.split())
    if header != b"P6" or maximum != b"255" or len(pixels) != width * height * 3:
        raise ValueError("Invalid native framebuffer")

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    rows = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def serve(binary, output, port):
    frame = output / "interactive.ppm"
    process = subprocess.Popen([str(binary), "--interactive", str(frame)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, text=True, bufsize=1)

    def ready():
        if process.stdout.readline().strip() != "ready":
            raise RuntimeError("Native preview stopped")

    ready()
    page = b"""<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
<title>nSealr native UI preview</title><style>
body{margin:24px;background:#080d12;color:#dce4ec;font:16px system-ui;text-align:center}
img{width:320px;height:480px;max-width:100%;border:1px solid #34404d;border-radius:18px;touch-action:none}
p{color:#a9b5c2}a{color:#d7f29a}</style>
<h2>nSealr native UI preview</h2><p>Actual LVGL pixels. Public examples only; no camera, keys or signing.</p>
<img id="screen" src="/frame.png" alt="Native device preview" draggable="false">
<p>Click buttons. Drag inside the text reader to scroll.</p><script>
const screen=document.getElementById('screen');let start,busy=false;
function point(e){let r=screen.getBoundingClientRect();return{x:Math.floor((e.clientX-r.left)*320/r.width),y:Math.floor((e.clientY-r.top)*480/r.height)}}
screen.onpointerdown=e=>{if(busy)return;start=point(e);screen.setPointerCapture(e.pointerId)};
screen.onpointerup=async e=>{if(!start||busy)return;let end=point(e),s=start;start=null;busy=true;
try{let drag=Math.abs(end.y-s.y)>12;await fetch('/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({x:s.x,y:s.y,end:drag?end.y:s.y})});screen.src='/frame.png?t='+Date.now()}finally{busy=false}};
screen.onpointercancel=()=>{start=null};</script>"""

    class Handler(BaseHTTPRequestHandler):
        def send(self, status, kind, body):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.send(200, "text/html; charset=utf-8", page)
            elif self.path.split("?", 1)[0] == "/frame.png":
                self.send(200, "image/png", png_from_ppm(frame))
            else:
                self.send(404, "text/plain", b"Not found")

        def do_POST(self):
            try:
                if self.path != "/input" or self.headers.get("Origin") not in (None, f"http://127.0.0.1:{port}"):
                    raise ValueError("Invalid origin or path")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size < 128:
                    raise ValueError("Invalid length")
                event = json.loads(self.rfile.read(size))
                x, y, end = (event[key] for key in ("x", "y", "end"))
                if not all(type(value) is int for value in (x, y, end)) or not (0 <= x < 320 and 0 <= y < 480 and 0 <= end < 480):
                    raise ValueError("Invalid coordinates")
                command = f"tap {x} {y}\n" if y == end else f"drag {x} {y} {end}\n"
                process.stdin.write(command)
                process.stdin.flush()
                ready()
                self.send(200, "application/json", b"{}")
            except (ValueError, KeyError, TypeError):
                self.send(400, "text/plain", b"Invalid input")

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Interactive native framebuffer: http://127.0.0.1:{port} (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        process.stdin.write("quit\n")
        process.stdin.flush()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lvgl", default=os.environ.get("LVGL_DIR"), help="Pinned LVGL checkout/component")
    parser.add_argument("--cmake", default=os.environ.get("CMAKE", shutil.which("cmake")))
    parser.add_argument("--serve", action="store_true", help="Use a browser only as framebuffer viewer/input")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not args.lvgl or not args.cmake:
        parser.error("Provide --lvgl (or LVGL_DIR) and CMake on PATH (or --cmake/CMAKE)")
    lvgl = Path(args.lvgl).resolve()
    metadata = lvgl / "idf_component.yml"
    if (lvgl / ".git").exists():
        pin = subprocess.check_output(["git", "-C", str(lvgl), "rev-parse", "HEAD"], text=True).strip()
        if pin != LVGL_COMMIT:
            parser.error(f"Expected LVGL {LVGL_COMMIT}, found {pin}")
    elif not metadata.exists() or f"commit_sha: {LVGL_COMMIT}" not in metadata.read_text():
        parser.error(f"LVGL component must declare the recorded source pin {LVGL_COMMIT}")
    build = ROOT / ".cache" / "ui-preview"
    output = build / "screens"
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        [args.cmake, "-S", str(ROOT / "firmware/preview"), "-B", str(build), f"-DLVGL_DIR={lvgl}", "-DCMAKE_BUILD_TYPE=Debug"],
        [args.cmake, "--build", str(build), "--parallel", str(min(os.cpu_count() or 2, 8))],
        [str(build / "ui-preview"), "--test"],
        [str(build / "ui-preview"), "--render", str(output)],
    ]
    with (build / "preview.log").open("w") as log:
        for command in commands:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                raise SystemExit(f"Preview failed; inspect {log.name}")
    for frame in output.glob("*.ppm"):
        frame.with_suffix(".png").write_bytes(png_from_ppm(frame))
    figures = "".join(f'<figure><img src="{path.name}" width="320" height="480"><figcaption>{html.escape(path.stem)}</figcaption></figure>'
                      for path in sorted(output.glob("*.png")) if path.name != "interactive.png")
    (output / "index.html").write_text('<!doctype html><meta charset="utf-8"><title>nSealr native screens</title>'
        '<style>body{background:#080d12;color:#dce4ec;font:16px system-ui}main{display:flex;flex-wrap:wrap;gap:24px}'
        'figure{margin:0}img{border:1px solid #34404d;border-radius:16px}figcaption{margin:12px 0 28px}</style>'
        '<h1>nSealr native screens</h1><p>Actual LVGL renders. Public examples only; no custody or signing.</p><main>' + figures + '</main>')
    print(f"Native navigation test passed; 14 screens rendered: {output / 'index.html'}")
    if args.serve:
        serve(build / "ui-preview", output, args.port)


if __name__ == "__main__":
    main()
