#!/usr/bin/env python3
"""Check the exact pinned metadata-v1 auth-negative inventory in a lab consumer."""
import argparse
import json
from pathlib import Path
import sys


EXPECTED = (
    "relay-step-response-auth-url-with-credentials.json",
    "relay-step-response-auth-url-with-fragment.json",
    "relay-step-response-auth-url-wrong-scheme.json",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lab", type=Path)
    parser.add_argument("specs", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.lab.resolve()))
    from scripts.integration_companion_nip46_cli import invalid_auth_challenge_relay_step_vectors

    expected = [json.loads((args.specs / "vectors/invalid" / name).read_text()) for name in EXPECTED]
    assert all(v["relay_step"]["format"] == "nsealr-nip46-relay-response-step-v1" for v in expected)
    actual = invalid_auth_challenge_relay_step_vectors(args.specs)
    print(json.dumps({"required_paths": list(EXPECTED), "selected_names": [v["name"] for v in actual]}), flush=True)
    key = lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
    assert sorted(map(key, actual)) == sorted(map(key, expected)), "metadata-v1 auth-negative inventory incomplete or unexpected"


if __name__ == "__main__":
    main()
