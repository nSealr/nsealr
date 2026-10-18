#!/usr/bin/env python3
"""Check sibling repository specs fixture snapshots against live specs."""

from __future__ import annotations

import hashlib
import json
import subprocess

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
SNAPSHOT_REPOSITORIES = ("companion", "firmware", "hardware", "raspberry", "smartcard")
DEFAULT_REQUIRED_SNAPSHOT_GLOBS: Mapping[str, Sequence[str]] = {
    "companion": (
        "vectors/events/*.json",
        "vectors/accounts/*.json",
        "vectors/access-surfaces/*.json",
        "vectors/custody/*.json",
        "vectors/features/*.json",
        "vectors/grants/*.json",
        "vectors/invalid/*.json",
        "vectors/nip46/*.json",
        "vectors/nip46-connection-uris/*.json",
        "vectors/nip46-connection-token-responses/*.json",
        "vectors/nip46-auth-challenges/*.json",
        "vectors/nip46-policy-files/*.json",
        "vectors/nip46-relay-events/*.json",
        "vectors/nip46-relay-steps/*.json",
        "vectors/nip46-session-gates/*.json",
        "vectors/nip46-sessions/*.json",
        "vectors/policies/*.json",
        "vectors/policy-changes/*.json",
        "vectors/policy-decisions/*.json",
        "vectors/route-selections/*.json",
        "vectors/route-refusals/*.json",
        "vectors/source-public-key-proofs/*.json",
        "vectors/review/*.json",
        "vectors/review-detail-pages/*.json",
        "vectors/review-display-frames/*.json",
        "vectors/review-screens/*.json",
        "vectors/review-transcripts/*.json",
        "schemas/policy-change-review-v0.schema.json",
    ),
    "firmware": (
        "vectors/accounts/esp32-qr-nip06-account-0.json",
        "vectors/accounts/esp32-usb-device-slot-0.json",
        "vectors/invalid/nip46-connect-*.json",
        "vectors/invalid/nip46-connection-uri-*.json",
        "vectors/invalid/nip46-permission-*.json",
        "vectors/invalid/nip46-policy-*.json",
        "vectors/invalid/nip46-relay-event-*.json",
        "vectors/invalid/nip46-sign-event-*.json",
        "vectors/invalid/qr-envelope-*.json",
        "vectors/invalid/request-*.json",
        "vectors/invalid/serial-frame*.json",
        "vectors/policies/manual-only-qr-vault.json",
        "vectors/policies/manual-only-persistent-device.json",
        "vectors/policies/scoped-automation-daily-use.json",
        "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json",
        "vectors/route-selections/esp32-qr-sign-event-account-0.json",
        "vectors/route-selections/esp32-usb-sign-event-slot-0.json",
        "vectors/review/*.json",
        "vectors/review-detail-pages/*.json",
        "vectors/review-display-frames/*.json",
        "vectors/review-screens/*.json",
        "vectors/review-transcripts/*.json",
        "vectors/transports/qr-animated-response-kind-1-basic.json",
        "vectors/transports/qr-envelope-kind-1-basic.json",
        "vectors/transports/qr-envelope-kind-1-long-events-many-tags.json",
        "vectors/transports/serial-frame-request-kind-1-basic.json",
        "vectors/devices/esp32-s3-capabilities-scaffold.json",
        "vectors/devices/esp32-s3-get-public-key-dev.json",
        "vectors/devices/esp32-s3-security-profile-development.json",
        "vectors/devices/esp32-s3-sign-event-disabled.json",
        "vectors/devices/esp32-s3-signing-status-disabled.json",
        "vectors/keys/*.json",
        "vectors/limits/nsealr-v0.json",
        "vectors/nip19/*.json",
        "vectors/seedqr/*.json",
        "vectors/session-source-backups/*.json",
        "vectors/session-import-reviews/*.json",
        "vectors/source-public-key-proofs/*.json",
    ),
    "hardware": (
        "vectors/custody/persistent-secret-custody-v0.json",
        "vectors/accounts/custom-hardware-wallet-slot-0.json",
        "vectors/grants/custom-hardware-wallet-kind-1-session.json",
        "vectors/policies/manual-only-persistent-device.json",
        "vectors/policy-changes/custom-hardware-wallet-enable-kind-1-automation.json",
        "vectors/policies/scoped-automation-daily-use.json",
        "vectors/route-selections/custom-hardware-wallet-sign-event-slot-0.json",
    ),
    "raspberry": (
        "vectors/accounts/raspberry-qr-nip06-account-0.json",
        "vectors/nip19/*.json",
        "vectors/policies/manual-only-qr-vault.json",
        "vectors/route-selections/raspberry-qr-sign-event-account-0.json",
        "vectors/seedqr/*.json",
        "vectors/session-source-backups/*.json",
        "vectors/session-import-reviews/*.json",
        "vectors/source-public-key-proofs/*.json",
    ),
    "smartcard": (
        "vectors/accounts/smartcard-slot-0.json",
        "vectors/policies/manual-only-displayless-smartcard.json",
        "vectors/route-selections/smartcard-sign-event-slot-0.json",
    ),
}


