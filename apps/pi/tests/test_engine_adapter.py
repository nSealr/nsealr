"""Public-fixture request/owner tests: a real provisioned native library is required."""
import base64
import copy
import json
import os
from pathlib import Path
import sys
import ctypes as C
import importlib.util
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault.engine_adapter import EngineAdapter, EngineError


def vector(name):
    original = json.loads((ROOT / "protocols/contracts/v1/vectors/events" / name).read_text())
    amended = json.loads((ROOT / "docs/restart/implementation/QP01/request-engine/expectations.json").read_text())
    expected = next(row for row in amended["independent_positive_expectations"] if row["source_path"].endswith("/" + name))
    # Only the reviewed, independently calculated nonce-dependent signature
    # changes in this in-memory expectation. Original files remain untouched.
    assert {k: v for k, v in original["signed_event"].items() if k != "sig"} == {
        k: v for k, v in expected["expected_complete_event"].items() if k != "sig"}
    assert original["signature"] == expected["legacy_verification_reference"]["signature"]
    original["signature"] = expected["expected_signature"]
    original["signed_event"]["sig"] = expected["expected_signature"]
    original["response"]["result"]["event"]["sig"] = expected["expected_signature"]
    return original


def frame(raw):
    return b"nsealr1:" + base64.urlsafe_b64encode(raw).rstrip(b"=")


def compact(value):
    return json.dumps(value, separators=(",", ":")).encode()


def response(value):
    return json.loads(base64.urlsafe_b64decode(value[8:] + b"=" * (-len(value[8:]) % 4)))


class EngineAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = EngineAdapter(os.environ["NSEALR_QP01_LIBRARY"],
                                    os.environ["NSEALR_QP01_LIBRARY_SHA256"])

    def execute(self, request_frame, **overrides):
        self.pages = []
        self.aux_calls = 0

        def present(page):
            self.pages.append(page)
            return 1 if page.kind == 1 else 0

        def auxiliary():
            self.aux_calls += 1
            return bytes(32)

        args = dict(local_io=present, monotonic_clock=lambda: 0,
                    auxiliary=auxiliary, cancel=lambda: False)
        args.update(overrides)
        return self.adapter.run_request_frame(request_frame, **args)

    def assert_review(self, request_id):
        self.assertGreater(len(self.pages), 1)
        self.assertEqual([p.index for p in self.pages], list(range(len(self.pages))))
        self.assertTrue(all(p.total == len(self.pages) for p in self.pages))
        self.assertEqual([p.kind for p in self.pages], [0] * (len(self.pages)-1) + [1])
        for p in self.pages:
            self.assertIsInstance(p.label, bytes)
            self.assertIsInstance(p.body, bytes)
            self.assertEqual(p.position, f"{p.index+1}/{p.total}".encode())
        self.assertIn(request_id.encode(), b"".join(p.body for p in self.pages))
        self.assertEqual(self.aux_calls, 1)

    def test_P02_P03_real_basic_and_tagged_requests(self):
        for name in ["kind-1-basic.json", "kind-1-tags.json"]:
            with self.subTest(vector=name):
                data = vector(name)
                actual = response(self.execute(frame(compact(data["request"]))))
                self.assertEqual(actual, data["response"])
                self.assert_review(data["request"]["request_id"])
                # Fixed ASCII source vectors: newline is only the core's visual
                # wrapping. Check every incoming signed field at its own role,
                # including the empty tag field and the signed suffix.
                shown = {p.label.replace(b"\n", b"").split(b" / fragment")[0].decode():
                         json.loads(p.body.replace(b"\n", b"")) for p in self.pages}
                expected = data["signed_event"]
                self.assertEqual(shown["Selected actual signing identity"], expected["pubkey"])
                self.assertEqual(shown["Canonical event ID"], expected["id"])
                self.assertEqual(shown["Signed kind"], str(expected["kind"]))
                self.assertEqual(shown["Signed created_at (untrusted timestamp)"], str(expected["created_at"]))
                self.assertEqual(shown["Signed tag count"], str(len(expected["tags"])))
                self.assertEqual(shown["Signed content (plain text)"], expected["content"])
                for tag_index, tag in enumerate(expected["tags"]):
                    for field_index, field in enumerate(tag):
                        matching = [value for role, value in shown.items()
                                    if role.startswith(f"Signed tag {tag_index} field {field_index}:")]
                        self.assertEqual(matching, [field])

    def test_P04_changed_correlation_is_fresh(self):
        data = vector("kind-1-basic.json")
        changed = copy.deepcopy(data["request"])
        changed["request_id"] = "qp01-distinct-correlation"
        actual = response(self.execute(frame(compact(changed))))
        self.assertEqual(actual["request_id"], changed["request_id"])
        self.assertEqual(actual["result"]["event"], data["signed_event"])
        self.assert_review(changed["request_id"])

    def test_P05_B01_B02_original_raw_bytes_and_outer_bound(self):
        data = vector("kind-1-basic.json")
        raw = b" \n" + compact(dict(reversed(list(data["request"].items()))))
        self.assertEqual(response(self.execute(frame(raw))), data["response"])
        padded = compact(data["request"]).ljust(704, b" ")
        self.assertEqual(len(frame(padded)), 947)
        self.assertEqual(response(self.execute(frame(padded))), data["response"])
        for invalid in [b"", frame(padded + b" "), bytes(948)]:
            with self.subTest(length=len(invalid)), self.assertRaises(EngineError) as caught:
                self.execute(invalid)
            self.assertEqual(caught.exception.status, -1)
            self.assertEqual(self.pages, [])
            self.assertEqual(self.aux_calls, 0)

    def test_A01_A02_no_premature_or_rejected_authority(self):
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        for action, status in [(1, -9), (2, -5), (99, -6), (4, -9)]:
            with self.subTest(action=action), self.assertRaises(EngineError) as caught:
                self.execute(raw, local_io=lambda page: action)
            self.assertEqual(caught.exception.status, status)
            self.assertEqual(self.aux_calls, 0)

    def test_E01_no_auxiliary_fallback(self):
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        for count in [0, 1, 31, 33]:
            calls = []
            def aux():
                calls.append(count)
                return bytes(count)
            with self.subTest(count=count), self.assertRaises(EngineError) as caught:
                self.execute(raw, auxiliary=aux)
            self.assertEqual(caught.exception.status, -8)
            self.assertEqual(calls, [count])
        self.assertEqual(response(self.execute(raw)), vector("kind-1-basic.json")["response"])

    def test_P01_original_identity_and_no_signing(self):
        data = json.loads((ROOT / "protocols/contracts/v1/examples/request-get-public-key.json").read_text())
        expected = json.loads((ROOT / "protocols/contracts/v1/examples/response-get-public-key.json").read_text())
        result = self.execute(frame(compact(data)))
        self.assertEqual(len(result), 198)
        self.assertEqual(response(result), expected)
        self.assertEqual(self.pages, [])
        self.assertEqual(self.aux_calls, 0)

    def test_E01_positive_aux42_is_forwarded_exactly_once(self):
        expected = json.loads((ROOT / "docs/restart/implementation/QP01/request-engine/evidence/aux42-expected-01/stdout.log").read_text())
        data = vector("kind-1-basic.json")
        calls = []
        def auxiliary():
            value = bytes.fromhex(expected["input"]["aux_hex"])
            calls.append(value)
            return value
        actual = response(self.execute(frame(compact(data["request"])), auxiliary=auxiliary))
        self.assertEqual(calls, [bytes([0x42]) * 32])
        self.assertNotEqual(actual["result"]["event"]["sig"], data["signature"])
        data["response"]["result"]["event"]["sig"] = expected["expected_signature"]
        self.assertEqual(actual, data["response"])
        self.assertEqual([p.index for p in self.pages], list(range(len(self.pages))))
        self.assertEqual(self.pages[-1].kind, 1)

    def test_B03_strict_original_bytes_no_normalization(self):
        raw = compact(vector("kind-1-basic.json")["request"])
        malformed = [b"bad", b"nsealr1:e30=", b"nsealr1:e31", frame(b"{\xff}"),
                     frame(raw.replace(b'"version":2', b'"version":2,"version":2')),
                     frame(raw.replace(b'"version":2', b'"version":2,"\\u0076ersion":2')),
                     frame(raw.replace(b'"version":2', b'"version":2e0')),
                     frame(raw.replace(b'"version":2', b'"version":-0')),
                     frame(raw.replace(b'"version":2', b'"version":2.0')),
                     frame(raw[:-1] + b',"approved":true}')]
        for value in malformed:
            with self.subTest(raw=value), self.assertRaises(EngineError) as caught:
                self.execute(value)
            self.assertEqual(caught.exception.status, -3)
            self.assertEqual((self.pages, self.aux_calls), ([], 0))

    def test_B04_unsupported_workflows(self):
        raw = vector("kind-1-basic.json")["request"]
        for kind in [4, 13, 14, 1059, 10050, 22242, 65535]:
            changed = copy.deepcopy(raw)
            changed["params"]["event_template"]["kind"] = kind
            with self.subTest(kind=kind), self.assertRaises(EngineError) as caught:
                self.execute(frame(compact(changed)))
            self.assertEqual(caught.exception.status, -4)
            self.assertEqual((self.pages, self.aux_calls), ([], 0))
        with self.assertRaises(EngineError) as caught:
            self.execute(frame(compact(dict(version=2, request_id="caps", method="get_capabilities"))))
        self.assertEqual(caught.exception.status, -4)

    def test_T01_T02_callback_failures_are_closed(self):
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        def failure(*args):
            raise KeyboardInterrupt("explicit callback BaseException")
        for name, status in [("local_io", -6), ("monotonic_clock", -7), ("auxiliary", -8), ("cancel", -7)]:
            with self.subTest(callback=name), self.assertRaises(EngineError) as caught:
                self.execute(raw, **{name: failure})
            self.assertEqual(caught.exception.status, status)
        for value in [None, True, -1, 1 << 64, (1 << 64)-1]:
            with self.subTest(tick=value), self.assertRaises(EngineError) as caught:
                self.execute(raw, monotonic_clock=lambda: value)
            self.assertEqual(caught.exception.status, -7)
        with self.assertRaises(EngineError) as caught:
            self.execute(raw, cancel=lambda: True)
        self.assertEqual(caught.exception.status, -11)

    def test_L01_reentrant_first_clock_and_presentation(self):
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        nested = []
        def again():
            with self.assertRaises(EngineError) as caught:
                self.adapter.run_request_frame(raw, lambda p: 1, lambda: 0, lambda: bytes(32), lambda: False)
            nested.append(caught.exception.status)
        def clock():
            again()
            return 0
        def present(page):
            again()
            return 1 if page.kind == 1 else 0
        self.assertEqual(response(self.execute(raw, local_io=present, monotonic_clock=clock)), vector("kind-1-basic.json")["response"])
        self.assertGreater(len(nested), 2)
        self.assertEqual(set(nested), {-2})

    def test_L02_native_reservation_survives_blocked_callback(self):
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        entered, release, cancelled = threading.Event(), threading.Event(), threading.Event()
        outcomes = []
        other = EngineAdapter(self.adapter.library_path, self.adapter.library_sha256)
        def present(page):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test failed to release its controlled callback")
            return 0
        def operation():
            try:
                self.adapter.run_request_frame(raw, present, lambda: 0, lambda: bytes(32), cancelled.is_set)
            except EngineError as exc:
                outcomes.append(exc.status)
        worker = threading.Thread(target=operation)
        worker.start()
        try:
            self.assertTrue(entered.wait(5))
            cancelled.set()
            self.assertTrue(worker.is_alive())
            for adapter in [self.adapter, other]:
                with self.assertRaises(EngineError) as caught:
                    adapter.run_request_frame(raw, lambda p: 1, lambda: 0, lambda: bytes(32), lambda: False)
                self.assertEqual(caught.exception.status, -2)
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(outcomes, [-11])
        self.assertEqual(response(self.execute(raw)), vector("kind-1-basic.json")["response"])

    def test_N01_no_reference_signer_or_loader_fallback(self):
        from nsealr_vault import signer
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        with patch.object(signer, "sign_request", side_effect=AssertionError("forbidden reference signer")), \
             patch.object(signer, "sign_event", side_effect=AssertionError("forbidden reference signer")):
            self.assertEqual(response(self.execute(raw)), vector("kind-1-basic.json")["response"])
        with self.assertRaises(FileNotFoundError):
            EngineAdapter("/nonexistent/qp01-library.so", "0" * 64)
        with self.assertRaisesRegex(ValueError, "SHA256"):
            EngineAdapter(self.adapter.library_path, "0" * 64)
        # Explicit loader-shape unit control, not an actual foreign-library run.
        with patch("nsealr_vault.engine_adapter.C.CDLL", return_value=object()), self.assertRaises(AttributeError):
            EngineAdapter(self.adapter.library_path, self.adapter.library_sha256)

    def test_uncertain_native_exception_quarantines_wrapper(self):
        adapter = EngineAdapter(self.adapter.library_path, self.adapter.library_sha256)
        raw = frame(compact(vector("kind-1-basic.json")["request"]))
        args = (raw, lambda p: 1, lambda: 0, lambda: bytes(32), lambda: False)
        # Unit fault at the Python native-call boundary; no crash/abort recovery claim.
        with patch.object(adapter, "_run", side_effect=OSError("unknown native outcome")):
            with self.assertRaises(OSError):
                adapter.run_request_frame(*args)
        with self.assertRaisesRegex(RuntimeError, "quarantined"):
            adapter.run_request_frame(*args)


