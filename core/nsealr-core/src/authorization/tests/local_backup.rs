use super::*;
use core::cell::RefCell;
use std::collections::VecDeque;

#[derive(Default)]
struct Observation {
    key_location: Option<usize>,
    wiped: Option<[u8; 64]>,
}
std::thread_local! {
    static OBSERVATION: RefCell<Observation> = RefCell::new(Observation::default());
}
pub(in crate::authorization) fn observe_key_location(location: usize) {
    OBSERVATION.with(|o| o.borrow_mut().key_location = Some(location));
}
pub(in crate::authorization) fn observe_text_wipe(text: &[u8; 64]) {
    // Only already-zero bytes are copied, while the workspace is still live.
    OBSERVATION.with(|o| o.borrow_mut().wiped = Some(*text));
}

#[derive(Clone, Copy)]
enum Change {
    Context,
    MissingContext,
    MissingClock,
    Clock(u64),
}
struct BackupIo {
    input: VecDeque<LocalInput>,
    clock: Option<u64>,
    epoch: Option<u64>,
    present_change: Option<(usize, Change)>,
    reveal_change: Option<Change>,
    clear_change: Option<Change>,
    fail_present: Option<usize>,
    fail_reveal: bool,
    fail_clear: bool,
    frames: Vec<(String, String, usize, bool, [u8; 32])>,
    reveals: Vec<String>,
    reveal_deadline: Option<u64>,
    clears: usize,
    visible: bool,
}
impl Default for BackupIo {
    fn default() -> Self {
        Self {
            input: [
                LocalInput::None,
                LocalInput::Next,
                LocalInput::None,
                LocalInput::Approve,
            ]
            .into_iter()
            .collect(),
            clock: Some(0),
            epoch: Some(7),
            present_change: None,
            reveal_change: None,
            clear_change: None,
            fail_present: None,
            fail_reveal: false,
            fail_clear: false,
            frames: Vec::new(),
            reveals: Vec::new(),
            reveal_deadline: None,
            clears: 0,
            visible: false,
        }
    }
}
impl BackupIo {
    fn change(&mut self, change: Change) {
        match change {
            Change::Context => self.epoch = self.epoch.and_then(|n| n.checked_add(1)),
            Change::MissingContext => self.epoch = None,
            Change::MissingClock => self.clock = None,
            Change::Clock(n) => self.clock = Some(n),
        }
    }
    fn scripted(input: &[LocalInput]) -> Self {
        Self {
            input: input.iter().copied().collect(),
            ..Self::default()
        }
    }
}
impl LocalNsecBackupIo for BackupIo {
    fn now(&mut self) -> Option<u64> {
        self.clock
    }
    fn context(&mut self) -> Option<u64> {
        self.epoch
    }
    fn present(
        &mut self,
        frame: &LocalNsecBackupFrame<'_>,
        deadline: u64,
    ) -> Result<LocalInput, LocalDisplayError> {
        assert_eq!(frame.total(), 2);
        assert!(self.clock.unwrap_or(0) < deadline);
        self.frames.push((
            frame.title().into(),
            frame.body().into(),
            frame.index(),
            frame.is_decision(),
            *frame.public_key(),
        ));
        let call = self.frames.len();
        if let Some((at, change)) = self.present_change {
            if at == call {
                self.change(change);
            }
        }
        if self.fail_present == Some(call) {
            return Err(LocalDisplayError);
        }
        Ok(self.input.pop_front().unwrap_or(LocalInput::None))
    }
    fn reveal(&mut self, nsec: &str, deadline: u64) -> Result<(), LocalDisplayError> {
        assert_eq!(nsec.len(), 63);
        // Deliberate copies are exclusively of published fixture material.
        self.reveals.push(nsec.into());
        self.visible = true;
        self.reveal_deadline = Some(deadline);
        if let Some(change) = self.reveal_change {
            self.change(change);
        }
        if self.fail_reveal {
            Err(LocalDisplayError)
        } else {
            Ok(())
        }
    }
    fn clear(&mut self) -> Result<(), LocalDisplayError> {
        self.clears += 1;
        if let Some(change) = self.clear_change {
            self.change(change);
        }
        if self.fail_clear {
            return Err(LocalDisplayError);
        }
        self.visible = false;
        Ok(())
    }
}
fn run(owner: &mut AuthorizationSession, io: &mut BackupIo) -> Result<(), LocalNsecBackupError> {
    let key_location = owner
        .key
        .as_ref()
        .map(|key| key.as_bytes().as_ptr() as usize);
    OBSERVATION.with(|o| *o.borrow_mut() = Observation::default());
    let before = backend_calls();
    let result = owner.backup_nsec_and_lock(io);
    assert_eq!(
        backend_calls(),
        before,
        "backup must not invoke the signing backend"
    );
    assert!(owner.key.is_none() && owner.public_key().is_none() && owner.pending.is_none());
    assert_eq!(owner.state(), AuthorizationState::Locked);
    assert_eq!(io.clears, 1);
    OBSERVATION.with(|o| {
        let o = o.borrow();
        assert_eq!(o.wiped, Some([0; 64]));
        if o.key_location.is_some() {
            assert_eq!(
                o.key_location, key_location,
                "borrow the live original slot in place"
            );
        }
    });
    result
}
fn error(error: AuthorizationError) -> LocalNsecBackupError {
    LocalNsecBackupError::Authorization(error)
}

