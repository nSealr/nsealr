//! One owned key, one immutable operation, and one consuming local consent.
//!
//! Host protocols cannot create local input or sign through this module.
//! Explicit engine signing requires one-use local consent and an injected,
//! fallible auxiliary source. Transport/device qualification is separate.
use crate::{
    event::{EventError, OperationLimits, ParsedRequest, RequestMethod},
    hash::Sha256,
    nip19::SecretKey,
    review::event::{
        validate_catalog, InspectionError, InspectionFrame, InspectionGeometry, ReviewDocument,
    },
};
use k256::schnorr::{Signature, SigningKey, VerifyingKey};
use zeroize::{Zeroize, Zeroizing};

/// Fixed portable-test lifetime in trusted monotonic ticks, not wall-clock time.
pub const REVIEW_LIFETIME: u64 = 100;
/// Diagnostic state, with no transferable execution authority.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthorizationState {
    /// No selected key.
    Locked,
    /// Key selected, no pending operation.
    Idle,
    /// Complete local inspection in progress.
    Reviewing,
    /// One private consent awaits its first attempt.
    Approved,
    /// An attempt has consumed consent; completion is still subject to invalidation.
    Executing,
    /// No remaining consent; a fresh request and review are required.
    Spent,
}
/// Closed failures from the portable authorization boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthorizationError {
    /// Strict request parsing failed.
    Parse(EventError),
    /// Semantic validation or complete review failed.
    Inspection(InspectionError),
    /// No selected actual key.
    Locked,
    /// An existing operation may not be replaced implicitly.
    Busy,
    /// Transition is not allowed from the current private state.
    InvalidState,
    /// Trusted monotonic time is missing, rolled back or overflowed.
    Clock,
    /// Fixed review deadline was reached.
    Expired,
    /// A bounded generation counter exhausted; reconstruct a locked owner.
    Exhausted,
    /// Correlation, operation or local context changed after review.
    Binding,
    /// Local display did not successfully present a complete frame.
    Display,
    /// The selected secret could not be admitted by the backend.
    Key,
    /// Production signing/output has not been qualified and is disabled.
    SigningUnavailable,
    /// The backend failed or returned a signature for other bytes/identity.
    Backend,
    /// Auxiliary input was unavailable, unhealthy, interrupted or not exactly 32 bytes.
    Auxiliary,
    /// The caller's public result buffer cannot hold the complete signed event.
    Output,
}
/// Maximum private public-result staging area; independent of retained consent.
pub const SIGNED_EVENT_BYTES: usize = 9216;
/// Fallible auxiliary-source failure; there is no deterministic fallback/retry.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuxiliaryError {
    /// No qualified source is available.
    Unavailable,
    /// Collection was interrupted.
    Interrupted,
    /// The source's own health check failed.
    Health,
    /// Other provider failure.
    Provider,
}
/// Synchronous provider for exactly 32 auxiliary bytes per signing attempt.
///
/// Return the number of bytes supplied, or a failure. The engine wipes its entire
/// destination on every path and refuses short/oversized reports. The provider
/// must stop all writes before returning; ongoing DMA, terminal recovery, source
/// entropy quality and physical qualification are adapter responsibilities.
pub trait AuxiliarySource {
    /// Fill only this destination, cease writes, then report the exact count.
    fn fill(&mut self, destination: &mut [u8; 32]) -> Result<usize, AuxiliaryError>;
}
fn fill_auxiliary(
    provider: &mut dyn AuxiliarySource,
    destination: &mut [u8; 32],
) -> Result<(), AuthorizationError> {
    destination.zeroize();
    if provider.fill(destination) != Ok(32) {
        destination.zeroize();
        return Err(AuthorizationError::Auxiliary);
    }
    Ok(())
}
impl From<EventError> for AuthorizationError {
    fn from(e: EventError) -> Self {
        Self::Parse(e)
    }
}
impl From<InspectionError> for AuthorizationError {
    fn from(e: InspectionError) -> Self {
        Self::Inspection(e)
    }
}

