#!/usr/bin/env python3
"""Read-only independent comparison of installed runtime to pinned upstream bytes."""

import argparse
import datetime
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

import kipy
import kipilot_mcp


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--adapter-git", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    require(not args.output.exists(), "Refuse existing evidence")
    pins = json.loads((args.repo / "docs/restart/implementation/E01/inputs.json").read_text())["toolchain"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    metadata_url = "https://pypi.org/pypi/kicad-python/0.8.0/json"
    metadata = json.load(urllib.request.urlopen(metadata_url, timeout=30))
    wheel = next(x for x in metadata["urls"] if x["filename"].endswith(".whl"))
    wheel_bytes = urllib.request.urlopen(wheel["url"], timeout=30).read()
    require(digest(wheel_bytes) == pins["kicad_python_wheel_sha256"], "Official wheel pin mismatch")
    matched_binding = {}
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as z:
        for name in z.namelist():
            if name.startswith("kipy/") and not name.endswith("/"):
                installed = Path(kipy.__file__).parent.parent / name
                require(installed.read_bytes() == z.read(name), "Modified binding: " + name)
                matched_binding[name] = digest(z.read(name))
    archive_argv = ["git", "-C", str(args.adapter_git), "archive", pins["kipilot_commit"]]
    archive = subprocess.check_output(archive_argv)
    require(digest(archive) == "5256d558127c685c4cd4ff6c4d24af141a028e2b51709bd617ec69061f0328c1",
            "Adapter archive pin mismatch")
    matched_adapter = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for item in tar.getmembers():
            if item.isfile():
                data = tar.extractfile(item).read()
                require((args.runtime / "adapter" / item.name).read_bytes() == data,
                        "Runtime adapter source mismatch: " + item.name)
                if item.name.startswith("src/kipilot_mcp/"):
                    relative = item.name.removeprefix("src/kipilot_mcp/")
                    require((Path(kipilot_mcp.__file__).parent / relative).read_bytes() == data,
                            "Installed adapter mismatch: " + item.name)
                    matched_adapter[relative] = digest(data)
    imports = []
    for module in ["kipy", "kipy.board", "kipy.board_types", "kipy.board_jobs",
                   "kipy.board_rules", "kipy.schematic", "kipy.schematic_types"]:
        argv = [sys.executable, "-B", "-c", "import importlib; importlib.import_module(" + repr(module) + ")"]
        run = subprocess.run(argv, env=env, capture_output=True, text=True)
        imports.append({"module": module, "argv": argv, "returncode": run.returncode,
                        "stdout": run.stdout, "stderr": run.stderr})
    require([x["returncode"] for x in imports] == [0, 0, 0, 1, 1, 1, 1],
            "Fresh import findings changed")
    pip_argv = ["uv", "pip", "check", "--python", sys.executable]
    check = subprocess.run(pip_argv, capture_output=True, text=True, env=env)
    require(check.returncode == 0, "Installed dependencies inconsistent")
    installed = {d.metadata["Name"].lower().replace("_", "-"): d.version
                 for d in importlib.metadata.distributions()}
    requirements = dict(line.split("==") for line in
                        (args.repo / "tools/cad/requirements.txt").read_text().splitlines())
    require(all(installed[name] == version for name, version in requirements.items()),
            "Requirement tuple mismatch")
    data = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewer": "/root/independent_cad_review",
        "command": [sys.executable, "-B", *sys.argv],
        "metadata_url": metadata_url,
        "wheel_url": wheel["url"], "wheel_sha256": digest(wheel_bytes),
        "binding_path": kipy.__file__, "binding_files": matched_binding,
        "adapter_archive_command": archive_argv, "adapter_archive_sha256": digest(archive),
        "adapter_path": kipilot_mcp.__file__, "adapter_package_files": matched_adapter,
        "fresh_imports": imports,
        "pip_check": {"argv": pip_argv, "returncode": check.returncode,
                      "stdout": check.stdout, "stderr": check.stderr},
        "installed_packages": installed, "pinned_requirements_matched": len(requirements),
        "passed": True,
        "limit": "Read-only comparison of the author's installed environment; clean installation provenance comes from the archived fresh installation and resolver logs."
    }
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps({"passed": True, "binding_files": len(matched_binding),
                      "adapter_files": len(matched_adapter), "requirements": len(requirements)}))


if __name__ == "__main__":
    main()
