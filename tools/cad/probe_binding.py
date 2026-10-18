"""Probe the installed official wheel and retain unsupported fresh-process imports."""

import importlib.metadata
import io
import json
import pathlib
import subprocess
import sys
import urllib.request
import zipfile
import hashlib
from common import output, require, write_json
import kipy
from kipy.kicad_api_version import KICAD_API_VERSION

rows = []
for module in [
    "kipy",
    "kipy.board",
    "kipy.board_types",
    "kipy.board_jobs",
    "kipy.board_rules",
    "kipy.schematic",
    "kipy.schematic_types",
]:
    p = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import importlib; importlib.import_module({module!r})",
        ],
        capture_output=True,
        text=True,
    )
    rows.append(
        {
            "module": module,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    )
require(
    all(x["returncode"] == 0 for x in rows[:3]), "Required PCB binding imports failed"
)
metadata_url = "https://pypi.org/pypi/kicad-python/0.8.0/json"
metadata = json.load(urllib.request.urlopen(metadata_url, timeout=30))
wheel = next(x for x in metadata["urls"] if x["filename"].endswith(".whl"))
data = urllib.request.urlopen(wheel["url"], timeout=30).read()
sha = hashlib.sha256(data).hexdigest()
require(
    sha == "3d43af4aa2515e88829a9d30e408b8ce89537431a802104ee2a50392f0deaa16",
    "Official wheel changed",
)
checked = []
with zipfile.ZipFile(io.BytesIO(data)) as z:
    for name in z.namelist():
        if name.startswith("kipy/") and not name.endswith("/"):
            require(
                (pathlib.Path(kipy.__file__).parent.parent / name).read_bytes()
                == z.read(name),
                "Installed wheel mismatch: " + name,
            )
            checked.append(name)
write_json(
    output() / "binding-probe.json",
    {
        "imports": rows,
        "api_version": KICAD_API_VERSION,
        "python": sys.version,
        "wheel_url": wheel["url"],
        "wheel_sha256": sha,
        "matched_package_files": checked,
        "packages": {
            n: importlib.metadata.version(n)
            for n in ["kicad-python", "protobuf", "mcp", "kipilot-mcp", "sexpdata"]
        },
    },
)
