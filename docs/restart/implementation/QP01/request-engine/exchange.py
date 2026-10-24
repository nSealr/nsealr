#!/usr/bin/env python3
"""Finite host fixture exchange/provisioner; no device route or camera input."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "crates/nsealr-pi-engine-fixture/src/lib.rs"
CLIENT = Path(__file__).with_name("client-exchange.ts")
COMPOSITION = ROOT / "docs/restart/implementation/QH01/manual-port/python-rgb-composition"
LIFECYCLE_CASES = ("scan_null_after_settlement", "scan_pending_timeout_after_settlement",
                   "fixture_cancel_B3_verified_preG")
ENGINE_CASES = ("fixture_request_engine", "fixture_request_engine_loaded_sha_refusal")
NATIVE_PREPARATION_SCOPE = "QH01_NATIVE_LEAF_PREPARATION_V1"


def source_binding(paths=None):
    if paths is None:
        paths = ["Cargo.toml", "Cargo.lock", "crates/nsealr-pi-engine-fixture/Cargo.toml",
                 "crates/nsealr-pi-engine-fixture/src/lib.rs"]
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


def build_artifact(command, source, manifest, name, kind, paths=None):
    """Bind the actual Cargo artifact to this producer's unchanged inputs."""
    before = source_binding(paths)
    result = subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True)
    artifacts = []
    for line in result.stdout.splitlines():
        record = json.loads(line)
        if record.get("reason") != "compiler-artifact":
            continue
        target = record["target"]
        if target["name"] != name or kind not in target["kind"]:
            continue
        if (Path(target["src_path"]).resolve() != source or
                Path(record["manifest_path"]).resolve() != manifest):
            raise RuntimeError("Cargo artifact has wrong source or manifest")
        if kind == "bin":
            executable = record.get("executable")
            if executable is None or executable not in record["filenames"]:
                raise RuntimeError("Cargo artifact has no bound executable")
            artifacts.append(Path(executable).resolve(strict=True))
        else:
            artifacts.extend(Path(p).resolve(strict=True) for p in record["filenames"] if p.endswith(".so"))
    if len(artifacts) != 1 or source_binding(paths) != before:
        raise RuntimeError("missing/ambiguous artifact or changed build input")
    artifact = artifacts[0]
    if not artifact.is_file():
        raise RuntimeError("Cargo artifact is not a regular file")
    if kind == "bin" and not os.access(artifact, os.X_OK):
        raise RuntimeError("Cargo worker artifact is not executable")
    binary = artifact.read_bytes()
    if binary[:4] != b"\x7fELF":
        raise RuntimeError("host experiment requires the actual ELF")
    return artifact, hashlib.sha256(binary).hexdigest(), before


def provision():
    command = ["cargo", "build", "-p", "nsealr-pi-engine-fixture", "--locked", "--offline",
               "--release", "--message-format=json"]
    library, digest, before = build_artifact(
        command, SOURCE, ROOT / "crates/nsealr-pi-engine-fixture/Cargo.toml",
        "nsealr_pi_engine_fixture", "cdylib")
    print(json.dumps({"role": "public fixture build, not hardware qualification", "argv": command,
                      "source": before, "library": str(library), "sha256": digest,
                      "CARGO_TARGET_DIR": os.environ.get("CARGO_TARGET_DIR")}), flush=True)
    paths = ["apps/pi/qr-worker/" + p for p in ("Cargo.toml", "Cargo.lock", "src/main.rs", "rust-toolchain.toml")]
    paths += [".cargo/config.toml", "rust-toolchain.toml"]
    command = ["cargo", "build", "--manifest-path", "apps/pi/qr-worker/Cargo.toml",
               "--locked", "--offline", "--release", "--message-format=json"]
    worker, worker_digest, worker_before = build_artifact(
        command, ROOT / "apps/pi/qr-worker/src/main.rs", ROOT / "apps/pi/qr-worker/Cargo.toml",
        "nsealr-qr-worker", "bin", paths)
    print(json.dumps({"role": "public RGB worker build, initialization v2, not hardware qualification",
                      "argv": command, "source": worker_before, "worker": str(worker), "sha256": worker_digest,
                      "CARGO_TARGET_DIR": os.environ.get("CARGO_TARGET_DIR")}), flush=True)
    return {"NSEALR_QP01_LIBRARY": str(library), "NSEALR_QP01_LIBRARY_SHA256": digest,
            "NSEALR_QP01_QR_WORKER": str(worker), "NSEALR_QP01_QR_WORKER_SHA256": worker_digest}


