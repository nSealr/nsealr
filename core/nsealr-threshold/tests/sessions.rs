use nsealr_core::event::Event;
use nsealr_threshold::*;
use zeroize::Zeroizing;

struct Entropy {
    byte: u8,
    fail: bool,
    short: bool,
}
impl Entropy {
    fn new(byte: u8) -> Self {
        Self {
            byte,
            fail: false,
            short: false,
        }
    }
}
impl EntropySource for Entropy {
    fn fill(&mut self, seed: &mut [u8; 32]) -> Result<usize, Error> {
        seed.fill(self.byte);
        self.byte = self.byte.wrapping_add(1);
        if self.fail {
            Err(Error::Entropy)
        } else if self.short {
            Ok(31)
        } else {
            Ok(32)
        }
    }
}
struct Local {
    now: u64,
    live: bool,
    allow: bool,
    authenticate: bool,
    delay_review: bool,
    delay_round: bool,
    checks: usize,
    revoke_on: usize,
    saved: Option<ReviewApproval>,
    use_saved: bool,
}
impl Local {
    fn new() -> Self {
        Self {
            now: 1,
            live: true,
            allow: true,
            authenticate: true,
            delay_review: false,
            delay_round: false,
            checks: 0,
            revoke_on: usize::MAX,
            saved: None,
            use_saved: false,
        }
    }
}
impl ReviewAuthority for Local {
    fn now_ms(&mut self) -> Option<u64> {
        Some(self.now)
    }
    fn review(&mut self, intent: ReviewIntent<'_>) -> Result<ReviewApproval, Error> {
        assert_eq!(intent.event.content(), "threshold test: complete event");
        assert_eq!(intent.event.kind(), 1);
        assert_eq!(
            intent.group.public_key(),
            intent.binding.intent.public_key()
        );
        assert_eq!(intent.event.id(), *intent.binding.intent.event_id());
        assert!(intent
            .binding
            .intent
            .participants()
            .contains(&intent.binding.participant));
        if !self.allow {
            return Err(Error::Review);
        }
        if self.delay_review {
            self.now = intent.binding.deadline_ms;
        }
        if self.use_saved {
            return self.saved.take().ok_or(Error::Review);
        }
        self.saved = Some(intent.approve());
        Ok(intent.approve())
    }
    fn check_live(&mut self, _: &ReviewBinding) -> Result<(), Error> {
        self.checks += 1;
        if !self.live || self.checks == self.revoke_on {
            Err(Error::Review)
        } else {
            Ok(())
        }
    }
    fn admit_round(&mut self, binding: &ReviewBinding, round: &SigningRound) -> Result<(), Error> {
        assert_eq!(&binding.intent, round.intent());
        if self.delay_round {
            self.now = binding.deadline_ms;
        }
        if self.authenticate {
            Ok(())
        } else {
            Err(Error::Review)
        }
    }
}
fn event(pubkey: &[u8; 32]) -> Event {
    Event::parse(&serde_json::to_vec(&serde_json::json!({"pubkey":hex(pubkey),"created_at":1700000000,"kind":1,"tags":[],"content":"threshold test: complete event"})).unwrap(),pubkey).unwrap()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn setup(threshold: u16, count: u16) -> Vec<Participant> {
    dealer(threshold, count, None, &mut Entropy::new(1)).unwrap()
}
fn owners(participants: Vec<Participant>) -> Vec<Signer> {
    participants
        .into_iter()
        .map(|participant| {
            let mut s = Signer::new();
            s.select(participant);
            s
        })
        .collect()
}
fn commit(
    signers: &mut [Signer],
    group: &Group,
    set: &[ParticipantId],
    session: u8,
    source: &mut Entropy,
) -> (RoundIntent, Vec<Commitment>, Vec<Local>) {
    let intent =
        RoundIntent::for_event(group, &event(group.public_key()), [session; 32], set).unwrap();
    let mut authorities: Vec<_> = signers.iter().map(|_| Local::new()).collect();
    let commitments = signers
        .iter_mut()
        .zip(&mut authorities)
        .map(|(signer, local)| {
            signer
                .begin(
                    event(group.public_key()),
                    intent.clone(),
                    100,
                    local,
                    source,
                )
                .unwrap()
        })
        .collect();
    (intent, commitments, authorities)
}
#[test]
fn dealer_2_of_3_and_3_of_5_restore_and_sign() {
    for (threshold, count) in [(2, 3), (3, 5)] {
        let participants = setup(threshold, count);
        let group = participants[0].group().clone();
        let selected: Vec<_> = participants
            .into_iter()
            .rev()
            .take(threshold as usize)
            .map(|p| {
                let backup = p.backup().unwrap();
                assert!(backup.len() <= MAX_BACKUP_BYTES);
                Participant::restore(&backup, group.identity(), &p.identifier()).unwrap()
            })
            .collect();
        let ids: Vec<_> = selected.iter().map(Participant::identifier).collect();
        let mut signers = owners(selected);
        let (intent, commitments, mut local) =
            commit(&mut signers, &group, &ids, 9, &mut Entropy::new(10));
        let mut reversed = commitments.clone();
        reversed.reverse();
        let round = SigningRound::new(&intent, &reversed).unwrap();
        let shares: Vec<_> = signers
            .iter_mut()
            .zip(&mut local)
            .map(|(s, a)| s.sign(&round, a).unwrap())
            .collect();
        assert!(round.aggregate(&group, &shares).is_ok());
        assert_eq!(signers[0].sign(&round, &mut local[0]), Err(Error::State));
        let mut malicious = shares.clone();
        malicious[0].scalar = [0; 32];
        assert_eq!(round.aggregate(&group, &malicious), Err(Error::Crypto));
        let mut duplicate = shares.clone();
        duplicate[1] = duplicate[0].clone();
        assert_eq!(round.aggregate(&group, &duplicate), Err(Error::Participant));
        assert_eq!(round.aggregate(&group, &shares[..1]), Err(Error::Bounds));
        let wrong_group = setup(threshold, count).remove(0).group().clone();
        // Deterministic fixture source gives the same group; alter its source here.
        let wrong_group = if wrong_group.identity() == group.identity() {
            dealer(threshold, count, None, &mut Entropy::new(90))
                .unwrap()
                .remove(0)
                .group()
                .clone()
        } else {
            wrong_group
        };
        assert_eq!(round.aggregate(&wrong_group, &shares), Err(Error::Group));
    }
}
#[test]
fn signing_rejects_changed_event_group_session_participant_set_and_own_commitment() {
    for attack in 0..5 {
        let participants = setup(2, 3);
        let group = participants[0].group().clone();
        let ids: Vec<_> = participants
            .iter()
            .take(2)
            .map(Participant::identifier)
            .collect();
        let all: Vec<_> = participants.iter().map(Participant::identifier).collect();
        let mut signers = owners(participants);
        let (intent, mut commitments, mut local) =
            commit(&mut signers[..2], &group, &ids, 9, &mut Entropy::new(10));
        let changed = match attack {
            0 => {
                let other = Event::parse(
                    &serde_json::to_vec(&serde_json::json!({"pubkey":hex(group.public_key()),"created_at":1700000001,"kind":1,"tags":[],"content":"changed"})).unwrap(),
                    group.public_key(),
                )
                .unwrap();
                RoundIntent::for_event(&group, &other, [9; 32], &ids).unwrap()
            }
            1 => {
                RoundIntent::for_event(&group, &event(group.public_key()), [10; 32], &ids).unwrap()
            }
            2 => RoundIntent::for_event(&group, &event(group.public_key()), [9; 32], &all[1..])
                .unwrap(),
            3 => {
                let other = dealer(2, 3, None, &mut Entropy::new(90))
                    .unwrap()
                    .remove(0)
                    .group()
                    .clone();
                RoundIntent::for_event(&other, &event(other.public_key()), [9; 32], &ids).unwrap()
            }
            _ => intent.clone(),
        };
        if attack == 2 {
            commitments[0].participant = all[2];
        }
        for c in &mut commitments {
            c.intent = *changed.binding();
        }
        if attack == 4 {
            commitments[0].points = commitments[1].points;
        }
        let round = SigningRound::new(&changed, &commitments).unwrap();
        assert_eq!(signers[0].sign(&round, &mut local[0]), Err(Error::Binding));
        assert_eq!(signers[0].sign(&round, &mut local[0]), Err(Error::State));
    }
}
#[test]
fn malformed_duplicate_unknown_and_mixed_commitments_fail_before_signing() {
    let p = setup(2, 3);
    let group = p[0].group().clone();
    let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
    let mut s = owners(p);
    let (intent, c, _) = commit(&mut s[..2], &group, &ids, 7, &mut Entropy::new(22));
    let mut bad = c.clone();
    bad[1] = bad[0].clone();
    assert!(matches!(
        SigningRound::new(&intent, &bad),
        Err(Error::Binding)
    ));
    bad = c.clone();
    bad[1].intent[31] ^= 1;
    assert!(matches!(
        SigningRound::new(&intent, &bad),
        Err(Error::Binding)
    ));
    bad = c.clone();
    bad[1].points = [0; 66];
    assert!(matches!(
        SigningRound::new(&intent, &bad),
        Err(Error::Encoding)
    ));
    assert!(matches!(
        SigningRound::new(&intent, &c[..1]),
        Err(Error::Bounds)
    ));
    assert!(matches!(
        RoundIntent::for_event(
            &group,
            &event(group.public_key()),
            [0; 32],
            &[ids[0], ids[0]]
        ),
        Err(Error::Participant)
    ));
    assert!(matches!(
        RoundIntent::for_event(
            &group,
            &event(group.public_key()),
            [0; 32],
            &[[0; 32], [0; 32]]
        ),
        Err(Error::Participant)
    ));
    assert!(matches!(
        RoundIntent::for_event(&group, &event(group.public_key()), [0; 32], &[ids[0]; 6]),
        Err(Error::Bounds)
    ));
}
#[test]
fn error_cancel_lock_timeout_clock_and_replay_retire_nonce() {
    for failure in 0..8 {
        let p = setup(2, 3);
        let group = p[0].group().clone();
        let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
        let mut s = owners(p);
        let (intent, c, mut local) = commit(&mut s[..2], &group, &ids, 8, &mut Entropy::new(20));
        let round = SigningRound::new(&intent, &c).unwrap();
        match failure {
            0 => s[0].cancel(),
            1 => s[0].lock(),
            2 => local[0].now = 100,
            3 => local[0].now = 0,
            4 => local[0].live = false,
            5 => local[0].authenticate = false,
            6 => local[0].delay_round = true,
            _ => local[0].revoke_on = local[0].checks + 3,
        }
        assert!(
            s[0].sign(&round, &mut local[0]).is_err(),
            "failure={failure}"
        );
        local[0] = Local::new();
        assert_eq!(s[0].sign(&round, &mut local[0]), Err(Error::State));
    }
}
#[test]
fn review_entropy_and_busy_errors_emit_no_commitment_and_no_old_nonce() {
    for failure in 0..6 {
        let p = setup(2, 3);
        let group = p[0].group().clone();
        let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
        let mut s = owners(p);
        let intent =
            RoundIntent::for_event(&group, &event(group.public_key()), [1; 32], &ids).unwrap();
        let mut local = Local::new();
        let mut entropy = Entropy::new(10);
        match failure {
            0 => local.allow = false,
            1 => local.delay_review = true,
            2 => entropy.fail = true,
            3 => entropy.short = true,
            4 => local.revoke_on = 2,
            _ => local.now = 101,
        }
        assert!(s[0]
            .begin(
                event(group.public_key()),
                intent.clone(),
                100,
                &mut local,
                &mut entropy
            )
            .is_err());
        assert_ne!(s[0].state(), State::Committed);
    }
    let p = setup(2, 3);
    let group = p[0].group().clone();
    let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
    let mut s = owners(p);
    let (intent, c, mut local) = commit(&mut s[..2], &group, &ids, 1, &mut Entropy::new(10));
    let round = SigningRound::new(&intent, &c).unwrap();
    assert_eq!(
        s[0].begin(
            event(group.public_key()),
            intent,
            100,
            &mut local[0],
            &mut Entropy::new(15)
        ),
        Err(Error::State)
    );
    assert_eq!(s[0].sign(&round, &mut local[0]), Err(Error::State));
}
#[test]
fn fresh_backup_restore_has_no_round_and_requires_expected_group_and_share() {
    let p = setup(2, 3);
    let group = p[0].group().clone();
    let first = p[0].identifier();
    let backup = p[0].backup().unwrap();
    assert!(matches!(
        Participant::restore(&backup, &[4; 32], &first),
        Err(Error::Group)
    ));
    assert!(matches!(
        Participant::restore(&backup, group.identity(), &p[1].identifier()),
        Err(Error::Participant)
    ));
    for pos in [0, 4, 36, 68, 100, backup.len() - 1] {
        let mut bad = backup.to_vec();
        bad[pos] ^= 1;
        assert!(Participant::restore(&bad, group.identity(), &first).is_err());
    }
    let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
    let mut s = owners(p);
    let (intent, c, mut local) = commit(&mut s[..2], &group, &ids, 1, &mut Entropy::new(10));
    let round = SigningRound::new(&intent, &c).unwrap();
    let after = s[0].selected().unwrap().backup().unwrap();
    assert_eq!(*backup, *after);
    s[0].select(Participant::restore(&after, group.identity(), &first).unwrap());
    assert_eq!(s[0].sign(&round, &mut local[0]), Err(Error::State));
}
#[test]
fn repeat_seed_after_cancel_is_rejected_and_nonconsecutive_repeat_uses_new_stream() {
    let mut p = setup(2, 3);
    let group = p[0].group().clone();
    let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
    let mut s = Signer::new();
    s.select(p.remove(0));
    let intent = RoundIntent::for_event(&group, &event(group.public_key()), [1; 32], &ids).unwrap();
    let mut local = Local::new();
    let first = s
        .begin(
            event(group.public_key()),
            intent.clone(),
            100,
            &mut local,
            &mut Entropy::new(10),
        )
        .unwrap();
    s.cancel();
    assert_eq!(
        s.begin(
            event(group.public_key()),
            intent.clone(),
            100,
            &mut local,
            &mut Entropy::new(10)
        ),
        Err(Error::Entropy)
    );
    let second = s
        .begin(
            event(group.public_key()),
            intent.clone(),
            100,
            &mut local,
            &mut Entropy::new(11),
        )
        .unwrap();
    s.cancel();
    let third = s
        .begin(
            event(group.public_key()),
            intent,
            100,
            &mut local,
            &mut Entropy::new(10),
        )
        .unwrap();
    assert_ne!(first.points, second.points);
    assert_ne!(first.points, third.points);
}
#[test]
fn stale_typed_approval_cannot_approve_new_round() {
    let mut p = setup(2, 3);
    let group = p[0].group().clone();
    let ids: Vec<_> = p.iter().take(2).map(Participant::identifier).collect();
    let mut s = Signer::new();
    s.select(p.remove(0));
    let intent = RoundIntent::for_event(&group, &event(group.public_key()), [1; 32], &ids).unwrap();
    let mut local = Local::new();
    s.begin(
        event(group.public_key()),
        intent.clone(),
        100,
        &mut local,
        &mut Entropy::new(10),
    )
    .unwrap();
    s.cancel();
    local.use_saved = true;
    assert_eq!(
        s.begin(
            event(group.public_key()),
            intent,
            100,
            &mut local,
            &mut Entropy::new(11)
        ),
        Err(Error::Review)
    );
}
#[test]
fn dealer_bounds_and_entropy_failure_do_not_create_shares() {
    assert!(matches!(
        dealer(1, 3, None, &mut Entropy::new(1)),
        Err(Error::Bounds)
    ));
    assert!(matches!(
        dealer(2, 6, None, &mut Entropy::new(1)),
        Err(Error::Bounds)
    ));
    let mut bad = Entropy::new(1);
    bad.fail = true;
    assert!(matches!(dealer(2, 3, None, &mut bad), Err(Error::Entropy)));
    assert!(matches!(
        dealer(2, 3, Some(Zeroizing::new([0; 32])), &mut Entropy::new(1)),
        Err(Error::Encoding)
    ));
}
#[test]
fn dkg_2_of_3_and_3_of_5_restore_sign_and_reject_wrong_ceremony() {
    for (threshold, count) in [(2, 3), (3, 5)] {
        let ids: Vec<_> = (1..=count)
            .map(|n| {
                let mut id = [0; 32];
                id[31] = n;
                id
            })
            .collect();
        let mut broadcasts = Vec::new();
        let mut one = Vec::new();
        for (i, participant) in ids.iter().enumerate() {
            let (owner, broadcast) = dkg::RoundOne::start(
                threshold,
                &ids,
                *participant,
                [8; 32],
                &mut Entropy::new(40 + i as u8),
            )
            .unwrap();
            one.push(owner);
            broadcasts.push(broadcast);
        }
        let mut two = Vec::new();
        let mut deliveries = Vec::new();
        for (owner, participant) in one.into_iter().zip(&ids) {
            let incoming: Vec<_> = broadcasts
                .iter()
                .filter(|b| &b.sender != participant)
                .map(|b| dkg::Broadcast {
                    ceremony: b.ceremony,
                    sender: b.sender,
                    package: b.package.clone(),
                })
                .collect();
            let (owner, out) = owner.advance(&incoming).unwrap();
            two.push(owner);
            deliveries.extend(out);
        }
        let mut participants = Vec::new();
        for (owner, participant) in two.into_iter().zip(&ids) {
            let incoming: Vec<_> = deliveries
                .iter()
                .filter(|d| &d.recipient == participant)
                .map(|d| dkg::Delivery {
                    ceremony: d.ceremony,
                    sender: d.sender,
                    recipient: d.recipient,
                    package: d.package.clone(),
                })
                .collect();
            participants.push(owner.finish(&incoming).unwrap());
        }
        let group = participants[0].group().clone();
        assert!(participants
            .iter()
            .all(|p| p.group().identity() == group.identity()));
        for p in &participants {
            let backup = p.backup().unwrap();
            assert_eq!(
                Participant::restore(&backup, group.identity(), &p.identifier())
                    .unwrap()
                    .group()
                    .identity(),
                group.identity()
            );
        }
        let mut s = owners(participants.into_iter().take(threshold as usize).collect());
        let set: Vec<_> = s
            .iter()
            .map(|s| s.selected().unwrap().identifier())
            .collect();
        let (intent, c, mut local) = commit(&mut s, &group, &set, 8, &mut Entropy::new(70));
        let round = SigningRound::new(&intent, &c).unwrap();
        let shares: Vec<_> = s
            .iter_mut()
            .zip(&mut local)
            .map(|(s, a)| s.sign(&round, a).unwrap())
            .collect();
        assert!(round.aggregate(&group, &shares).is_ok());
        let (owner, _) =
            dkg::RoundOne::start(threshold, &ids, ids[0], [9; 32], &mut Entropy::new(90)).unwrap();
        let wrong: Vec<_> = broadcasts
            .into_iter()
            .filter(|b| b.sender != ids[0])
            .collect();
        assert!(matches!(owner.advance(&wrong), Err(Error::Binding)));
    }
}

#[test]
fn malicious_rechecksummed_backup_cannot_substitute_share_or_group() {
    use sha2::{Digest, Sha256};
    let p = setup(2, 3);
    let group = p[0].group();
    let participant = p[0].identifier();
    let backup = p[0].backup().unwrap();
    let checksum = |bytes: &mut Vec<u8>| {
        let end = bytes.len() - 32;
        let mut h = Sha256::new();
        for part in [SCHEME, &bytes[..end]] {
            h.update((part.len() as u64).to_be_bytes());
            h.update(part);
        }
        bytes[end..].copy_from_slice(&h.finalize());
    };
    let mut wrong = backup.to_vec();
    wrong[36..68].fill(1);
    checksum(&mut wrong);
    assert!(matches!(
        Participant::restore(&wrong, group.identity(), &participant),
        Err(Error::Group)
    ));
    let mut wrong = backup.to_vec();
    wrong[68] = 3;
    checksum(&mut wrong);
    assert!(Participant::restore(&wrong, group.identity(), &participant).is_err());
    assert!(Participant::restore(
        &vec![0; MAX_BACKUP_BYTES + 1],
        group.identity(),
        &participant
    )
    .is_err());
    assert!(
        Participant::restore(&backup[..backup.len() - 1], group.identity(), &participant).is_err()
    );
}
#[test]
fn dkg_malicious_peer_proof_duplicate_and_secret_delivery_are_rejected() {
    let ids: Vec<_> = (1..=3)
        .map(|n| {
            let mut id = [0; 32];
            id[31] = n;
            id
        })
        .collect();
    let mut broadcasts = Vec::new();
    let mut owners = Vec::new();
    for (index, member) in ids.iter().enumerate() {
        let (o, b) = dkg::RoundOne::start(
            2,
            &ids,
            *member,
            [4; 32],
            &mut Entropy::new(100 + index as u8),
        )
        .unwrap();
        owners.push(o);
        broadcasts.push(b);
    }
    let forged: Vec<_> = broadcasts
        .iter()
        .skip(1)
        .rev()
        .zip(ids.iter().skip(1))
        .map(|(b, sender)| dkg::Broadcast {
            ceremony: b.ceremony,
            sender: *sender,
            package: b.package.clone(),
        })
        .collect();
    let (probe, _) =
        dkg::RoundOne::start(2, &ids, ids[0], [4; 32], &mut Entropy::new(110)).unwrap();
    assert!(matches!(probe.advance(&forged), Err(Error::Crypto)));
    let duplicate: Vec<_> = (0..2)
        .map(|_| dkg::Broadcast {
            ceremony: broadcasts[1].ceremony,
            sender: ids[1],
            package: broadcasts[1].package.clone(),
        })
        .collect();
    let (probe, _) =
        dkg::RoundOne::start(2, &ids, ids[0], [4; 32], &mut Entropy::new(110)).unwrap();
    assert!(matches!(probe.advance(&duplicate), Err(Error::Participant)));
    let mut two = Vec::new();
    let mut deliveries = Vec::new();
    for (owner, member) in owners.into_iter().zip(&ids) {
        let incoming: Vec<_> = broadcasts
            .iter()
            .filter(|b| &b.sender != member)
            .map(|b| dkg::Broadcast {
                ceremony: b.ceremony,
                sender: b.sender,
                package: b.package.clone(),
            })
            .collect();
        let (o, d) = owner.advance(&incoming).unwrap();
        two.push(o);
        deliveries.extend(d);
    }
    let mut incoming: Vec<_> = deliveries
        .into_iter()
        .filter(|d| d.recipient == ids[0])
        .collect();
    incoming[0].package = incoming[1].package.clone();
    assert!(matches!(
        two.remove(0).finish(&incoming),
        Err(Error::Crypto)
    ));
}