#[test]
fn local_nsec_backup_original_odd_y_borrow_warning_and_no_payload() {
    for row in k01_inputs()["identity_expectations"].as_array().unwrap() {
        let encoded = row["original_scalar_hex"].as_str().unwrap();
        let mut raw = [0; 32];
        for (i, b) in raw.iter_mut().enumerate() {
            *b = u8::from_str_radix(&encoded[i * 2..i * 2 + 2], 16).unwrap();
        }
        let original = raw;
        let mut owner = session();
        owner
            .select_key(SecretKey::take_from(&mut raw).unwrap())
            .unwrap();
        let pk = owner.public_key().unwrap();
        let mut io = BackupIo::default();
        let status: Result<(), LocalNsecBackupError> = run(&mut owner, &mut io);
        assert_eq!(status, Ok(()));
        assert_eq!(io.reveals.len(), 1);
        let recovered = crate::nip19::decode_nsec(&io.reveals[0]).unwrap();
        assert_eq!(recovered.as_bytes(), &original);
        if row["public_fixture_scalar"] == "n-3" {
            assert_ne!(recovered.as_bytes(), secret(3).as_bytes());
        }
        assert_eq!(io.reveal_deadline, Some(120));
        assert_eq!(io.frames.len(), 4);
        for f in &io.frames {
            assert_eq!(f.4, pk);
            assert!(f.1.lines().all(|line| line.len() <= 32));
        }
        assert_eq!(io.frames[0].0, "Secret recovery");
        assert_eq!(
            io.frames[0].1,
            "nsec is your identity secret.\nAnyone with it can sign.\nCopy only in private."
        );
        assert_eq!(io.frames[0].2, 0);
        assert!(!io.frames[0].3);
        assert_eq!(io.frames[2].0, "Backup and lock");
        assert_eq!(
            io.frames[2].1,
            "Show nsec, then lock?\nCopies do not revoke others.\nReload locally to sign again."
        );
        assert_eq!(io.frames[2].2, 1);
        assert!(io.frames[2].3);
        assert!(!io.visible);
    }
}

#[test]
fn local_nsec_backup_rejects_stale_early_and_wrong_page_actions() {
    let cases: &[(&[LocalInput], LocalNsecBackupError)] = &[
        (&[LocalInput::Next], LocalNsecBackupError::StaleInput),
        (&[LocalInput::Approve], LocalNsecBackupError::StaleInput),
        (
            &[LocalInput::None, LocalInput::Approve],
            LocalNsecBackupError::InvalidInput,
        ),
        (
            &[LocalInput::None, LocalInput::Next, LocalInput::Approve],
            LocalNsecBackupError::StaleInput,
        ),
        (
            &[
                LocalInput::None,
                LocalInput::Next,
                LocalInput::None,
                LocalInput::Next,
            ],
            LocalNsecBackupError::InvalidInput,
        ),
    ];
    for &(input, expected) in cases {
        let mut owner = session();
        let mut io = BackupIo::scripted(input);
        assert_eq!(run(&mut owner, &mut io), Err(expected));
        assert!(io.reveals.is_empty());
    }
}

