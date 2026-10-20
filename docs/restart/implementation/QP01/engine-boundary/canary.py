#!/usr/bin/env python3
"""One host-only public-fixture Python↔Rust canary, with simulated local UI."""
from __future__ import annotations

import ctypes as c
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[4]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault.crypto import event_id, verify_schnorr_signature  # noqa: E402
import secp256k1  # noqa: E402
import _cffi_backend  # noqa: E402

CAPACITY = 9216
BytePtr = c.POINTER(c.c_uint8)
Present = c.CFUNCTYPE(
    c.c_int32, c.c_uint32, c.c_uint32, c.c_uint32,
    BytePtr, c.c_size_t, BytePtr, c.c_size_t, BytePtr, c.c_size_t,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: canary.py <exact-host-cdylib.so> <public-result.json>")
    library_path = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2])
    inputs = json.loads((BASE / "inputs.json").read_text())
    expected = inputs["expected_row"]
    check(hashlib.sha256((BASE / "request.json").read_bytes()).hexdigest()
          == inputs["request_sha256"], "fixed request changed")
    library = c.CDLL(str(library_path))
    run = library.qp01_public_fixture_run
    run.argtypes = [Present, BytePtr, c.c_size_t, c.POINTER(c.c_size_t)]
    run.restype = c.c_int32
    result = {
        "role": "Executed host public-fixture ABI canary; no device/ARM/provider qualification",
        "python": sys.version,
        "machine": platform.machine(),
        "libc": platform.libc_ver(),
        "pointer_bytes": c.sizeof(c.c_void_p),
        "library": str(library_path),
        "library_sha256": hashlib.sha256(library_path.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256((BASE / "inputs.json").read_bytes()).hexdigest(),
        "independent_reference": {
            "path": "apps/pi/app/nsealr_vault/crypto.py",
            "sha256": hashlib.sha256((ROOT / "apps/pi/app/nsealr_vault/crypto.py").read_bytes()).hexdigest(),
            "secp256k1_version": importlib.metadata.version("secp256k1"),
            "secp256k1_module": secp256k1.__file__,
            "cffi_version": importlib.metadata.version("cffi"),
            "cffi_backend_sha256": hashlib.sha256(Path(_cffi_backend.__file__).read_bytes()).hexdigest(),
        },
        "cases": [],
        "completed": False,
    }

    def invoke(mode: str) -> dict:
        frames: list[dict] = []
        callback_errors: list[str] = []
        nested: list[dict] = []

        def present(kind, index, total, label, label_len, body, body_len, position, position_len):
            try:
                check(kind in (0, 1), "unknown presentation kind")
                check(0 < total <= 1024 and index < total, "invalid page coordinates")
                check(label_len <= 176 and body_len <= 264 and position_len <= 9,
                      "public frame exceeds core storage bounds")
                frame = {
                    "kind": "data" if kind == 0 else "decision",
                    "index": index, "total": total,
                    "label": c.string_at(label, label_len).decode("ascii"),
                    "body": c.string_at(body, body_len).decode("ascii"),
                    "position": c.string_at(position, position_len).decode("ascii"),
                    "byte_lengths": [label_len, body_len, position_len],
                    "lifetime": "Python copies public bytes inside this callback only",
                }
                frames.append(frame)
                if mode == "approve-complete" and len(frames) == 1:
                    check(kind == 0, "expected actual first Data frame")
                    # Same-thread synchronous reentry via the real FFI export.
                    nested_frames: list[int] = []
                    nested_ui = Present(lambda *args: nested_frames.append(1) or -1)
                    nested_output = (c.c_uint8 * CAPACITY)(*([0xA5] * CAPACITY))
                    nested_written = c.c_size_t(123)
                    status = run(nested_ui, nested_output, CAPACITY, c.byref(nested_written))
                    nested.append({"status": status, "written": nested_written.value,
                                   "all_zero": not any(nested_output),
                                   "ui_calls": len(nested_frames)})
                    check(status == -2 and nested_written.value == 0
                          and not any(nested_output) and not nested_frames, "reentry was not refused")
                if mode == "callback-exception":
                    raise RuntimeError("simulated public-fixture display failure")
                if mode == "reject-local":
                    check(kind == 0, "reject must apply to actual Data presentation")
                    frame["action"] = "reject"
                    return 2
                if mode == "approve-premature":
                    check(kind == 0, "premature approval must occur on Data")
                    frame["action"] = "approve-premature"
                    return 1
                frame["action"] = "next" if kind == 0 else "approve"
                return 0 if kind == 0 else 1
            except BaseException as error:
                # Never let ctypes swallow an exception and supply an
                # unspecified callback return. No exception crosses this ABI.
                callback_errors.append(repr(error))
                return -1

        # A strong local reference keeps the callback alive throughout Rust.
        callback = Present(present)
        output = (c.c_uint8 * CAPACITY)(*([0xA5] * CAPACITY))
        written = c.c_size_t(123)
        status = run(callback, output, CAPACITY, c.byref(written))
        check(written.value <= CAPACITY, "invalid returned extent")
        raw = bytes(output[:written.value])
        observation = {"id": mode, "status": status, "written": written.value,
                       "all_zero": not any(output), "frames": frames,
                       "callback_errors": callback_errors, "nested": nested,
                       "output_utf8": raw.decode("utf-8"),
                       "output_sha256": hashlib.sha256(raw).hexdigest()}
        result["cases"].append(observation)
        return observation

    try:
        positive = invoke("approve-complete")
        check(positive["status"] == 0 and positive["written"] > 0
              and not positive["callback_errors"], "positive signing failed")
        frames = positive["frames"]
        check([f["index"] for f in frames] == list(range(frames[0]["total"]))
              and all(f["total"] == len(frames) for f in frames)
              and frames[-1]["kind"] == "decision"
              and all(f["kind"] == "data" for f in frames[:-1]),
              "not every actual core frame reached Python in order")
        event = json.loads(positive["output_utf8"])
        template = json.loads(expected["template"])
        check(event == {**template, "pubkey": expected["pubkey"],
                        "id": expected["event_id"], "sig": expected["signature"]},
              "event fields/ID/signature differ from independent pre-runtime row")
        check(event_id(event) == expected["event_id"], "independent canonical ID mismatch")
        check(verify_schnorr_signature(event["pubkey"], event["id"], event["sig"]),
              "existing independent Python/libsecp verifier rejected Rust output")
        positive["independent_verification"] = True
        for mode, status in [("reject-local", -3), ("approve-premature", -4),
                             ("callback-exception", -5)]:
            observed = invoke(mode)
            check(observed["status"] == status and observed["written"] == 0
                  and observed["all_zero"] and len(observed["frames"]) == 1,
                  mode + " did not fail closed")
            check(bool(observed["callback_errors"]) == (mode == "callback-exception"),
                  "unexpected callback exception")
        recovery = invoke("recovery-same-public-fixture")
        check(recovery["status"] == 0 and recovery["output_utf8"] == positive["output_utf8"]
              and not recovery["callback_errors"], "reservation/lifetime failed to recover")
        result["completed"] = True
        print(json.dumps({"completed": True,
                          "cases": [{"id": x["id"], "status": x["status"],
                                     "frames": len(x["frames"]), "written": x["written"]}
                                    for x in result["cases"]],
                          "reentry_status": positive["nested"][0]["status"],
                          "single_output_independently_verified": True}))
        return 0
    except BaseException as error:
        result["failure"] = repr(error)
        raise
    finally:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
