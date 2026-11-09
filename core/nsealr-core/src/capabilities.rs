//! Profile-specific compatibility data. None of these records is signing authority.
//!
//! Local observations are supplied by the trusted adapter. There is deliberately
//! no wire-deserialization path into them, release evidence or an authorization
//! session. Reported support and availability are separate diagnostic axes.

use crate::text::FixedStr;

/// Maximum identifier/label bytes in portable conformance data.
pub const MAX_IDENTIFIER_BYTES: usize = 128;
/// Maximum discovery JSON bytes in the portable conformance harness.
pub const MAX_DISCOVERY_JSON_BYTES: usize = 8192;
/// Maximum method entries in portable conformance data.
pub const MAX_METHODS: usize = 16;
/// Maximum transport entries in portable conformance data.
pub const MAX_TRANSPORTS: usize = 4;
/// Maximum diagnostics; this is not a measured device capacity.
pub const MAX_DIAGNOSTICS: usize = 32;
/// A bounded public identifier, never an evidence or authority token.
pub type Identifier = FixedStr<MAX_IDENTIFIER_BYTES>;

/// Largest exact public JSON integer; conversion must reject larger values.
pub const MAX_SAFE_INTEGER: u64 = 9_007_199_254_740_991;

/// Finite method/transport dimensions. Names carry bytes, counts and milliseconds;
/// no unit conversion or absent/unlimited value is inferred from a device claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FiniteLimits {
    /// Original decoded request JSON byte ceiling.
    pub request_json_bytes: u64,
    /// Decoded response JSON byte ceiling.
    pub response_json_bytes: u64,
    /// One encoded transport frame's byte ceiling.
    pub frame_bytes: u64,
    /// Complete reassembled decoded byte ceiling.
    pub reassembly_bytes: u64,
    /// Complete frame-count ceiling.
    pub frame_count: u64,
    /// Aggregate retained bytes, including pending frame/input reservations.
    pub retained_bytes: u64,
    /// Pending operation count ceiling.
    pub pending_requests: u64,
    /// Queued frame count; zero explicitly disables this queue.
    pub queued_frames: u64,
    /// Queued operation count; zero explicitly disables this queue.
    pub queued_operations: u64,
    /// Cached response count; zero explicitly disables response caching.
    pub cached_responses: u64,
    /// The local deadline policy in milliseconds; never extends S03 lifetime.
    pub deadline_ms: u64,
}

/// Failure of a finite bound or checked expansion.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LimitError {
    /// A dimension is not exactly representable by the public JSON contract.
    UnsafeInteger,
    /// A required dimension is zero; disabled queue/cache dimensions are separate.
    ZeroRequired,
    /// Simultaneous pending inputs cannot fit aggregate retention.
    AggregateInsufficient,
    /// Requested input or expanded output exceeds the smaller applicable cap.
    LimitExceeded,
    /// Checked encoding/retention arithmetic cannot be represented.
    ArithmeticOverflow,
}

impl FiniteLimits {
    /// Validate complete finite dimensions without allocating from peer sizes.
    pub fn validate(self) -> Result<(), LimitError> {
        let required = [
            self.request_json_bytes,
            self.response_json_bytes,
            self.frame_bytes,
            self.reassembly_bytes,
            self.frame_count,
            self.retained_bytes,
            self.pending_requests,
            self.deadline_ms,
        ];
        if required.contains(&0) {
            return Err(LimitError::ZeroRequired);
        }
        if required
            .iter()
            .copied()
            .chain([
                self.queued_frames,
                self.queued_operations,
                self.cached_responses,
            ])
            .any(|value| value > MAX_SAFE_INTEGER)
        {
            return Err(LimitError::UnsafeInteger);
        }
        let pending_bytes = self
            .request_json_bytes
            .checked_mul(self.pending_requests)
            .ok_or(LimitError::ArithmeticOverflow)?;
        let queued_frame_bytes = self
            .frame_bytes
            .checked_mul(self.queued_frames)
            .ok_or(LimitError::ArithmeticOverflow)?;
        let queued_operation_bytes = self
            .request_json_bytes
            .checked_mul(self.queued_operations)
            .ok_or(LimitError::ArithmeticOverflow)?;
        let cached_response_bytes = self
            .response_json_bytes
            .checked_mul(self.cached_responses)
            .ok_or(LimitError::ArithmeticOverflow)?;
        let retained = pending_bytes
            .checked_add(queued_frame_bytes)
            .and_then(|value| value.checked_add(queued_operation_bytes))
            .and_then(|value| value.checked_add(cached_response_bytes))
            .ok_or(LimitError::ArithmeticOverflow)?;
        if retained > self.retained_bytes
            || self.reassembly_bytes > self.retained_bytes
            || self.response_json_bytes > self.retained_bytes
        {
            return Err(LimitError::AggregateInsufficient);
        }
        Ok(())
    }

