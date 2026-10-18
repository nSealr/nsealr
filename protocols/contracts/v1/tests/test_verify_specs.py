from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.verify_specs import (
    check_access_surface_vector,
    check_smartcard_apdu_vector,
    check_device_security_profile_vector,
    check_feature_matrix_vector,
    check_review_detail_page_vector,
    check_review_transcript_vector,
    check_seedqr_vector,
    check_session_import_review_vector,
    check_session_source_backup_vector,
    check_source_public_key_proof_vector,
    check_static_qr_vector,
    check_nip46_bridge_decisions,
    check_nip19_nsec_vector,
    check_nip46_connection_uri_vector,
    check_nip46_policy_file_vector,
    check_policy_decision_vector,
    check_policy_change_review_vector,
    check_route_refusal_contract_vector,
    check_invalid_vector,
    json_utf8_size,
    implementation_limits,
    invalid_vector_names,
    load_json,
    nip46_policy_file_vector_names,
    nip46_connection_uri_vector_names,
    nip19_nsec_vector_names,
    nip46_vector_names,
    policy_decision_vector_names,
    policy_change_review_vector_names,
    review_detail_page_vector_names,
    review_display_frame_vector_names,
    review_screen_vector_names,
    review_transcript_vector_names,
    seedqr_vector_names,
    review_vector_names,
    route_refusal_contract_vector_names,
    smartcard_apdu_vector_names,
    session_import_review_vector_names,
    session_source_backup_vector_names,
    source_public_key_proof_vector_names,
    access_surface_vector_names,
    display_safe_text,
    device_security_profile_vector_names,
    feature_matrix_vector_names,
)
import scripts.verify_specs as verify_specs


ROOT = Path(__file__).resolve().parents[1]


def vector_names_from_dir(relative: str) -> list[str]:
    return sorted(path.stem for path in (ROOT / relative).glob("*.json"))


