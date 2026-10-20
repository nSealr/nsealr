//! Requirement-derived profile diagnostics, using the one independent artifact.
use nsealr_core::capabilities::*;
use serde_json::Value;

fn case(id: &str) -> Value {
    let data: Value = serde_json::from_str(include_str!(concat!(
        env!("OUT_DIR"),
        "/t01-profile-cases-v1.json"
    )))
    .unwrap();
    data["cases"]
        .as_array()
        .unwrap()
        .iter()
        .find(|case| case["id"] == id)
        .unwrap()
        .clone()
}

// Fixed independent profile requirements from original P01/T01, not computed
// through the evaluator under test.
fn local(profile: Profile) -> LocalObservations {
    let (custody, component) = match profile {
        Profile::Esp32NoSe => (Custody::McuWrappedPersistent, ComponentObservation::Absent),
        Profile::PiQr | Profile::P4Qr => (Custody::VolatileSession, ComponentObservation::Absent),
        Profile::CustomBoard => (
            Custody::CustomSeAssistedPersistent,
            ComponentObservation::MatchingRequiredConfiguration,
        ),
    };
    LocalObservations {
        custody,
        component,
        groups: [LocalAssessment {
            availability: Availability::Available,
            verification: Verification::Verified,
        }; 9],
        boot_enforcement: Availability::Available,
        boot_limitation_evidence: Verification::Unknown,
    }
}

fn assessed(profile: Profile, observations: &LocalObservations) -> ProfileAssessment {
    assess_profile(
        profile,
        observations,
        AssessmentContext::ConformanceOnly,
        true,
    )
}

#[test]
fn exact_profiles_and_each_independent_required_group() {
    let profiles = case("P-01");
    let missing = case("P-02");
    for profile in profiles["input"]["profiles"].as_array().unwrap() {
        let id = profile.as_str().unwrap();
        let profile = Profile::from_id(id).unwrap();
        assert_eq!(profile.id(), id);
        let observations = local(profile);
        assert_eq!(profile.custody(), observations.custody);
        assert_eq!(assessed(profile, &observations).blockers().count(), 0);
        let message_required = missing["input"]["message_required_profiles"]
            .as_array()
            .unwrap()
            .iter()
            .any(|id| id == profile.id());
        assert_eq!(profile.requires_messages(), message_required);
        for (index, group) in REQUIREMENTS.iter().enumerate() {
            assert_eq!(group.id(), missing["input"]["remove_groups"][index]);
            let mut absent = observations.clone();
            absent.groups[index] = LocalAssessment::UNKNOWN;
            let result = assessed(profile, &absent);
            let blockers: Vec<_> = result.blockers().collect();
            if *group == Requirement::Messages && !message_required {
                assert!(blockers.is_empty());
            } else {
                assert_eq!(blockers.len(), 1);
                assert_eq!(blockers[0].requirement, *group);
                assert_eq!(blockers[0].reason, BlockerReason::Unknown);
            }
        }
    }
    for not_profile in case("P-09")["input"]["not_signer_profiles"]
        .as_array()
        .unwrap()
    {
        assert_eq!(Profile::from_id(not_profile.as_str().unwrap()), None);
    }
}

#[test]
fn local_verification_and_availability_do_not_collapse() {
    let independent_rows = [
        (
            Availability::Unknown,
            Verification::Verified,
            Some(BlockerReason::Unknown),
        ),
        (
            Availability::Available,
            Verification::Unknown,
            Some(BlockerReason::Unknown),
        ),
        (
            Availability::Unavailable,
            Verification::Verified,
            Some(BlockerReason::Unavailable),
        ),
        (
            Availability::Available,
            Verification::Unverified,
            Some(BlockerReason::Unverified),
        ),
        (
            Availability::Available,
            Verification::Unavailable,
            Some(BlockerReason::Unverified),
        ),
        (Availability::Available, Verification::Verified, None),
    ];
    for (availability, verification, expected) in independent_rows {
        let mut observations = local(Profile::Esp32NoSe);
        observations.groups[0] = LocalAssessment {
            availability,
            verification,
        };
        let result = assessed(Profile::Esp32NoSe, &observations);
        assert_eq!(result.blockers().next().map(|b| b.reason), expected);
    }
}

#[test]
fn pi_boot_limitation_requires_its_own_evidence() {
    assert_eq!(case("P-03")["input"]["profile"], "pi_qr");
    let mut observations = local(Profile::PiQr);
    observations.boot_enforcement = Availability::Unavailable;
    observations.boot_limitation_evidence = Verification::Verified;
    assert_eq!(assessed(Profile::PiQr, &observations).blockers().count(), 0);
    for verification in [
        Verification::Unknown,
        Verification::Unavailable,
        Verification::Unverified,
    ] {
        observations.boot_limitation_evidence = verification;
        let result = assessed(Profile::PiQr, &observations);
        assert_eq!(
            result.blockers().next().unwrap().requirement,
            Requirement::Lifecycle
        );
    }
    observations.boot_enforcement = Availability::Unknown;
    assert!(assessed(Profile::PiQr, &observations)
        .blockers()
        .next()
        .is_some());
    // A scoped Pi limitation is not borrowed by another profile.
    let mut p4 = local(Profile::P4Qr);
    p4.boot_enforcement = Availability::Unavailable;
    p4.boot_limitation_evidence = Verification::Verified;
    assert_eq!(
        assessed(Profile::P4Qr, &p4)
            .blockers()
            .next()
            .unwrap()
            .requirement,
        Requirement::Lifecycle
    );
}