    /// Intersect exact dimensions; a peer never increases a local hard ceiling.
    pub fn intersect(self, peer: Self) -> Result<Self, LimitError> {
        self.validate()?;
        peer.validate()?;
        let result = Self {
            request_json_bytes: self.request_json_bytes.min(peer.request_json_bytes),
            response_json_bytes: self.response_json_bytes.min(peer.response_json_bytes),
            frame_bytes: self.frame_bytes.min(peer.frame_bytes),
            reassembly_bytes: self.reassembly_bytes.min(peer.reassembly_bytes),
            frame_count: self.frame_count.min(peer.frame_count),
            retained_bytes: self.retained_bytes.min(peer.retained_bytes),
            pending_requests: self.pending_requests.min(peer.pending_requests),
            queued_frames: self.queued_frames.min(peer.queued_frames),
            queued_operations: self.queued_operations.min(peer.queued_operations),
            cached_responses: self.cached_responses.min(peer.cached_responses),
            deadline_ms: self.deadline_ms.min(peer.deadline_ms),
        };
        result.validate()?;
        Ok(result)
    }
}

/// Check bounded encoding expansion before allocation/retention. This arithmetic
/// helper makes no NIP-44 cryptographic or extended-length correctness claim.
pub fn checked_expansion(
    input_bytes: u64,
    input_cap: u64,
    multiplier: u64,
    overhead: u64,
    output_cap: u64,
) -> Result<u64, LimitError> {
    if input_cap == 0 || output_cap == 0 || multiplier == 0 {
        return Err(LimitError::ZeroRequired);
    }
    if input_bytes > MAX_SAFE_INTEGER
        || input_cap > MAX_SAFE_INTEGER
        || output_cap > MAX_SAFE_INTEGER
        || multiplier > MAX_SAFE_INTEGER
        || overhead > MAX_SAFE_INTEGER
    {
        return Err(LimitError::UnsafeInteger);
    }
    if input_bytes > input_cap {
        return Err(LimitError::LimitExceeded);
    }
    let expanded = input_bytes
        .checked_mul(multiplier)
        .and_then(|value| value.checked_add(overhead))
        .ok_or(LimitError::ArithmeticOverflow)?;
    if expanded > output_cap {
        return Err(LimitError::LimitExceeded);
    }
    Ok(expanded)
}

/// The four existing signer profiles. Board SDK and external signers are separate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Profile {
    /// Connected initial MCU profile with explicit absent SE.
    Esp32NoSe,
    /// Offline Pi QR profile with volatile custody.
    PiQr,
    /// Offline P4 QR profile with volatile custody.
    P4Qr,
    /// Connected custom profile requiring the selected SE configuration.
    CustomBoard,
}

