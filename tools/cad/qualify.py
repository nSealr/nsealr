#!/usr/bin/env python3
"""Bounded E01 harness: fresh installation, native fixture, read-only PCB MCP."""

import argparse
import json
import platform
from pathlib import Path
import subprocess
import tarfile
from common import HERE, digest, environment, now, require, run, write_json

PINS = HERE.parent.parent / "docs/restart/implementation/E01/inputs.json"


def prepare(args):
    base, out = args.runtime.resolve(), args.output.resolve()
    require(
        not base.exists() and not out.exists(), "Use fresh runtime and evidence paths"
    )
    require(
        not base.is_relative_to(out) and not out.is_relative_to(base),
        "Separate runtime/evidence paths",
    )
    display = args.display
    require(
        display.startswith(":") and display[1:].isdigit(), "Display must be :NUMBER"
    )
    require(
        not Path("/tmp/.X11-unix/X" + display[1:]).exists(), "Display already occupied"
    )
    require(
        not Path("/tmp/.X" + display[1:] + "-lock").exists(),
        "Display lock already exists",
    )
    source = args.tool_root.resolve()
    pins = json.loads(PINS.read_text())["toolchain"]
    for name, key in [
        ("kicad-10.0.7-x86_64-lite.AppImage.tar", "appimage_archive_sha256"),
        ("kicad-10.0.7-x86_64-lite.AppImage", "appimage_sha256"),
    ]:
        require(digest(source / name) == pins[key], "Tool input hash mismatch: " + name)
    base.mkdir(parents=True)
    out.mkdir(parents=True)
    for d in ["config/10.0", "cache", "documents", "runtime", "sources"]:
        (base / d).mkdir(parents=True)
    (base / "runtime").chmod(0o700)
    (out / "logs").mkdir()
    (out / "visuals").mkdir()
    # Re-extract this pinned image, avoiding trust in an unverified existing AppDir.
    image = source / "kicad-10.0.7-x86_64-lite.AppImage"
    start = now()
    p = subprocess.run(
        [str(image), "--appimage-extract"], cwd=base, capture_output=True, text=True
    )
    (out / "logs/extraction.stdout").write_text(p.stdout)
    (out / "logs/extraction.stderr").write_text(p.stderr)
    write_json(
        out / "extraction.json",
        {
            "argv": [str(image), "--appimage-extract"],
            "cwd": str(base),
            "start_utc": start,
            "end_utc": now(),
            "returncode": p.returncode,
        },
    )
    require(p.returncode == 0, "AppImage extraction failed")
    (base / "sysroot").symlink_to(source / "sysroot")
    config = base / "config/10.0"
    write_json(
        config / "kicad_common.json",
        {
            "meta": {"version": 6},
            "api": {"enable_server": True},
            "do_not_show_again": {
                "data_collection_prompt": True,
                "update_check_prompt": True,
            },
            "system": {"language": "Default", "working_dir": str(out)},
            "auto_backup": {"enabled": False},
        },
    )
    for app, version in [("pcbnew", 5), ("eeschema", 3)]:
        write_json(
            config / f"{app}.json",
            {
                "meta": {"version": version},
                "system": {"first_run_shown": False, "file_history": []},
            },
        )
    for lib in ["sym", "fp", "design-block"]:
        (config / f"{lib}-lib-table").write_text(
            "(" + lib.replace("-", "_") + "_lib_table (version 7))\n"
        )
    revision = pins["kipilot_commit"]
    archive = base / "sources/adapter.tar"
    archive.write_bytes(
        subprocess.check_output(
            ["git", "-C", str(source / "kipilot-mcp"), "archive", revision]
        )
    )
    require(
        digest(archive)
        == "5256d558127c685c4cd4ff6c4d24af141a028e2b51709bd617ec69061f0328c1",
        "Adapter archive hash",
    )
    (base / "adapter").mkdir()
    with tarfile.open(archive) as f:
        # Archive is a hash-pinned trusted source, extract only normal files/directories.
        require(
            all(x.isfile() or x.isdir() for x in f.getmembers()),
            "Unexpected archive entry",
        )
        f.extractall(base / "adapter", filter="data")
    selected = ["sysroot/usr/bin/Xvfb", "sysroot/usr/bin/xdotool"]
    helper_pins = {
        "sysroot/usr/bin/Xvfb": "16667b1eaafbe0b09527c2152e45f81b4b8e977012281062fc2fb2427afa66ce",
        "sysroot/usr/bin/xdotool": "2fcee924be08b180f4b1bea93eddedbaa8b0ea4b0886f6cbf77a113e8b8a130f",
    }
    require(
        all(digest(base / n) == sha for n, sha in helper_pins.items()),
        "Helper input hash mismatch",
    )
    libraries = [
        "symbols/Device.kicad_symdir/R.kicad_sym",
        "symbols/Connector_Generic.kicad_symdir/Conn_01x03.kicad_sym",
        "footprints/Resistor_SMD.pretty/R_0805_2012Metric.kicad_mod",
        "footprints/Connector_PinHeader_2.54mm.pretty/PinHeader_1x03_P2.54mm_Vertical.kicad_mod",
    ]
    config_data = {
        "runtime": str(base),
        "output": str(out),
        "display": display,
        "prepared_utc": now(),
        "host": platform.platform(),
        "pins": pins,
        "source_files": {
            str(p.relative_to(HERE)): digest(p)
            for p in HERE.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        },
        "helper_hashes": {n: digest(base / n) for n in selected},
        "selected_library_hashes": {
            n: digest(base / "squashfs-root/share/kicad" / n) for n in libraries
        },
        "source_commit": subprocess.check_output(
            ["git", "-C", str(HERE), "rev-parse", "HEAD"], text=True
        ).strip(),
        "source_status": subprocess.check_output(
            ["git", "-C", str(HERE), "status", "--short"], text=True
        ),
        "environment": {
            k: v
            for k, v in environment(base).items()
            if k
            in [
                "KICAD_CONFIG_HOME",
                "KICAD_DOCUMENTS_HOME",
                "XDG_CACHE_HOME",
                "XDG_RUNTIME_DIR",
                "TMPDIR",
                "LIBGL_ALWAYS_SOFTWARE",
                "KIPILOT_ENABLE_MUTATIONS",
            ]
        },
    }
    write_json(base / "session.json", config_data)
    write_json(out / "inputs.json", config_data)
    print("Prepared", base, out)


