#!/usr/bin/env python3
"""Record actual combined S03 commands using the already pinned environment."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
ENVIRONMENT = Path("/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/environment.json")

def main():
    name, *command = sys.argv[1:]
    assert name and all(c.isalnum() or c in "-_" for c in name)
    if command and command[0] == "--":
        command = command[1:]
    assert command
    out = HERE / "commands" / name
    out.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(json.loads(ENVIRONMENT.read_bytes()))
    env["S03_OBSERVED"] = str(HERE / "observed-events.json")
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    source_status = subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    then = time.monotonic()
    with (out / "stdout.log").open("wb") as stdout, (out / "stderr.log").open("wb") as stderr:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
    files = []
    for path in sorted(out.glob("*.log")):
        data = path.read_bytes()
        files.append(dict(path=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    record = dict(command=command, cwd=str(ROOT), started_utc=started,
                  source_commit=source_commit,
                  initial_worktree_status_sha256=hashlib.sha256(source_status).hexdigest(),
                  elapsed_seconds=time.monotonic()-then, exit_code=result.returncode,
                  environment_source=str(ENVIRONMENT),
                  environment_sha256=hashlib.sha256(ENVIRONMENT.read_bytes()).hexdigest(),
                  additional_environment={"S03_OBSERVED": env["S03_OBSERVED"]}, files=files)
    (out / "command.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record))
    if result.returncode:
        print((out / "stdout.log").read_text(errors="replace")[-6000:])
        print((out / "stderr.log").read_text(errors="replace")[-6000:])
    raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