def ci(directory):
    pi = (ROOT / directory).resolve()
    if pi != ROOT / "apps/pi":
        raise ValueError("--ci requires the actual apps/pi directory")
    env = dict(os.environ, **provision())
    # The entire existing setup/test/lint/audit/docs runs ONCE, after provisioning.
    subprocess.run(["make", "-C", str(pi), "ci"], cwd=ROOT, env=env, check=True)
    env["NSEALR_QP01_PYTHON"] = str(pi / ".venv/bin/python")
    subprocess.run(["node", "--import", "tsx/esm", str(CLIENT)], cwd=ROOT, env=env, check=True)
    subprocess.run(["node", "--import", "tsx/esm", str(CLIENT), "--first-owner-gate"],
                   cwd=ROOT, env=env, check=True)
    subprocess.run([str(pi / ".venv/bin/python"), "-B", str(COMPOSITION / "test_attention_reporting.py"), "-v"],
                   cwd=ROOT, env=env, check=True)
    composition_ci(pi, env)
    for case in LIFECYCLE_CASES:
        composition_ci(pi, env, case)
    preparation = prepare_native_leaf(env)
    for case in ENGINE_CASES:
        composition_ci(pi, env, case, preparation)
    shutil.rmtree(Path(preparation["output_dir"]).parent)  # Both actual cases collected and traced.


