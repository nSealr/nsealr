#!/usr/bin/env python3
"""Evaluate the frozen E01 formula before any native aux0x42 call."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[5]
source = ROOT / "docs/restart/implementation/K01/check_observed.py"
spec = importlib.util.spec_from_file_location("existing_k01_aux42", source)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
_, _, bip = checker.load_oracle()
expected = Path(__file__).with_name("expectations.json")
case = next(c for c in json.loads(expected.read_text())["cases"] if c["id"] == "E01")["positive_auxiliary_forwarding_control"]
signature = bip.schnorr_sign(bytes.fromhex(case["raw_event_id"]), bytes.fromhex(case["scalar_hex"]), bytes.fromhex(case["aux_hex"]))
assert signature.hex() != case["expected_signature_rule"]["must_differ_from_zero_aux_signature"]
assert bip.schnorr_verify(bytes.fromhex(case["raw_event_id"]), bytes.fromhex(case["pubkey"]), signature)
print(json.dumps({"role": "independent expected bytes BEFORE native E01 aux42 execution",
                  "unix_time": time.time(), "input": case, "expected_signature": signature.hex(),
                  "expectations_sha256": hashlib.sha256(expected.read_bytes()).hexdigest(),
                  "existing_loader_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                  "native_calls": 0}, indent=2))
