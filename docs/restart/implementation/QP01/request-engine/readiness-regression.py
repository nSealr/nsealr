#!/usr/bin/env python3
"""No-request regression for the proposed finite child readiness boundary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["ready_without_request", "wrong_hash"], required=True)
    args = parser.parse_args()
    library = Path(os.environ["NSEALR_QP01_LIBRARY"]).resolve(strict=True)
    expected = os.environ["NSEALR_QP01_LIBRARY_SHA256"]
    assert hashlib.sha256(library.read_bytes()).hexdigest() == expected
    script = Path(__file__).with_name("exchange.py")
    env = dict(os.environ)
    if args.case == "wrong_hash":
        env["NSEALR_QP01_LIBRARY_SHA256"] = "0" * 64
    read_fd, write_fd = os.pipe()
    argv = [sys.executable, "-B", str(script), "--ready-fd", str(write_fd)]
    child = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             pass_fds=(write_fd,))
    os.close(write_fd)
    ready = bytearray()
    safety_kill = False
    started = time.monotonic()
    selector = selectors.DefaultSelector()
    selector.register(read_fd, selectors.EVENT_READ)
    try:
        while True:
            remaining = 5 - (time.monotonic() - started)
            if remaining <= 0 or not selector.select(remaining):
                safety_kill = True
                child.kill()
                break
            chunk = os.read(read_fd, 2)
            if not chunk:
                break
            ready.extend(chunk)
            if len(ready) > 1:
                safety_kill = True
                child.kill()
                break
    finally:
        selector.close()
        os.close(read_fd)
        # No frame is ever sent. EOF refuses the idle child and collects it.
        try:
            stdout, stderr = child.communicate(b"", timeout=max(.001, 5 - (time.monotonic() - started)))
        except subprocess.TimeoutExpired:
            safety_kill = True
            child.kill()
            stdout, stderr = child.communicate()
    observation = {
        "case": args.case, "argv": argv, "child_pid": child.pid,
        "library": str(library), "library_sha256": expected,
        "exchange_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "ready_hex": bytes(ready).hex(), "stdin_bytes_sent": 0,
        "stdout_hex": stdout.hex(), "stderr": stderr.decode(),
        "exit_code": child.returncode, "collected": child.returncode is not None,
        "safety_kill": safety_kill, "elapsed_seconds": time.monotonic() - started,
        "scope": "Actual child initialization/EOF only; no native request, signing or client campaign",
    }
    print(json.dumps(observation, indent=2), flush=True)
    assert not safety_kill, "readiness/idle child did not settle inside unchanged5s safety"
    assert stdout == b"", "no request may produce a response"
    assert child.returncode != 0, "EOF without a request must refuse"
    if args.case == "ready_without_request":
        assert bytes(ready) == b"R", "missing exact library-ready handshake before any request"
    else:
        assert ready == b"", "wrong library hash must never become ready"
        assert b"SHA256 mismatch" in stderr, "must exercise the real library check, not another failure"


if __name__ == "__main__":
    main()
