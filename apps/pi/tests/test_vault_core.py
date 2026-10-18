import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nsealr_vault.crypto import sign_event, verify_schnorr_signature
from nsealr_vault.adapters import ComposedButtonQrVaultIO, FileButtonQrVaultIO, FileQrVaultIO
from nsealr_vault.controls import ReviewControlSession, review_transcript_for_screen_review
from nsealr_vault.display import (
    DisplayFrameLimits,
    ReviewDetailPageLimits,
    approval_digest_for_request,
    render_display_frame,
    render_review_detail_frame,
    render_review_detail_pages,
    render_review_pages,
    screen_review_for_request,
)
from nsealr_vault.hardware_flow import (
    run_detail_button_qr_vault_flow,
    run_button_qr_vault_flow,
    run_button_qr_vault_flow_with_secret_provider,
    run_qr_vault_flow,
)
from nsealr_vault.hardware_probe import run_seed_signer_compatibility_probe
from nsealr_vault.cli import main as vault_cli_main
from nsealr_vault.nip06 import derive_nip06_secret
from nsealr_vault.qr import (
    ANIMATED_QR_ENVELOPE_PREFIX,
    decode_animated_qr_envelope_frames,
    decode_qr_envelope,
    encode_animated_qr_envelope_frames,
    encode_qr_envelope,
)
from nsealr_vault.review import review_event_template
from nsealr_vault.seed_entry import (
    MnemonicSessionSecretProvider,
    NsecSessionSecretProvider,
    SeedQrSessionSecretProvider,
    SessionImportSource,
    bip39_word_indexes_from_mnemonic,
    generate_bip39_session_source,
    generate_nsec_session_source,
    mnemonic_from_bip39_word_indexes,
    mnemonic_from_compact_seedqr,
    mnemonic_from_standard_seedqr,
    normalize_mnemonic_words,
    nsec_from_secret_key,
    public_key_from_session_import_source,
    secret_key_from_session_import_source,
    secret_key_from_nsec,
    session_import_review,
    session_import_source_fingerprint,
    session_source_backup_payload,
    session_source_backup_review,
)
from nsealr_vault.session_import_flow import (
    SessionImportFlowError,
    SessionImportTranscriptStep,
    StatelessSessionSecretProvider,
    StatelessSessionKeyring,
    run_session_import_flow,
)
from nsealr_vault.session_source_qr import (
    SessionSourceQrError,
    parse_compact_seedqr_session_source,
    parse_session_source_qr_text,
)
from nsealr_vault.session_source_qr_import_flow import (
    run_compact_seedqr_session_import_flow,
    run_session_source_qr_text_import_flow,
)
from nsealr_vault.session_source_backup_flow import (
    SessionSourceBackupFlowError,
    SessionSourceBackupTranscriptStep,
    run_session_source_backup_flow,
    run_session_source_backup_io_flow,
)
from nsealr_vault.signer import sign_request


ROOT = Path(__file__).resolve().parents[1]


def specs_dir() -> Path:
    sibling = ROOT.parent / "specs"
    if sibling.exists():
        return sibling
    return ROOT / "tests/fixtures/specs"


SPECS = specs_dir()
KEY = json.loads((SPECS / "vectors/keys/test-key-1.json").read_text(encoding="utf-8"))
NIP06_KEY = json.loads((SPECS / "vectors/keys/nip06-account-0-leader.json").read_text(encoding="utf-8"))
BASIC_VECTOR = json.loads((SPECS / "vectors/events/kind-1-basic.json").read_text(encoding="utf-8"))
BASIC_REQUEST = json.loads((SPECS / "examples/request-kind-1-basic.json").read_text(encoding="utf-8"))
TAGGED_REQUEST = json.loads((SPECS / "examples/request-kind-1-tags.json").read_text(encoding="utf-8"))
ANIMATED_QR_VECTOR = json.loads((SPECS / "vectors/transports/qr-animated-response-kind-1-basic.json").read_text(encoding="utf-8"))
SCROLL_DETAIL_REQUEST = {
    "version": 1,
    "request_id": "req-scroll-detail",
    "method": "sign_event",
    "params": {
        "event_template": {
            "created_at": 1710000000,
            "kind": 1,
            "tags": [["t", f"tag{index}"] for index in range(4)],
            "content": "review detail tags",
        }
    },
}
REVIEW_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review").glob("*.json"))
]
SCREEN_REVIEW_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-screens").glob("*.json"))
]
REVIEW_TRANSCRIPT_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-transcripts").glob("*.json"))
]
DISPLAY_FRAME_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-display-frames").glob("*.json"))
]
REVIEW_DETAIL_PAGE_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/review-detail-pages").glob("*.json"))
]
TAGGED_REVIEW_VECTOR = json.loads((SPECS / "vectors/review/kind-1-tags.json").read_text(encoding="utf-8"))
LIMIT_PROFILE = json.loads((SPECS / "vectors/limits/nsealr-v0.json").read_text(encoding="utf-8"))
INVALID_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/invalid").glob("*.json"))
]
RASPBERRY_ACCOUNT_DESCRIPTOR = json.loads(
    (SPECS / "vectors/accounts/raspberry-qr-nip06-account-0.json").read_text(encoding="utf-8")
)
MANUAL_QR_POLICY = json.loads((SPECS / "vectors/policies/manual-only-qr-vault.json").read_text(encoding="utf-8"))
RASPBERRY_ROUTE_SELECTION = json.loads(
    (SPECS / "vectors/route-selections/raspberry-qr-sign-event-account-0.json").read_text(encoding="utf-8")
)
SEEDSIGNER_VECTOR_1 = json.loads(
    (SPECS / "vectors/seedqr/seedsigner-vector-1.json").read_text(encoding="utf-8")
)
SEEDSIGNER_VECTOR_1_MNEMONIC = SEEDSIGNER_VECTOR_1["mnemonic"]
SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR = SEEDSIGNER_VECTOR_1["standard_seedqr_digits"]
SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX = SEEDSIGNER_VECTOR_1["compact_seedqr_hex"]
NIP19_NSEC_VECTOR = json.loads(
    (SPECS / "vectors/nip19/nsec-test-key-1.json").read_text(encoding="utf-8")
)
TEST_KEY_1_NSEC = NIP19_NSEC_VECTOR["nsec"]
SESSION_IMPORT_REVIEW_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/session-import-reviews").glob("*.json"))
]
SOURCE_PUBLIC_KEY_PROOF_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/source-public-key-proofs").glob("*.json"))
]
SESSION_SOURCE_BACKUP_VECTORS = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted((SPECS / "vectors/session-source-backups").glob("*.json"))
]


def session_import_review_vector(name: str) -> dict[str, object]:
    for vector in SESSION_IMPORT_REVIEW_VECTORS:
        if vector["name"] == name:
            return vector
    raise AssertionError(f"missing session import review vector: {name}")


def session_source_backup_vector(name: str) -> dict[str, object]:
    for vector in SESSION_SOURCE_BACKUP_VECTORS:
        if vector["name"] == name:
            return vector
    raise AssertionError(f"missing session source backup vector: {name}")


def source_public_key_proof_vector(name: str) -> dict[str, object]:
    for vector in SOURCE_PUBLIC_KEY_PROOF_VECTORS:
        if vector["name"] == name:
            return vector
    raise AssertionError(f"missing source public-key proof vector: {name}")


class MemoryQrVaultIO:
    def __init__(self, request_qr: str, approved: bool) -> None:
        self.request_qr = request_qr
        self.approved = approved
        self.screen_review: dict | None = None
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def show_review(self, screen_review: dict) -> bool:
        self.screen_review = screen_review
        return self.approved

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class MemoryButtonQrVaultIO:
    def __init__(self, request_qr: str, buttons: list[str]) -> None:
        self.request_qr = request_qr
        self.buttons = list(buttons)
        self.displayed_pages: list[tuple[int, str]] = []
        self.frames: list[dict] = []
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.displayed_pages.append((page_index, frame["title"]))
        self.frames.append(frame)

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more buttons")
        return self.buttons.pop(0)

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class MemorySessionSourceBackupIO:
    def __init__(self, buttons: list[str]) -> None:
        self.buttons = list(buttons)
        self.frames: list[tuple[int, dict]] = []
        self.backup_payloads: list[dict[str, str]] = []

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.frames.append((page_index, frame))

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more backup buttons")
        return self.buttons.pop(0)

    def emit_backup_payload(self, backup_payload: dict[str, str]) -> None:
        self.backup_payloads.append(backup_payload)


class NextOnlyButtonQrVaultIO:
    def __init__(self, request_qr: str) -> None:
        self.request_qr = request_qr
        self.displayed_pages: list[tuple[int, str]] = []
        self.response_qr: str | None = None

    def scan_request_qr(self) -> str:
        return self.request_qr

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.displayed_pages.append((page_index, frame["title"]))

    def read_review_button(self) -> str:
        return "next"

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class FakeMnemonicWordInput:
    def __init__(self, words: list[str]) -> None:
        self.words = list(words)
        self.prompts: list[tuple[int, int]] = []

    def read_mnemonic_word(self, word_index: int, word_count: int) -> str:
        self.prompts.append((word_index, word_count))
        if not self.words:
            raise RuntimeError("no more mnemonic words")
        return self.words.pop(0)


class FakeQrScanner:
    def __init__(self, request_qr: str) -> None:
        self.request_qr = request_qr
        self.calls = 0

    def scan_request_qr(self) -> str:
        self.calls += 1
        return self.request_qr


class FakeReviewDisplay:
    def __init__(self) -> None:
        self.frames: list[tuple[int, str]] = []

    def display_review_frame(self, screen_review: dict, page_index: int, frame: dict) -> None:
        self.frames.append((page_index, frame["title"]))


class FakeButtonInput:
    def __init__(self, buttons: list[str]) -> None:
        self.buttons = list(buttons)

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more fake buttons")
        return self.buttons.pop(0)


class FakeResponseQrDisplay:
    def __init__(self) -> None:
        self.response_qr: str | None = None

    def emit_response_qr(self, response_qr: str) -> None:
        self.response_qr = response_qr


