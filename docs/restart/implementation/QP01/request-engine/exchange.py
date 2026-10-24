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


def composition_record(output, env, command, before, generated):
    """Expose the existing harness's actual receipts; do not invent a verdict."""
    load = lambda name: json.loads((output / name).read_text())
    rows = load("node-records.json")
    frame = lambda raw: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"v": 1, "id": "bridge_rgb_kind1_basic", "scope": "QH01_HOST_COMPOSITION_CI_V1",
            "role": "public_host_fixture_synthetic_client_clock", "argv": command,
            "source_before": before, "source_after": source_binding(list(before)),
            "generated_before": generated, "generated_after": source_binding(list(generated)),
            "worker_initialization": {"path": env["NSEALR_QP01_QR_WORKER"], "sha256": env["NSEALR_QP01_QR_WORKER_SHA256"]},
            "actual": load("result.json"), "collection": load("collection.json"),
            "frames": {"presented": frame(rows[0]["frame"].encode("ascii")),
                       "decoded": frame((output / "decoded.envelope").read_bytes()),
                       "scanned": frame(rows[1]["frame"].encode("ascii"))},
            "decoded_request": load("decoded.json"), "node_records": rows,
            "expected_public_key": json.loads((ROOT / "protocols/contracts/v1/examples/response-get-public-key.json").read_text())["result"]["public_key"],
            "service_response": load("service-response.json"),
            "native_response_base64": base64.b64encode((output / "native-response.bin").read_bytes()).decode("ascii"),
            "limits": ["synthetic client100; real O8/shared4; native C5000 unchanged",
                       "no timeout/cancel seam, camera/physical, key or production-provider qualification"]}


def composition_ci(pi, env):
    packages = ["client", "core", "policy", "protocol", "qr", "transport", "framing"]
    source_paths = ["tools/bridge/build_packages.mjs", "pnpm-lock.yaml", "apps/bridge/service/package.json",
                    str(Path(__file__).relative_to(ROOT)), "apps/pi/tests/test_engine_adapter.py",
                    "apps/pi/app/nsealr_vault/qr_owner_adapter.py", "apps/pi/app/nsealr_vault/qr_worker.py"]
    source_paths += [str((COMPOSITION / name).relative_to(ROOT)) for name in
                     ("run-composition.py", "bridge-child.mjs", "test_attention_reporting.py")]
    source_paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "apps/bridge/service/src").glob("*.ts")) if not p.name.endswith(".test.ts")]
    source_paths += [str(p.relative_to(ROOT)) for name in packages for p in sorted((ROOT / f"packages/{name}/src").rglob("*.ts"))]
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
    print("\n" + json.dumps({"qh01_composition_command": {"v": 1, "argv": command, "output": str(output)}}), flush=True)
    try:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        record = composition_record(output, env, command, before, generated)
        if record["source_before"] != record["source_after"] or record["generated_before"] != record["generated_after"]:
            raise RuntimeError("composition source or compiled input changed")
        print("\n" + json.dumps({"qh01_composition_case": record}), flush=True)
    except BaseException:
        try:
            print("\n" + json.dumps({"qh01_composition_failure": {"v": 1, "output_retained": str(output)}}), flush=True)
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
