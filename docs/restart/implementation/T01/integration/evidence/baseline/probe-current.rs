use nsealr_core::policy::signing_policy::{evaluate_signing_readiness, SigningGateNames, SigningReadiness};

fn main() {
    let readiness = SigningReadiness {
        runtime_signing_feature_enabled: true,
        parser_limits_enforced: true,
        trusted_review_display_accepted: true,
        physical_approval_controls_accepted: true,
        approval_digest_binding_verified: true,
        unicode_review_rendering_accepted: true,
        key_provisioning_ready: true,
        source_public_key_proof_ready: true,
        secure_boot_enabled: true,
        flash_encryption_enabled: true,
        debug_locked: true,
        companion_signed_output_verification_ready: true,
        development_accepted_gates: SigningGateNames::new(),
    };
    let diagnostic = evaluate_signing_readiness(&readiness);
    assert!(diagnostic.signing_enabled);
    assert!(diagnostic.missing_gates.is_empty());
    println!("{{\"source\":\"dbad656997ad8cf9024ca1489291f5f1d4d3094a\",\"all_twelve_booleans_diagnostic_enabled\":true,\"physical_evidence_supplied\":false,\"signature_produced\":false}}");
}
