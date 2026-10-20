"""Finite evaluation of changed literal schema constraints, not a schema engine.

Expected requirement sets come from unchanged pre-implementation inputs. This
does not validate complete wire objects or recover raw numeric spelling.
"""
import hashlib
import itertools
import json
from pathlib import Path
import re

BASE = Path("protocols/contracts/v1")
OUT = Path(__file__).parent / "schema-obligations.json"
load = lambda name: json.loads((BASE / name).read_text())
schema = load("schemas/profile-requirements-v1.schema.json")
rules = schema["properties"]["required_groups"]
common = [r["properties"]["required_groups"]["contains"]["const"] for r in schema["allOf"][:-1]]
condition = schema["allOf"][-1]
connected = condition["if"]["properties"]["profile"]["enum"]
assert {"required_groups", "profile"} <= set(schema["required"])
rows = []
for original in load("vectors/profile-capabilities/cases-v1.json")["requirements"]:
    profile, expected = original["profile"], set(original["required_groups"])
    branch = condition["then" if profile in connected else "else"]["properties"]["required_groups"]
    samples = [list(v) for n in range(10) for v in itertools.combinations(rules["items"]["enum"], n)]
    samples += [original["required_groups"] + [original["required_groups"][0]], original["required_groups"] + ["R-UNKNOWN"]]
    observations, accepted = [], []
    for values in samples:
        actual = (rules["minItems"] <= len(values) <= rules["maxItems"]
                  and (not rules["uniqueItems"] or len(values) == len(set(values)))
                  and all(v in rules["items"]["enum"] for v in values)
                  and all(group in values for group in common)
                  and branch["minItems"] <= len(values) <= branch["maxItems"]
                  and ("contains" not in branch or branch["contains"]["const"] in values)
                  and ("not" not in branch or branch["not"]["contains"]["const"] not in values))
        expect = len(values) == len(expected) and set(values) == expected
        assert actual == expect, (profile, values, actual, expect)
        observations.append({"groups": values, "actual_from_constraints": actual, "independent_expected": expect})
        if actual:
            accepted.append(values)
    rows.append({"profile": profile, "independent_expected_groups": original["required_groups"],
                 "observations": len(observations), "accepted_sets": accepted,
                 "observation_sha256": hashlib.sha256(json.dumps(observations, sort_keys=True).encode()).hexdigest()})

numeric = []
for name, definition in [("signing-request-v2", "event_template"), ("signing-response-v2", "signed_event")]:
    current = load("schemas/" + name + ".schema.json")
    for field, maximum in [("kind", 65535), ("created_at", 9007199254740991)]:
        spec = current["$defs"][definition]["properties"][field]
        assert spec["type"] == "integer"
        checks = []
        for value in [-1, 0, 1, 65535, 65536, 9007199254740991, 9007199254740992, 0.5, 1.0]:
            integer = type(value) is int or type(value) is float and value.is_integer()
            actual = integer and spec["minimum"] <= value <= spec["maximum"]
            expect = integer and 0 <= value <= maximum
            assert actual == expect
            checks.append({"input": value, "literal_constraints_accept": actual, "independent_expected": expect})
        numeric.append({"schema": name, "field": field, "actual_constraint": spec, "checks": checks})
ids = []
for name in ["signing-request-v2", "signing-response-v2", "error-v0"]:
    current = load("schemas/" + name + ".schema.json")
    spec = current["properties"]["request_id"] if name == "error-v0" else current["$defs"]["request_id"]
    for length in [0, 1, 64, 128, 129]:
        actual = spec["minLength"] <= length <= spec["maxLength"] and re.search(spec["pattern"], "A" * length) is not None
        assert actual == (1 <= length <= 128)
        ids.append({"schema": name, "ASCII_request_id_length": length, "literal_constraints_accept": actual})
error = load("schemas/error-v0.schema.json")
assert "signing_disabled" in error["properties"]["error"]["properties"]["code"]["enum"]
assert error["properties"]["version"]["const"] == 2
assert load("schemas/signing-response-v2.schema.json")["oneOf"][-1]["$ref"] == "error-v0.schema.json"
result = {"candidate": "24b0b58a6ee085d8176a801a7bad5595d39965b7", "status": "PASS_FINITE_SCHEMA_OBLIGATIONS_ONLY",
          "execution_limit": __doc__, "requirements": rows,
          "requirements_total_observations": sum(r["observations"] for r in rows),
          "numeric_boundaries": numeric, "request_id_boundaries": ids,
          "disabled_error_version2_and_response_reference": True}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"requirements_observations": result["requirements_total_observations"],
                  "profile_sets": len(rows), "numeric_cases": sum(len(r["checks"]) for r in numeric),
                  "ID_cases": len(ids), "status": result["status"]}))