def validate_session(base, out):
    session = json.loads((base / "session.json").read_text())
    require(
        session["runtime"] == str(base) and session["output"] == str(out),
        "Runtime/evidence pairing mismatch",
    )
    current = {
        str(p.relative_to(HERE)): digest(p)
        for p in HERE.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    require(
        current == session["source_files"],
        "Harness changed since preparation; use a fresh attempt",
    )


def install(args):
    base, out = args.runtime.resolve(), args.output.resolve()
    validate_session(base, out)
    require(not (base / "venv").exists(), "Refuse existing venv")
    run("uv-version", ["uv", "--version"], out=out)
    env = environment(base)
    require(
        subprocess.check_output([str(args.python), "--version"], text=True).strip()
        == "Python 3.12.15",
        "Python pin",
    )
    run(
        "venv", ["uv", "venv", "--python", args.python, base / "venv"], env=env, out=out
    )
    run(
        "install",
        [
            "uv",
            "pip",
            "install",
            "--python",
            base / "venv/bin/python",
            "-r",
            HERE / "requirements.txt",
            base / "adapter",
        ],
        env=env,
        out=out,
    )
    run(
        "pip-check",
        ["uv", "pip", "check", "--python", base / "venv/bin/python"],
        env=env,
        out=out,
    )
    inventory = run(
        "freeze",
        ["uv", "pip", "freeze", "--python", base / "venv/bin/python"],
        env=env,
        out=out,
    )
    (out / "requirements-installed.txt").write_text(inventory)
    env.update(CAD_TOOLS_ROOT=str(base), CAD_QUAL_ROOT=str(out))
    run(
        "binding-probe",
        [base / "venv/bin/python", HERE / "probe_binding.py"],
        env=env,
        out=out,
    )


def execute(args):
    base, out = args.runtime.resolve(), args.output.resolve()
    validate_session(base, out)
    env = environment(base)
    env.update(CAD_TOOLS_ROOT=str(base), CAD_QUAL_ROOT=str(out))
    require(
        not (out / "fixtures").exists(),
        "Refuse existing run; preserve all previous attempts",
    )
    run(
        "campaign",
        [base / "venv/bin/python", HERE / "campaign.py"],
        env=env,
        out=out,
        timeout=240,
    )
    write_json(
        out / "manifest.json",
        {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        },
    )


def verify(args):
    out = args.output.resolve()
    manifest = json.loads((out / "manifest.json").read_text())
    for name, sha in manifest.items():
        require(digest(out / name) == sha, "Evidence hash mismatch: " + name)
    result = json.loads((out / "results.json").read_text())
    require(result["passed"], "Campaign did not pass")
    print("Verified", len(manifest), "artifact hashes; scope:", result["scope"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for name in ["prepare", "install", "run", "verify"]:
        q = sub.add_parser(name)
        q.add_argument("--output", type=Path, required=True)
        if name != "verify":
            q.add_argument("--runtime", type=Path, required=True)
        if name == "prepare":
            q.add_argument("--tool-root", type=Path, required=True)
            q.add_argument("--display", default=":96")
        if name == "install":
            q.add_argument("--python", type=Path, required=True)
    args = p.parse_args()
    {"prepare": prepare, "install": install, "run": execute, "verify": verify}[
        args.command
    ](args)
