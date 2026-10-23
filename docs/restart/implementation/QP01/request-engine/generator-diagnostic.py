#!/usr/bin/env python3
"""Two current-generator calls only; never call main/sign_fixture/write_json."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[5]
R00 = Path("/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools")
EXPECTED = {
    "secp256k1/__init__.py": "fcce0bd7593070a7cdc450d9556570465c9f8e0770331e6b33028b97c42eabf8",
    "secp256k1/_libsecp256k1.cpython-312-x86_64-linux-gnu.so": "7bf7d7cec3a072f2a21e8464e42537da1fa56fd7476ad7336baa02c8e1b5ef71",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    import secp256k1
    import secp256k1._libsecp256k1 as native
    installed = R00 / "python/lib/python3.12/site-packages"
    assert Path(secp256k1.__file__).resolve() == installed / "secp256k1/__init__.py"
    assert Path(native.__file__).resolve() == installed / "secp256k1/_libsecp256k1.cpython-312-x86_64-linux-gnu.so"
    record = next(r for r in json.loads((ROOT / "tools/baseline/inputs.json").read_text())["python_packages"] if r["name"] == "secp256k1")
    wheel = R00 / "wheels" / record["filename"]
    assert sha(wheel) == record["sha256"] == "1041694e429eb465123cb742911d2aad5cbd9e0cf2891aaaf794a887938647d1"
    with zipfile.ZipFile(wheel) as archive:
        for path, expected in EXPECTED.items():
            assert sha(installed / path) == expected == hashlib.sha256(archive.read(path)).hexdigest()
    elf = Path(native.__file__).resolve()
    mappings = [line for line in Path("/proc/self/maps").read_text().splitlines() if line.split()[-1] == str(elf)]
    assert mappings and any("x" in line.split()[1] for line in mappings)
    assert all(int(line.split()[4]) == elf.stat().st_ino for line in mappings)
    generator_path = ROOT / "protocols/contracts/v1/scripts/generate_fixtures.py"
    generator = load("qp01_existing_generator", generator_path)
    checker = load("qp01_existing_k01", ROOT / "docs/restart/implementation/K01/check_observed.py")
    _, _, oracle = checker.load_oracle()
    prior_path = Path(__file__).with_name("evidence") / "nonce-diagnostic-02/stdout.log"
    assert sha(prior_path) == "6a7e1858c69e3f7d5b22e8151c923443136770f6d098ac38bb956ad75ddbc589"
    prior = json.loads(prior_path.read_text())["rows"]
    assert len(prior) == 2
    key_path = ROOT / "protocols/contracts/v1/vectors/keys/test-key-1.json"
    key = json.loads(key_path.read_text())
    assert key["secret_key"] == generator.SECRET_KEY_HEX == "11" * 32
    private = secp256k1.PrivateKey(bytes.fromhex(generator.SECRET_KEY_HEX), raw=True)
    calls, rows = [], []

    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_name == "schnorr_sign" and frame.f_code.co_filename == secp256k1.__file__:
            values = frame.f_locals
            calls.append({"digest_hex": values["msg"].hex(), "bip340tag": values["bip340tag"], "raw": values["raw"]})

    assert sys.getprofile() is None
    for old in prior:
        source = ROOT / old["fixture"]
        assert sha(source) == old["fixture_sha256"]
        fixture = json.loads(source.read_text())
        sys.setprofile(profile)
        try:
            actual = generator.sign_event(private, fixture["event_template"])
        finally:
            sys.setprofile(None)
        signature = bytes.fromhex(actual["sig"])
        valid = oracle.schnorr_verify(bytes.fromhex(actual["id"]), bytes.fromhex(actual["pubkey"]), signature)
        assert valid and actual["id"] == old["event_id"] and actual["pubkey"] == old["pubkey"]
        assert {k: actual[k] for k in fixture["event_template"]} == fixture["event_template"]
        assert calls[-1] == {"digest_hex": old["event_id"], "bip340tag": "", "raw": True}
        assert sha(source) == old["fixture_sha256"]
        rows.append({"fixture": old["fixture"], "fixture_sha256": old["fixture_sha256"],
                     "actual_generator_event": actual, "actual_binding_call": calls[-1],
                     "legacy_signature": old["legacy_signature"], "frozen_zero_aux_signature": old["oracle_zero_aux_signature"],
                     "frozen_Rust_signature": old["actual_signature"], "oracle_verifies_generator_signature": valid,
                     "generator_equals_legacy": actual["sig"] == old["legacy_signature"],
                     "generator_equals_zero_aux": actual["sig"] == old["oracle_zero_aux_signature"],
                     "generator_equals_Rust": actual["sig"] == old["actual_signature"]})
    assert len(calls) == 2 and sha(elf) == EXPECTED["secp256k1/" + elf.name]
    print(json.dumps({"role": "current pinned generator reproducibility only; historical fixture signing provenance remains unknown",
                      "python": str(Path(sys.executable).resolve()), "python_sha256": sha(Path(sys.executable).resolve()),
                      "generator_path": str(generator_path.relative_to(ROOT)), "generator_sha256": sha(generator_path),
                      "wheel_path": str(wheel), "wheel_sha256": sha(wheel), "installed_base": str(installed),
                      "binding_and_loaded_ELF_sha256": EXPECTED, "actual_ELF_mappings": mappings,
                      "prior_diagnostic_sha256": sha(prior_path), "generator_sign_event_calls": len(calls),
                      "corpus_writer_calls": 0, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()
