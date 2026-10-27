#!/usr/bin/env python3
"""One finite negative: a wrong provider must be rejected before execution."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--uv", type=Path, required=True)
parser.add_argument("--sdk", type=Path, required=True)
parser.add_argument("--result-dir", type=Path, required=True)
args = parser.parse_args()
args.result_dir.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="p4-admission-negative-") as temporary:
    root = Path(temporary)
    marker = root / "EXECUTED"
    provider = root / "wrong-python"
    provider.write_text(
        "#!/usr/bin/python3\nfrom pathlib import Path\n"
        + "Path(" + repr(str(marker)) + ").write_text('EXECUTED')\n"
        + "print('Python 3.12.15')\n")
    provider.chmod(0o755)
    argv = ["/usr/bin/python3", str(args.repo.resolve() / "apps/p4/build.py"),
            "python", "--work-dir", str(root / "work"),
            "--base-python", str(provider), "--uv", str(args.uv.resolve()),
            "--sdk", str(args.sdk.resolve())]
    result = subprocess.run(argv, capture_output=True)
    (args.result_dir / "stdout.log").write_bytes(result.stdout)
    (args.result_dir / "stderr.log").write_bytes(result.stderr)
    record = {"argv": argv, "exit": result.returncode,
              "fixture_sha256": hashlib.sha256(provider.read_bytes()).hexdigest(),
              "source_head": subprocess.check_output(
                  ["git", "-C", str(args.repo), "rev-parse", "HEAD"], text=True).strip(),
              "provider_marker_exists": marker.exists(),
              "bootstrap_commands_started": (root / "work/logs").exists(),
              "expected": "Nonzero SHA admission refusal before the executable provider runs",
              "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
              "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}
    passed = (result.returncode != 0 and not marker.exists()
              and not record["bootstrap_commands_started"]
              and b"Unpinned base Python binary" in result.stderr)
    record["pass"] = passed
    (args.result_dir / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    if not passed:
        raise SystemExit(1)
