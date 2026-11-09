//! Native local nsec disclosure from the existing owner, followed by retirement.
//!
//! This is trusted-image IO, not a transport API or hardware qualification.
use super::{
    AuthorizationError, AuthorizationSession, AuthorizationState, LocalDisplayError, LocalInput,
};
use crate::nip19::encode_nsec;
use zeroize::{Zeroize, Zeroizing};

/// Maximum local backup flow duration in trusted monotonic seconds.
pub const NSEC_BACKUP_LIFETIME: u64 = 600;
/// Maximum reveal duration, also bounded by the complete backup deadline.
pub const NSEC_BACKUP_REVEAL_LIFETIME: u64 = 120;
/// Finite presentation budget, including neutral events and navigation.
pub const NSEC_BACKUP_MAX_PRESENTATIONS: usize = 32;

/// Closed local recovery failures; none carries secret material.
///
/// Any error may follow an authorized reveal attempt. It cannot recall bytes or
/// pixels already handed to the trusted IO or deliberately copied by the user.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LocalNsecBackupError {
    /// An existing owner, clock, counter or key invariant failed.
    Authorization(AuthorizationError),
    /// The local user rejected the flow.
    Cancelled,
    /// An action arrived before neutral was observed for this presentation.
    StaleInput,
    /// An action is not permitted on the current warning/decision page.
    InvalidInput,
    /// The finite presentation budget was exhausted.
    StepLimit,
    /// The trusted local recovery/revocation epoch changed or disappeared.
    Context,
    /// Presentation or reveal failed; a failed reveal may already have disclosed.
    Display,
    /// The clear attempt failed. The adapter must quarantine uncertain display
    /// storage and refuse a fresh device session until its own cleanup succeeds.
    Clear,
}

/// A borrowed public warning/decision, constructed only by the owner.
///
/// The adapter must display the complete title, body and actual full public key.
/// These public fields contain no nsec. Copying the frame creates no authority.
pub struct LocalNsecBackupFrame<'a> {
    public_key: &'a [u8; 32],
    decision: bool,
}

impl LocalNsecBackupFrame<'_> {
    /// Public title to present completely.
    pub fn title(&self) -> &'static str {
        if self.decision {
            "Backup and lock"
        } else {
            "Secret recovery"
        }
    }
    /// Complete warning or decision text.
    pub fn body(&self) -> &'static str {
        if self.decision {
            "Show nsec, then lock?\nCopies do not revoke others.\nReload locally to sign again."
        } else {
            "nsec is your identity secret.\nAnyone with it can sign.\nCopy only in private."
        }
    }
    /// The selected public key, derived from the original owned scalar.
    pub fn public_key(&self) -> &[u8; 32] {
        self.public_key
    }
    /// Zero-based position, with a separate final decision.
    pub fn index(&self) -> usize {
        usize::from(self.decision)
    }
    /// The complete flow has one warning and one decision.
    pub fn total(&self) -> usize {
        2
    }
    /// Whether this is the separate final decision; this is not approval.
    pub fn is_decision(&self) -> bool {
        self.decision
    }
}

