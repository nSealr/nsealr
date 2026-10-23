"""Public-fixture request/owner tests: a real provisioned native library is required."""
import base64
import copy
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/pi/app"))
from nsealr_vault.engine_adapter import EngineAdapter, EngineError


def vector(name):
    return json.loads((ROOT / "protocols/contracts/v1/vectors/events" / name).read_text())


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


if __name__ == "__main__":
    unittest.main()