class ProjectToolingTests(unittest.TestCase):
    def test_setup_uses_in_tree_build_to_keep_pip_logs_clean(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("install --use-feature=in-tree-build --help", makefile)
        self.assertIn("--use-feature=in-tree-build", makefile)
        self.assertIn("$$PIP_IN_TREE_BUILD", makefile)


class HardwareProbeTests(unittest.TestCase):
    @staticmethod
    def _remote_access_disabled(args: tuple[str, ...]) -> tuple[int, str, str]:
        service = args[-1]
        if args[:2] == ("systemctl", "is-enabled") and service in {"ssh", "sshd"}:
            return 1, "disabled", ""
        if args[:2] == ("systemctl", "is-active") and service in {"ssh", "sshd"}:
            return 3, "inactive", ""
        return 127, "", "unexpected command"

    def test_seed_signer_probe_passes_with_pi_zero_profile(self) -> None:
        files = {
            "/proc/device-tree/model": "Raspberry Pi Zero Rev 1.3\x00",
            "/boot/config.txt": "start_x=1\ndtparam=spi=on\n",
            "/proc/swaps": "Filename\tType\tSize\tUsed\tPriority\n",
        }

        report = run_seed_signer_compatibility_probe(
            read_text=lambda path: files[str(path)],
            find_module=lambda name: name in {"RPi.GPIO", "spidev", "picamera"},
            run_command=self._remote_access_disabled,
        )

        self.assertTrue(report["ready_for_hardware_acceptance"])
        self.assertFalse(report["production_signing_enabled"])
        self.assertFalse(report["persistent_secret_present"])
        self.assertFalse(report["tropic01_used"])
        self.assertEqual(report["acceptance_blockers"], [])
        self.assertEqual(report["human_actions_required"], [])
        self.assertEqual(
            {check["id"]: check["status"] for check in report["checks"]},
            {
                "board_model": "pass",
                "gpio_python_module": "pass",
                "spi_python_module": "pass",
                "camera_python_module": "pass",
                "boot_camera_enabled": "pass",
                "boot_spi_enabled": "pass",
                "swap_disabled": "pass",
                "wireless_absent_or_blocked": "pass",
                "remote_access_disabled": "pass",
            },
        )

    def test_seed_signer_probe_blocks_non_pi_environment(self) -> None:
        report = run_seed_signer_compatibility_probe(
            read_text=lambda path: (_ for _ in ()).throw(FileNotFoundError(str(path))),
            find_module=lambda name: False,
        )

        self.assertFalse(report["ready_for_hardware_acceptance"])
        self.assertIn("not a completed hardware acceptance report", " ".join(report["limitations"]))
        self.assertEqual(report["checks"][0]["id"], "board_model")
        self.assertEqual(report["checks"][0]["status"], "blocked")
        self.assertIn("board_model", report["acceptance_blockers"])
        self.assertIn("Run the probe on the target Raspberry Pi Zero-class board.", report["human_actions_required"])

    def test_seed_signer_probe_fails_when_remote_access_is_active(self) -> None:
        files = {
            "/proc/device-tree/model": "Raspberry Pi Zero Rev 1.3\x00",
            "/boot/config.txt": "start_x=1\ndtparam=spi=on\n",
            "/proc/swaps": "Filename\tType\tSize\tUsed\tPriority\n",
        }

        def remote_access_active(args: tuple[str, ...]) -> tuple[int, str, str]:
            if args == ("systemctl", "is-enabled", "ssh"):
                return 0, "enabled", ""
            if args == ("systemctl", "is-active", "ssh"):
                return 0, "active", ""
            if args[:2] == ("systemctl", "is-enabled"):
                return 1, "disabled", ""
            if args[:2] == ("systemctl", "is-active"):
                return 3, "inactive", ""
            return 127, "", "unexpected command"

        report = run_seed_signer_compatibility_probe(
            read_text=lambda path: files[str(path)],
            find_module=lambda name: name in {"RPi.GPIO", "spidev", "picamera"},
            run_command=remote_access_active,
        )

        statuses = {check["id"]: check["status"] for check in report["checks"]}
        self.assertFalse(report["ready_for_hardware_acceptance"])
        self.assertEqual(statuses["remote_access_disabled"], "fail")
        self.assertIn("remote_access_disabled", report["acceptance_blockers"])
        self.assertIn("Disable SSH/remote-login services before signing acceptance.", report["human_actions_required"])

    def test_hardware_probe_cli_writes_report_without_requiring_hardware(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            output = Path(temp_root) / "probe.json"

            exit_code = vault_cli_main(["hardware-probe", "--out", str(output)])

            self.assertEqual(exit_code, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["format"], "nsealr-raspberry-seedsigner-compatibility-probe-v0")
            self.assertFalse(report["production_signing_enabled"])


class VaultCoreTests(unittest.TestCase):
    def assert_valid_signed_event(self, signed: dict) -> None:
        expected = dict(BASIC_VECTOR["signed_event"])
        expected.pop("sig")
        actual = dict(signed)
        signature = actual.pop("sig")

        self.assertEqual(actual, expected)
        self.assertTrue(verify_schnorr_signature(signed["pubkey"], signed["id"], signature))

    def assert_valid_signed_event_for_pubkey(self, signed: dict, public_key: str) -> None:
        self.assertEqual(signed["pubkey"], public_key)
        self.assertTrue(verify_schnorr_signature(signed["pubkey"], signed["id"], signed["sig"]))

    def test_qr_envelope_round_trip_uses_shared_prefix(self) -> None:
        envelope = encode_qr_envelope(BASIC_REQUEST)

        self.assertTrue(envelope.startswith("nsealr1:"))
        self.assertNotIn("=", envelope)
        self.assertEqual(decode_qr_envelope(envelope), BASIC_REQUEST)

    def test_qr_encoder_rejects_oversized_static_payloads(self) -> None:
        oversized = {"payload": "x" * (LIMIT_PROFILE["limits"]["max_static_qr_decoded_json_bytes"] + 1)}

        with self.assertRaisesRegex(ValueError, "QR decoded JSON exceeds max_static_qr_decoded_json_bytes"):
            encode_qr_envelope(oversized)

    def test_animated_qr_envelope_matches_shared_vector(self) -> None:
        frames = encode_animated_qr_envelope_frames(
            ANIMATED_QR_VECTOR["decoded"],
            chunk_size_chars=ANIMATED_QR_VECTOR["chunk_size_chars"],
        )

        self.assertEqual(frames, ANIMATED_QR_VECTOR["frames"])
        self.assertTrue(all(frame.startswith(ANIMATED_QR_ENVELOPE_PREFIX) for frame in frames))
        self.assertEqual(decode_animated_qr_envelope_frames(frames), ANIMATED_QR_VECTOR["decoded"])
        self.assertEqual(decode_animated_qr_envelope_frames(list(reversed(frames))), ANIMATED_QR_VECTOR["decoded"])

    def test_animated_qr_envelope_rejects_malformed_frame_sets(self) -> None:
        with self.assertRaisesRegex(ValueError, "animated QR requires at least one frame"):
            decode_animated_qr_envelope_frames([])
        with self.assertRaisesRegex(ValueError, "animated QR frames must be unique and contiguous"):
            decode_animated_qr_envelope_frames(ANIMATED_QR_VECTOR["frames"][1:])
        tampered = list(ANIMATED_QR_VECTOR["frames"])
        tampered[0] = tampered[0][:-1] + "0"
        with self.assertRaisesRegex(ValueError, "animated QR frame checksum mismatch"):
            decode_animated_qr_envelope_frames(tampered)

    def test_limits_match_shared_v0_profile(self) -> None:
        from nsealr_vault.limits import NSEALR_V0_LIMITS

        self.assertEqual(LIMIT_PROFILE["name"], "nsealr-v0")
        self.assertEqual(NSEALR_V0_LIMITS, LIMIT_PROFILE["limits"])

    def test_qr_decoder_rejects_shared_invalid_qr_vectors(self) -> None:
        vectors = [vector for vector in INVALID_VECTORS if vector["category"] == "qr-envelope"]
        self.assertGreater(len(vectors), 0)

        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                with self.assertRaisesRegex(ValueError, vector["expected_error"]):
                    decode_qr_envelope(vector["envelope"])

    def test_signer_rejects_shared_invalid_signing_request_vectors(self) -> None:
        vectors = [vector for vector in INVALID_VECTORS if vector["category"] == "signing-request"]
        self.assertGreater(len(vectors), 0)

        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                response = sign_request(vector["request"], KEY["secret_key"], approved=True)

                self.assertFalse(response["ok"])
                self.assertEqual(response["error"]["code"], "invalid_request")
                self.assertIn(vector["expected_error"], response["error"]["message"])

    def test_sign_event_matches_shared_vector(self) -> None:
        signed = sign_event(BASIC_REQUEST["params"]["event_template"], KEY["secret_key"])

        self.assert_valid_signed_event(signed)

    def test_nip06_derivation_matches_shared_account_zero_vector(self) -> None:
        derived = derive_nip06_secret(
            NIP06_KEY["mnemonic"],
            passphrase=NIP06_KEY["passphrase"],
            account=NIP06_KEY["account"],
        )

        self.assertEqual(derived, NIP06_KEY["secret_key"])

    def test_seed_entry_normalizes_and_validates_bip39_mnemonic_words(self) -> None:
        words = ["  Leader ", "MONKEY", *NIP06_KEY["mnemonic"].split()[2:]]

        self.assertEqual(normalize_mnemonic_words(words), NIP06_KEY["mnemonic"])

        bad_words = NIP06_KEY["mnemonic"].split()
        bad_words[-1] = "about"
        with self.assertRaisesRegex(ValueError, "BIP-39 checksum"):
            normalize_mnemonic_words(bad_words)

        with self.assertRaisesRegex(ValueError, "mnemonic word count"):
            normalize_mnemonic_words(NIP06_KEY["mnemonic"].split()[:11])

        unknown_word = NIP06_KEY["mnemonic"].split()
        unknown_word[0] = "notaword"
        with self.assertRaisesRegex(ValueError, "BIP-39 English wordlist"):
            normalize_mnemonic_words(unknown_word)

    def test_mnemonic_session_secret_provider_reads_words_once_and_derives_nip06_secret(self) -> None:
        word_input = FakeMnemonicWordInput(NIP06_KEY["mnemonic"].split())
        provider = MnemonicSessionSecretProvider(
            word_input,
            word_count=12,
            account=NIP06_KEY["account"],
            passphrase=NIP06_KEY["passphrase"],
        )

        self.assertEqual(provider(), NIP06_KEY["secret_key"])
        self.assertEqual(word_input.prompts, [(index, 12) for index in range(1, 13)])
        self.assertFalse(hasattr(provider, "mnemonic"))

        with self.assertRaisesRegex(RuntimeError, "session mnemonic has already been consumed"):
            provider()

    def test_seedsigner_standard_seedqr_decodes_to_bip39_mnemonic(self) -> None:
        mnemonic = mnemonic_from_standard_seedqr(SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR)

        self.assertEqual(mnemonic, SEEDSIGNER_VECTOR_1_MNEMONIC)

        with self.assertRaisesRegex(ValueError, "only digits"):
            mnemonic_from_standard_seedqr(SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR + "x")
        with self.assertRaisesRegex(ValueError, "outside the BIP-39 English wordlist"):
            mnemonic_from_standard_seedqr("2048" * 12)
        with self.assertRaisesRegex(ValueError, "word count"):
            mnemonic_from_standard_seedqr("0000" * 13)

    def test_seedsigner_compact_seedqr_decodes_to_bip39_mnemonic(self) -> None:
        compact_seedqr = bytes.fromhex(SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX)

        self.assertEqual(mnemonic_from_compact_seedqr(compact_seedqr), SEEDSIGNER_VECTOR_1_MNEMONIC)

        with self.assertRaisesRegex(ValueError, "byte length"):
            mnemonic_from_compact_seedqr(compact_seedqr[:-1])

    def test_seedqr_session_secret_provider_reads_seed_once_and_derives_nip06_secret(self) -> None:
        provider = SeedQrSessionSecretProvider(
            SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR,
            qr_format="standard",
            account=0,
            passphrase="",
        )
        expected_secret = derive_nip06_secret(SEEDSIGNER_VECTOR_1_MNEMONIC)

        self.assertEqual(provider(), expected_secret)
        with self.assertRaisesRegex(RuntimeError, "session SeedQR has already been consumed"):
            provider()

        compact_provider = SeedQrSessionSecretProvider(
            bytes.fromhex(SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX),
            qr_format="compact",
        )
        self.assertEqual(compact_provider(), expected_secret)

    def test_nsec_session_secret_provider_decodes_nip19_nsec_once(self) -> None:
        self.assertEqual(NIP19_NSEC_VECTOR["secret_key"], KEY["secret_key"])
        self.assertEqual(NIP19_NSEC_VECTOR["public_key"], KEY["public_key"])
        self.assertEqual(secret_key_from_nsec(TEST_KEY_1_NSEC), KEY["secret_key"])
        self.assertEqual(nsec_from_secret_key(KEY["secret_key"]), TEST_KEY_1_NSEC)

        provider = NsecSessionSecretProvider(TEST_KEY_1_NSEC)
        self.assertEqual(provider(), KEY["secret_key"])
        with self.assertRaisesRegex(RuntimeError, "session nsec has already been consumed"):
            provider()

        with self.assertRaisesRegex(ValueError, "checksum"):
            secret_key_from_nsec(TEST_KEY_1_NSEC[:-1] + "q")
        with self.assertRaisesRegex(ValueError, "prefix"):
            secret_key_from_nsec("npub1fu64hh9hes90w2808n8tjc2ajp5yhddjef0ctx4s7zmsgp6cwx4qgy4eg9")
        with self.assertRaisesRegex(ValueError, "lowercase"):
            secret_key_from_nsec(TEST_KEY_1_NSEC.upper())
        with self.assertRaisesRegex(ValueError, "valid secp256k1 scalar"):
            nsec_from_secret_key("00" * 32)

    def test_generated_session_sources_are_ram_only_review_sources(self) -> None:
        seed_source = generate_bip39_session_source(
            "Generated seed",
            word_count=12,
            entropy=bytes(16),
        )
        nsec_source = generate_nsec_session_source(
            "Generated nsec",
            entropy=bytes.fromhex("01".zfill(64)),
        )

        self.assertEqual(seed_source.source_type, "bip39_seed")
        self.assertEqual(
            mnemonic_from_bip39_word_indexes(seed_source.bip39_word_indexes),
            "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
        )
        self.assertEqual(nsec_source.source_type, "nsec")
        self.assertEqual(nsec_source.nsec_secret_key, "00" * 31 + "01")
        self.assertEqual(secret_key_from_session_import_source(nsec_source), "00" * 31 + "01")

        rendered = json.dumps(
            [session_import_review(seed_source), session_import_review(nsec_source)],
            ensure_ascii=False,
        )
        self.assertIn("Secret: hidden", rendered)
        self.assertNotIn("abandon", rendered)
        self.assertNotIn(nsec_source.nsec_secret_key, rendered)

    def test_generated_session_sources_reject_invalid_entropy(self) -> None:
        with self.assertRaisesRegex(ValueError, "word count"):
            generate_bip39_session_source("Generated seed", word_count=15, entropy=bytes(20))
        with self.assertRaisesRegex(ValueError, "16 bytes"):
            generate_bip39_session_source("Generated seed", word_count=12, entropy=bytes(15))
        with self.assertRaisesRegex(ValueError, "valid secp256k1 scalar"):
            generate_nsec_session_source("Generated nsec", entropy=bytes(32))

        calls = 0

        def invalid_then_valid(length: int) -> bytes:
            nonlocal calls
            self.assertEqual(length, 32)
            calls += 1
            if calls == 1:
                return bytes(32)
            return bytes.fromhex("02".zfill(64))

        source = generate_nsec_session_source("Generated nsec", random_bytes=invalid_then_valid)

        self.assertEqual(calls, 2)
        self.assertEqual(source.nsec_secret_key, "00" * 31 + "02")

    def test_session_source_backup_review_matches_shared_danger_zone_vectors(self) -> None:
        seed_vector = session_source_backup_vector("seedqr-vector-1-backup")
        nsec_vector = session_source_backup_vector("nsec-test-key-1-backup")
        seed_source = SessionImportSource.bip39_seed(
            "SeedQR vector 1",
            SEEDSIGNER_VECTOR_1["standard_word_indexes"],
        )
        nsec_source = SessionImportSource.nsec(
            "nsec test vector",
            secret_key_from_nsec(TEST_KEY_1_NSEC),
        )

        seed_review = session_source_backup_review(seed_source)
        nsec_review = session_source_backup_review(nsec_source)

        self.assertEqual(seed_review["review_id"], seed_vector["review_id"])
        self.assertEqual(seed_review["approval_digest"], seed_vector["approval_digest"])
        self.assertEqual(seed_review["pages"], seed_vector["pages"])
        self.assertEqual(nsec_review["review_id"], nsec_vector["review_id"])
        self.assertEqual(nsec_review["approval_digest"], nsec_vector["approval_digest"])
        self.assertEqual(nsec_review["pages"], nsec_vector["pages"])

        rendered = json.dumps([seed_review, nsec_review], ensure_ascii=False)
        self.assertIn("Danger: secret export", rendered)
        self.assertIn("Approve to reveal", rendered)
        self.assertNotIn("attack", rendered)
        self.assertNotIn("expire", rendered)
        self.assertNotIn(TEST_KEY_1_NSEC, rendered)
        self.assertNotIn(NIP19_NSEC_VECTOR["secret_key"], rendered)

    def test_session_source_backup_payload_matches_shared_secret_payloads(self) -> None:
        seed_source = SessionImportSource.bip39_seed(
            "SeedQR vector 1",
            SEEDSIGNER_VECTOR_1["standard_word_indexes"],
        )
        nsec_source = SessionImportSource.nsec(
            "nsec test vector",
            secret_key_from_nsec(TEST_KEY_1_NSEC),
        )

        self.assertEqual(
            session_source_backup_payload(seed_source),
            session_source_backup_vector("seedqr-vector-1-backup")["backup_payload"],
        )
        self.assertEqual(
            session_source_backup_payload(nsec_source),
            session_source_backup_vector("nsec-test-key-1-backup")["backup_payload"],
        )

    def test_session_source_backup_flow_reveals_only_after_local_approval(self) -> None:
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))

        approved = run_session_source_backup_flow(source, ["next", "approve"])

        self.assertTrue(approved.approved)
        self.assertTrue(approved.revealed)
        self.assertEqual(approved.backup_payload, {"nsec": TEST_KEY_1_NSEC})
        self.assertEqual(
            approved.transcript,
            [
                SessionSourceBackupTranscriptStep(page_index=0, button="next", decision=None, revealed=False),
                SessionSourceBackupTranscriptStep(page_index=1, button="approve", decision=True, revealed=True),
            ],
        )

        rejected = run_session_source_backup_flow(source, ["reject"])
        self.assertFalse(rejected.approved)
        self.assertFalse(rejected.revealed)
        self.assertIsNone(rejected.backup_payload)
        with self.assertRaisesRegex(ValueError, "approval requires viewing every review page"):
            run_session_source_backup_flow(source, ["approve"])

    def test_session_source_backup_io_reveals_only_after_displayed_approval(self) -> None:
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))
        io = MemorySessionSourceBackupIO(["next", "approve"])

        result = run_session_source_backup_io_flow(source, io)

        self.assertTrue(result.approved)
        self.assertTrue(result.revealed)
        self.assertEqual(result.backup_payload, {"nsec": TEST_KEY_1_NSEC})
        self.assertEqual(io.backup_payloads, [{"nsec": TEST_KEY_1_NSEC}])
        self.assertEqual([page_index for page_index, _frame in io.frames], [0, 1])
        rendered_frames = json.dumps([frame for _page_index, frame in io.frames], ensure_ascii=False)
        self.assertIn("Danger: secret export", rendered_frames)
        self.assertNotIn(TEST_KEY_1_NSEC, rendered_frames)
        self.assertNotIn(NIP19_NSEC_VECTOR["secret_key"], rendered_frames)

    def test_session_source_backup_io_rejection_or_timeout_does_not_emit_payload(self) -> None:
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))
        rejected_io = MemorySessionSourceBackupIO(["reject"])

        rejected = run_session_source_backup_io_flow(source, rejected_io)

        self.assertFalse(rejected.approved)
        self.assertFalse(rejected.revealed)
        self.assertIsNone(rejected.backup_payload)
        self.assertEqual(rejected_io.backup_payloads, [])

        timeout_io = MemorySessionSourceBackupIO(["next", "next"])
        with self.assertRaisesRegex(SessionSourceBackupFlowError, "max button steps"):
            run_session_source_backup_io_flow(source, timeout_io, max_button_steps=1)
        self.assertEqual(timeout_io.backup_payloads, [])
        self.assertEqual([page_index for page_index, _frame in timeout_io.frames], [0])

    def test_session_import_review_matches_shared_secret_hidden_vectors(self) -> None:
        nip06_vector = session_import_review_vector("nip06-account-0-leader")
        seed_vector = session_import_review_vector("seedqr-vector-1")
        nsec_vector = session_import_review_vector("nsec-test-key-1")
        nip06_source = SessionImportSource.bip39_seed(
            "NIP-06 account 0",
            bip39_word_indexes_from_mnemonic(NIP06_KEY["mnemonic"]),
        )
        seed_source = SessionImportSource.bip39_seed(
            "SeedQR vector 1",
            SEEDSIGNER_VECTOR_1["standard_word_indexes"],
        )
        nsec_source = SessionImportSource.nsec(
            "nsec test vector",
            secret_key_from_nsec(TEST_KEY_1_NSEC),
        )

        nip06_review = session_import_review(nip06_source)
        seed_review = session_import_review(seed_source)
        nsec_review = session_import_review(nsec_source)

        self.assertEqual(session_import_source_fingerprint(nip06_source), nip06_vector["fingerprint"])
        self.assertEqual(nip06_review["review_id"], nip06_vector["review_id"])
        self.assertEqual(nip06_review["approval_digest"], nip06_vector["approval_digest"])
        self.assertEqual(nip06_review["pages"], nip06_vector["pages"])
        self.assertEqual(session_import_source_fingerprint(seed_source), seed_vector["fingerprint"])
        self.assertEqual(seed_review["review_id"], seed_vector["review_id"])
        self.assertEqual(seed_review["approval_digest"], seed_vector["approval_digest"])
        self.assertEqual(seed_review["pages"], seed_vector["pages"])
        self.assertEqual(session_import_source_fingerprint(nsec_source), nsec_vector["fingerprint"])
        self.assertEqual(nsec_review["review_id"], nsec_vector["review_id"])
        self.assertEqual(nsec_review["approval_digest"], nsec_vector["approval_digest"])
        self.assertEqual(nsec_review["pages"], nsec_vector["pages"])

        rendered = json.dumps([seed_review, nsec_review], ensure_ascii=False)
        self.assertNotIn("attack", rendered)
        self.assertNotIn("expire", rendered)
        self.assertNotIn(TEST_KEY_1_NSEC, rendered)
        self.assertNotIn(NIP19_NSEC_VECTOR["secret_key"], rendered)
        self.assertIn("Secret: hidden", rendered)

    def test_session_import_review_accepts_mnemonic_index_sources_without_deriving(self) -> None:
        indexes = bip39_word_indexes_from_mnemonic(SEEDSIGNER_VECTOR_1_MNEMONIC)
        source = SessionImportSource.bip39_seed("SeedQR vector 1", indexes)

        review = session_import_review(source)

        self.assertEqual(indexes, tuple(SEEDSIGNER_VECTOR_1["standard_word_indexes"]))
        self.assertEqual(mnemonic_from_bip39_word_indexes(indexes), SEEDSIGNER_VECTOR_1_MNEMONIC)
        self.assertEqual(review["review_id"], session_import_review_vector("seedqr-vector-1")["review_id"])

        with self.assertRaisesRegex(ValueError, "word index count"):
            mnemonic_from_bip39_word_indexes(indexes[:11])
        with self.assertRaisesRegex(ValueError, "outside the English wordlist"):
            mnemonic_from_bip39_word_indexes((*indexes[:-1], 2048))

    def test_session_import_source_secret_derivation_supports_bip39_and_nsec(self) -> None:
        seed_source = SessionImportSource.bip39_seed(
            "SeedQR vector 1",
            bip39_word_indexes_from_mnemonic(NIP06_KEY["mnemonic"]),
        )
        nsec_source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))

        self.assertEqual(
            secret_key_from_session_import_source(
                seed_source,
                account=NIP06_KEY["account"],
                passphrase=NIP06_KEY["passphrase"],
            ),
            NIP06_KEY["secret_key"],
        )
        self.assertEqual(secret_key_from_session_import_source(nsec_source), KEY["secret_key"])

    def test_session_import_source_public_key_proofs_match_shared_vectors(self) -> None:
        nip06_proof = source_public_key_proof_vector("nip06-account-0-leader")
        nsec_proof = source_public_key_proof_vector("nsec-test-key-1")
        nip06_source = SessionImportSource.bip39_seed(
            "NIP-06 account 0",
            tuple(NIP06_KEY["standard_word_indexes"]),
        )
        nsec_source = SessionImportSource.nsec("nsec test vector", NIP19_NSEC_VECTOR["secret_key"])

        self.assertEqual(session_import_source_fingerprint(nip06_source), nip06_proof["source_fingerprint"])
        self.assertEqual(
            public_key_from_session_import_source(
                nip06_source,
                account=nip06_proof["account"],
                passphrase=nip06_proof["passphrase"],
            ),
            nip06_proof["expected_public_key"],
        )
        self.assertEqual(session_import_source_fingerprint(nsec_source), nsec_proof["source_fingerprint"])
        self.assertEqual(
            public_key_from_session_import_source(nsec_source),
            nsec_proof["expected_public_key"],
        )

    def test_session_source_qr_parses_decoded_text_sources(self) -> None:
        nsec_source = parse_session_source_qr_text("nsec QR", f" \n{TEST_KEY_1_NSEC}\t")
        seedqr_source = parse_session_source_qr_text(
            "SeedQR QR",
            f"{SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR[:16]}\n{SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR[16:]}",
        )
        mnemonic_source = parse_session_source_qr_text("mnemonic QR", NIP06_KEY["mnemonic"])
        compact_source = parse_compact_seedqr_session_source(
            "CompactSeedQR QR",
            bytes.fromhex(SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX),
        )

        self.assertEqual(nsec_source, SessionImportSource.nsec("nsec QR", KEY["secret_key"]))
        self.assertEqual(
            seedqr_source,
            SessionImportSource.bip39_seed("SeedQR QR", SEEDSIGNER_VECTOR_1["standard_word_indexes"]),
        )
        self.assertEqual(
            mnemonic_source,
            SessionImportSource.bip39_seed("mnemonic QR", bip39_word_indexes_from_mnemonic(NIP06_KEY["mnemonic"])),
        )
        self.assertEqual(
            compact_source,
            SessionImportSource.bip39_seed("CompactSeedQR QR", SEEDSIGNER_VECTOR_1["standard_word_indexes"]),
        )

        with self.assertRaisesRegex(SessionSourceQrError, "must not be empty"):
            parse_session_source_qr_text("empty", " \n\t")
        with self.assertRaisesRegex(SessionSourceQrError, "checksum is invalid"):
            parse_session_source_qr_text("bad nsec", TEST_KEY_1_NSEC[:-1] + "q")
        with self.assertRaisesRegex(SessionSourceQrError, "mnemonic word is not"):
            parse_session_source_qr_text("bad text", " ".join(["abandon"] * 11 + ["notaword"]))

    def test_session_source_qr_import_flow_loads_only_after_local_approval(self) -> None:
        keyring = StatelessSessionKeyring()

        result = run_session_source_qr_text_import_flow(
            keyring,
            "nsec QR",
            TEST_KEY_1_NSEC,
            ["next", "approve"],
        )

        self.assertTrue(result.approved)
        self.assertTrue(result.loaded)
        self.assertEqual(keyring.size, 1)
        self.assertEqual(keyring.source_at(0), SessionImportSource.nsec("nsec QR", KEY["secret_key"]))

        rejected_keyring = StatelessSessionKeyring()
        rejected = run_compact_seedqr_session_import_flow(
            rejected_keyring,
            "CompactSeedQR QR",
            bytes.fromhex(SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX),
            ["reject"],
        )

        self.assertFalse(rejected.approved)
        self.assertFalse(rejected.loaded)
        self.assertTrue(rejected_keyring.empty)

    def test_session_import_flow_requires_local_approval_before_loading_keyring(self) -> None:
        keyring = StatelessSessionKeyring()
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))

        result = run_session_import_flow(keyring, source, ["next", "approve"])

        self.assertTrue(result.approved)
        self.assertTrue(result.loaded)
        self.assertEqual(result.review["review_id"], session_import_review_vector("nsec-test-key-1")["review_id"])
        self.assertEqual(keyring.size, 1)
        self.assertEqual(keyring.source_at(0), source)
        self.assertEqual(
            result.transcript,
            [
                SessionImportTranscriptStep(page_index=0, button="next", decision=None, loaded=False),
                SessionImportTranscriptStep(page_index=1, button="approve", decision=True, loaded=True),
            ],
        )

    def test_session_import_flow_rejection_does_not_load_keyring(self) -> None:
        keyring = StatelessSessionKeyring()
        source = SessionImportSource.bip39_seed("SeedQR vector 1", SEEDSIGNER_VECTOR_1["standard_word_indexes"])

        result = run_session_import_flow(keyring, source, ["reject"])

        self.assertFalse(result.approved)
        self.assertFalse(result.loaded)
        self.assertEqual(keyring.size, 0)
        self.assertEqual(len(result.transcript), 1)
        self.assertEqual(result.transcript[0].decision, False)
        self.assertFalse(result.transcript[0].loaded)

    def test_session_import_flow_blocks_early_or_nonterminal_approval(self) -> None:
        keyring = StatelessSessionKeyring()
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))

        with self.assertRaisesRegex(ValueError, "approval requires viewing every review page"):
            run_session_import_flow(keyring, source, ["approve"])
        self.assertTrue(keyring.empty)

        with self.assertRaisesRegex(SessionImportFlowError, "did not reach approval or rejection"):
            run_session_import_flow(keyring, source, ["next"])
        self.assertTrue(keyring.empty)

        with self.assertRaisesRegex(SessionImportFlowError, "max button steps"):
            run_session_import_flow(keyring, source, ["next", "next"], max_button_steps=1)
        self.assertTrue(keyring.empty)

    def test_stateless_session_keyring_bounds_sources_and_can_clear(self) -> None:
        keyring = StatelessSessionKeyring(max_sources=1)
        source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))

        keyring.add_source(source)

        self.assertFalse(keyring.empty)
        self.assertEqual(keyring.source_at(0), source)
        self.assertEqual(keyring.public_key_at(0), KEY["public_key"])
        with self.assertRaisesRegex(SessionImportFlowError, "keyring is full"):
            keyring.add_source(source)
        with self.assertRaisesRegex(SessionImportFlowError, "out of range"):
            keyring.source_at(1)
        with self.assertRaisesRegex(SessionImportFlowError, "out of range"):
            keyring.public_key_at(1)
        keyring.clear()
        self.assertTrue(keyring.empty)

    def test_stateless_session_keyring_wipes_internal_sources_on_clear(self) -> None:
        keyring = StatelessSessionKeyring(max_sources=2)
        nsec_source = SessionImportSource.nsec("nsec test vector", secret_key_from_nsec(TEST_KEY_1_NSEC))
        seed_source = SessionImportSource.bip39_seed(
            "SeedQR vector 1",
            bip39_word_indexes_from_mnemonic(NIP06_KEY["mnemonic"]),
        )

        keyring.add_source(nsec_source)
        keyring.add_source(seed_source)
        nsec_entry = keyring._sources[0]
        seed_entry = keyring._sources[1]

        self.assertEqual(nsec_entry.nsec_secret_key.hex(), nsec_source.nsec_secret_key)
        self.assertEqual(seed_entry.bip39_word_indexes, list(seed_source.bip39_word_indexes))

        keyring.clear()

        self.assertTrue(keyring.empty)
        self.assertEqual(nsec_entry.source_type, "wiped")
        self.assertEqual(nsec_entry.label, "")
        self.assertEqual(nsec_entry.nsec_secret_key, bytearray(32))
        self.assertEqual(seed_entry.source_type, "wiped")
        self.assertEqual(seed_entry.label, "")
        self.assertTrue(all(index == 0 for index in seed_entry.bip39_word_indexes))
        with self.assertRaisesRegex(SessionImportFlowError, "out of range"):
            keyring.source_at(0)

    def test_stateless_session_secret_provider_feeds_existing_signing_flow_once(self) -> None:
        keyring = StatelessSessionKeyring()
        source = SessionImportSource.bip39_seed(
            "NIP-06 account",
            bip39_word_indexes_from_mnemonic(NIP06_KEY["mnemonic"]),
        )
        run_session_import_flow(keyring, source, ["next", "approve"])
        provider = StatelessSessionSecretProvider(
            keyring,
            account=NIP06_KEY["account"],
            passphrase=NIP06_KEY["passphrase"],
        )
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["next", "next", "next", "approve"])

        self.assertEqual(provider.public_key(), NIP06_KEY["public_key"])
        result = run_button_qr_vault_flow_with_secret_provider(hardware, provider)

        self.assertTrue(result.approved)
        self.assertEqual(result.response["result"]["event"]["pubkey"], NIP06_KEY["public_key"])
        self.assertEqual(provider.public_key(), NIP06_KEY["public_key"])
        with self.assertRaisesRegex(RuntimeError, "stateless session source has already been consumed"):
            provider()

    def test_button_flow_can_use_word_by_word_mnemonic_session_secret_provider(self) -> None:
        word_input = FakeMnemonicWordInput(NIP06_KEY["mnemonic"].split())
        secret_provider = MnemonicSessionSecretProvider(
            word_input,
            word_count=12,
            account=NIP06_KEY["account"],
            passphrase=NIP06_KEY["passphrase"],
        )
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["next", "next", "next", "approve"])

        result = run_button_qr_vault_flow_with_secret_provider(hardware, secret_provider)

        self.assertTrue(result.approved)
        self.assertEqual(result.response["result"]["event"]["pubkey"], NIP06_KEY["public_key"])
        self.assertEqual(
            result.approval_digest,
            screen_review_for_request(BASIC_REQUEST, author_pubkey=NIP06_KEY["public_key"])["approval_digest"],
        )

    def test_review_model_preserves_raw_event_fields_and_author(self) -> None:
        review = review_event_template(TAGGED_REQUEST["params"]["event_template"])

        self.assertEqual(review["kind"], 1)
        self.assertEqual(review["created_at"], 1710000060)
        self.assertEqual(review["author_pubkey"], KEY["public_key"])
        self.assertEqual(review["content"], "nSealr fixture: tagged kind 1 event.")
        self.assertEqual(review["content_utf8_bytes"], len(review["content"].encode("utf-8")))
        self.assertEqual(review["tag_count"], 2)
        self.assertEqual(review["tags"], TAGGED_REQUEST["params"]["event_template"]["tags"])

    def test_review_model_matches_shared_review_vectors(self) -> None:
        for vector in REVIEW_VECTORS:
            self.assertEqual(
                review_event_template(vector["request"]["params"]["event_template"]),
                vector["review"],
            )

    def test_review_pages_prioritize_raw_event_content_tags_and_decision(self) -> None:
        review = review_event_template(TAGGED_REQUEST["params"]["event_template"])

        pages = render_review_pages(review)

        self.assertEqual(
            pages,
            [
                {
                    "title": "Event",
                    "lines": ["Kind 1", "Created 1710000060", "Author", KEY["public_key"]],
                    "action": "next",
                },
                {
                    "title": "Content",
                    "lines": ["nSealr fixture: tagged kind 1 event."],
                    "action": "next",
                },
                {
                    "title": "Tags",
                    "lines": [
                        "Tag 1/2",
                        "p",
                        KEY["public_key"],
                        "",
                        "mention",
                        "Tag 2/2",
                        "t",
                        "nsealr",
                    ],
                    "action": "next",
                },
                {
                    "title": "Decision",
                    "lines": ["Approve signing only if all pages match."],
                    "action": "approve_or_reject",
                },
            ],
        )

    def test_review_pages_always_end_with_approval_decision(self) -> None:
        review = review_event_template(BASIC_REQUEST["params"]["event_template"])

        pages = render_review_pages(review)

        self.assertEqual(pages[-1]["title"], "Decision")
        self.assertEqual(pages[-1]["lines"], ["Approve signing only if all pages match."])
        self.assertEqual(pages[-1]["action"], "approve_or_reject")

    def test_screen_review_binds_digest_to_request_and_pages(self) -> None:
        screen_review = screen_review_for_request(TAGGED_REVIEW_VECTOR["request"])

        self.assertEqual(screen_review["format"], "screen-pages")
        self.assertEqual(screen_review["request_id"], TAGGED_REVIEW_VECTOR["request"]["request_id"])
        self.assertRegex(screen_review["approval_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            screen_review["approval_digest"],
            approval_digest_for_request(TAGGED_REVIEW_VECTOR["request"]),
        )
        self.assertEqual(screen_review["pages"], render_review_pages(TAGGED_REVIEW_VECTOR["review"]))

    def test_screen_review_matches_shared_review_screen_vectors(self) -> None:
        for vector in SCREEN_REVIEW_VECTORS:
            self.assertEqual(screen_review_for_request(vector["request"]), vector["screen_review"])

    def test_review_transcripts_match_shared_vectors(self) -> None:
        screen_vectors = [vector for vector in REVIEW_TRANSCRIPT_VECTORS if vector.get("review_mode", "screen") == "screen"]
        self.assertEqual(
            [vector["name"] for vector in screen_vectors],
            ["kind-1-basic-approve", "kind-1-basic-reject"],
        )
        for vector in screen_vectors:
            request = decode_qr_envelope(vector["qr_envelope"])
            screen_review = screen_review_for_request(request)

            self.assertEqual(screen_review["approval_digest"], vector["approval_digest"])
            self.assertEqual(
                review_transcript_for_screen_review(screen_review, vector["buttons"]),
                vector["transcript"],
            )

    def test_display_frame_wraps_and_bounds_long_review_lines(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        screen_review = screen_review_for_request(vector["request"])

        frame = render_display_frame(
            screen_review,
            page_index=1,
            limits=DisplayFrameLimits(max_title_chars=12, max_body_lines=3, max_line_chars=20),
        )

        self.assertEqual(frame["title"], "Content")
        self.assertEqual(frame["page_indicator"], f"Page 2/{len(screen_review['pages'])}")
        self.assertEqual(frame["action_hint"], "Next")
        self.assertLessEqual(len(frame["body_lines"]), 3)
        self.assertTrue(all(len(line) <= 20 for line in frame["body_lines"]))
        self.assertTrue(frame["body_lines"][-1].endswith("..."))

    def test_display_frame_rejects_invalid_display_limits(self) -> None:
        screen_review = screen_review_for_request(BASIC_REQUEST)

        with self.assertRaisesRegex(ValueError, "display limits must be positive"):
            render_display_frame(screen_review, page_index=0, limits=DisplayFrameLimits(max_line_chars=0))

    def test_display_frames_match_shared_vectors(self) -> None:
        self.assertCountEqual(
            [vector["name"] for vector in DISPLAY_FRAME_VECTORS],
            [
                "kind-1-long-content-page-1-20x3",
                "kind-1-unicode-boundary-content-4x3",
            ],
        )
        for vector in DISPLAY_FRAME_VECTORS:
            source = json.loads(
                (SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8")
            )

            frame = render_display_frame(
                screen_review_for_request(source["request"]),
                page_index=vector["page_index"],
                limits=DisplayFrameLimits(**vector["limits"]),
            )

            self.assertEqual(frame, vector["frame"])

    def test_review_detail_pages_match_shared_vectors(self) -> None:
        self.assertCountEqual(
            [vector["name"] for vector in REVIEW_DETAIL_PAGE_VECTORS],
            [
                "kind-1-control-escapes-t-display-s3",
                "kind-1-long-events-many-tags-t-display-s3",
                "kind-1-tags-t-display-s3",
                "kind-1-unicode-boundary-t-display-s3",
            ],
        )
        for vector in REVIEW_DETAIL_PAGE_VECTORS:
            source = json.loads(
                (SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8")
            )
            review = review_event_template(source["request"]["params"]["event_template"])

            self.assertEqual(
                render_review_detail_pages(review, limits=ReviewDetailPageLimits(**vector["limits"])),
                vector["pages"],
            )
            self.assertEqual(approval_digest_for_request(source["request"]), vector["approval_digest"])

    def test_physical_approval_requires_viewing_all_review_pages(self) -> None:
        session = ReviewControlSession(screen_review_for_request(TAGGED_REQUEST))

        self.assertEqual(session.current_page["title"], "Event")
        self.assertFalse(session.can_approve)
        with self.assertRaises(ValueError):
            session.approve()

        while session.current_page["action"] != "approve_or_reject":
            self.assertIsNone(session.handle_button("next"))

        self.assertEqual(session.current_page["title"], "Decision")
        self.assertTrue(session.can_approve)
        self.assertTrue(session.handle_button("approve"))

    def test_physical_rejection_is_available_before_final_page(self) -> None:
        session = ReviewControlSession(screen_review_for_request(TAGGED_REQUEST))

        self.assertFalse(session.handle_button("reject"))
        self.assertTrue(session.rejected)
        self.assertFalse(session.approved)

    def test_physical_approval_rejects_invalid_review_page_order(self) -> None:
        screen_review = screen_review_for_request(BASIC_REQUEST)
        screen_review["pages"][0] = dict(screen_review["pages"][0], action="approve_or_reject")

        with self.assertRaises(ValueError):
            ReviewControlSession(screen_review)

    def test_review_model_does_not_infer_unknown_kind_or_long_content_warnings(self) -> None:
        review = review_event_template(
            {
                "created_at": 1710000000,
                "kind": 30078,
                "tags": [],
                "content": "x" * 420,
            }
        )

        self.assertEqual(review["kind"], 30078)
        self.assertEqual(review["content"], "x" * 420)
        self.assertEqual(review["content_utf8_bytes"], 420)
        self.assertNotIn("kind_name", review)
        self.assertNotIn("warnings", review)

    def test_sign_request_requires_explicit_approval(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=False)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["request_id"], BASIC_REQUEST["request_id"])
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_sign_request_returns_signed_event_when_approved(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=True)

        self.assertEqual(response["ok"], True)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_sign_request_rejects_mismatched_approval_digest(self) -> None:
        response = sign_request(BASIC_REQUEST, KEY["secret_key"], approved=True, approval_digest="00" * 32)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["request_id"], BASIC_REQUEST["request_id"])
        self.assertEqual(response["error"]["code"], "approval_digest_mismatch")

        signed = sign_request(
            BASIC_REQUEST,
            KEY["secret_key"],
            approved=True,
            approval_digest=approval_digest_for_request(BASIC_REQUEST),
        )
        self.assertEqual(signed["ok"], True)
        self.assert_valid_signed_event(signed["result"]["event"])

    def test_qr_vault_flow_binds_display_digest_before_signing(self) -> None:
        hardware = MemoryQrVaultIO(encode_qr_envelope(BASIC_REQUEST), approved=True)

        result = run_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.screen_review, screen_review_for_request(BASIC_REQUEST))
        self.assertEqual(result.approval_digest, hardware.screen_review["approval_digest"])
        self.assertTrue(result.approved)
        self.assertIsNotNone(hardware.response_qr)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_file_qr_vault_io_writes_review_and_response_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            response_path = Path(temp_root) / "response.qr"
            response_qr = encode_qr_envelope({"version": 1, "request_id": "req-file-io", "ok": False})
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST) + "\n", encoding="utf-8")

            adapter = FileQrVaultIO(request_path, review_path, response_path, approved=True)

            self.assertEqual(adapter.scan_request_qr(), encode_qr_envelope(BASIC_REQUEST))
            self.assertTrue(adapter.show_review(screen_review_for_request(BASIC_REQUEST)))
            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            adapter.emit_response_qr(response_qr)
            self.assertEqual(response_path.read_text(encoding="utf-8"), response_qr + "\n")

    def test_file_button_qr_vault_io_records_display_frames_and_buttons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            response_path = Path(temp_root) / "response.qr"
            frame_log_path = Path(temp_root) / "display-frames.json"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST) + "\n", encoding="utf-8")
            screen_review = screen_review_for_request(BASIC_REQUEST)
            frame = render_display_frame(screen_review, 0)

            adapter = FileButtonQrVaultIO(
                request_path,
                review_path,
                response_path,
                ["next", "reject"],
                display_frame_log=frame_log_path,
            )

            self.assertEqual(adapter.scan_request_qr(), encode_qr_envelope(BASIC_REQUEST))
            adapter.display_review_frame(screen_review, 0, frame)
            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review)
            self.assertEqual(json.loads(frame_log_path.read_text(encoding="utf-8")), [frame])
            self.assertEqual(adapter.read_review_button(), "next")
            self.assertEqual(adapter.read_review_button(), "reject")
            with self.assertRaisesRegex(RuntimeError, "button sequence ended before approval or rejection"):
                adapter.read_review_button()

    def test_composed_button_qr_vault_io_delegates_to_adapter_boundaries(self) -> None:
        scanner = FakeQrScanner(encode_qr_envelope(BASIC_REQUEST))
        display = FakeReviewDisplay()
        buttons = FakeButtonInput(["next", "next", "next", "approve"])
        response_display = FakeResponseQrDisplay()
        adapter = ComposedButtonQrVaultIO(
            scanner=scanner,
            review_display=display,
            button_input=buttons,
            response_display=response_display,
        )

        result = run_button_qr_vault_flow(adapter, KEY["secret_key"])

        self.assertEqual(scanner.calls, 1)
        self.assertEqual(display.frames, [(0, "Event"), (1, "Content"), (2, "Tags"), (3, "Decision")])
        self.assertTrue(result.approved)
        self.assertIsNotNone(response_display.response_qr)
        response = decode_qr_envelope(response_display.response_qr)
        self.assert_valid_signed_event(response["result"]["event"])

    def test_button_qr_vault_flow_requires_page_traversal_before_approval(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(TAGGED_REQUEST), ["next", "next", "next", "approve"])

        result = run_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.displayed_pages, [(0, "Event"), (1, "Content"), (2, "Tags"), (3, "Decision")])
        self.assertEqual(result.approval_digest, screen_review_for_request(TAGGED_REQUEST)["approval_digest"])
        self.assertTrue(result.approved)
        self.assertIsNotNone(hardware.response_qr)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_button_qr_vault_flow_accepts_animated_request_scan(self) -> None:
        animated_request = "\n".join(encode_animated_qr_envelope_frames(TAGGED_REQUEST, chunk_size_chars=32))
        hardware = MemoryButtonQrVaultIO(animated_request, ["next", "next", "next", "approve"])

        result = run_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertTrue(result.approved)
        self.assertEqual(result.request_id, TAGGED_REQUEST["request_id"])
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_button_qr_vault_flow_allows_early_rejection(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])

        result = run_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(hardware.displayed_pages, [(0, "Event")])
        self.assertFalse(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assertEqual(response["ok"], False)
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_button_qr_vault_flow_uses_secret_provider_for_approved_session_author(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(TAGGED_REQUEST), ["next", "next", "next", "approve"])
        provider_calls: list[str] = []

        def secret_provider() -> str:
            provider_calls.append("loaded")
            return KEY["secret_key"]

        result = run_button_qr_vault_flow_with_secret_provider(hardware, secret_provider)

        self.assertEqual(provider_calls, ["loaded"])
        self.assertTrue(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_button_qr_vault_flow_loads_key_before_rejection_to_bind_author(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])
        provider_calls: list[str] = []

        def secret_provider() -> str:
            provider_calls.append("loaded")
            return KEY["secret_key"]

        result = run_button_qr_vault_flow_with_secret_provider(hardware, secret_provider)

        self.assertEqual(provider_calls, ["loaded"])
        self.assertFalse(result.approved)
        response = decode_qr_envelope(hardware.response_qr)
        self.assertEqual(response["ok"], False)
        self.assertEqual(response["error"]["code"], "user_rejected")

    def test_button_qr_vault_flow_rejects_non_terminal_button_stream(self) -> None:
        hardware = NextOnlyButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST))

        with self.assertRaisesRegex(RuntimeError, "button review flow did not reach approval or rejection"):
            run_button_qr_vault_flow(hardware, KEY["secret_key"], max_button_steps=5)

        self.assertEqual(len(hardware.displayed_pages), 5)
        self.assertEqual(hardware.displayed_pages[-1], (3, "Decision"))
        self.assertIsNone(hardware.response_qr)

    def test_button_qr_vault_flow_requires_positive_step_limit(self) -> None:
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(BASIC_REQUEST), ["reject"])

        with self.assertRaisesRegex(ValueError, "button review flow max steps must be positive"):
            run_button_qr_vault_flow(hardware, KEY["secret_key"], max_button_steps=0)

        self.assertEqual(hardware.displayed_pages, [])
        self.assertIsNone(hardware.response_qr)

    def test_button_qr_vault_flow_matches_shared_review_transcript_vectors(self) -> None:
        for vector in REVIEW_TRANSCRIPT_VECTORS:
            hardware = MemoryButtonQrVaultIO(vector["qr_envelope"], list(vector["buttons"]))
            if vector.get("review_mode", "screen") == "detail":
                detail_vector = next(
                    item for item in REVIEW_DETAIL_PAGE_VECTORS if item["name"] == vector["detail_review_vector"]
                )
                result = run_detail_button_qr_vault_flow(
                    hardware,
                    KEY["secret_key"],
                    detail_limits=ReviewDetailPageLimits(**detail_vector["limits"]),
                    response_encoder=lambda response: "\n".join(encode_animated_qr_envelope_frames(response)),
                )
            else:
                result = run_button_qr_vault_flow(
                    hardware,
                    KEY["secret_key"],
                    display_limits=DisplayFrameLimits(max_line_chars=64),
                )

            self.assertEqual(result.review_transcript, vector["transcript"])
            self.assertEqual(result.approval_digest, vector["approval_digest"])
            self.assertEqual(result.approved, vector["transcript"][-1]["approved_for_signing"])

    def test_detail_button_qr_vault_flow_uses_logical_pages_without_forced_scroll(self) -> None:
        request = SCROLL_DETAIL_REQUEST
        hardware = MemoryButtonQrVaultIO(encode_qr_envelope(request), ["next", "next", "next", "approve"])

        result = run_detail_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(
            [(frame["title"], frame["page_indicator"]) for frame in hardware.frames],
            [
                ("Event", "Page 1/4"),
                ("Content", "Page 2/4"),
                ("Tags", "Page 3/4 Lines 1-9/12"),
                ("Decision", "Page 4/4"),
            ],
        )
        self.assertEqual(hardware.frames[2]["action_hint"], "Next/Scroll")
        self.assertEqual(
            result.approval_digest,
            screen_review_for_request(request, author_pubkey=KEY["public_key"])["approval_digest"],
        )
        self.assertTrue(result.approved)

    def test_detail_button_qr_vault_flow_scrolls_inside_logical_page(self) -> None:
        request = SCROLL_DETAIL_REQUEST
        hardware = MemoryButtonQrVaultIO(
            encode_qr_envelope(request),
            ["next", "next", "scroll", "next", "approve"],
        )

        result = run_detail_button_qr_vault_flow(hardware, KEY["secret_key"])

        self.assertEqual(
            [(frame["title"], frame["page_indicator"]) for frame in hardware.frames],
            [
                ("Event", "Page 1/4"),
                ("Content", "Page 2/4"),
                ("Tags", "Page 3/4 Lines 1-9/12"),
                ("Tags", "Page 3/4 Lines 10-12/12"),
                ("Decision", "Page 4/4"),
            ],
        )
        self.assertTrue(result.approved)

    def test_detail_review_frame_preserves_page_indicator_and_styles(self) -> None:
        vector = next(item for item in REVIEW_DETAIL_PAGE_VECTORS if item["name"] == "kind-1-long-events-many-tags-t-display-s3")
        detail_review = {
            "format": "review-detail-pages-v0",
            "approval_digest": vector["approval_digest"],
            "pages": vector["pages"],
        }

        frame = render_review_detail_frame(detail_review, 2)

        self.assertEqual(frame["title"], "Tags")
        self.assertEqual(frame["page_indicator"], "Page 3/4 Lines 1-9/29")
        self.assertEqual(frame["body_lines"], vector["pages"][2]["lines"])
        self.assertEqual(frame["body_line_styles"], vector["pages"][2]["body_line_styles"])

    def test_cli_signs_qr_request_and_outputs_qr_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_signs_animated_qr_request_and_outputs_animated_qr_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qra"
            response_path = Path(temp_root) / "response.qra"
            request_path.write_text("\n".join(encode_animated_qr_envelope_frames(BASIC_REQUEST)) + "\n", encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr-animated",
                    "--output-format",
                    "qr-animated",
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            response_frames = response_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreater(len(response_frames), 1)
            response = decode_animated_qr_envelope_frames(response_frames)
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_signs_qr_request_from_nip06_mnemonic_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            mnemonic_path = Path(temp_root) / "mnemonic.txt"
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            mnemonic_path.write_text(NIP06_KEY["mnemonic"] + "\n", encoding="utf-8")
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--mnemonic-file",
                    str(mnemonic_path),
                    "--account",
                    str(NIP06_KEY["account"]),
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_signs_qr_request_from_stdin_secret_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--secret-key-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=KEY["secret_key"] + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_signs_qr_request_from_stdin_nip06_mnemonic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--mnemonic-stdin",
                    "--account",
                    str(NIP06_KEY["account"]),
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=NIP06_KEY["mnemonic"] + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_signs_qr_request_from_stdin_mnemonic_words(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--mnemonic-words-stdin",
                    "--mnemonic-word-count",
                    "12",
                    "--account",
                    str(NIP06_KEY["account"]),
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input="\n".join(NIP06_KEY["mnemonic"].split()) + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_signs_qr_request_from_standard_seedqr_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")
            expected_public_key = sign_event(
                BASIC_REQUEST["params"]["event_template"],
                derive_nip06_secret(SEEDSIGNER_VECTOR_1_MNEMONIC),
            )["pubkey"]

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--seedqr-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], expected_public_key)

    def test_cli_signs_qr_request_from_compact_seedqr_hex_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")
            expected_public_key = sign_event(
                BASIC_REQUEST["params"]["event_template"],
                derive_nip06_secret(SEEDSIGNER_VECTOR_1_MNEMONIC),
            )["pubkey"]

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--compact-seedqr-hex-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=SEEDSIGNER_VECTOR_1_COMPACT_SEEDQR_HEX + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], expected_public_key)

    def test_cli_signs_qr_request_from_nsec_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--nsec-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_rejects_invalid_seedqr_without_writing_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--seedqr-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input="not-a-seedqr\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SeedQR digit stream must contain only digits", result.stderr)
            self.assertFalse(response_path.exists())

    def test_cli_rejects_invalid_nsec_without_writing_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "sign",
                    "--nsec-stdin",
                    "--request",
                    str(request_path),
                    "--response",
                    str(response_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "qr",
                    "--approve",
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC[:-1] + "q\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("nsec bech32 checksum is invalid", result.stderr)
            self.assertFalse(response_path.exists())

    def test_cli_review_import_writes_secret_hidden_seedqr_review(self) -> None:
        vector = session_import_review_vector("seedqr-vector-1")
        with tempfile.TemporaryDirectory() as temp_root:
            review_path = Path(temp_root) / "import-review.json"

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review-import",
                    "--seedqr-stdin",
                    "--label",
                    "SeedQR vector 1",
                    "--out",
                    str(review_path),
                ],
                cwd=ROOT,
                input=SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR + "\n",
                text=True,
                check=True,
            )

            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["review_id"], vector["review_id"])
            self.assertEqual(review["approval_digest"], vector["approval_digest"])
            self.assertEqual(review["pages"], vector["pages"])
            rendered = json.dumps(review, ensure_ascii=False)
            for word in SEEDSIGNER_VECTOR_1_MNEMONIC.split():
                self.assertNotIn(word, rendered)

    def test_cli_review_import_writes_secret_hidden_nsec_review(self) -> None:
        vector = session_import_review_vector("nsec-test-key-1")
        with tempfile.TemporaryDirectory() as temp_root:
            review_path = Path(temp_root) / "import-review.json"

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review-import",
                    "--nsec-stdin",
                    "--label",
                    "nsec test vector",
                    "--out",
                    str(review_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                text=True,
                check=True,
            )

            review = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review["review_id"], vector["review_id"])
            self.assertEqual(review["approval_digest"], vector["approval_digest"])
            self.assertEqual(review["pages"], vector["pages"])
            rendered = json.dumps(review, ensure_ascii=False)
            self.assertNotIn(TEST_KEY_1_NSEC, rendered)
            self.assertNotIn(NIP19_NSEC_VECTOR["secret_key"], rendered)
            self.assertIn("Secret: hidden", rendered)

    def test_cli_review_import_rejects_invalid_source_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            review_path = Path(temp_root) / "import-review.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review-import",
                    "--seedqr-stdin",
                    "--label",
                    "bad source",
                    "--out",
                    str(review_path),
                ],
                cwd=ROOT,
                input="not-a-seedqr\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SeedQR digit stream must contain only digits", result.stderr)
            self.assertFalse(review_path.exists())

    def test_cli_review_import_rejects_empty_label_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            review_path = Path(temp_root) / "import-review.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review-import",
                    "--nsec-stdin",
                    "--label",
                    "",
                    "--out",
                    str(review_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session import label must not be empty", result.stderr)
            self.assertFalse(review_path.exists())

    def test_cli_backup_source_reveals_nsec_only_after_final_approval(self) -> None:
        vector = session_source_backup_vector("nsec-test-key-1-backup")
        with tempfile.TemporaryDirectory() as temp_root:
            backup_path = Path(temp_root) / "backup-result.json"

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "backup-source",
                    "--nsec-stdin",
                    "--label",
                    "nsec test vector",
                    "--button-sequence",
                    "next,approve",
                    "--out",
                    str(backup_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                text=True,
                check=True,
            )

            result = json.loads(backup_path.read_text(encoding="utf-8"))
            self.assertEqual(result["format"], "nsealr-session-source-backup-result-v0")
            self.assertTrue(result["approved"])
            self.assertTrue(result["revealed"])
            self.assertEqual(result["backup_payload"], vector["backup_payload"])
            self.assertEqual(result["review"]["review_id"], vector["review_id"])
            self.assertEqual(result["review"]["approval_digest"], vector["approval_digest"])
            self.assertEqual(result["review"]["pages"], vector["pages"])
            self.assertEqual(
                result["transcript"],
                [
                    {"page_index": 0, "button": "next", "decision": None, "revealed": False},
                    {"page_index": 1, "button": "approve", "decision": True, "revealed": True},
                ],
            )
            review_json = json.dumps(result["review"], ensure_ascii=False)
            self.assertNotIn(TEST_KEY_1_NSEC, review_json)
            self.assertNotIn(NIP19_NSEC_VECTOR["secret_key"], review_json)

    def test_cli_backup_source_rejects_without_revealing_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            backup_path = Path(temp_root) / "backup-result.json"

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "backup-source",
                    "--nsec-stdin",
                    "--label",
                    "nsec test vector",
                    "--button-sequence",
                    "reject",
                    "--out",
                    str(backup_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                text=True,
                check=True,
            )

            result = json.loads(backup_path.read_text(encoding="utf-8"))
            self.assertFalse(result["approved"])
            self.assertFalse(result["revealed"])
            self.assertIsNone(result["backup_payload"])
            self.assertEqual(
                result["transcript"],
                [{"page_index": 0, "button": "reject", "decision": False, "revealed": False}],
            )

    def test_cli_backup_source_rejects_early_approval_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            backup_path = Path(temp_root) / "backup-result.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "backup-source",
                    "--nsec-stdin",
                    "--label",
                    "nsec test vector",
                    "--button-sequence",
                    "approve",
                    "--out",
                    str(backup_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approval requires viewing every review page", result.stderr)
            self.assertFalse(backup_path.exists())

    def test_cli_backup_source_rejects_scroll_without_writing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            backup_path = Path(temp_root) / "backup-result.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "backup-source",
                    "--nsec-stdin",
                    "--label",
                    "nsec test vector",
                    "--button-sequence",
                    "scroll",
                    "--out",
                    str(backup_path),
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unsupported button action: scroll", result.stderr)
            self.assertFalse(backup_path.exists())

    def test_cli_reviews_qr_request_without_secret_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review.json"
            request_path.write_text(encode_qr_envelope(TAGGED_REVIEW_VECTOR["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), TAGGED_REVIEW_VECTOR["review"])

    def test_cli_review_can_write_screen_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            request_path.write_text(encode_qr_envelope(TAGGED_REVIEW_VECTOR["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "screen-json",
                ],
                cwd=ROOT,
                check=True,
            )

            review_output = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review_output["format"], "screen-pages")
            self.assertEqual(review_output["request_id"], TAGGED_REVIEW_VECTOR["request"]["request_id"])
            self.assertRegex(review_output["approval_digest"], r"^[0-9a-f]{64}$")
            self.assertEqual(review_output["pages"][-1]["action"], "approve_or_reject")

    def test_cli_review_can_bind_explicit_author_pubkey(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "screen-json",
                    "--author-pubkey",
                    NIP06_KEY["public_key"],
                ],
                cwd=ROOT,
                check=True,
            )

            review_output = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review_output["pages"][0]["lines"], ["Kind 1", "Created 1710000000", "Author", NIP06_KEY["public_key"]])

    def test_cli_review_can_write_bounded_display_frame_json(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            frame_path = Path(temp_root) / "display-frame.json"
            request_path.write_text(encode_qr_envelope(vector["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(frame_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "display-frame-json",
                    "--display-page",
                    "1",
                    "--max-line-chars",
                    "20",
                    "--max-body-lines",
                    "3",
                ],
                cwd=ROOT,
                check=True,
            )

            frame = json.loads(frame_path.read_text(encoding="utf-8"))
            self.assertEqual(frame["title"], "Content")
            self.assertLessEqual(len(frame["body_lines"]), 3)
            self.assertTrue(all(len(line) <= 20 for line in frame["body_lines"]))
            self.assertTrue(frame["body_lines"][-1].endswith("..."))

    def test_cli_review_can_write_detail_pages_json(self) -> None:
        vector = next(item for item in REVIEW_DETAIL_PAGE_VECTORS if item["name"] == "kind-1-tags-t-display-s3")
        source = json.loads((SPECS / f"vectors/review/{vector['source_review_vector']}.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            detail_pages_path = Path(temp_root) / "review-detail-pages.json"
            request_path.write_text(encode_qr_envelope(source["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(detail_pages_path),
                    "--input-format",
                    "qr",
                    "--output-format",
                    "detail-pages-json",
                    "--max-title-chars",
                    str(vector["limits"]["max_title_chars"]),
                    "--max-line-chars",
                    str(vector["limits"]["max_line_chars"]),
                    "--max-body-lines",
                    str(vector["limits"]["max_body_lines"]),
                    "--max-compact-line-chars",
                    str(vector["limits"]["max_compact_line_chars"]),
                    "--max-compact-body-lines",
                    str(vector["limits"]["max_compact_body_lines"]),
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(detail_pages_path.read_text(encoding="utf-8")), vector["pages"])

    def test_cli_flow_writes_review_screen_and_signed_response_qr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_can_emit_animated_qr_response_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qra"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--output-format",
                    "qr-animated",
                    "--approve",
                ],
                cwd=ROOT,
                check=True,
            )

            response_frames = response_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreater(len(response_frames), 1)
            response = decode_animated_qr_envelope_frames(response_frames)
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_accepts_button_sequence_for_physical_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_can_read_secret_key_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key-stdin",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                input=KEY["secret_key"] + "\n",
                text=True,
                check=True,
            )

            self.assertEqual(json.loads(review_path.read_text(encoding="utf-8")), screen_review_for_request(BASIC_REQUEST))
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_can_read_nip06_mnemonic_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--mnemonic-stdin",
                    "--account",
                    str(NIP06_KEY["account"]),
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                input=NIP06_KEY["mnemonic"] + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_flow_can_read_mnemonic_words_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--mnemonic-words-stdin",
                    "--mnemonic-word-count",
                    "12",
                    "--account",
                    str(NIP06_KEY["account"]),
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                input="\n".join(NIP06_KEY["mnemonic"].split()) + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], NIP06_KEY["public_key"])

    def test_cli_flow_can_read_standard_seedqr_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")
            expected_public_key = sign_event(
                BASIC_REQUEST["params"]["event_template"],
                derive_nip06_secret(SEEDSIGNER_VECTOR_1_MNEMONIC),
            )["pubkey"]

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--seedqr-stdin",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                input=SEEDSIGNER_VECTOR_1_STANDARD_SEEDQR + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], expected_public_key)

    def test_cli_flow_can_read_nsec_from_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--nsec-stdin",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                ],
                cwd=ROOT,
                input=TEST_KEY_1_NSEC + "\n",
                text=True,
                check=True,
            )

            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event(response["result"]["event"])

    def test_cli_flow_rejects_early_button_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "approve",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approval requires viewing every review page", result.stderr)
            self.assertFalse(response_path.exists())

    def test_cli_flow_can_write_display_frame_log_for_button_sequence(self) -> None:
        vector = next(item for item in REVIEW_VECTORS if item["name"] == "kind-1-long-events-many-tags")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            frame_log_path = Path(temp_root) / "display-frames.json"
            request_path.write_text(encode_qr_envelope(vector["request"]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,reject",
                    "--display-frame-log",
                    str(frame_log_path),
                    "--max-line-chars",
                    "20",
                    "--max-body-lines",
                    "3",
                ],
                cwd=ROOT,
                check=True,
            )

            frames = json.loads(frame_log_path.read_text(encoding="utf-8"))
            self.assertEqual([frame["title"] for frame in frames], ["Event", "Content"])
            self.assertLessEqual(len(frames[1]["body_lines"]), 3)
            self.assertTrue(all(len(line) <= 20 for line in frames[1]["body_lines"]))
            self.assertTrue(frames[1]["body_lines"][-1].endswith("..."))

    def test_cli_flow_can_write_st7789_layout_log_for_button_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            layout_log_path = Path(temp_root) / "display-layout.json"
            request_path.write_text(encode_qr_envelope(BASIC_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,reject",
                    "--st7789-layout-log",
                    str(layout_log_path),
                ],
                cwd=ROOT,
                check=True,
            )

            layouts = json.loads(layout_log_path.read_text(encoding="utf-8"))
            self.assertEqual(len(layouts), 2)
            self.assertTrue(any(command["role"] == "title" for command in layouts[0]))
            self.assertTrue(any(command["role"] == "action_hint" for command in layouts[0]))
            for layout in layouts:
                for command in layout:
                    self.assertLessEqual(command["x"] + command["width"], 240)
                    self.assertLessEqual(command["y"] + command["height"], 240)

    def test_cli_flow_can_write_review_transcript_log_for_button_sequence(self) -> None:
        vector = next(item for item in REVIEW_TRANSCRIPT_VECTORS if item["name"] == "kind-1-basic-approve")
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-screen.json"
            response_path = Path(temp_root) / "response.qr"
            transcript_log_path = Path(temp_root) / "review-transcript.json"
            request_path.write_text(vector["qr_envelope"], encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    ",".join(vector["buttons"]),
                    "--review-transcript-log",
                    str(transcript_log_path),
                    "--max-line-chars",
                    "64",
                ],
                cwd=ROOT,
                check=True,
            )

            self.assertEqual(json.loads(transcript_log_path.read_text(encoding="utf-8")), vector["transcript"])

    def test_cli_flow_can_use_detail_review_pages_for_button_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.qr"
            review_path = Path(temp_root) / "review-detail.json"
            response_path = Path(temp_root) / "response.qr"
            request_path.write_text(encode_qr_envelope(TAGGED_REQUEST), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "flow",
                    "--secret-key",
                    KEY["secret_key"],
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                    "--response",
                    str(response_path),
                    "--button-sequence",
                    "next,next,next,approve",
                    "--review-mode",
                    "detail",
                ],
                cwd=ROOT,
                check=True,
            )

            review_output = json.loads(review_path.read_text(encoding="utf-8"))
            self.assertEqual(review_output["format"], "review-detail-pages-v0")
            self.assertEqual(review_output["pages"][2]["page_indicator"], "Page 3/4")
            response = decode_qr_envelope(response_path.read_text(encoding="utf-8").strip())
            self.assert_valid_signed_event_for_pubkey(response["result"]["event"], KEY["public_key"])

    def test_cli_review_rejects_host_supplied_event_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            request_path = Path(temp_root) / "request.json"
            review_path = Path(temp_root) / "review.json"
            request = json.loads(json.dumps(TAGGED_REVIEW_VECTOR["request"]))
            request["params"]["event_template"]["id"] = "00" * 32
            request_path.write_text(json.dumps(request), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nsealr_vault",
                    "review",
                    "--request",
                    str(request_path),
                    "--review",
                    str(review_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("event_template contains forbidden fields", result.stderr)
            self.assertFalse(review_path.exists())

    def test_os_profile_notes_pin_stateless_qr_vault_constraints(self) -> None:
        text = (ROOT / "os/stateless-qr-vault-profile.md").read_text(encoding="utf-8")

        self.assertIn("nSealr/hardware", text)
        self.assertIn("removable microSD", text)
        self.assertIn("no swap", text)
        self.assertIn("no remote access", text)
        self.assertIn("RAM-only", text)
        self.assertIn("seed files", text)
        self.assertIn("command-line secret arguments", text)
        self.assertIn("not a downloadable OS image", text)
        self.assertIn("does not add or require TROPIC01", text)

    def test_identity_policy_docs_pin_manual_stateless_route(self) -> None:
        route = RASPBERRY_ACCOUNT_DESCRIPTOR["signer_route"]
        selection = RASPBERRY_ROUTE_SELECTION["selection"]
        self.assertEqual(route["type"], "raspberry_qr_vault")
        self.assertEqual(route["repository"], "raspberry")
        self.assertEqual(route["transport"], "qr")
        self.assertEqual(route["custody"], "stateless_session")
        self.assertEqual(route["trusted_review"], "device_display")
        self.assertEqual(route["policy_support"], "manual_only")
        self.assertTrue(RASPBERRY_ACCOUNT_DESCRIPTOR["capabilities"]["physical_review"])
        self.assertTrue(RASPBERRY_ACCOUNT_DESCRIPTOR["capabilities"]["physical_approval"])
        self.assertFalse(RASPBERRY_ACCOUNT_DESCRIPTOR["capabilities"]["persistent_grants"])
        self.assertEqual(
            RASPBERRY_ACCOUNT_DESCRIPTOR["recovery"]["source_fingerprint"],
            session_import_review_vector("nip06-account-0-leader")["fingerprint"],
        )
        self.assertEqual(RASPBERRY_ACCOUNT_DESCRIPTOR["policy_profile_id"], MANUAL_QR_POLICY["policy_id"])
        self.assertEqual(selection["account_id"], RASPBERRY_ACCOUNT_DESCRIPTOR["account_id"])
        self.assertEqual(selection["route_type"], route["type"])
        self.assertEqual(selection["repository"], route["repository"])
        self.assertEqual(selection["transport"], route["transport"])
        self.assertEqual(selection["custody"], route["custody"])
        self.assertEqual(selection["trusted_review"], route["trusted_review"])
        self.assertEqual(selection["policy_support"], route["policy_support"])
        self.assertFalse(selection["persistent_grants"])
        self.assertFalse(selection["contains_secret_material"])

        docs = "\n".join(
            [
                (ROOT / "README.md").read_text(encoding="utf-8"),
                (ROOT / "docs/architecture.md").read_text(encoding="utf-8"),
                (ROOT / "docs/roadmap.md").read_text(encoding="utf-8"),
                (ROOT / "docs/testing.md").read_text(encoding="utf-8"),
            ]
        )
        self.assertIn("nsealr-account-descriptor-v0", docs)
        self.assertIn("raspberry_qr_vault", docs)
        self.assertIn("policy-manual-only-qr-vault", docs)
        self.assertIn("persistent_grants: false", docs)
        self.assertNotIn("legacy screen pages", (ROOT / "app/nsealr_vault/cli.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