def prepare_native_leaf(env):
    """One joined existing TSC recipe, shared by the two finite native cases."""
    temporary = Path(tempfile.mkdtemp(prefix="nsealr-qh01-native-leaf-"))
    output = temporary / "module"
    context = output / "package.json"
    source = "docs/restart/implementation/QP01/request-engine/native-leaf.ts"
    command = ["pnpm", "exec", "tsc", "--ignoreConfig", "--target", "ES2022", "--module", "NodeNext",
               "--moduleResolution", "NodeNext", "--strict", "--esModuleInterop", "--forceConsistentCasingInFileNames",
               "--skipLibCheck", "--resolveJsonModule", "--types", "node", "--declaration",
               "--rootDir", "docs/restart/implementation/QP01/request-engine", "--outDir", str(output), source]
    try:
        print("\n" + json.dumps({"qh01_request_engine_build_command": {"v": 1, "argv": command,
                              "cwd": str(ROOT), "output_dir": str(output)}}), flush=True)
        output.mkdir()
        context.write_text('{"type":"module"}\n')
        before = source_binding([source, "package.json", "pnpm-lock.yaml"])
        compiler = (ROOT / "node_modules/typescript/bin/tsc").resolve(strict=True)
        version = json.loads((ROOT / "node_modules/typescript/package.json").read_text())["version"]
        if version != "6.0.3" or json.loads((ROOT / "package.json").read_text()).get("type") != "module":
            raise RuntimeError("required pinned TSC6.0.3/current-root ESM context missing")
        compiler_sha = hashlib.sha256(compiler.read_bytes()).hexdigest()
        result = subprocess.run(command, cwd=ROOT, env=env, check=True)
        record = {"v": 1, "scope": NATIVE_PREPARATION_SCOPE,
                  "role": "current_checkout_joined_compiler_artifacts_only", "argv": command, "cwd": str(ROOT),
                  "compiler": {"path": str(compiler), "version": version, "sha256": compiler_sha},
                  "status": result.returncode, "source_before": before, "source_after": source_binding(list(before)),
                  "output_dir": str(output), "receipt": str(temporary / "preparation.json"),
                  "outputs": {name: {"path": str(output / name), "bytes": (output / name).stat().st_size,
                              "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest()}
                              for name in ("native-leaf.js", "native-leaf.d.ts")},
                  "package_context": {"path": str(context), "bytes": context.stat().st_size,
                              "sha256": hashlib.sha256(context.read_bytes()).hexdigest(), "value": {"type": "module"}}}
        if type(result.returncode) is not int or result.returncode != 0 or record["source_after"] != before:
            raise RuntimeError("native helper compilation/input changed")
        if hashlib.sha256(compiler.read_bytes()).hexdigest() != compiler_sha or json.loads(context.read_text()) != {"type": "module"}:
            raise RuntimeError("native compiler/package context changed")
        Path(record["receipt"]).write_text(json.dumps(record, indent=2) + "\n")
        print("\n" + json.dumps({"qh01_request_engine_build": record}), flush=True)
        return record
    except BaseException as error:
        try:
            print("\n" + json.dumps({"qh01_request_engine_build_failure": {"v": 1, "output_retained": str(temporary),
                    "error": {"type": type(error).__name__, "message": str(error)},
                    "returncode": getattr(error, "returncode", None)}}), flush=True)
        except BaseException:
            pass
        raise


def composition_record(output, env, command, before, generated, case="positive", preparation=None):
    """Expose the existing harness's actual receipts; do not invent a verdict."""
    load = lambda name: json.loads((output / name).read_text())
    rows = load("node-records.json")
    frame = lambda raw: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    cancelled = case == "fixture_cancel_B3_verified_preG"
    record = {"v": 1, "id": "bridge_rgb_kind1_basic", "scope": "QH01_HOST_COMPOSITION_CI_V1",
            "role": "public_host_fixture_synthetic_client_clock", "argv": command,
            "source_before": before, "source_after": source_binding(list(before)),
            "generated_before": generated, "generated_after": source_binding(list(generated)),
            "worker_initialization": {"path": env["NSEALR_QP01_QR_WORKER"], "sha256": env["NSEALR_QP01_QR_WORKER_SHA256"]},
            "actual": load("result.json"), "collection": load("collection.json"),
            "frames": {"presented": frame(rows[0]["frame"].encode("ascii")),
                       "decoded": None if cancelled else frame((output / "decoded.envelope").read_bytes()),
                       "scanned": frame(rows[1]["frame"].encode("ascii")) if case == "positive" else None},
            "decoded_request": None if cancelled else load("decoded.json"), "node_records": rows,
            "expected_public_key": json.loads((ROOT / "protocols/contracts/v1/examples/response-get-public-key.json").read_text())["result"]["public_key"],
            "service_response": load("service-response.json"),
            "native_response_base64": base64.b64encode((output / "native-response.bin").read_bytes()).decode("ascii"),
            "limits": ["synthetic client100; real O8/shared4; native C5000 unchanged",
                       "no timeout/cancel seam, camera/physical, key or production-provider qualification"]}
    if case in ENGINE_CASES:
        refused = case == ENGINE_CASES[1]
        receipt = json.loads(Path(preparation["receipt"]).read_text())
        after = {"source": source_binding(list(preparation["source_before"])),
                 "compiler_sha256": hashlib.sha256(Path(preparation["compiler"]["path"]).read_bytes()).hexdigest(),
                 "outputs": {name: {"path": item["path"], "bytes": Path(item["path"]).stat().st_size,
                             "sha256": hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()}
                             for name, item in preparation["outputs"].items()},
                 "package_context_sha256": hashlib.sha256(Path(preparation["package_context"]["path"]).read_bytes()).hexdigest()}
        if (receipt != preparation or after["source"] != preparation["source_before"] or
                after["source"] != preparation["source_after"] or after["compiler_sha256"] != preparation["compiler"]["sha256"] or
                after["outputs"] != preparation["outputs"] or after["package_context_sha256"] != preparation["package_context"]["sha256"]):
            raise RuntimeError("native preparation changed during case")
        record.update({"id": case, "scope": "QH01_RGB_ENGINE_CI_V1", "native_preparation": receipt,
                       "native_preparation_after": after,
                       "native_initialization": load("engine-initialization.json"),
                       "native_settlement": load("engine-settlement.json")["qh01_engine_leaf_settlement"],
                       "native_outcome": load("engine-outcome.json")["qh01_engine_leaf_outcome"],
                       "native_observation": None if refused else load("engine-observation.json")["qh01_engine_leaf_observation"],
                       "native_refusal": load("engine-refusal.json")["qh01_engine_leaf_refusal"] if refused else None,
                       "limits": ["synthetic client100; real O8/shared4/C5000 unchanged; no hard C collection bound",
                                  "public fixture/zeroaux/synthetic review; no combined deadline-expiry or clientAbort proof",
                                  "no camera/physical, key or production-provider qualification"]})
        record["frames"]["scanned"] = None if refused else frame(rows[1]["frame"].encode("ascii"))
        record["frames"]["engine_response"] = None if refused else frame((output / "engine-response.envelope").read_bytes())
    elif case != "positive":
        lifecycle = rows[-1]["lifecycle"]
        record.update({"id": case, "scope": "QH01_HOST_LIFECYCLE_CI_V1",
                       "cancel_refusals": load("cancel-refusals.json") if cancelled else None,
                       "limits": ["synthetic client100; real O8/shared4; native C5000 unchanged",
                                  "fixed trusted fixture/port cancel; no external clientAbort API or decoder counter",
                                  "no camera/physical, key or production-provider qualification"]})
        record["frames"]["late_scan"] = ({"bytes": lifecycle["late_scan_bytes"],
                                            "sha256": lifecycle["late_scan_sha256"]}
                                           if case == "scan_pending_timeout_after_settlement" else None)
    return record


def composition_ci(pi, env, case="positive", preparation=None):
    if case not in ("positive", *LIFECYCLE_CASES, *ENGINE_CASES):
        raise ValueError("unknown trusted composition case")
    engine_case = case in ENGINE_CASES
    if engine_case and preparation is None:
        raise ValueError("engine case requires actual current-root native preparation")
    packages = ["client", "core", "policy", "protocol", "qr", "transport", "framing"]
    source_paths = ["tools/bridge/build_packages.mjs", "pnpm-lock.yaml", "apps/bridge/service/package.json",
                    str(Path(__file__).relative_to(ROOT)), "apps/pi/tests/test_engine_adapter.py",
                    "apps/pi/app/nsealr_vault/qr_owner_adapter.py", "apps/pi/app/nsealr_vault/qr_worker.py"]
    source_paths += [str((COMPOSITION / name).relative_to(ROOT)) for name in
                     ("run-composition.py", "bridge-child.mjs", "test_attention_reporting.py")]
    source_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "apps/bridge/service/src").glob("*.ts")) if not p.name.endswith(".test.ts")]
    source_paths += [str(p.relative_to(ROOT)) for name in packages for p in sorted((ROOT / f"packages/{name}/src").rglob("*.ts"))]
    if engine_case:
        source_paths += ["docs/restart/implementation/QP01/request-engine/" + name for name in
                         ("native-leaf.ts", "client-exchange.ts", "expectations.json")]
        source_paths += ["apps/pi/app/nsealr_vault/engine_adapter.py", "Cargo.toml", "Cargo.lock",
                         "crates/nsealr-pi-engine-fixture/Cargo.toml", "crates/nsealr-pi-engine-fixture/src/lib.rs"]
    before = source_binding(source_paths)
    generated_paths = [str(p.relative_to(ROOT)) for directory in [ROOT / f"packages/{name}/dist" for name in packages] + [ROOT / "apps/bridge/service/dist"]
                       for p in sorted(directory.rglob("*")) if p.is_file() and p.suffix in (".js", ".ts")]
    generated = source_binding(generated_paths)
    node = shutil.which("node", path=env.get("PATH"))
    if node is None:
        raise RuntimeError("required current Node executable missing")
    temporary = Path(tempfile.mkdtemp(prefix="nsealr-qh01-composition-"))
    output = temporary / "case"
    command = [str(pi / ".venv/bin/python"), "-B", str(COMPOSITION / "run-composition.py"),
               "--output", str(output), "--worker", env["NSEALR_QP01_QR_WORKER"],
               "--sha256", env["NSEALR_QP01_QR_WORKER_SHA256"], "--node", str(Path(node).resolve()),
               "--bridge", str(ROOT / "apps/bridge/service/dist"), "--reuse", str(ROOT)]
    namespace = "qh01_request_engine" if engine_case else "qh01_composition" if case == "positive" else "qh01_lifecycle"
    identity = {} if case == "positive" else {"id": case}
    if engine_case:
        module = preparation["outputs"]["native-leaf.js"]
        command += ["--case", "fixture_request_engine", "--engine-library", env["NSEALR_QP01_LIBRARY"],
                    "--engine-sha256", env["NSEALR_QP01_LIBRARY_SHA256"], "--engine-module", module["path"],
                    "--engine-module-sha256", module["sha256"], "--engine-preparation", preparation["receipt"]]
        if case == ENGINE_CASES[1]:
            command.append("--engine-refusal")
    elif case != "positive":
        command += ["--case", case]
    print("\n" + json.dumps({namespace + "_command": {"v": 1, **identity, "argv": command, "output": str(output)}}), flush=True)
    try:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        record = composition_record(output, env, command, before, generated, case, preparation)
        if record["source_before"] != record["source_after"] or record["generated_before"] != record["generated_after"]:
            raise RuntimeError("composition source or compiled input changed")
        print("\n" + json.dumps({namespace + "_case": record}), flush=True)
    except BaseException:
        try:
            print("\n" + json.dumps({namespace + "_failure": {"v": 1, **identity, "output_retained": str(output),
                  **({"preparation_retained": preparation["output_dir"]} if engine_case else {})}}), flush=True)
        except BaseException:
            pass
        raise
    shutil.rmtree(temporary)  # Only after the existing harness's known collection.