/// Synchronous trusted local recovery IO, never supplied by a host request.
///
/// The clock uses monotonic seconds in the same domain/unit as the owner.
/// The context is the recovery/revocation epoch, stable across legitimate page
/// changes, not an external ticket or approval capability. Presentation-specific
/// stale events must also be rejected by the adapter.
///
/// Hardware consent, complete readable rendering and physical memory behavior
/// remain device obligations; an IO return value does not attest those facts.
pub trait LocalNsecBackupIo {
    /// Trusted monotonic seconds, with no host clock or deadline rescaling.
    fn now(&mut self) -> Option<u64>;
    /// Current trusted local recovery/revocation epoch.
    fn context(&mut self) -> Option<u64>;
    /// Present the whole public frame before returning input for that frame.
    ///
    /// None means an actual neutral/released condition observed after successful
    /// presentation. A fresh subsequent physical event may then return Next,
    /// Back, Approve or Reject. A held/queued event from another view is not fresh.
    /// Return before the absolute deadline; failure acknowledges no page.
    fn present(
        &mut self,
        frame: &LocalNsecBackupFrame<'_>,
        deadline: u64,
    ) -> Result<LocalInput, LocalDisplayError>;
    /// Borrow the canonical original nsec for explicitly approved local display.
    ///
    /// Do not log, transport, retain a reference or continue accessing it after
    /// return. Deliberate raster/text copies belong to the adapter's sensitive
    /// inventory. Honor the absolute reveal deadline. Even Err may mean bytes
    /// were already delivered; the owner always attempts clear afterwards.
    fn reveal(&mut self, nsec: &str, deadline: u64) -> Result<(), LocalDisplayError>;
    /// Attempt to clear local copies and deliver a blank display after every
    /// returning path, even when no reveal occurred.
    ///
    /// RAM zeroization evidence and blank delivery/ACK are separate properties;
    /// ACK does not attest physical erasure of LCD memory. Failure requires
    /// adapter quarantine, not a claim of zero exposure or successful erasure.
    fn clear(&mut self) -> Result<(), LocalDisplayError>;
}

struct BackupBinding {
    owner: [u64; 21],
    local: u64,
    deadline: u64,
    public_key: [u8; 32],
}

impl AuthorizationSession {
    fn backup_checkpoint(
        &mut self,
        io: &mut dyn LocalNsecBackupIo,
        binding: &BackupBinding,
        until: u64,
    ) -> Result<u64, LocalNsecBackupError> {
        let now = self
            .time(io.now())
            .map_err(LocalNsecBackupError::Authorization)?;
        if io.context() != Some(binding.local)
            || self.context(binding.deadline) != binding.owner
            || self.public_key() != Some(binding.public_key)
            || self.state != AuthorizationState::Spent
        {
            return Err(LocalNsecBackupError::Context);
        }
        if now >= until {
            return Err(LocalNsecBackupError::Authorization(
                AuthorizationError::Expired,
            ));
        }
        Ok(now)
    }