#[test]
fn local_nsec_backup_back_navigation_requires_neutral_again() {
    let mut io = BackupIo::scripted(&[
        LocalInput::None,
        LocalInput::Next,
        LocalInput::None,
        LocalInput::Back,
        LocalInput::None,
        LocalInput::Next,
        LocalInput::None,
        LocalInput::Approve,
    ]);
    assert_eq!(run(&mut session(), &mut io), Ok(()));
    assert_eq!(
        io.frames.iter().map(|f| f.2).collect::<Vec<_>>(),
        [0, 0, 1, 1, 0, 0, 1, 1]
    );
}

#[test]
fn local_nsec_backup_cancel_and_present_errors_retire_old_approval() {
    for fail in [None, Some(1), Some(4)] {
        let mut owner = approved(EMPTY);
        let previous = owner.session;
        let mut io = BackupIo {
            fail_present: fail,
            ..BackupIo::default()
        };
        if fail.is_none() {
            io.input = [LocalInput::Reject].into_iter().collect();
        }
        assert_eq!(
            run(&mut owner, &mut io),
            Err(if fail.is_some() {
                LocalNsecBackupError::Display
            } else {
                LocalNsecBackupError::Cancelled
            })
        );
        assert_eq!(owner.session, previous + 2);
        assert!(io.reveals.is_empty());
        assert!(owner.attempt_sign("r", Some(0)).is_err());
    }
}

#[test]
fn local_nsec_backup_frozen_clock_and_none_input_are_finite() {
    let mut io = BackupIo::scripted(&[]);
    assert_eq!(
        run(&mut session(), &mut io),
        Err(LocalNsecBackupError::StepLimit)
    );
    assert_eq!(io.frames.len(), NSEC_BACKUP_MAX_PRESENTATIONS);
    assert!(io.reveals.is_empty());
}

#[test]
fn local_nsec_backup_context_before_reveal_and_after_reveal() {
    for change in [Change::Context, Change::MissingContext] {
        for at in [1, 2, 3, 4] {
            let mut io = BackupIo {
                present_change: Some((at, change)),
                ..BackupIo::default()
            };
            assert_eq!(
                run(&mut session(), &mut io),
                Err(LocalNsecBackupError::Context)
            );
            assert!(io.reveals.is_empty());
        }
        let mut io = BackupIo {
            reveal_change: Some(change),
            ..BackupIo::default()
        };
        assert_eq!(
            run(&mut session(), &mut io),
            Err(LocalNsecBackupError::Context)
        );
        assert_eq!(
            io.reveals.len(),
            1,
            "an authorized disclosure cannot be recalled"
        );
    }
    let mut io = BackupIo {
        epoch: None,
        ..BackupIo::default()
    };
    assert_eq!(
        run(&mut session(), &mut io),
        Err(LocalNsecBackupError::Context)
    );
    assert!(io.frames.is_empty());
}

#[test]
fn local_nsec_backup_missing_and_rollback_clocks_retire_without_reveal() {
    for clock in [None, Some(9)] {
        let mut owner = session();
        owner.time(Some(10)).unwrap();
        let mut io = BackupIo {
            clock,
            ..BackupIo::default()
        };
        assert_eq!(
            run(&mut owner, &mut io),
            Err(error(AuthorizationError::Clock))
        );
        assert!(io.reveals.is_empty());
    }
    for at in [1, 2, 3, 4] {
        for change in [Change::MissingClock, Change::Clock(9)] {
            let mut io = BackupIo {
                clock: Some(10),
                present_change: Some((at, change)),
                ..BackupIo::default()
            };
            assert_eq!(
                run(&mut session(), &mut io),
                Err(error(AuthorizationError::Clock))
            );
            assert!(io.reveals.is_empty());
        }
    }
}

#[test]
fn local_nsec_backup_deadline_overflow_and_expiry_precede_disclosure() {
    let mut io = BackupIo {
        clock: Some(u64::MAX - 599),
        ..BackupIo::default()
    };
    assert_eq!(
        run(&mut session(), &mut io),
        Err(error(AuthorizationError::Clock))
    );
    assert!(io.frames.is_empty());
    let mut io = BackupIo {
        clock: Some(u64::MAX - 600),
        present_change: Some((4, Change::Clock(u64::MAX - 100))),
        ..BackupIo::default()
    };
    assert_eq!(
        run(&mut session(), &mut io),
        Err(error(AuthorizationError::Clock))
    );
    assert!(io.reveals.is_empty());
    let mut io = BackupIo {
        present_change: Some((4, Change::Clock(600))),
        ..BackupIo::default()
    };
    assert_eq!(
        run(&mut session(), &mut io),
        Err(error(AuthorizationError::Expired))
    );
    assert!(io.reveals.is_empty());
}