def exchange(settlement_fd=None, ready_fd=None):
    if ready_fd is not None and (ready_fd < 3 or ready_fd == settlement_fd):
        raise ValueError("readiness requires its own inherited control descriptor")
    sys.path.insert(0, str(ROOT / "apps/pi/app"))
    from nsealr_vault.engine_adapter import EngineAdapter, MonotonicSeconds
    adapter = EngineAdapter(os.environ["NSEALR_QP01_LIBRARY"], os.environ["NSEALR_QP01_LIBRARY_SHA256"])
    if ready_fd is not None:
        # Initialization only: no stdin read, native request, review or signing.
        # The parent starts its actual client operation after this exact token.
        if os.write(ready_fd, b"R") != 1:
            raise RuntimeError("readiness token was not written")
        os.close(ready_fd)
    incoming = sys.stdin.buffer.read(948)
    pages = []

    def present(page):
        # Synthetic conformance display/action only: all actual borrowed bytes
        # are recorded. This is not human/physical consent or a qualified UI.
        pages.append({"kind": page.kind, "index": page.index, "total": page.total,
                      "label": page.label.decode("ascii"), "body": page.body.decode("ascii"),
                      "position": page.position.decode("ascii")})
        return 1 if page.kind == 1 else 0

    output = adapter.run_request_frame(incoming, present, MonotonicSeconds(), lambda: bytes(32), lambda: False)
    print(json.dumps({"library": str(adapter.library_path), "sha256": adapter.library_sha256,
                      "input_bytes": len(incoming), "input_sha256": hashlib.sha256(incoming).hexdigest(),
                      "output_bytes": len(output), "output_sha256": hashlib.sha256(output).hexdigest(),
                      "synthetic_complete_review": pages}), file=sys.stderr, flush=True)
    if settlement_fd is not None:
        # Finite harness-only process-settlement control AFTER native return.
        # It models a child that cannot settle merely because the client timed
        # out; this neither pauses the native clock nor grants extra authority.
        if os.read(settlement_fd, 1) != b"R":
            raise RuntimeError("controlled child was not explicitly released")
    sys.stdout.buffer.write(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci", metavar="DIRECTORY")
    parser.add_argument("--settlement-fd", type=int, choices=[3])
    parser.add_argument("--ready-fd", type=int)
    args = parser.parse_args()
    if args.ci:
        ci(args.ci)
    else:
        exchange(args.settlement_fd, args.ready_fd)


if __name__ == "__main__":
    main()