class VerifySpecsTests(unittest.TestCase):
    def test_review_vector_names_are_discovered_from_directory(self) -> None:
        names = review_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/review"))
        self.assertIn("kind-1-control-escapes", names)
        self.assertIn("kind-1-basic", names)
        self.assertIn("kind-1-unicode-boundary", names)

    def test_review_screen_vector_names_are_discovered_from_directory(self) -> None:
        names = review_screen_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/review-screens"))
        self.assertIn("kind-1-basic", names)

    def test_review_display_frame_vector_names_are_discovered_from_directory(self) -> None:
        names = review_display_frame_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/review-display-frames"))
        self.assertIn("kind-1-long-content-page-1-20x3", names)
        self.assertIn("kind-1-unicode-boundary-content-4x3", names)

    def test_review_detail_page_vector_names_are_discovered_from_directory(self) -> None:
        names = review_detail_page_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/review-detail-pages"))
        self.assertIn("kind-1-control-escapes-t-display-s3", names)
        self.assertIn("kind-1-long-events-many-tags-t-display-s3", names)
        self.assertIn("kind-1-tags-t-display-s3", names)
        self.assertIn("kind-1-unicode-boundary-t-display-s3", names)

    def test_review_detail_page_vectors_validate_complete_display_pages(self) -> None:
        for name in review_detail_page_vector_names():
            errors: list[str] = []

            check_review_detail_page_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_review_detail_page_vectors_reject_body_style_length_drift(self) -> None:
        vector = deepcopy(load_json("vectors/review-detail-pages/kind-1-tags-t-display-s3.json"))
        vector["name"] = "mutated-detail-style-length"
        vector["pages"][2]["body_line_styles"].pop()
        source = load_json("vectors/review/kind-1-tags.json")
        screen = load_json("vectors/review-screens/kind-1-tags.json")

        def load_mutation(path: str, errors: list[str]) -> dict:
            if path == "vectors/review-detail-pages/mutated-detail-style-length.json":
                return vector
            if path == "vectors/review/kind-1-tags.json":
                return source
            if path == "vectors/review-screens/kind-1-tags.json":
                return screen
            return load_json(path)

        errors: list[str] = []
        with patch("scripts.verify_specs.load_required_json", side_effect=load_mutation):
            check_review_detail_page_vector("mutated-detail-style-length", errors)

        self.assertIn("body_line_styles length must match lines", "\n".join(errors))

    def test_review_detail_page_vectors_reject_continuation_style_drift(self) -> None:
        vector = deepcopy(load_json("vectors/review-detail-pages/kind-1-tags-t-display-s3.json"))
        vector["name"] = "mutated-detail-continuation-style"
        vector["pages"][2]["body_line_styles"][3] = "normal"
        source = load_json("vectors/review/kind-1-tags.json")
        screen = load_json("vectors/review-screens/kind-1-tags.json")

        def load_mutation(path: str, errors: list[str]) -> dict:
            if path == "vectors/review-detail-pages/mutated-detail-continuation-style.json":
                return vector
            if path == "vectors/review/kind-1-tags.json":
                return source
            if path == "vectors/review-screens/kind-1-tags.json":
                return screen
            return load_json(path)

        errors: list[str] = []
        with patch("scripts.verify_specs.load_required_json", side_effect=load_mutation):
            check_review_detail_page_vector("mutated-detail-continuation-style", errors)

        self.assertIn("continuation lines must use value style", "\n".join(errors))

    def test_display_safe_text_renders_json_control_escapes_visibly(self) -> None:
        self.assertEqual(
            display_safe_text("line 1\nline 2\tTabbed\rCarriage\bBackspace\fFormfeed"),
            "line 1\\nline 2\\tTabbed\\rCarriage\\bBackspace\\fFormfeed",
        )

    def test_review_transcript_vector_names_are_discovered_from_directory(self) -> None:
        names = review_transcript_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/review-transcripts"))
        self.assertIn("kind-1-basic-approve", names)
        self.assertIn("kind-1-long-events-many-tags-detail-scroll-approve", names)

    def test_review_transcript_vectors_validate_display_navigation(self) -> None:
        for name in review_transcript_vector_names():
            errors: list[str] = []

            check_review_transcript_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_static_qr_transport_vectors_validate_envelope_payloads(self) -> None:
        names = [
            path.stem
            for path in sorted((ROOT / "vectors/transports").glob("qr-envelope-*.json"))
        ]
        self.assertIn("qr-envelope-kind-1-long-events-many-tags", names)
        for name in names:
            errors: list[str] = []

            check_static_qr_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_nip46_vector_names_are_discovered_from_directory(self) -> None:
        names = nip46_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/nip46"))
        self.assertIn("sign-event-kind-1-basic", names)

    def test_nip46_policy_file_vectors_are_discovered_from_directory(self) -> None:
        names = nip46_policy_file_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/nip46-policy-files"))
        self.assertIn("sign-event-kind-1-approved", names)

    def test_nip46_connection_uri_vectors_are_discovered_from_directory(self) -> None:
        names = nip46_connection_uri_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/nip46-connection-uris"))
        self.assertIn("bunker-remote-signer-token", names)
        self.assertIn("nostrconnect-client-token", names)

    def test_seedqr_vectors_are_discovered_from_directory(self) -> None:
        names = seedqr_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/seedqr"))
        self.assertIn("seedsigner-vector-1", names)

    def test_seedqr_vectors_validate_standard_and_compact_payloads(self) -> None:
        for name in seedqr_vector_names():
            errors: list[str] = []

            check_seedqr_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_nip19_nsec_vectors_are_discovered_from_directory(self) -> None:
        names = nip19_nsec_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/nip19"))
        self.assertIn("nsec-test-key-1", names)

    def test_nip19_nsec_vectors_validate_private_key_payloads(self) -> None:
        for name in nip19_nsec_vector_names():
            errors: list[str] = []

            check_nip19_nsec_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_session_import_review_vectors_are_discovered_from_directory(self) -> None:
        names = session_import_review_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/session-import-reviews"))
        self.assertIn("seedqr-vector-1", names)
        self.assertIn("nsec-test-key-1", names)

    def test_session_import_review_vectors_validate_secret_hidden_pages(self) -> None:
        for name in session_import_review_vector_names():
            errors: list[str] = []

            check_session_import_review_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_session_import_review_vectors_reject_secret_leakage(self) -> None:
        vector = deepcopy(load_json("vectors/session-import-reviews/seedqr-vector-1.json"))
        vector["pages"][0]["lines"].append("attack")
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/session-import-reviews/mutated-seed-leak.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_session_import_review_vector("mutated-seed-leak", errors)

        self.assertIn("must not expose mnemonic word 'attack'", "\n".join(errors))

    def test_source_public_key_proof_vectors_are_discovered_from_directory(self) -> None:
        names = source_public_key_proof_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/source-public-key-proofs"))
        self.assertIn("nip06-account-0-leader", names)
        self.assertIn("nsec-test-key-1", names)

    def test_source_public_key_proof_vectors_validate_source_binding(self) -> None:
        for name in source_public_key_proof_vector_names():
            errors: list[str] = []

            check_source_public_key_proof_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_source_public_key_proof_vectors_reject_descriptor_only_substitution(self) -> None:
        vector = deepcopy(load_json("vectors/source-public-key-proofs/nip06-account-0-leader.json"))
        vector["expected_public_key"] = "0" * 64
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/source-public-key-proofs/mutated-public-key.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_source_public_key_proof_vector("mutated-public-key", errors)

        self.assertIn("expected_public_key must match source public_key", "\n".join(errors))

    def test_session_source_backup_vectors_are_discovered_from_directory(self) -> None:
        names = session_source_backup_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/session-source-backups"))
        self.assertIn("seedqr-vector-1-backup", names)
        self.assertIn("nsec-test-key-1-backup", names)

    def test_session_source_backup_vectors_validate_danger_zone_reviews(self) -> None:
        for name in session_source_backup_vector_names():
            errors: list[str] = []

            check_session_source_backup_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_session_source_backup_vectors_reject_review_secret_leakage(self) -> None:
        vector = deepcopy(load_json("vectors/session-source-backups/nsec-test-key-1-backup.json"))
        vector["pages"][0]["lines"].append(vector["backup_payload"]["nsec"])
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/session-source-backups/mutated-backup-leak.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_session_source_backup_vector("mutated-backup-leak", errors)

        self.assertIn("review pages must not expose source nsec", "\n".join(errors))

    def test_implementation_limits_are_named_and_conservative(self) -> None:
        limits = implementation_limits()

        self.assertEqual(limits["format"], "nsealr-implementation-limits-v0")
        self.assertEqual(limits["name"], "nsealr-v0")
        self.assertEqual(limits["limits"]["max_request_id_length"], 128)
        self.assertLessEqual(limits["limits"]["max_decoded_request_json_bytes"], 4096)
        self.assertLessEqual(limits["limits"]["max_static_qr_decoded_json_bytes"], 4096)
        self.assertLessEqual(limits["limits"]["max_nip46_decrypted_message_json_bytes"], 4096)

    def test_valid_request_vectors_fit_v0_limit_profile(self) -> None:
        limits = implementation_limits()["limits"]
        valid_request_vectors = [
            load_json(f"vectors/review/{name}.json")["request"]
            for name in review_vector_names()
        ]

        for request in valid_request_vectors:
            with self.subTest(request_id=request["request_id"]):
                request_size = json_utf8_size(request)
                self.assertLessEqual(request_size, limits["max_decoded_request_json_bytes"])
                self.assertLessEqual(request_size, limits["max_static_qr_decoded_json_bytes"])

    def test_invalid_vectors_are_discovered_from_directory(self) -> None:
        names = invalid_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/invalid"))
        self.assertIn("request-event-template-pubkey", names)
        self.assertIn("serial-frame-oversized", names)
        self.assertIn("serial-frame-unsupported-type", names)

    def test_invalid_vectors_validate_expected_rejections(self) -> None:
        for name in invalid_vector_names():
            errors: list[str] = []

            check_invalid_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_nip46_policy_file_vectors_validate_approved_permissions(self) -> None:
        errors: list[str] = []

        check_nip46_policy_file_vector("sign-event-kind-1-approved", errors)

        self.assertEqual(errors, [])

    def test_nip46_connection_uri_vectors_validate_descriptor_boundaries(self) -> None:
        for name in nip46_connection_uri_vector_names():
            errors: list[str] = []

            check_nip46_connection_uri_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_smartcard_apdu_vectors_are_discovered_from_directory(self) -> None:
        names = smartcard_apdu_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/smartcard"))
        self.assertIn("get-public-key", names)
        self.assertIn("get-public-key-nonzero-p1", names)
        self.assertIn("get-public-key-with-le", names)
        self.assertIn("sign-event-id-kind-1-basic", names)
        self.assertIn("sign-event-id-nonzero-p2", names)
        self.assertIn("sign-event-id-with-le", names)
        self.assertIn("sign-event-id-wrong-length", names)
        self.assertIn("unsupported-cla", names)
        self.assertIn("unsupported-ins", names)

    def test_smartcard_apdu_vectors_validate_commands_and_status_words(self) -> None:
        for name in smartcard_apdu_vector_names():
            errors: list[str] = []

            check_smartcard_apdu_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_nip46_policy_file_schema_declares_required_contract(self) -> None:
        schema = load_json("schemas/nip46-policy-file-v0.schema.json")

        self.assertEqual(schema["title"], "nSealr NIP-46 Policy File v0")
        self.assertEqual(schema["required"], ["format", "approved_permissions"])
        permission_variants = schema["$defs"]["permission"]["oneOf"]
        self.assertNotIn(
            {
                "required": ["method"],
                "properties": {"method": {"const": "sign_event"}},
                "additionalProperties": False,
            },
            permission_variants,
        )

    def test_nip46_permission_policy_vectors_pin_request_decisions(self) -> None:
        policy_vectors = {
            name: load_json(f"vectors/nip46/{name}.json")
            for name in ("get-public-key", "ping", "sign-event-kind-1-basic")
        }
        self.assertEqual(policy_vectors["get-public-key"]["permission_requirement"], {"method": "get_public_key"})
        self.assertEqual(policy_vectors["ping"]["permission_requirement"], {"method": "ping"})
        self.assertEqual(
            policy_vectors["sign-event-kind-1-basic"]["permission_requirement"],
            {"method": "sign_event", "parameter": "1", "event_kind": 1},
        )
        for name, vector in policy_vectors.items():
            self.assertGreaterEqual(len(vector.get("permission_checks", [])), 2, name)

    def test_nip46_bridge_decision_vectors_are_explicit(self) -> None:
        for name in nip46_vector_names():
            vector = load_json(f"vectors/nip46/{name}.json")
            self.assertGreaterEqual(len(vector.get("bridge_decisions", [])), 1, name)

        sign_event = load_json("vectors/nip46/sign-event-kind-1-basic.json")
        self.assertEqual(
            sign_event["bridge_decisions"][0]["decision"]["type"],
            "signer_request",
        )
        self.assertEqual(
            sign_event["bridge_decisions"][1]["decision"],
            {
                "type": "permission_denied",
                "permission_requirement": {
                    "method": "sign_event",
                    "parameter": "1",
                    "event_kind": 1,
                },
                "response_message": {
                    "id": "nip46-req-1",
                    "error": "permission_denied: request requires approved permission sign_event:1",
                },
            },
        )

        connect = load_json("vectors/nip46/connect-policy-review.json")
        self.assertEqual(connect["bridge_decisions"][0]["decision"]["type"], "connect_review")
        self.assertEqual(
            connect["connect_review"]["pages"],
            [
                {
                    "title": "Connect",
                    "page_indicator": "Page 1/2",
                    "body_lines": [
                        "Remote signer",
                        "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
                        "Secret: provided",
                    ],
                },
                {
                    "title": "Permissions",
                    "page_indicator": "Page 2/2",
                    "body_lines": [
                        "sign_event:1",
                        "nip44_encrypt",
                    ],
                },
            ],
        )
        self.assertRegex(connect["connect_review"]["connect_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            connect["connect_approval"],
            {
                "format": "nsealr-nip46-connect-approval-v0",
                "id": "nip46-connect-1",
                "connect_digest": connect["connect_review"]["connect_digest"],
                "approved_at": 1900000001,
                "acknowledges_connect": False,
                "creates_grants": False,
                "opens_relay": False,
                "persists_session_state": False,
                "stores_production_secrets": False,
                "exposes_secret": False,
            },
        )

    def test_nip46_bridge_decision_checker_rejects_mismatches(self) -> None:
        vector = deepcopy(load_json("vectors/nip46/ping.json"))
        vector["bridge_decisions"][0]["decision"]["response_message"]["result"] = "wrong"
        errors: list[str] = []

        check_nip46_bridge_decisions(
            "vectors/nip46/ping.json",
            vector,
            vector["request_message"],
            errors,
        )

        self.assertIn("bridge_decisions[0].decision mismatch", "\n".join(errors))

    def test_identity_policy_contract_vectors_are_discovered(self) -> None:
        self.assertTrue(hasattr(verify_specs, "account_descriptor_vector_names"))
        self.assertTrue(hasattr(verify_specs, "policy_profile_vector_names"))
        self.assertTrue(hasattr(verify_specs, "grant_descriptor_vector_names"))

        self.assertEqual(
            verify_specs.account_descriptor_vector_names(),
            vector_names_from_dir("vectors/accounts"),
        )
        self.assertEqual(
            verify_specs.policy_profile_vector_names(),
            vector_names_from_dir("vectors/policies"),
        )
        self.assertEqual(
            verify_specs.grant_descriptor_vector_names(),
            vector_names_from_dir("vectors/grants"),
        )
        self.assertIn("raspberry-qr-nip06-account-0", verify_specs.account_descriptor_vector_names())
        self.assertIn("esp32-qr-nip06-account-0", verify_specs.account_descriptor_vector_names())
        self.assertIn("smartcard-slot-0", verify_specs.account_descriptor_vector_names())
        self.assertIn("custom-hardware-wallet-slot-0", verify_specs.account_descriptor_vector_names())
        self.assertIn("manual-only-qr-vault", verify_specs.policy_profile_vector_names())
        self.assertIn("manual-only-displayless-smartcard", verify_specs.policy_profile_vector_names())
        self.assertIn("esp32-usb-kind-1-session", verify_specs.grant_descriptor_vector_names())

    def test_identity_policy_contract_vectors_validate(self) -> None:
        for name in verify_specs.account_descriptor_vector_names():
            errors: list[str] = []
            verify_specs.check_account_descriptor_vector(name, errors)
            self.assertEqual(errors, [], name)

        for name in verify_specs.policy_profile_vector_names():
            errors = []
            verify_specs.check_policy_profile_vector(name, errors)
            self.assertEqual(errors, [], name)

        for name in verify_specs.grant_descriptor_vector_names():
            errors = []
            verify_specs.check_grant_descriptor_vector(name, errors)
            self.assertEqual(errors, [], name)

    def test_route_refusal_contract_vectors_are_discovered_from_directory(self) -> None:
        names = route_refusal_contract_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/route-refusals"))
        self.assertEqual(names, ["signer-route-refusals-v0"])

    def test_route_refusal_contract_vectors_validate_every_route(self) -> None:
        for name in route_refusal_contract_vector_names():
            errors: list[str] = []

            check_route_refusal_contract_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_route_refusal_contract_vectors_reject_acknowledgement_drift(self) -> None:
        vector = deepcopy(load_json("vectors/route-refusals/signer-route-refusals-v0.json"))
        vector["cases"][0]["external_review_acknowledgement"]["mode"] = "required"
        vector["cases"][-1]["without_dispatcher"] = {
            "error_code": "signer_route_unavailable",
            "message": "bad display-less shortcut",
            "retryable": False,
        }
        vector["safety"]["dispatches_without_signer"] = True
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/route-refusals/mutated-route-refusals.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_route_refusal_contract_vector("mutated-route-refusals", errors)

        joined = "\n".join(errors)
        self.assertIn("trusted-review routes must reject external review acknowledgement", joined)
        self.assertIn("display-less route must not bypass acknowledgement before dispatcher", joined)
        self.assertIn("safety boundary mismatch", joined)

    def test_grant_descriptors_reject_stale_decision_field(self) -> None:
        vector = deepcopy(load_json("vectors/grants/esp32-usb-kind-1-session.json"))
        vector["decision"] = "allow_until_expiry"
        errors: list[str] = []

        verify_specs.check_grant_descriptor_shape("mutated-grant.json", vector, errors)

        self.assertIn("mutated-grant.json: grant descriptor has unknown fields ['decision']", "\n".join(errors))

    def test_policy_profiles_reject_unknown_policy_vocabulary(self) -> None:
        vector = deepcopy(load_json("vectors/policies/scoped-automation-daily-use.json"))
        vector["manual_review_required"].append("auto_like")
        vector["forbidden_permissions"].append("shadow_export")
        vector["risk_tiers"]["reaction"] = "low_scoped"
        vector["risk_tiers"]["delete"] = "auto"
        errors: list[str] = []

        verify_specs.check_policy_profile_shape("mutated-policy.json", vector, errors)

        joined = "\n".join(errors)
        self.assertIn("manual_review_required contains unsupported values ['auto_like']", joined)
        self.assertIn("forbidden_permissions contains unsupported values ['shadow_export']", joined)
        self.assertIn("risk_tiers contains unsupported keys ['reaction']", joined)
        self.assertIn("risk_tiers.delete uses unsupported tier 'auto'", joined)

    def test_policy_decision_vectors_are_discovered_from_directory(self) -> None:
        names = policy_decision_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/policy-decisions"))

    def test_policy_decision_vectors_validate(self) -> None:
        for name in policy_decision_vector_names():
            errors: list[str] = []

            check_policy_decision_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_policy_decision_vectors_reject_closed_contract_drift(self) -> None:
        vector = deepcopy(load_json("vectors/policy-decisions/grant-sign-event-kind-1-allowed.json"))
        vector["unsigned_metadata"] = "not allowed"
        vector["request"]["route_type"] = "raspberry_qr_vault"
        vector["request"]["extra"] = "not allowed"
        vector["decision"]["grant_id"] = "kind-1-session"
        vector["decision"]["audit_event"]["client_label"] = "not allowed"
        vector["decision"]["audit_event"]["grant_id"] = "kind-1-session"
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/policy-decisions/mutated-policy-decision-contract.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_policy_decision_vector("mutated-policy-decision-contract", errors)

        joined = "\n".join(errors)
        self.assertIn("policy decision vector has unknown fields ['unsigned_metadata']", joined)
        self.assertIn("request has unknown fields ['extra']", joined)
        self.assertIn("request.route_type must be a persistent or external route", joined)
        self.assertIn("decision.grant_id must be a grant-* stable string id", joined)
        self.assertIn("audit_event has unknown fields ['client_label']", joined)
        self.assertIn("audit_event.grant_id must be a grant-* stable string id", joined)

    def test_feature_matrix_vectors_are_discovered_from_directory(self) -> None:
        names = feature_matrix_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/features"))
        self.assertIn("signer-feature-matrix-v0", names)

    def test_feature_matrix_vectors_validate_solution_behavior_contracts(self) -> None:
        for name in feature_matrix_vector_names():
            errors: list[str] = []

            check_feature_matrix_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_access_surface_vectors_are_discovered_from_directory(self) -> None:
        names = access_surface_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/access-surfaces"))
        self.assertEqual(names, ["browser-provider-local-service-esp32-usb-unavailable"])

    def test_access_surface_vectors_validate_secretless_browser_boundary(self) -> None:
        for name in access_surface_vector_names():
            errors: list[str] = []

            check_access_surface_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_access_surface_vectors_reject_secret_and_safety_drift(self) -> None:
        vector = deepcopy(load_json("vectors/access-surfaces/browser-provider-local-service-esp32-usb-unavailable.json"))
        vector["client"]["secret_key"] = "00" * 32
        vector["safety"]["stores_production_secrets"] = True
        errors: list[str] = []

        with patch("scripts.verify_specs.load_required_json") as load_mock:
            def load_mutation(path: str, errors_arg: list[str]) -> dict:
                if path == "vectors/access-surfaces/mutated-browser-secret.json":
                    return vector
                return load_json(path)

            load_mock.side_effect = load_mutation
            check_access_surface_vector("mutated-browser-secret", errors)

        joined = "\n".join(errors)
        self.assertIn("must not contain secret field client.secret_key", joined)
        self.assertIn("safety boundary mismatch", joined)

    def test_device_security_profile_vectors_are_discovered_from_directory(self) -> None:
        names = device_security_profile_vector_names()

        expected = sorted(path.stem for path in (ROOT / "vectors/devices").glob("*security-profile-*.json"))
        self.assertEqual(names, expected)
        self.assertIn("esp32-s3-security-profile-development", names)

    def test_device_security_profile_vectors_validate_hardening_boundary(self) -> None:
        for name in device_security_profile_vector_names():
            errors: list[str] = []

            check_device_security_profile_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_feature_matrix_rejects_shared_feature_contract_drift(self) -> None:
        matrix = deepcopy(load_json("vectors/features/signer-feature-matrix-v0.json"))
        matrix["solutions"]["esp32_qr_vault"]["features"]["nostr_event_review_universal"][
            "contract_id"
        ] = "esp32-special-review"
        errors: list[str] = []

        verify_specs.check_feature_matrix_shape(
            "vectors/features/mutated-contract-drift.json",
            matrix,
            errors,
        )

        self.assertIn("shared feature contract drift", "\n".join(errors))

    def test_feature_matrix_keeps_stateless_qr_vault_targets_in_parity(self) -> None:
        matrix = deepcopy(load_json("vectors/features/signer-feature-matrix-v0.json"))
        matrix["solutions"]["esp32_qr_vault"]["features"]["qr_response"]["target"] = "not_applicable"
        errors: list[str] = []

        verify_specs.check_feature_matrix_shape(
            "vectors/features/mutated-vault-parity.json",
            matrix,
            errors,
        )

        self.assertIn("stateless_qr_vault parity mismatch", "\n".join(errors))

    def test_account_descriptors_reject_embedded_secret_material(self) -> None:
        account = deepcopy(load_json("vectors/accounts/raspberry-qr-nip06-account-0.json"))
        account["recovery"]["mnemonic"] = "leader monkey parrot ring guide accident before fence cannon height naive bean"
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-secret-account.json",
            account,
            errors,
        )

        self.assertIn("must not contain secret field recovery.mnemonic", "\n".join(errors))

    def test_identity_policy_contracts_reject_unsupported_fields(self) -> None:
        account = deepcopy(load_json("vectors/accounts/esp32-usb-device-slot-0.json"))
        account["unsigned_metadata"] = "not allowed"
        account["signer_route"]["display_hint"] = "not allowed"
        account["capabilities"]["autofill_policy"] = True
        account["recovery"]["legacy_hint"] = "not allowed"
        account["policy_profile_id"] = "manual-only"
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-unsupported-fields.json",
            account,
            errors,
        )

        joined = "\n".join(errors)
        self.assertIn("account descriptor has unknown fields ['unsigned_metadata']", joined)
        self.assertIn("signer_route has unknown fields ['display_hint']", joined)
        self.assertIn("capabilities has unknown fields ['autofill_policy']", joined)
        self.assertIn("device_slot recovery has unknown fields ['legacy_hint']", joined)
        self.assertIn("policy_profile_id must be a policy-* stable string id", joined)

        policy = deepcopy(load_json("vectors/policies/scoped-automation-daily-use.json"))
        policy["notes"] = "not allowed"
        policy["grant_constraints"]["companion_override_allowed"] = False
        errors = []

        verify_specs.check_policy_profile_shape(
            "vectors/policies/mutated-unsupported-fields.json",
            policy,
            errors,
        )

        joined = "\n".join(errors)
        self.assertIn("policy profile has unknown fields ['notes']", joined)
        self.assertIn("grant_constraints has unknown fields ['companion_override_allowed']", joined)

        manual_policy = deepcopy(load_json("vectors/policies/manual-only-persistent-device.json"))
        manual_policy["grant_constraints"] = {"expiry_required": True}
        errors = []

        verify_specs.check_policy_profile_shape(
            "vectors/policies/mutated-manual-constraints.json",
            manual_policy,
            errors,
        )

        self.assertIn("grant_constraints must be absent when grants are not allowed", "\n".join(errors))

        grant = deepcopy(load_json("vectors/grants/esp32-usb-kind-1-session.json"))
        grant["unsigned_metadata"] = "not allowed"
        grant["grant_id"] = "kind-1-session"
        grant["client"]["origin"] = "https://example.com"
        grant["client"]["label"] = 123
        grant["permission"]["reason"] = "not allowed"
        grant["rate_limit"]["burst"] = 1
        errors = []

        verify_specs.check_grant_descriptor_shape(
            "vectors/grants/mutated-unsupported-fields.json",
            grant,
            errors,
        )

        joined = "\n".join(errors)
        self.assertIn("grant descriptor has unknown fields ['unsigned_metadata']", joined)
        self.assertIn("grant_id must be a grant-* stable string id", joined)
        self.assertIn("client has unknown fields ['origin']", joined)
        self.assertIn("client.label must be a string", joined)
        self.assertIn("permission has unknown fields ['reason']", joined)
        self.assertIn("rate_limit has unknown fields ['burst']", joined)

    def test_account_descriptors_reject_missing_nip06_source_vector(self) -> None:
        account = deepcopy(load_json("vectors/accounts/esp32-qr-nip06-account-0.json"))
        account["recovery"]["source_vector"] = "vectors/keys/missing-nip06-account.json"
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-missing-nip06-source.json",
            account,
            errors,
        )

        self.assertIn("NIP-06 recovery source_vector is missing", "\n".join(errors))

    def test_account_descriptors_reject_nip06_source_fingerprint_mismatch(self) -> None:
        account = deepcopy(load_json("vectors/accounts/esp32-qr-nip06-account-0.json"))
        account["recovery"]["source_fingerprint"] = "0000000000000000"
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-source-fingerprint.json",
            account,
            errors,
        )

        self.assertIn("NIP-06 recovery source_fingerprint mismatch", "\n".join(errors))

    def test_policy_profiles_reject_automation_for_qr_vault_routes(self) -> None:
        policy = deepcopy(load_json("vectors/policies/manual-only-qr-vault.json"))
        policy["mode"] = "scoped_automation"
        policy["grants_allowed"] = True
        errors: list[str] = []

        verify_specs.check_policy_profile_shape(
            "vectors/policies/mutated-qr-automation.json",
            policy,
            errors,
        )

        self.assertIn("QR vault routes must remain manual_only with grants_allowed false", "\n".join(errors))

    def test_policy_profiles_reject_automation_for_display_less_smartcard_routes(self) -> None:
        policy = deepcopy(load_json("vectors/policies/manual-only-displayless-smartcard.json"))
        policy["mode"] = "scoped_automation"
        policy["grants_allowed"] = True
        errors: list[str] = []

        verify_specs.check_policy_profile_shape(
            "vectors/policies/mutated-smartcard-automation.json",
            policy,
            errors,
        )

        self.assertIn("display-less smartcard routes must remain manual_only", "\n".join(errors))

    def test_policy_profiles_reject_automation_for_external_nip46_routes(self) -> None:
        policy = deepcopy(load_json("vectors/policies/external-signer-manual-route.json"))
        policy["mode"] = "scoped_automation"
        policy["grants_allowed"] = True
        policy["grant_constraints"] = {
            "expiry_required": True,
            "rate_limit_required": True,
            "revocation_required": True,
            "audit_log_required": True,
            "device_confirmation_required": True,
        }
        errors: list[str] = []

        verify_specs.check_policy_profile_shape(
            "vectors/policies/mutated-external-nip46-automation.json",
            policy,
            errors,
        )

        self.assertIn("external NIP-46 routes must remain external-policy manual without nSealr grants", "\n".join(errors))

    def test_account_descriptors_reject_display_less_smartcard_trusted_review_claims(self) -> None:
        account = deepcopy(load_json("vectors/accounts/smartcard-slot-0.json"))
        account["signer_route"]["trusted_review"] = "device_display"
        account["signer_route"]["policy_support"] = "scoped_automation"
        account["capabilities"]["physical_review"] = True
        account["capabilities"]["persistent_grants"] = True
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-smartcard-trusted-review.json",
            account,
            errors,
        )

        joined = "\n".join(errors)
        self.assertIn("smartcard routes must remain display_less", joined)
        self.assertIn("display-less smartcard routes must use manual_only policy support", joined)
        self.assertIn("display-less smartcard routes must not claim physical review or approval", joined)
        self.assertIn("display-less smartcard routes must not support persistent grants", joined)

    def test_account_descriptors_reject_external_nip46_persistent_grants(self) -> None:
        account = deepcopy(load_json("vectors/accounts/external-nip46-bunker.json"))
        account["capabilities"]["persistent_grants"] = True
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-external-nip46-grants.json",
            account,
            errors,
        )

        self.assertIn("external NIP-46 routes must not claim nSealr persistent grants", "\n".join(errors))

    def test_account_descriptors_reject_policy_route_mismatch(self) -> None:
        account = deepcopy(load_json("vectors/accounts/smartcard-slot-0.json"))
        account["policy_profile_id"] = "policy-scoped-automation-daily-use"
        errors: list[str] = []

        verify_specs.check_account_descriptor_shape(
            "vectors/accounts/mutated-smartcard-policy-route.json",
            account,
            errors,
        )

        self.assertIn("policy_profile_id does not include signer route type smartcard", "\n".join(errors))

    def test_grant_descriptors_reject_wildcard_or_non_persistent_policy_routes(self) -> None:
        grant = deepcopy(load_json("vectors/grants/esp32-usb-kind-1-session.json"))
        grant["permission"]["method"] = "*"
        grant["route_type"] = "esp32_qr_vault"
        errors: list[str] = []

        verify_specs.check_grant_descriptor_shape(
            "vectors/grants/mutated-wildcard-qr-grant.json",
            grant,
            errors,
        )

        joined = "\n".join(errors)
        self.assertIn("grant route_type must be a nSealr persistent policy route", joined)
        self.assertIn("grant permission must not use wildcards", joined)

        for route_type in ("smartcard", "external_nip46"):
            grant = deepcopy(load_json("vectors/grants/esp32-usb-kind-1-session.json"))
            grant["route_type"] = route_type
            errors = []

            verify_specs.check_grant_descriptor_shape(
                f"vectors/grants/mutated-{route_type}-grant.json",
                grant,
                errors,
            )

            self.assertIn("grant route_type must be a nSealr persistent policy route", "\n".join(errors))

        grant = deepcopy(load_json("vectors/grants/esp32-usb-kind-1-session.json"))
        grant["permission"] = {"method": "nip44_decrypt"}
        errors = []

        verify_specs.check_grant_descriptor_shape(
            "vectors/grants/mutated-decrypt-grant.json",
            grant,
            errors,
        )

        self.assertIn("decrypt grant permissions require manual review", "\n".join(errors))

    def test_policy_change_review_vectors_are_discovered_from_directory(self) -> None:
        names = policy_change_review_vector_names()

        self.assertEqual(names, vector_names_from_dir("vectors/policy-changes"))
        self.assertIn("esp32-usb-enable-kind-1-automation", names)

    def test_policy_change_review_vectors_require_device_approval(self) -> None:
        for name in policy_change_review_vector_names():
            errors: list[str] = []

            check_policy_change_review_vector(name, errors)

            self.assertEqual(errors, [], name)

    def test_policy_change_review_rejects_companion_authority(self) -> None:
        vector = deepcopy(load_json("vectors/policy-changes/esp32-usb-enable-kind-1-automation.json"))
        vector["proposal"]["companion_authoritative"] = True

        def load_mutation(path: str, errors: list[str]) -> dict:
            if path == "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json":
                return vector
            return load_json(path)

        errors: list[str] = []
        with patch("scripts.verify_specs.load_required_json", side_effect=load_mutation):
            check_policy_change_review_vector("esp32-usb-enable-kind-1-automation", errors)

        self.assertIn("companion_authoritative must be false", "\n".join(errors))

    def test_policy_change_review_rejects_loose_ids_and_requester_labels(self) -> None:
        vector = deepcopy(load_json("vectors/policy-changes/esp32-usb-enable-kind-1-automation.json"))
        vector["proposal"]["proposal_id"] = f"proposal-{'x' * 120}"
        vector["review"]["proposal_id"] = vector["proposal"]["proposal_id"]
        vector["proposal"]["requested_by"]["label"] = 123

        def load_mutation(path: str, errors: list[str]) -> dict:
            if path == "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json":
                return vector
            return load_json(path)

        errors: list[str] = []
        with patch("scripts.verify_specs.load_required_json", side_effect=load_mutation):
            check_policy_change_review_vector("esp32-usb-enable-kind-1-automation", errors)

        joined = "\n".join(errors)
        self.assertIn("proposal_id must be a proposal-* stable string id", joined)
        self.assertIn("review.proposal_id must be a proposal-* stable string id", joined)
        self.assertIn("requested_by.label must be a non-empty string", joined)

    def test_identity_policy_schemas_declare_required_contracts(self) -> None:
        account_schema = load_json("schemas/account-descriptor-v0.schema.json")
        policy_schema = load_json("schemas/policy-profile-v0.schema.json")
        grant_schema = load_json("schemas/grant-descriptor-v0.schema.json")
        policy_change_schema = load_json("schemas/policy-change-review-v0.schema.json")
        policy_decision_schema = load_json("schemas/policy-decision-vector-v0.schema.json")
        route_selection_schema = load_json("schemas/route-selection-vector-v0.schema.json")

        self.assertEqual(account_schema["title"], "nSealr Account Descriptor v0")
        self.assertIn("signer_route", account_schema["required"])
        self.assertNotIn("secret_key", account_schema["properties"])
        self.assertFalse(account_schema["additionalProperties"])
        self.assertFalse(account_schema["properties"]["signer_route"]["additionalProperties"])
        self.assertFalse(account_schema["properties"]["capabilities"]["additionalProperties"])
        self.assertEqual(account_schema["properties"]["policy_profile_id"]["pattern"], "^policy-[A-Za-z0-9._:-]{1,121}$")
        account_route_semantics = account_schema["allOf"]
        self.assertEqual(len(account_route_semantics), 6)
        self.assertIn({
            "if": {
                "properties": {
                    "signer_route": {
                        "properties": {"type": {"const": "esp32_usb_nip46"}},
                        "required": ["type"],
                    }
                },
                "required": ["signer_route"],
            },
            "then": {
                "properties": {
                    "signer_route": {
                        "required": ["repository"],
                        "properties": {
                            "repository": {"const": "firmware"},
                            "transport": {"const": "usb"},
                            "custody": {"const": "device_persistent"},
                            "trusted_review": {"const": "device_display"},
                            "policy_support": {"const": "scoped_automation"},
                        },
                    },
                    "capabilities": {
                        "properties": {
                            "physical_review": {"const": True},
                            "physical_approval": {"const": True},
                            "persistent_grants": {"const": True},
                        }
                    },
                },
            },
        }, account_route_semantics)
        self.assertIn({
            "if": {
                "properties": {
                    "signer_route": {
                        "properties": {"type": {"const": "external_nip46"}},
                        "required": ["type"],
                    }
                },
                "required": ["signer_route"],
            },
            "then": {
                "properties": {
                    "signer_route": {
                        "not": {"required": ["repository"]},
                        "properties": {
                            "transport": {"const": "nip46_relay"},
                            "custody": {"const": "external_signer"},
                            "trusted_review": {"const": "external_policy"},
                            "policy_support": {"const": "external"},
                        },
                    },
                    "capabilities": {
                        "properties": {
                            "physical_review": {"const": False},
                            "physical_approval": {"const": False},
                            "persistent_grants": {"const": False},
                        }
                    },
                },
            },
        }, account_route_semantics)
        self.assertEqual(policy_schema["title"], "nSealr Policy Profile v0")
        self.assertIn("grants_allowed", policy_schema["required"])
        self.assertFalse(policy_schema["additionalProperties"])
        self.assertFalse(policy_schema["properties"]["grant_constraints"]["additionalProperties"])
        self.assertEqual(policy_schema["properties"]["policy_id"]["pattern"], "^policy-[A-Za-z0-9._:-]{1,121}$")
        self.assertEqual(len(policy_schema["allOf"]), 3)
        self.assertIn({
            "if": {
                "properties": {
                    "route_types": {
                        "contains": {"const": "external_nip46"}
                    }
                },
                "required": ["route_types"],
            },
            "then": {
                "properties": {
                    "mode": {"const": "manual_only"},
                    "grants_allowed": {"const": False},
                }
            },
        }, policy_schema["allOf"])
        self.assertEqual(grant_schema["title"], "nSealr Grant Descriptor v0")
        self.assertIn("expires_at", grant_schema["required"])
        self.assertFalse(grant_schema["additionalProperties"])
        self.assertFalse(grant_schema["properties"]["client"]["additionalProperties"])
        self.assertFalse(grant_schema["properties"]["permission"]["additionalProperties"])
        self.assertFalse(grant_schema["properties"]["rate_limit"]["additionalProperties"])
        self.assertEqual(grant_schema["properties"]["grant_id"]["pattern"], "^grant-[A-Za-z0-9._:-]{1,122}$")
        self.assertEqual(grant_schema["properties"]["route_type"]["enum"], ["esp32_usb_nip46", "custom_hardware_wallet"])
        self.assertEqual(policy_change_schema["title"], "nSealr Policy Change Review v0")
        self.assertIn("proposal", policy_change_schema["required"])
        self.assertEqual(
            policy_change_schema["properties"]["proposal"]["properties"]["proposal_id"]["pattern"],
            "^proposal-[A-Za-z0-9._:-]{1,119}$",
        )
        self.assertEqual(
            policy_change_schema["properties"]["proposal"]["properties"]["current_policy_id"]["pattern"],
            "^policy-[A-Za-z0-9._:-]{1,121}$",
        )
        self.assertEqual(
            policy_change_schema["properties"]["proposal"]["properties"]["proposed_grant_ids"]["items"]["pattern"],
            "^grant-[A-Za-z0-9._:-]{1,122}$",
        )
        self.assertEqual(
            policy_decision_schema["properties"]["policy_profile_id"]["pattern"],
            "^policy-[A-Za-z0-9._:-]{1,121}$",
        )
        self.assertEqual(
            policy_decision_schema["properties"]["request"]["properties"]["grant_ids"]["items"]["pattern"],
            "^grant-[A-Za-z0-9._:-]{1,122}$",
        )
        self.assertEqual(
            route_selection_schema["properties"]["selection"]["properties"]["policy_profile_id"]["pattern"],
            "^policy-[A-Za-z0-9._:-]{1,121}$",
        )
        route_selection_semantics = route_selection_schema["properties"]["selection"]["allOf"]
        self.assertEqual(len(route_selection_semantics), 6)
        self.assertIn({
            "if": {
                "properties": {"route_type": {"const": "esp32_usb_nip46"}},
                "required": ["route_type"],
            },
            "then": {
                "required": ["repository"],
                "properties": {
                    "repository": {"const": "firmware"},
                    "transport": {"const": "usb"},
                    "custody": {"const": "device_persistent"},
                    "trusted_review": {"const": "device_display"},
                    "policy_support": {"const": "scoped_automation"},
                    "physical_review": {"const": True},
                    "physical_approval": {"const": True},
                    "persistent_grants": {"const": True},
                },
            },
        }, route_selection_semantics)
        self.assertIn({
            "if": {
                "properties": {"route_type": {"const": "external_nip46"}},
                "required": ["route_type"],
            },
            "then": {
                "not": {"required": ["repository"]},
                "properties": {
                    "transport": {"const": "nip46_relay"},
                    "custody": {"const": "external_signer"},
                    "trusted_review": {"const": "external_policy"},
                    "policy_support": {"const": "external"},
                    "physical_review": {"const": False},
                    "physical_approval": {"const": False},
                    "persistent_grants": {"const": False},
                },
            },
        }, route_selection_semantics)


    def test_nip46_session_active_vector_names_are_discovered_from_directory(self) -> None:
        names = verify_specs.nip46_session_active_vector_names()
        self.assertEqual(names, sorted(names))
        for name in names:
            self.assertTrue(
                (verify_specs.ROOT / "vectors" / "nip46-sessions-active" / f"{name}.json").exists()
            )

    def _load_active_session(self, stem: str) -> dict:
        import json
        path = verify_specs.ROOT / "vectors" / "nip46-sessions-active" / f"{stem}.json"
        return json.loads(path.read_text(encoding="utf-8"))["session"]

    def test_nip46_session_active_shape_accepts_connect_ack(self) -> None:
        errors: list[str] = []
        value = self._load_active_session("connect-ack-kind-1")
        verify_specs.check_nip46_session_active_shape(
            "vectors/nip46-sessions-active/connect-ack-kind-1.json", value, errors
        )
        self.assertEqual(errors, [])

    def test_nip46_session_active_vectors_validate_and_bind_to_source(self) -> None:
        errors: list[str] = []
        for rel in verify_specs.nip46_session_active_vector_names():
            verify_specs.check_nip46_session_active_vector(rel, errors)
        self.assertEqual(errors, [])
        self.assertIn("connect-ack-kind-1", verify_specs.nip46_session_active_vector_names())

    def test_nip46_session_active_phases_present(self) -> None:
        names = set(verify_specs.nip46_session_active_vector_names())
        self.assertTrue({"connect-ack-kind-1", "session-active-kind-1", "session-closed-kind-1"} <= names)
        errors: list[str] = []
        for rel in ("session-active-kind-1", "session-closed-kind-1"):
            verify_specs.check_nip46_session_active_vector(rel, errors)
        self.assertEqual(errors, [])

    def test_nip46_session_active_invalid_vectors_are_rejected(self) -> None:
        import json
        stems = [
            "nip46-session-active-secret-in-persisted-state",
            "nip46-session-active-unknown-phase",
            "nip46-session-active-stores-production-secrets",
            "nip46-session-active-connect-ack-dispatches",
            "nip46-session-active-closed-opens-relay",
            "nip46-session-active-bad-nip44-version",
        ]
        for stem in stems:
            vector_path = f"vectors/invalid/{stem}.json"
            vector = json.loads((verify_specs.ROOT / "vectors" / "invalid" / f"{stem}.json").read_text(encoding="utf-8"))
            errors: list[str] = []
            verify_specs.check_nip46_session_active_shape(vector_path, vector["session"], errors)
            self.assertTrue(errors, f"{stem} should have been rejected by the shape validator")
            self.assertTrue(
                any(vector["expected_error"] in e for e in errors),
                f"{stem}: expected_error {vector['expected_error']!r} not found in {errors}",
            )


if __name__ == "__main__":
    unittest.main()