impl Profile {
    /// Exact public profile identifier.
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::Esp32NoSe => "esp32_no_se",
            Self::PiQr => "pi_qr",
            Self::P4Qr => "p4_qr",
            Self::CustomBoard => "custom_board",
        }
    }

    /// Reject unknown profiles; never choose another device on failure.
    #[must_use]
    pub fn from_id(id: &str) -> Option<Self> {
        match id {
            "esp32_no_se" => Some(Self::Esp32NoSe),
            "pi_qr" => Some(Self::PiQr),
            "p4_qr" => Some(Self::P4Qr),
            "custom_board" => Some(Self::CustomBoard),
            _ => None,
        }
    }

    /// Whether the first connected release requires message qualification.
    #[must_use]
    pub const fn requires_messages(self) -> bool {
        matches!(self, Self::Esp32NoSe | Self::CustomBoard)
    }

    /// Custody required by this profile's first release.
    #[must_use]
    pub const fn custody(self) -> Custody {
        match self {
            Self::Esp32NoSe => Custody::McuWrappedPersistent,
            Self::PiQr | Self::P4Qr => Custody::VolatileSession,
            Self::CustomBoard => Custody::CustomSeAssistedPersistent,
        }
    }
}

/// Implementation support, independent of configuration or availability.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Support {
    /// Implemented for the exact selected manifest.
    Supported,
    /// Explicitly unavailable; never interpreted as configured or verified.
    Unavailable,
    /// Not established; blocks a required property.
    Unknown,
}

/// Selected configuration, independent of release qualification.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Configuration {
    /// Selected by the local configuration, not evidence of qualification.
    Configured,
    /// Implemented but not selected/configured.
    Unconfigured,
    /// Explicitly unavailable; never interpreted as configured or verified.
    Unavailable,
    /// Not established; blocks a required property.
    Unknown,
}

/// Current availability, rechecked by the operation owner at use.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Availability {
    /// Currently available within the selected finite constraints.
    Available,
    /// Explicitly unavailable; never interpreted as configured or verified.
    Unavailable,
    /// Not established; blocks a required property.
    Unknown,
}

/// Local evidence assessment. This axis is not part of a wire descriptor.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verification {
    /// Local evidence supports the exact scoped property.
    Verified,
    /// No accepted verification for the claimed property.
    Unverified,
    /// Explicitly unavailable; never interpreted as configured or verified.
    Unavailable,
    /// Not established; blocks a required property.
    Unknown,
}

/// Closed diagnostic reason vocabulary, not arbitrary host-supplied evidence.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    /// The local provider/session is locked.
    Locked,
    /// The required provider is missing.
    ProviderMissing,
    /// The bounded local resource is busy.
    Busy,
    /// The operation is not implemented.
    NotImplemented,
    /// Not established; blocks a required property.
    Unknown,
}

/// Untrusted reported feature state. It cannot become a local observation.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ReportedFeature {
    /// Reported implementation support; never local verification.
    pub support: Support,
    /// Reported selected configuration.
    pub configuration: Configuration,
    /// Current availability axis.
    pub availability: Availability,
    /// Closed unavailable/unknown reason; none for available state.
    pub reason: Option<Reason>,
}

/// A contradictory descriptor must reject, rather than be normalized.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StateError {
    /// Configured state contradicts unsupported or unknown implementation.
    ConfiguredUnsupported,
    /// Available requires supported and configured state.
    AvailableWithoutConfiguration,
    /// Available state must not carry a failure reason.
    AvailableWithReason,
    /// Unavailable or unknown state requires a bounded reason.
    MissingReason,
}

impl ReportedFeature {
    /// Validate the independent axes without promoting them to trusted state.
    pub fn validate(self) -> Result<(), StateError> {
        if self.configuration == Configuration::Configured && self.support != Support::Supported {
            return Err(StateError::ConfiguredUnsupported);
        }
        if self.availability == Availability::Available {
            if self.support != Support::Supported || self.configuration != Configuration::Configured
            {
                return Err(StateError::AvailableWithoutConfiguration);
            }
            if self.reason.is_some() {
                return Err(StateError::AvailableWithReason);
            }
        } else if self.reason.is_none() {
            return Err(StateError::MissingReason);
        }
        Ok(())
    }
}

