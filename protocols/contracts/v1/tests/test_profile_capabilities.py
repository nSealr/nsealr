"""Independent contract controls, without runtime consumer imports.

These data/schema/negative controls complement actual Rust/Bridge/Pi dispatch,
resource and Git-provenance tests; inventory enumeration is not execution proof.
"""
from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

from scripts import verify_specs as v

ROOT = Path(__file__).resolve().parents[1]
COMMON = v.load_json("vectors/profile-capabilities/cases-v1.json")


def raw_metadata(source: bytes) -> object:
    """Independent Python JSON witness: preserve spelling before interpretation."""
    if len(source) > 8192 or source.startswith(b"\xef\xbb\xbf"):
        raise ValueError("byte bound/BOM")
    def integer(token: str) -> int:
        if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) > v.MAX_SAFE_INTEGER:
            raise ValueError("unsigned safe decimal required")
        return int(token)
    def pairs(entries: list) -> dict:
        if len(entries) > 32 or len({key for key, _ in entries}) != len(entries):
            raise ValueError("member bound/decoded duplicate")
        if any(len(key.encode("utf8")) > 128 for key, _ in entries):
            raise ValueError("key bound")
        return dict(entries)
    def no_float(_token: str) -> None:
        raise ValueError("float/constant forbidden")
    parsed = json.loads(source.decode("utf8"), object_pairs_hook=pairs, parse_int=integer, parse_float=no_float, parse_constant=no_float)
    pending = [(parsed, 0)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)):
            if depth >= 8: raise ValueError("depth bound")
            pending.extend((item, depth + 1) for item in (value.values() if isinstance(value, dict) else value))
        elif isinstance(value, str): value.encode("utf8")  # rejects lone surrogates
    return parsed