    /// Review a local nsec backup, attempt display cleanup, and retire custody.
    ///
    /// Pending work and old consent are invalidated before any IO. The original
    /// SecretKey is borrowed in place, never taken, cloned or normalized. Only a
    /// complete warning, separate decision and fresh neutral/event sequence may
    /// reach reveal. No seed, auxiliary or signing provider is invoked.
    ///
    /// Every returning path wipes the current 64-byte text workspace, locks the
    /// owner in place and attempts IO clear. Lock preserves the trusted clock
    /// epoch. Clear failure is reported for adapter quarantine; this core method
    /// does not attest pixels, inaccessible SDK/backend copies, physical erasure
    /// or cleanup after panic/abort/nonreturning IO.
    ///
    /// Errors after reveal cannot recall an already disclosed backup. The
    /// returned status carries no secret payload.
    ///
    /// ```compile_fail
    /// use nsealr_core::{
    ///     authorization::{AuthorizationSession, LocalNsecBackupIo},
    ///     nip19::SecretKey,
    /// };
    /// fn raw_key(owner: &mut AuthorizationSession, io: &mut dyn LocalNsecBackupIo) -> SecretKey {
    ///     owner.backup_nsec_and_lock(io).unwrap()
    /// }
    /// ```
    pub fn backup_nsec_and_lock(
        &mut self,
        io: &mut dyn LocalNsecBackupIo,
    ) -> Result<(), LocalNsecBackupError> {
        self.invalidate();
        let mut text = Zeroizing::new([0u8; 64]);
        let mut completion_deadline = None;
        let result = (|| {
            self.advance(|s| &mut s.session)
                .map_err(LocalNsecBackupError::Authorization)?;
            // Reserve the final lock generation before any disclosure.
            if self.session == u64::MAX {
                return Err(LocalNsecBackupError::Authorization(
                    AuthorizationError::Exhausted,
                ));
            }
            let public_key = self
                .public_key()
                .ok_or(LocalNsecBackupError::Authorization(
                    AuthorizationError::Locked,
                ))?;
            let start = self
                .time(io.now())
                .map_err(LocalNsecBackupError::Authorization)?;
            let deadline = start.checked_add(NSEC_BACKUP_LIFETIME).ok_or(
                LocalNsecBackupError::Authorization(AuthorizationError::Clock),
            )?;
            completion_deadline = Some(deadline);
            let binding = BackupBinding {
                owner: self.context(deadline),
                local: io.context().ok_or(LocalNsecBackupError::Context)?,
                deadline,
                public_key,
            };
            let mut decision = false;
            let mut seen_warning = false;
            let mut neutral = false;
            for _ in 0..NSEC_BACKUP_MAX_PRESENTATIONS {
                self.backup_checkpoint(io, &binding, deadline)?;
                let frame = LocalNsecBackupFrame {
                    public_key: &binding.public_key,
                    decision,
                };
                let input = io.present(&frame, deadline);
                let now = self.backup_checkpoint(io, &binding, deadline)?;
                let input = input.map_err(|_| LocalNsecBackupError::Display)?;
                match input {
                    LocalInput::Reject => return Err(LocalNsecBackupError::Cancelled),
                    LocalInput::None => neutral = true,
                    _ if !neutral => return Err(LocalNsecBackupError::StaleInput),
                    LocalInput::Next if !decision => {
                        seen_warning = true;
                        decision = true;
                        neutral = false;
                    }
                    LocalInput::Back => {
                        decision = false;
                        neutral = false;
                    }
                    LocalInput::Approve if decision && seen_warning => {
                        let reveal_deadline = now
                            .checked_add(NSEC_BACKUP_REVEAL_LIFETIME)
                            .ok_or(LocalNsecBackupError::Authorization(
                                AuthorizationError::Clock,
                            ))?
                            .min(deadline);
                        completion_deadline = Some(reveal_deadline);
                        let key = self
                            .key
                            .as_ref()
                            .ok_or(LocalNsecBackupError::Authorization(
                                AuthorizationError::Locked,
                            ))?;
                        #[cfg(test)]
                        super::tests::local_backup::observe_key_location(
                            key.as_bytes().as_ptr() as usize
                        );
                        let nsec = encode_nsec(key, &mut *text).map_err(|_| {
                            LocalNsecBackupError::Authorization(AuthorizationError::Key)
                        })?;
                        self.backup_checkpoint(io, &binding, reveal_deadline)?;
                        let displayed = io.reveal(nsec, reveal_deadline);
                        self.backup_checkpoint(io, &binding, reveal_deadline)?;
                        return displayed.map_err(|_| LocalNsecBackupError::Display);
                    }
                    _ => return Err(LocalNsecBackupError::InvalidInput),
                }
            }
            Err(LocalNsecBackupError::StepLimit)
        })();
        text.zeroize();
        #[cfg(test)]
        super::tests::local_backup::observe_text_wipe(&text);
        // Retire custody before clear, which is itself an external IO call.
        let locked = self.lock();
        let cleared = io.clear();
        let ended = self.time(io.now());
        // Clear has precedence: the adapter must not miss uncertain display state.
        cleared.map_err(|_| LocalNsecBackupError::Clear)?;
        locked.map_err(LocalNsecBackupError::Authorization)?;
        result?;
        let ended = ended.map_err(LocalNsecBackupError::Authorization)?;
        if completion_deadline.is_some_and(|deadline| ended >= deadline) {
            return Err(LocalNsecBackupError::Authorization(
                AuthorizationError::Expired,
            ));
        }
        Ok(())
    }
}