/// Explicit custody designs; absence of a required component never selects another.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Custody {
    /// Session-only identity; no persistent identity storage.
    VolatileSession,
    /// MCU-wrapped persistent identity; no SE protection inferred.
    McuWrappedPersistent,
    /// Persistent design depending on exact required SE configuration.
    CustomSeAssistedPersistent,
}

/// Observation about the exact required component/configuration.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ComponentObservation {
    /// Explicitly no SE, as required by the no-SE/offline profiles.
    Absent,
    /// Trusted adapter observed the exact selected part/configuration.
    MatchingRequiredConfiguration,
    /// Not established; blocks a required property.
    Unknown,
    /// Observed part or configuration does not match the required one.
    WrongPartOrConfiguration,
    /// Required provider failed or is unavailable.
    ProviderUnavailable,
}

/// Existing release assertion groups, not new task or release states.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Requirement {
    /// Custody-derived identity and expected-key/output binding.
    Identity,
    /// Honest review and one-use local consent.
    Authorization,
    /// The exact implemented operation/catalog contract.
    Catalog,
    /// Secret ownership,provider and entropy constraints.
    Secret,
    /// Finite input/output/work/retention/deadline constraints.
    Bounds,
    /// Same-identity local recovery/import/export requirements.
    Recovery,
    /// Exact boot/update/debug/interface and limitation evidence.
    Lifecycle,
    /// Existing reviewed release procedures/artifact binding.
    Release,
    /// Connected-profile primitive/context/workflow qualification.
    Messages,
}

impl Requirement {
    /// Original T01/P01 group identifier.
    #[must_use]
    pub const fn id(self) -> &'static str {
        match self {
            Self::Identity => "R-ID",
            Self::Authorization => "R-AUTH",
            Self::Catalog => "R-CATALOG",
            Self::Secret => "R-SECRET",
            Self::Bounds => "R-BOUNDS",
            Self::Recovery => "R-RECOVERY",
            Self::Lifecycle => "R-LIFECYCLE",
            Self::Release => "R-RELEASE",
            Self::Messages => "R-MSG",
        }
    }
}

/// The fixed group order allows bounded diagnostics and exact missing-group tests.
pub const REQUIREMENTS: [Requirement; 9] = [
    Requirement::Identity,
    Requirement::Authorization,
    Requirement::Catalog,
    Requirement::Secret,
    Requirement::Bounds,
    Requirement::Recovery,
    Requirement::Lifecycle,
    Requirement::Release,
    Requirement::Messages,
];

/// A trusted local assessment, constructed by the adapter, never from wire fields.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LocalAssessment {
    /// Current availability axis.
    pub availability: Availability,
    /// Trusted local evidence assessment, not a wire assertion.
    pub verification: Verification,
}

impl LocalAssessment {
    /// Missing observations are unknown, never implicitly true.
    pub const UNKNOWN: Self = Self {
        availability: Availability::Unknown,
        verification: Verification::Unknown,
    };
}

/// Trusted local inputs. No constructor accepts `ReportedFeature` or JSON.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalObservations {
    /// Locally selected actual custody.
    pub custody: Custody,
    /// Trusted observation of the required/absent component.
    pub component: ComponentObservation,
    /// One independent local assessment per fixed requirement group.
    pub groups: [LocalAssessment; 9],
    /// Actual boot-enforcement availability, not download authenticity.
    pub boot_enforcement: Availability,
    /// Evidence for a scoped boot limitation, when permitted.
    pub boot_limitation_evidence: Verification,
}

/// Evidence context only; neither variant creates a release or signing authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AssessmentContext {
    /// Evaluate production evidence eligibility; synthetic evidence rejects.
    Production,
    /// Diagnostic synthetic inputs only; no release or physical claim.
    ConformanceOnly,
}

