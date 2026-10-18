#!/usr/bin/env python3
"""Independent exact-candidate audit and native-clean placement fault control.

Run with the recorded Python environment (sexpdata is the only extra import).
Uses a fresh runtime and evidence output; does not change author artifacts.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(test, message):
    if not test:
        raise RuntimeError(message)


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    repo, runtime, out = args.repo.resolve(), args.runtime.resolve(), args.output.resolve()
    require(not runtime.exists() and not out.exists(), "Fresh paths required")
    runtime.mkdir(parents=True)
    out.mkdir(parents=True)
    (out / "logs").mkdir()
    author = repo / "docs/restart/implementation/E01/evidence"
    result = {"started_utc": utc(), "reviewer": "/root/independent_cad_review"}
    command_log = []
    env = dict(os.environ)
    for key in ["KICAD_API_TOKEN", "KICAD_API_SOCKET", "DISPLAY", "PYTHONPATH"]:
        env.pop(key, None)
    for key, directory in {
        "KICAD_CONFIG_HOME": "config",
        "KICAD_DOCUMENTS_HOME": "documents",
        "XDG_CACHE_HOME": "cache",
        "XDG_RUNTIME_DIR": "runtime",
        "TMPDIR": "runtime",
    }.items():
        (runtime / directory).mkdir(exist_ok=True)
        env[key] = str(runtime / directory)
    (runtime / "runtime").chmod(0o700)
    env.update(PYTHONDONTWRITEBYTECODE="1", KIPILOT_ENABLE_MUTATIONS="false")

    def run(name, argv, expected=0, cwd=repo):
        argv = list(map(str, argv))
        started = utc()
        p = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=90)
        (out / "logs" / (name + ".stdout")).write_bytes(p.stdout)
        (out / "logs" / (name + ".stderr")).write_bytes(p.stderr)
        command_log.append({"name": name, "argv": argv, "cwd": str(cwd),
                            "started_utc": started, "finished_utc": utc(),
                            "returncode": p.returncode, "expected": expected})
        write(out / "commands.json", command_log)
        require(p.returncode == expected, name + ": unexpected exit " + str(p.returncode))
        return p.stdout.decode()

    candidate = run("candidate", ["git", "rev-parse", "HEAD"]).strip()
    require(candidate == "89943be5a52ce43058d446da640b5fb550a124d3", "Candidate mismatch")
    result["candidate"] = candidate
    result["implementation_commit"] = "1524af02c70ab5e74bd7089d9055b2568e7a2250"
    result["source_tree"] = run("source-tree", ["git", "rev-parse", "HEAD:tools/cad"]).strip()
    require(run("source-diff", ["git", "diff", result["implementation_commit"], candidate,
                               "--", "tools/cad"]) == "", "Source changed since execution")
    result["review_interpreter"] = {"executable": sys.executable, "version": sys.version,
                                    "sha256": sha(sys.executable)}
    result["archive_manifests"] = {}
    for attempt in ["attempt-01", "attempt-02"]:
        path = author / (attempt + "-archive-manifest.json")
        manifest = json.loads(path.read_text())
        for relative, digest in manifest.items():
            require(sha(author / attempt / relative) == digest, "Archive mismatch: " + relative)
        result["archive_manifests"][attempt] = {"sha256": sha(path), "entries": len(manifest)}
    evidence = author / "attempt-02"
    source_inputs = json.loads((evidence / "inputs.json").read_text())
    for relative, digest in source_inputs["source_files"].items():
        require(sha(repo / "tools/cad" / relative) == digest, "Source snapshot mismatch: " + relative)
    result["source_snapshot_files_matched"] = len(source_inputs["source_files"])
    spec = json.loads((repo / "docs/restart/implementation/reviews/E01-spec.json").read_text())
    for item in spec["files"]:
        require(sha(repo / item["path"]) == item["sha256"], "Spec reviewed file changed")
    result["spec_files_matched"] = len(spec["files"])
    result["export_source_links"] = {}
    for variant in ["fixed", "roundtrip"]:
        links = json.loads((evidence / "exports" / variant / "source-hashes.json").read_text())
        for name, digest in links.items():
            require(sha(evidence / "fixtures" / variant / name) == digest, "Export source mismatch")
        result["export_source_links"][variant] = links

    sys.path.insert(0, str(repo / "tools/cad"))
    from checks import checks, circuit
    import sexpdata
    result["review_parser"] = {"file": sexpdata.__file__, "sha256": sha(sexpdata.__file__)}
    result["recomputed_author_checks"] = checks(evidence)
    result["native_source_copper_layers"] = {}
    for variant in ["fixed", "roundtrip"]:
        tree = sexpdata.loads((evidence / "fixtures" / variant / "canary.kicad_pcb").read_text())
        layers = next(x for x in tree if isinstance(x, list) and str(x[0]) == "layers")
        copper = [x[1] for x in layers[1:] if x[2] == sexpdata.Symbol("signal")]
        require(copper == ["F.Cu", "B.Cu"], "Unexpected copper layer stack")
        result["native_source_copper_layers"][variant] = copper

    pins = json.loads((repo / "docs/restart/implementation/E01/inputs.json").read_text())["toolchain"]
    require(sha(args.image) == pins["appimage_sha256"], "Native image pin mismatch")
    result["native_image_sha256"] = sha(args.image)
    run("extract-native-image", [args.image, "--appimage-extract"], cwd=runtime)
    app = runtime / "squashfs-root/AppRun"
    result["native_version"] = run("native-version", [app, "kicad-cli", "version"]).strip()
    require(result["native_version"] == "10.0.7", "Wrong native version")

    for variant in ["fixed", "drift"]:
        fixture = out / "fixtures" / variant
        shutil.copytree(evidence / "fixtures/fixed", fixture)
        export = out / "exports" / variant
        export.mkdir(parents=True)
        if variant == "drift":
            board = fixture / "canary.kicad_pcb"
            text = board.read_text()
            require(text.count("(at 35 32.54)") == 1, "Ambiguous R1 position")
            board.write_text(text.replace("(at 35 32.54)", "(at 35.1 32.54)"))
        native_sources = {p.name: sha(p) for p in fixture.iterdir()
                          if p.suffix in [".kicad_sch", ".kicad_pcb", ".kicad_pro"]}
        run(variant + "-erc", [app, "kicad-cli", "sch", "erc", "--format", "json",
            "--severity-all", "--exit-code-violations", "-o", export / "erc.json",
            fixture / "canary.kicad_sch"])
        run(variant + "-drc", [app, "kicad-cli", "pcb", "drc", "--format", "json",
            "--severity-all", "--all-track-errors", "--schematic-parity",
            "--exit-code-violations", "-o", export / "drc.json", fixture / "canary.kicad_pcb"])
        run(variant + "-netlist", [app, "kicad-cli", "sch", "export", "netlist",
            "--format", "kicadxml", "-o", export / "netlist.xml", fixture / "canary.kicad_sch"])
        drc = json.loads((export / "drc.json").read_text())
        require(not drc["violations"] and not drc["unconnected_items"] and not drc["schematic_parity"],
                "Native-clean control failed")
        write(export / "source-hashes.json", native_sources)
    result["native_fixed_oracle"] = circuit(out, "fixed")
    try:
        circuit(out, "drift")
    except RuntimeError as exc:
        require(str(exc) == "Footprint pose mismatch", "Wrong rejection reason")
        result["adversarial_experiment"] = {
            "mutation": "R1 x position changed from 35.0 to 35.1 mm; all other source bytes preserved",
            "erc_exit": 0, "drc_exit": 0, "unconnected": 0, "schematic_parity": 0,
            "oracle": "rejected", "message": str(exc),
            "interpretation": "Native ERC/DRC alone accepts this electrically connected position drift; the separately specified placement oracle rejects it."
        }
    else:
        raise RuntimeError("Placement fault escaped the contract oracle")
    result["finished_utc"] = utc()
    result["passed"] = True
    write(out / "results.json", result)
    write(out / "manifest.json", {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()})
    print(json.dumps({"passed": True, "archive_manifests": result["archive_manifests"],
                      "adversarial_experiment": result["adversarial_experiment"]}, indent=2))


if __name__ == "__main__":
    main()