/// A physical-event result bound to the synchronous local presentation call.
/// Firmware adapters must never construct this from a host request or grant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LocalInput {
    /// No fresh local action.
    None,
    /// Acknowledge this data page and advance one page.
    Next,
    /// Return one page without changing the deadline.
    Back,
    /// Consent, accepted only on the separate final decision page.
    Approve,
    /// Reject this operation.
    Reject,
}
/// Borrowed presentation with no detached approval capability.
pub enum LocalPresentation<'a> {
    /// A complete fragment; all label, value and position data must be displayed.
    Data(&'a InspectionFrame),
    /// Distinct decision after every data page was displayed and acknowledged.
    Decision(&'a InspectionFrame),
}
/// Trusted-image display/input boundary, not a host protocol interface.
///
/// The adapter must present the entire frame and return only a fresh physical
/// action captured for that presentation. An error means no page was seen.
/// Hardware isolation, debounce and usable readable Unicode need device proof.
pub trait LocalReviewIo {
    /// Trusted monotonic ticks from the same clock used for intake/execution.
    fn now(&mut self) -> Option<u64>;
    /// Present completely and await/poll a fresh event for this exact frame.
    fn present(&mut self, frame: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError>;
}
/// Local display failure; it cannot acknowledge a page.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LocalDisplayError;

struct Pending {
    request: ParsedRequest,
    public_key: [u8; 32],
    event_id: [u8; 32],
    context: [u64; 21],
    review: [u8; 32],
    binding: [u8; 32],
    pages: usize,
    cursor: usize,
    seen: usize,
    deadline: u64,
}
struct Execution<'a> {
    owner: &'a mut AuthorizationSession,
    operation: u64,
    public_key: [u8; 32],
    event_id: [u8; 32],
    binding: [u8; 32],
}

/// Non-cloneable owner of custody, pending operation and one-use local consent.
///
/// No public constructor accepts an approved flag, external pages or a ticket.
/// `&mut self` serializes transitions; threaded callers must share this owner.
///
/// ```compile_fail
/// use nsealr_core::authorization::AuthorizationSession;
/// fn require_clone<T: Clone>() {}
/// require_clone::<AuthorizationSession>();
/// ```
/// ```compile_fail
/// use nsealr_core::authorization::AuthorizationSession;
/// fn steal(s: &AuthorizationSession) { let _ = &s.key; }
/// ```
/// ```compile_fail
/// use nsealr_core::authorization::AuthorizationSession;
/// fn bypass(s: &mut AuthorizationSession) {
///     s.execute("r", Some(0), |_, _| Ok([0; 64]));
/// }
/// ```
/// ```compile_fail
/// use nsealr_core::policy::approval_gate::ApprovalGate;
/// ```
pub struct AuthorizationSession {
    key: Option<SecretKey>,
    public_key: Option<[u8; 32]>,
    pending: Option<Pending>,
    state: AuthorizationState,
    session: u64,
    account: u64,
    policy: u64,
    operation: u64,
    limit_version: u64,
    review_version: u64,
    limits: OperationLimits,
    geometry: InspectionGeometry,
    last_now: Option<u64>,
    exhausted: bool,
}
impl AuthorizationSession {
    /// Constructs a locked owner with trusted local bounds.
    pub fn new(
        limits: OperationLimits,
        geometry: InspectionGeometry,
    ) -> Result<Self, AuthorizationError> {
        limits.validate()?;
        geometry.validate()?;
        Ok(Self {
            key: None,
            public_key: None,
            pending: None,
            state: AuthorizationState::Locked,
            session: 0,
            account: 0,
            policy: 0,
            operation: 0,
            limit_version: 0,
            review_version: 0,
            limits,
            geometry,
            last_now: None,
            exhausted: false,
        })
    }
    /// State for diagnostics only; copying it cannot authorize anything.
    pub fn state(&self) -> AuthorizationState {
        self.state
    }
    /// Public key derived from actual consumed custody, never a descriptor.
    pub fn public_key(&self) -> Option<[u8; 32]> {
        self.public_key
    }
    fn invalidate(&mut self) {
        self.pending = None;
        self.state = if self.key.is_some() {
            AuthorizationState::Spent
        } else {
            AuthorizationState::Locked
        };
    }
    fn advance(&mut self, which: fn(&mut Self) -> &mut u64) -> Result<(), AuthorizationError> {
        if self.exhausted {
            return Err(AuthorizationError::Exhausted);
        }
        if let Some(next) = which(self).checked_add(1) {
            *which(self) = next;
            Ok(())
        } else {
            self.exhausted = true;
            self.key = None;
            self.public_key = None;
            self.invalidate();
            Err(AuthorizationError::Exhausted)
        }
    }
    /// Retains the original S02 scalar as the sole long-lived secret owner.
    /// Only the derived x-only public key is cached. Odd-Y normalization occurs
    /// in a scoped backend conversion here and once per actual signing attempt;
    /// the original recovery representation is never replaced by n-d. Backend
    /// scratch/move wiping is not a universal target-memory guarantee.
    pub fn select_key(&mut self, secret: SecretKey) -> Result<(), AuthorizationError> {
        self.key = None;
        self.public_key = None;
        self.invalidate();
        self.advance(|s| &mut s.account)?;
        let public_key = {
            let backend =
                SigningKey::from_slice(secret.as_bytes()).map_err(|_| AuthorizationError::Key)?;
            backend.verifying_key().to_bytes().into()
        };
        self.key = Some(secret);
        self.public_key = Some(public_key);
        self.state = AuthorizationState::Idle;
        Ok(())
    }
    /// Cancels pending work and any in-flight completion, retaining selected key.
    pub fn cancel(&mut self) {
        self.invalidate();
    }
    /// Drops selected key and invalidates all old session callbacks.
    pub fn lock(&mut self) -> Result<(), AuthorizationError> {
        self.key = None;
        self.public_key = None;
        self.invalidate();
        self.advance(|s| &mut s.session)
    }
    /// Resets to locked and permits a fresh trusted clock epoch only after reset.
    pub fn reset(&mut self) -> Result<(), AuthorizationError> {
        self.lock()?;
        self.last_now = None;
        Ok(())
    }
    /// A trusted local policy change invalidates even an identical policy value.
    pub fn policy_changed(&mut self) -> Result<(), AuthorizationError> {
        self.invalidate();
        self.advance(|s| &mut s.policy)
    }
    /// Changes trusted review/limit configuration, invalidating prior consent.
    pub fn configure(
        &mut self,
        limits: OperationLimits,
        geometry: InspectionGeometry,
    ) -> Result<(), AuthorizationError> {
        self.invalidate();
        self.advance(|s| &mut s.limit_version)?;
        self.advance(|s| &mut s.review_version)?;
        limits.validate()?;
        geometry.validate()?;
        self.limits = limits;
        self.geometry = geometry;
        Ok(())
    }
    fn time(&mut self, now: Option<u64>) -> Result<u64, AuthorizationError> {
        let Some(now) = now else {
            self.invalidate();
            return Err(AuthorizationError::Clock);
        };
        if self.last_now.is_some_and(|last| now < last) {
            self.invalidate();
            return Err(AuthorizationError::Clock);
        }
        self.last_now = Some(now);
        if self.pending.as_ref().is_some_and(|p| now >= p.deadline) {
            self.invalidate();
            return Err(AuthorizationError::Expired);
        }
        Ok(now)
    }
    fn context(&self, deadline: u64) -> [u64; 21] {
        [
            1,
            self.session,
            self.account,
            self.policy,
            self.operation,
            self.limit_version,
            self.review_version,
            deadline,
            self.limits.input_bytes as u64,
            self.limits.content_bytes as u64,
            self.limits.tags as u64,
            self.limits.fields_per_tag as u64,
            self.limits.field_bytes as u64,
            self.limits.text_bytes as u64,
            self.limits.canonical_bytes as u64,
            self.limits.review_pages as u64,
            self.geometry.columns as u64,
            self.geometry.lines as u64,
            2,
            1,
            REVIEW_LIFETIME,
        ]
    }
    fn document<'a>(&self, p: &'a Pending) -> ReviewDocument<'a> {
        ReviewDocument {
            event: p
                .request
                .event
                .as_ref()
                .expect("sign-event pending invariant"),
            public_key: &p.public_key,
            event_id: &p.event_id,
            request_id: p.request.request_id(),
            context: &p.context,
            geometry: self.geometry,
            max_pages: self.limits.review_pages,
            limits: self.limits,
        }
    }
    fn binding(p: &Pending) -> [u8; 32] {
        let mut hash = Sha256::new();
        for bytes in [
            b"nsealr.authorization.v1".as_slice(),
            p.request.request_id().as_bytes(),
            &p.public_key,
            &p.event_id,
            &p.review,
        ] {
            hash.update(&(bytes.len() as u64).to_be_bytes());
            hash.update(bytes);
        }
        for n in p.context.iter().chain(core::iter::once(&p.deadline)) {
            hash.update(&8u64.to_be_bytes());
            hash.update(&n.to_be_bytes());
        }
        hash.update(&8u64.to_be_bytes());
        hash.update(&(p.pages as u64).to_be_bytes());
        hash.finalize()
    }
    /// Parses and preflights one request. Busy intake never replaces or extends it.
    /// `now` must come from the trusted local monotonic clock, never the host.
    pub fn begin_request(
        &mut self,
        input: &[u8],
        now: Option<u64>,
    ) -> Result<(), AuthorizationError> {
        if self.exhausted {
            return Err(AuthorizationError::Exhausted);
        }
        let key = self.public_key().ok_or(AuthorizationError::Locked)?;
        let now = self.time(now)?;
        if matches!(
            self.state,
            AuthorizationState::Reviewing
                | AuthorizationState::Approved
                | AuthorizationState::Executing
        ) {
            return Err(AuthorizationError::Busy);
        }
        self.invalidate();
        let request = ParsedRequest::parse(input, self.limits)?;
        if request.method() != RequestMethod::SignEvent {
            return Err(AuthorizationError::InvalidState);
        }
        let event = request.event.as_ref().ok_or(AuthorizationError::Binding)?;
        validate_catalog(event, &key, self.limits)?;
        let event_id = event.event_id(&key)?;
        let deadline = now
            .checked_add(REVIEW_LIFETIME)
            .ok_or(AuthorizationError::Clock)?;
        self.advance(|s| &mut s.operation)?;
        let mut pending = Pending {
            request,
            public_key: key,
            event_id,
            context: self.context(deadline),
            review: [0; 32],
            binding: [0; 32],
            pages: 0,
            cursor: 0,
            seen: 0,
            deadline,
        };
        let (review, total) = self.document(&pending).commitment()?;
        pending.review = review;
        pending.pages = total - 1; // The final separately rendered decision frame.
        pending.binding = Self::binding(&pending);
        self.pending = Some(pending);
        self.state = AuthorizationState::Reviewing;
        Ok(())
    }
    /// Presents exactly the current page and handles only its synchronous local event.
    /// Display failure leaves the page unacknowledged; time is checked on both sides.
    pub fn review_step(&mut self, io: &mut impl LocalReviewIo) -> Result<(), AuthorizationError> {
        self.time(io.now())?;
        if self.state != AuthorizationState::Reviewing {
            self.invalidate();
            return Err(AuthorizationError::InvalidState);
        }
        let p = self.pending.as_ref().ok_or(AuthorizationError::Binding)?;
        let input = if p.cursor < p.pages {
            let frame = self.document(p).frame(p.cursor, p.pages + 1)?;
            io.present(LocalPresentation::Data(&frame))
        } else {
            let frame = self.document(p).frame(p.pages, p.pages + 1)?;
            io.present(LocalPresentation::Decision(&frame))
        };
        self.time(io.now())?;
        let input = input.map_err(|_| AuthorizationError::Display)?;
        let p = self.pending.as_mut().ok_or(AuthorizationError::Binding)?;
        match input {
            LocalInput::None => {}
            LocalInput::Reject => self.invalidate(),
            LocalInput::Back => p.cursor = p.cursor.saturating_sub(1),
            LocalInput::Next if p.cursor < p.pages => {
                p.cursor += 1;
                p.seen = p.seen.max(p.cursor);
            }
            LocalInput::Approve if p.cursor == p.pages && p.seen == p.pages => {
                self.state = AuthorizationState::Approved
            }
            _ => {
                self.invalidate();
                return Err(AuthorizationError::InvalidState);
            }
        }
        Ok(())
    }
    fn validate_pending(&self, p: &Pending) -> Result<(), AuthorizationError> {
        if p.request.method() != RequestMethod::SignEvent
            || p.pages >= self.limits.review_pages
            || self.public_key() != Some(p.public_key)
            || p.context != self.context(p.deadline)
            || p.seen != p.pages
            || p.cursor != p.pages
            || p.event_id
                != p.request
                    .event
                    .as_ref()
                    .ok_or(AuthorizationError::Binding)?
                    .event_id(&p.public_key)?
            || self.document(p).commitment()? != (p.review, p.pages + 1)
            || Self::binding(p) != p.binding
        {
            return Err(AuthorizationError::Binding);
        }
        Ok(())
    }
    fn consume_approval(&mut self) -> Result<(), AuthorizationError> {
        // The consuming linearization point precedes even the fresh clock call.
        let previous = core::mem::replace(&mut self.state, AuthorizationState::Spent);
        if previous != AuthorizationState::Approved {
            self.invalidate();
            return Err(AuthorizationError::InvalidState);
        }
        Ok(())
    }
    fn start_execution(
        &mut self,
        request_id: &str,
        now: Option<u64>,
    ) -> Result<Execution<'_>, AuthorizationError> {
        self.consume_approval()?;
        self.start_consumed_execution(request_id, now)
    }
    fn start_consumed_execution(
        &mut self,
        request_id: &str,
        now: Option<u64>,
    ) -> Result<Execution<'_>, AuthorizationError> {
        let result = (|| {
            self.time(now)?;
            let p = self.pending.as_ref().ok_or(AuthorizationError::Binding)?;
            if p.request.request_id() != request_id {
                return Err(AuthorizationError::Binding);
            }
            self.validate_pending(p)?;
            Ok((self.operation, p.public_key, p.event_id, p.binding))
        })();
        match result {
            Ok((operation, public_key, event_id, binding)) => {
                self.state = AuthorizationState::Executing;
                Ok(Execution {
                    owner: self,
                    operation,
                    public_key,
                    event_id,
                    binding,
                })
            }
            Err(error) => {
                self.invalidate();
                Err(error)
            }
        }
    }
    fn finish_execution(
        execution: Execution<'_>,
        result: Result<[u8; 64], AuthorizationError>,
        now: Option<u64>,
    ) -> Result<[u8; 64], AuthorizationError> {
        let owner = execution.owner;
        let valid =
            owner.state == AuthorizationState::Executing && owner.operation == execution.operation;
        let previous = core::mem::replace(&mut owner.state, AuthorizationState::Spent);
        let output = (|| {
            owner.time(now)?;
            if !valid || previous != AuthorizationState::Executing {
                return Err(AuthorizationError::Binding);
            }
            let p = owner.pending.as_ref().ok_or(AuthorizationError::Binding)?;
            owner.validate_pending(p)?;
            if p.binding != execution.binding
                || p.event_id != execution.event_id
                || p.public_key != execution.public_key
            {
                return Err(AuthorizationError::Binding);
            }
            let signature = result?;
            let key = VerifyingKey::from_slice(&execution.public_key)
                .map_err(|_| AuthorizationError::Backend)?;
            let sig = Signature::try_from(signature.as_slice())
                .map_err(|_| AuthorizationError::Backend)?;
            key.verify_raw(&execution.event_id, &sig)
                .map_err(|_| AuthorizationError::Backend)?;
            Ok(signature)
        })();
        owner.invalidate();
        output
    }
    fn backend_key(&self, expected: &[u8; 32]) -> Result<SigningKey, AuthorizationError> {
        let key = SigningKey::from_slice(
            self.key
                .as_ref()
                .ok_or(AuthorizationError::Locked)?
                .as_bytes(),
        )
        .map_err(|_| AuthorizationError::Key)?;
        if key.verifying_key().to_bytes().as_slice() != expected {
            return Err(AuthorizationError::Binding);
        }
        Ok(key)
    }
    fn execute(
        &mut self,
        request_id: &str,
        now: Option<u64>,
        backend: impl FnOnce(&SigningKey, &[u8; 32]) -> Result<[u8; 64], AuthorizationError>,
    ) -> Result<[u8; 64], AuthorizationError> {
        let execution = self.start_execution(request_id, now)?;
        let result = (|| {
            let key = execution.owner.backend_key(&execution.public_key)?;
            backend(&key, &execution.event_id)
        })();
        Self::finish_execution(execution, result, now)
    }
    /// Signs one completely reviewed operation with explicit local providers.
    ///
    /// Consent is spent before invoking `clock`, checking caller correlation or
    /// touching the auxiliary source/backend. The callback must supply fresh
    /// trusted monotonic ticks both before execution and before release. All
    /// errors leave the whole caller output zeroed and require a fresh review.
    /// The signature and privately staged serialization are released only after
    /// raw-ID verification and fresh completion/context checks. This API enables no transport,
    /// hardware isolation, production key or provider qualification.
    pub fn sign_approved(
        &mut self,
        request_id: &str,
        clock: &mut dyn FnMut() -> Option<u64>,
        auxiliary: &mut dyn AuxiliarySource,
        output: &mut [u8],
    ) -> Result<usize, AuthorizationError> {
        let consumed = self.consume_approval();
        output.fill(0);
        consumed?;
        let execution = self.start_consumed_execution(request_id, clock())?;
        let mut staged = [0u8; SIGNED_EVENT_BYTES];
        let mut length = 0;
        let result = (|| {
            let mut aux = Zeroizing::new([0u8; 32]);
            fill_auxiliary(auxiliary, &mut aux)?;
            let signature = {
                let key = execution.owner.backend_key(&execution.public_key)?;
                #[cfg(test)]
                tests::observe_backend_attempt();
                key.sign_raw(&execution.event_id, &aux)
                    .map_err(|_| AuthorizationError::Backend)?
                    .to_bytes()
            };
            let p = execution
                .owner
                .pending
                .as_ref()
                .ok_or(AuthorizationError::Binding)?;
            let serialized = p
                .request
                .event
                .as_ref()
                .ok_or(AuthorizationError::Binding)?
                .write_signed(
                    &execution.public_key,
                    &execution.event_id,
                    &signature,
                    &mut staged,
                );
            length = serialized?;
            if length > output.len() {
                return Err(AuthorizationError::Output);
            }
            Ok(signature)
        })();
        Self::finish_execution(execution, result, clock())?;
        output[..length].copy_from_slice(&staged[..length]);
        Ok(length)
    }
    /// Consumes the first attempt and reports disabled production signing.
    /// Failure, including a wrong request ID, never preserves retry authority.
    pub fn attempt_sign(
        &mut self,
        request_id: &str,
        now: Option<u64>,
    ) -> Result<(), AuthorizationError> {
        self.execute(request_id, now, |_, _| {
            Err(AuthorizationError::SigningUnavailable)
        })
        .map(|_| ())
    }
}

// These retained-storage ceilings also compile on the firmware target. They do
// not bound compiler-generated stack copies or backend scratch memory.
const _: () = assert!(core::mem::size_of::<Pending>() <= 8192);
const _: () = assert!(core::mem::size_of::<AuthorizationSession>() <= 16384);

#[cfg(test)]
mod tests;