/// Why one exact requirement is blocked.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BlockerReason {
    /// Not established; blocks a required property.
    Unknown,
    /// Explicitly unavailable; never interpreted as configured or verified.
    Unavailable,
    /// No accepted verification for the claimed property.
    Unverified,
    /// Selected custody differs from this profile requirement.
    CustodyMismatch,
    /// The exact required component/configuration is not available.
    RequiredComponentUnavailable,
    /// The explicit absent-component requirement was not met.
    UnexpectedComponent,
    /// Required boot or scoped limitation evidence is missing.
    MissingBootLimitationEvidence,
    /// Synthetic conformance data cannot qualify production.
    ConformanceEvidenceNotProduction,
}

/// Bounded per-group diagnostic. A matching descriptor alone supplies none of it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Blocker {
    /// The exact blocked requirement.
    pub requirement: Requirement,
    /// Closed unavailable/unknown reason; none for available state.
    pub reason: BlockerReason,
}

/// Profile assessment contains reasons, not a universal `signing_enabled` value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfileAssessment {
    /// The locally selected signer profile; never chosen by a wire claim.
    pub profile: Profile,
    blockers: [Option<Blocker>; MAX_DIAGNOSTICS],
    len: usize,
}

impl ProfileAssessment {
    /// Actual blockers only; unused bounded capacity is not exposed as evidence.
    pub fn blockers(&self) -> impl Iterator<Item = &Blocker> {
        self.blockers[..self.len].iter().flatten()
    }

    fn block(&mut self, requirement: Requirement, reason: BlockerReason) {
        // At most nine groups plus four profile-specific checks below.
        self.blockers[self.len] = Some(Blocker {
            requirement,
            reason,
        });
        self.len += 1;
    }
}

/// Assess the selected profile against actual local inputs. This diagnostic
/// cannot construct S03 consent, authenticate attached hardware or ship a release.
#[must_use]
pub fn assess_profile(
    profile: Profile,
    observations: &LocalObservations,
    context: AssessmentContext,
    conformance_evidence: bool,
) -> ProfileAssessment {
    let mut result = ProfileAssessment {
        profile,
        blockers: [None; MAX_DIAGNOSTICS],
        len: 0,
    };
    for (index, requirement) in REQUIREMENTS.iter().copied().enumerate() {
        if requirement == Requirement::Messages && !profile.requires_messages() {
            continue;
        }
        let observation = observations.groups[index];
        let reason = match (observation.availability, observation.verification) {
            (Availability::Unknown, _) | (_, Verification::Unknown) => Some(BlockerReason::Unknown),
            (Availability::Unavailable, _) => Some(BlockerReason::Unavailable),
            (_, Verification::Unverified | Verification::Unavailable) => {
                Some(BlockerReason::Unverified)
            }
            (Availability::Available, Verification::Verified) => None,
        };
        if let Some(reason) = reason {
            result.block(requirement, reason);
        }
    }
    if observations.custody != profile.custody() {
        result.block(Requirement::Secret, BlockerReason::CustodyMismatch);
    }
    match (profile, observations.component) {
        (Profile::CustomBoard, ComponentObservation::MatchingRequiredConfiguration) => {}
        (Profile::CustomBoard, _) => result.block(
            Requirement::Secret,
            BlockerReason::RequiredComponentUnavailable,
        ),
        (_, ComponentObservation::Absent) => {}
        (_, _) => result.block(Requirement::Secret, BlockerReason::UnexpectedComponent),
    }
    match observations.boot_enforcement {
        Availability::Available => {}
        Availability::Unavailable
            if profile == Profile::PiQr
                && observations.boot_limitation_evidence == Verification::Verified => {}
        _ => result.block(
            Requirement::Lifecycle,
            BlockerReason::MissingBootLimitationEvidence,
        ),
    }
    if conformance_evidence && context == AssessmentContext::Production {
        result.block(
            Requirement::Release,
            BlockerReason::ConformanceEvidenceNotProduction,
        );
    }
    result
}