#[test]
fn local_nsec_backup_reveal_deadline_is_capped_by_total_lifetime() {
    let mut io = BackupIo {
        present_change: Some((4, Change::Clock(550))),
        ..BackupIo::default()
    };
    assert_eq!(run(&mut session(), &mut io), Ok(()));
    assert_eq!(io.reveal_deadline, Some(600));
}

#[test]
fn local_nsec_backup_expired_or_failed_reveal_may_have_exposed_bytes() {
    for (change, expected) in [
        (Change::Clock(120), error(AuthorizationError::Expired)),
        (Change::Clock(0), LocalNsecBackupError::Display),
        (Change::MissingClock, error(AuthorizationError::Clock)),
    ] {
        let mut io = BackupIo {
            reveal_change: Some(change),
            fail_reveal: true,
            ..BackupIo::default()
        };
        assert_eq!(run(&mut session(), &mut io), Err(expected));
        assert_eq!(io.reveals.len(), 1);
        assert!(!io.visible);
    }
}

#[test]
fn local_nsec_backup_clear_failure_has_priority_and_no_zero_exposure_claim() {
    for reject in [false, true] {
        let mut io = BackupIo {
            fail_clear: true,
            ..BackupIo::default()
        };
        if reject {
            io.input = [LocalInput::Reject].into_iter().collect();
        }
        assert_eq!(
            run(&mut session(), &mut io),
            Err(LocalNsecBackupError::Clear)
        );
        assert_eq!(io.reveals.len(), usize::from(!reject));
        assert_eq!(io.visible, !reject);
    }
    for change in [Change::MissingClock, Change::Clock(120)] {
        let mut io = BackupIo {
            clear_change: Some(change),
            ..BackupIo::default()
        };
        let expected = match change {
            Change::MissingClock => AuthorizationError::Clock,
            _ => AuthorizationError::Expired,
        };
        assert_eq!(run(&mut session(), &mut io), Err(error(expected)));
        assert_eq!(io.reveals.len(), 1);
    }
}

#[test]
fn local_nsec_backup_counters_reserve_retirement_before_reveal() {
    for session_counter in [u64::MAX - 1, u64::MAX] {
        let mut owner = session();
        owner.session = session_counter;
        let mut io = BackupIo::default();
        assert_eq!(
            run(&mut owner, &mut io),
            Err(error(AuthorizationError::Exhausted))
        );
        assert!(owner.exhausted);
        assert!(io.reveals.is_empty());
        assert_eq!(
            owner.select_key(secret(3)),
            Err(AuthorizationError::Exhausted)
        );
    }
    let mut owner = session();
    owner.session = u64::MAX - 2;
    let mut io = BackupIo::default();
    assert_eq!(run(&mut owner, &mut io), Ok(()));
    assert_eq!(owner.session, u64::MAX);
}

#[test]
fn local_nsec_backup_locked_owner_and_retained_clock_epoch() {
    let mut owner = AuthorizationSession::new(limits(), geometry()).unwrap();
    let mut io = BackupIo::default();
    assert_eq!(
        run(&mut owner, &mut io),
        Err(error(AuthorizationError::Locked))
    );
    assert!(io.frames.is_empty());
    assert!(io.reveals.is_empty());
    let mut owner = session();
    let mut io = BackupIo {
        clock: Some(50),
        ..BackupIo::default()
    };
    assert_eq!(run(&mut owner, &mut io), Ok(()));
    assert_eq!(owner.last_now, Some(50));
    owner.select_key(secret(3)).unwrap();
    let mut io = BackupIo {
        clock: Some(49),
        ..BackupIo::default()
    };
    assert_eq!(
        run(&mut owner, &mut io),
        Err(error(AuthorizationError::Clock))
    );
    assert!(io.reveals.is_empty());
}