class FixtureSnapshotError(AssertionError):
    """Raised when a committed specs fixture snapshot drifts from live specs."""


def iter_snapshot_files(root: Path) -> Iterable[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


def vector_files(root: Path) -> set[str]:
    vector_root = root / "vectors"
    if not vector_root.is_dir() or vector_root.is_symlink():
        raise FixtureSnapshotError(f"missing or nonregular vectors directory: {vector_root}")
    paths = set()
    for path in vector_root.rglob("*"):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise FixtureSnapshotError(f"nonregular vector entry: {path}")
        if path.is_file():
            paths.add(path.relative_to(root).as_posix())
    return paths


def validate_provenance(snapshot_root: Path, specs: Path) -> None:
    """Require a complete snapshot of the claimed committed upstream bytes."""
    metadata_path = snapshot_root / "SOURCE.json"
    if not metadata_path.is_file() or metadata_path.is_symlink():
        raise FixtureSnapshotError(f"missing or nonregular SOURCE.json: {snapshot_root}")
    try:
        metadata = json.loads(metadata_path.read_text())
    except (OSError, UnicodeError, ValueError) as exc:
        raise FixtureSnapshotError(f"invalid SOURCE.json: {exc}") from exc
    if not isinstance(metadata, dict):
        raise FixtureSnapshotError("SOURCE.json must be an object")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=specs, text=True).strip()
    if metadata.get("repository") != "https://github.com/nSealr/specs" or metadata.get("commit") != commit:
        raise FixtureSnapshotError("SOURCE.json upstream repository/commit mismatch")
    tree = subprocess.check_output(
        ["git", "ls-tree", "-rz", "--full-tree", commit, "--", "vectors/"], cwd=specs,
    )
    blobs = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        header, relative = entry.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise FixtureSnapshotError(f"nonregular committed vector: {relative!r}")
        blobs[relative.decode()] = oid
    recorded = metadata.get("files")
    if (not isinstance(recorded, dict) or not blobs or set(recorded) != set(blobs)
            or set(blobs) != vector_files(specs) or set(blobs) != vector_files(snapshot_root)):
        raise FixtureSnapshotError("SOURCE.json vector inventory mismatch")
    for relative, oid in blobs.items():
        source = (specs / relative).read_bytes()
        committed = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=specs)
        snapshot = (snapshot_root / relative).read_bytes()
        if source != committed:
            raise FixtureSnapshotError(f"upstream vector differs from claimed commit: {relative}")
        if snapshot != source:
            raise FixtureSnapshotError(f"snapshot vector differs from specs: {relative}")
        if hashlib.sha256(source).hexdigest() != recorded[relative]:
            raise FixtureSnapshotError(f"SOURCE.json hash mismatch: {relative}")


def compare_fixture_snapshots(
    *,
    org: Path = ORG,
    repositories: Iterable[str] = SNAPSHOT_REPOSITORIES,
    required_snapshot_globs: Mapping[str, Sequence[str]] | None = None,
) -> int:
    specs = org / "specs"
    if not specs.exists():
        raise FixtureSnapshotError(f"missing specs repository: {specs}")

    required_globs = DEFAULT_REQUIRED_SNAPSHOT_GLOBS if required_snapshot_globs is None else required_snapshot_globs
    checked = 0
    failures: list[str] = []
    for repository in repositories:
        snapshot_root = org / repository / "tests" / "fixtures" / "specs"
        if not snapshot_root.exists():
            raise FixtureSnapshotError(f"{repository}: missing fixture snapshot root: {snapshot_root}")

        # Core owns a complete import. Partial consumers keep their own glob contract.
        # Require metadata independently of iteration, even with empty required globs.
        if (repository == "firmware" or (snapshot_root / "SOURCE.json").exists()
                or (snapshot_root / "SOURCE.json").is_symlink()):
            validate_provenance(snapshot_root, specs)

        for pattern in required_globs.get(repository, ()):
            for source in sorted(path for path in specs.glob(pattern) if path.is_file()):
                relative = source.relative_to(specs)
                if not (snapshot_root / relative).exists():
                    failures.append(f"{repository}: {relative} required snapshot is missing")

        for snapshot in iter_snapshot_files(snapshot_root):
            relative = snapshot.relative_to(snapshot_root)
            if relative == Path("SOURCE.json"):
                continue
            source = specs / relative
            if not source.exists():
                failures.append(f"{repository}: {relative} is missing from specs")
                continue
            if source.read_bytes() != snapshot.read_bytes():
                failures.append(f"{repository}: {relative} differs from specs")
            checked += 1

    if failures:
        raise FixtureSnapshotError("\n".join(failures))

    return checked


def main() -> int:
    checked = compare_fixture_snapshots()
    print(f"nSealr specs fixture snapshot check passed ({checked} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