#[test]
fn required_component_and_custody_never_fall_back() {
    assert_eq!(case("P-05")["expected"]["fallback"], false);
    let profile = Profile::CustomBoard;
    for bad in [
        ComponentObservation::Absent,
        ComponentObservation::Unknown,
        ComponentObservation::WrongPartOrConfiguration,
        ComponentObservation::ProviderUnavailable,
    ] {
        let mut observations = local(profile);
        observations.component = bad;
        let result = assessed(profile, &observations);
        assert_eq!(
            result.blockers().next().unwrap().reason,
            BlockerReason::RequiredComponentUnavailable
        );
        assert_eq!(observations.custody, Custody::CustomSeAssistedPersistent);
    }
    let mut wrong_custody = local(profile);
    wrong_custody.custody = Custody::McuWrappedPersistent;
    assert_eq!(
        assessed(profile, &wrong_custody)
            .blockers()
            .next()
            .unwrap()
            .reason,
        BlockerReason::CustodyMismatch
    );
    let mut no_se = local(Profile::Esp32NoSe);
    no_se.component = ComponentObservation::Unknown;
    assert_eq!(
        assessed(Profile::Esp32NoSe, &no_se)
            .blockers()
            .next()
            .unwrap()
            .reason,
        BlockerReason::UnexpectedComponent
    );
}

#[test]
fn synthetic_evidence_cannot_qualify_production() {
    assert_eq!(
        case("P-08")["expected"]["production_release_load"],
        "reject"
    );
    let observations = local(Profile::PiQr);
    let result = assess_profile(
        Profile::PiQr,
        &observations,
        AssessmentContext::Production,
        true,
    );
    assert_eq!(
        result.blockers().next().unwrap().reason,
        BlockerReason::ConformanceEvidenceNotProduction
    );
    // Absence of the synthetic marker does not invent evidence; these exact
    // group observations remain an explicit caller input, not a wire conversion.
    let mut unknown = observations;
    unknown.groups = [LocalAssessment::UNKNOWN; 9];
    assert_eq!(
        assess_profile(
            Profile::PiQr,
            &unknown,
            AssessmentContext::Production,
            false
        )
        .blockers()
        .count(),
        8
    );
}

#[test]
fn reported_axes_remain_distinct_and_contradictions_reject() {
    let allowed = [
        ReportedFeature {
            support: Support::Supported,
            configuration: Configuration::Configured,
            availability: Availability::Available,
            reason: None,
        },
        ReportedFeature {
            support: Support::Supported,
            configuration: Configuration::Unconfigured,
            availability: Availability::Unavailable,
            reason: Some(Reason::Locked),
        },
        ReportedFeature {
            support: Support::Supported,
            configuration: Configuration::Configured,
            availability: Availability::Unavailable,
            reason: Some(Reason::ProviderMissing),
        },
        ReportedFeature {
            support: Support::Unknown,
            configuration: Configuration::Unknown,
            availability: Availability::Unknown,
            reason: Some(Reason::Unknown),
        },
    ];
    assert_eq!(case("A-01")["expected"]["distinct_states"], allowed.len());
    for feature in allowed {
        assert_eq!(feature.validate(), Ok(()));
    }
    let mut feature = allowed[0];
    for support in [Support::Unavailable, Support::Unknown] {
        feature.support = support;
        assert_eq!(feature.validate(), Err(StateError::ConfiguredUnsupported));
    }
    feature = allowed[0];
    feature.configuration = Configuration::Unconfigured;
    assert_eq!(
        feature.validate(),
        Err(StateError::AvailableWithoutConfiguration)
    );
    feature.configuration = Configuration::Unavailable;
    assert_eq!(
        feature.validate(),
        Err(StateError::AvailableWithoutConfiguration)
    );
    feature = allowed[0];
    feature.reason = Some(Reason::Busy);
    assert_eq!(feature.validate(), Err(StateError::AvailableWithReason));
    feature = allowed[3];
    feature.reason = None;
    assert_eq!(feature.validate(), Err(StateError::MissingReason));
    feature.reason = Some(Reason::NotImplemented);
    assert_eq!(feature.validate(), Ok(()));
}

fn conformance_limits() -> FiniteLimits {
    FiniteLimits {
        request_json_bytes: 704,
        response_json_bytes: 8192,
        frame_bytes: 1024,
        reassembly_bytes: 8192,
        frame_count: 32,
        retained_bytes: 8192,
        pending_requests: 1,
        queued_frames: 0,
        queued_operations: 0,
        cached_responses: 0,
        deadline_ms: 100,
    }
}