class ProvisioningControls(unittest.TestCase):
    def test_actual_driver_orders_full_pi_then_client_with_same_library(self):
        path = ROOT / "docs/restart/implementation/QP01/request-engine/exchange.py"
        spec = importlib.util.spec_from_file_location("qp01_exchange", path)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        calls = []
        lib = {"NSEALR_QP01_LIBRARY": "/explicit/test.so", "NSEALR_QP01_LIBRARY_SHA256": "a"*64}
        def provision():
            calls.append("build")
            return lib
        def run(argv, **kwargs):
            calls.append(argv)
            self.assertEqual(kwargs["cwd"], ROOT)
            self.assertTrue(kwargs["check"])
            for key, value in lib.items():
                self.assertEqual(kwargs["env"][key], value)
        with patch.object(driver, "provision", side_effect=provision), patch.object(driver.subprocess, "run", side_effect=run):
            driver.ci("apps/pi")
        self.assertEqual(calls, ["build", ["make", "-C", str(ROOT / "apps/pi"), "ci"],
                                ["node", "--import", "tsx/esm", str(driver.CLIENT)]])
        with self.assertRaises(ValueError):
            driver.ci("apps/pi/tests")

    def test_failed_full_pi_never_reaches_client(self):
        path = ROOT / "docs/restart/implementation/QP01/request-engine/exchange.py"
        spec = importlib.util.spec_from_file_location("qp01_exchange_failed", path)
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        with patch.object(driver, "provision", return_value={}), \
             patch.object(driver.subprocess, "run", side_effect=RuntimeError("full Pi failure")) as run:
            with self.assertRaisesRegex(RuntimeError, "full Pi failure"):
                driver.ci("apps/pi")
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