class ProfileContractTests(unittest.TestCase):
    def manifest(self, profile: str = "esp32_no_se") -> dict:
        return deepcopy(v.load_json(COMMON["implementation_examples"][profile]))

    def report(self) -> dict:
        value = self.manifest()
        value.pop("conformance_only")
        return {**value, "format": "nsealr.capabilities.v1", "form": "full"}

    def test_exact_original_42_cases_and_explicit_unqualified_examples(self) -> None:
        expected = [f"{prefix}-{i:02}" for prefix, count in (("A", 6), ("P", 9), ("S", 7), ("R", 6), ("L", 7), ("D", 7)) for i in range(1, count + 1)]
        self.assertEqual([case["id"] for case in COMMON["cases"]], expected)
        errors: list[str] = []
        v.check_profile_contract(COMMON, errors)
        self.assertEqual(errors, [])
        for profile in v.PROFILE_CUSTODY:
            manifest = self.manifest(profile)
            self.assertTrue(manifest["conformance_only"])
            self.assertEqual(manifest["device"]["hardware"], "unidentified")
            self.assertEqual(manifest["custody"]["mode"], v.PROFILE_CUSTODY[profile])
            self.assertNotEqual(next(item for item in manifest["methods"] if item["id"] == "sign_event")["availability"], "available")

    def test_each_missing_own_group_rejects_without_other_profile_requirements(self) -> None:
        for original in COMMON["requirements"]:
            for group in original["required_groups"]:
                data = deepcopy(COMMON)
                record = next(entry for entry in data["requirements"] if entry["profile"] == original["profile"])
                record["required_groups"].remove(group)
                errors: list[str] = []
                v.check_profile_contract(data, errors)
                self.assertTrue(errors, (original["profile"], group))
        offline = [row for row in COMMON["requirements"] if row["profile"] in {"pi_qr", "p4_qr"}]
        self.assertTrue(all("R-MSG" not in row["required_groups"] for row in offline))

    def test_four_states_are_distinct_and_contradictions_reject(self) -> None:
        states = next(case for case in COMMON["cases"] if case["id"] == "A-01")["input"]["states"]
        self.assertEqual(len(set(map(tuple, states))), 4)
        for support, configuration, availability in states:
            v.feature_state(dict(support=support, configuration=configuration, availability=availability, reason=None if availability == "available" else "unknown"))
        for change in ({"support": "unknown"}, {"configuration": "unknown"}, {"reason": "locked"}):
            with self.assertRaises(ValueError):
                v.feature_state({"support": "supported", "configuration": "configured", "availability": "available", "reason": None, **change})

    def test_all_authority_claims_reject_at_every_named_position(self) -> None:
        case = next(case for case in COMMON["cases"] if case["id"] == "A-03")
        for field in case["input"]["forbidden_fields"]:
            for location in case["input"]["positions"]:
                report = self.report()
                target = {"root": report, "method": report["methods"][0], "transport": report["transports"][0], "messages": report["messages"], "device": report["device"]}[location]
                target[field] = True
                with self.subTest(field=field, location=location), self.assertRaises(ValueError):
                    v.validate_capability_data(report)

    def test_unknown_manifest_semantics_and_duplicate_catalog_reject(self) -> None:
        for name, value in (("profile", "board_sdk"), ("consent", "host_approved"), ("implementation_id", "")):
            report = self.report(); report[name] = value
            with self.assertRaises(ValueError): v.validate_capability_data(report)
        for field in ("methods", "transports"):
            report = self.report(); report[field].append(deepcopy(report[field][0]))
            with self.assertRaises(ValueError): v.validate_capability_data(report)
        report = self.report(); report["methods"][1]["algorithm_ids"] *= 2
        with self.assertRaises(ValueError): v.validate_capability_data(report)
        report = self.report(); report["methods"][0]["revision"] = 2
        with self.assertRaises(ValueError): v.validate_capability_data(report)

    def test_raw_intake_rejects_spelling_unicode_and_resource_attacks(self) -> None:
        invalid = [b'{"kind":1,"kind":2}', b'{"kind":1,"k\\u0069nd":2}', b'{}{}', b'\xef\xbb\xbf{}', b'{"name":"\xff"}', b'{"name":"\\ud800"}', b'{"n":-0}', b'{"n":1.0}', b'{"n":1e0}', b'{"n":NaN}', b'{"n":9007199254740992}', b'[' * 9 + b'0' + b']' * 9, b' ' * 8193, json.dumps({str(i): i for i in range(33)}).encode(), json.dumps({"x" * 129: 0}).encode()]
        for source in invalid:
            with self.subTest(source=source[:80]), self.assertRaises((ValueError, UnicodeError)):
                raw_metadata(source)
        self.assertEqual(raw_metadata(b'{"n":0,"label":"ok"}'), {"n": 0, "label": "ok"})
        with self.assertRaises(ValueError):
            v.validate_capability_data(raw_metadata(b'[]'))
        report = self.report(); report["device"]["name"] = "\u00e9" * 65
        with self.assertRaises(ValueError): v.validate_capability_data(report)

    def test_wire2_rejects_wire1_and_retired_status_without_fallback(self) -> None:
        request = v.load_json("examples/request-kind-1-basic.json")
        errors: list[str] = []
        v.check_request_shape(Path("wire2"), request, errors)
        self.assertEqual(errors, [])
        for change in ({"version": 1}, {"version": True}, {"version": 2.0}, {"method": "get_signing_status"}):
            errors = []; v.check_request_shape(Path("legacy"), {**request, **change}, errors)
            self.assertTrue(errors)
        for name in ("signing-request-v0", "signing-response-v0", "account-descriptor-v0", "route-selection-vector-v0"):
            self.assertFalse((ROOT / "schemas" / f"{name}.schema.json").exists())

    def test_finite_dimensions_checked_before_aggregate_retention(self) -> None:
        limits = deepcopy(COMMON["limits_manifest"])
        self.assertEqual(v.validate_limits_data(limits), limits)
        for bad in (None, "unlimited", -1, 1.5, v.MAX_SAFE_INTEGER + 1, 0):
            candidate = deepcopy(limits); candidate["methods"][0]["request_json_bytes"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError): v.validate_limits_data(candidate)
        for change in ({"retained_bytes": 1}, {"unknown_unit": 1}, {"pending_requests": v.MAX_SAFE_INTEGER}):
            candidate = deepcopy(limits); candidate["methods"][0].update(change)
            with self.assertRaises(ValueError): v.validate_limits_data(candidate)
        candidate = deepcopy(limits); del candidate["methods"][0]["deadline_ms"]
        with self.assertRaises(ValueError): v.validate_limits_data(candidate)
        for row in limits["methods"]:
            self.assertEqual(row["queued_operations"], 0)
            self.assertEqual(row["cached_responses"], 0)

    def test_primitive_is_not_context_workflow_or_generic_ecc(self) -> None:
        report = self.report()
        primitive = report["messages"]["nip44_v2_primitive"]
        primitive.update(support="supported", configuration="configured", availability="available", reason=None)
        v.validate_capability_data(report)
        self.assertEqual(report["messages"]["nip17_59_one_to_one_text_v1"]["availability"], "unavailable")
        report["messages"]["nip17_59_one_to_one_text_v1"].update(support="supported", configuration="configured", availability="available", reason=None, workflow_id="synthetic_admitted_sequence")
        with self.assertRaises(ValueError): v.validate_capability_data(report)
        report["messages"]["verified_message_context_v1"].update(support="supported", configuration="configured", availability="available", reason=None)
        v.validate_capability_data(report)  # metadata consistency, no execution API
        report["methods"][0]["algorithm_ids"] = ["generic_ecc"]
        with self.assertRaises(ValueError): v.validate_capability_data(report)


if __name__ == "__main__": unittest.main()