#[test]
fn finite_limits_keep_local_caps_and_zero_disabled_queues() {
    let local = conformance_limits();
    assert_eq!(local.validate(), Ok(()));
    assert_eq!(
        local.frame_bytes,
        case("L-05")["input"]["serial_frame_cap"].as_u64().unwrap()
    );
    assert_eq!(
        local.request_json_bytes,
        case("L-05")["input"]["legacy_request_cap"]
            .as_u64()
            .unwrap()
    );
    let mut smaller = local;
    smaller.request_json_bytes = 512;
    smaller.deadline_ms = 50;
    let intersection = local.intersect(smaller).unwrap();
    assert_eq!(intersection.request_json_bytes, 512);
    assert_eq!(intersection.frame_bytes, 1024);
    assert_eq!(intersection.deadline_ms, 50);
    assert_eq!(intersection.queued_frames, 0);
    assert_eq!(intersection.queued_operations, 0);
    assert_eq!(intersection.cached_responses, 0);
    let mut bad = local;
    bad.pending_requests = 0;
    assert_eq!(bad.validate(), Err(LimitError::ZeroRequired));
    assert_eq!(bad.intersect(local), Err(LimitError::ZeroRequired));
    assert_eq!(local.intersect(bad), Err(LimitError::ZeroRequired));
    bad = local;
    bad.request_json_bytes = MAX_SAFE_INTEGER + 1;
    assert_eq!(bad.validate(), Err(LimitError::UnsafeInteger));
    bad = local;
    bad.queued_frames = MAX_SAFE_INTEGER + 1;
    assert_eq!(bad.validate(), Err(LimitError::UnsafeInteger));
    bad = local;
    bad.pending_requests = 12;
    assert_eq!(bad.validate(), Err(LimitError::AggregateInsufficient));
    bad = local;
    bad.reassembly_bytes += 1;
    assert_eq!(bad.validate(), Err(LimitError::AggregateInsufficient));
    bad = local;
    bad.response_json_bytes += 1;
    assert_eq!(bad.validate(), Err(LimitError::AggregateInsufficient));
    bad = local;
    bad.request_json_bytes = MAX_SAFE_INTEGER;
    bad.pending_requests = MAX_SAFE_INTEGER;
    assert_eq!(bad.validate(), Err(LimitError::ArithmeticOverflow));
    bad = local;
    bad.frame_bytes = MAX_SAFE_INTEGER;
    bad.queued_frames = MAX_SAFE_INTEGER;
    assert_eq!(bad.validate(), Err(LimitError::ArithmeticOverflow));
    bad = local;
    bad.request_json_bytes = MAX_SAFE_INTEGER;
    bad.queued_operations = MAX_SAFE_INTEGER;
    assert_eq!(bad.validate(), Err(LimitError::ArithmeticOverflow));
    bad = local;
    bad.cached_responses = MAX_SAFE_INTEGER;
    assert_eq!(bad.validate(), Err(LimitError::ArithmeticOverflow));
    bad = local;
    bad.request_json_bytes = MAX_SAFE_INTEGER;
    bad.pending_requests = 2048;
    bad.queued_operations = 2048;
    assert_eq!(bad.validate(), Err(LimitError::ArithmeticOverflow));
}

#[test]
fn checked_expansion_rejects_before_allocation_at_independent_boundaries() {
    assert_eq!(checked_expansion(703, 704, 1, 0, 704), Ok(703));
    assert_eq!(checked_expansion(704, 704, 1, 0, 704), Ok(704));
    assert_eq!(
        checked_expansion(705, 704, 1, 0, 704),
        Err(LimitError::LimitExceeded)
    );
    for length in case("L-03")["input"]["lengths"].as_array().unwrap() {
        assert_eq!(
            checked_expansion(length.as_u64().unwrap(), 704, 4, 128, 1024),
            Err(LimitError::LimitExceeded)
        );
    }
    assert_eq!(
        checked_expansion(704, 704, 2, 0, 1024),
        Err(LimitError::LimitExceeded)
    );
    assert_eq!(
        checked_expansion(
            MAX_SAFE_INTEGER,
            MAX_SAFE_INTEGER,
            MAX_SAFE_INTEGER,
            0,
            MAX_SAFE_INTEGER
        ),
        Err(LimitError::ArithmeticOverflow)
    );
    assert_eq!(
        checked_expansion(1, MAX_SAFE_INTEGER + 1, 1, 0, 100),
        Err(LimitError::UnsafeInteger)
    );
    assert_eq!(
        checked_expansion(1, 100, 1, MAX_SAFE_INTEGER + 1, 100),
        Err(LimitError::UnsafeInteger)
    );
    assert_eq!(
        checked_expansion(1, 100, 0, 0, 100),
        Err(LimitError::ZeroRequired)
    );
    assert_eq!(
        checked_expansion(1, 0, 1, 0, 100),
        Err(LimitError::ZeroRequired)
    );
    assert_eq!(
        checked_expansion(1, 100, 1, 0, 0),
        Err(LimitError::ZeroRequired)
    );
}
