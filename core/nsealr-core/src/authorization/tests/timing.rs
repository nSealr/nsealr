use super::*;

#[test]
fn configured_review_lifetime_binds_the_exact_deadline_and_never_extends_on_read() {
    let mut owner = session();
    owner.configure_review_lifetime(1800).unwrap();
    owner
        .begin_request(request(EMPTY).as_bytes(), Some(50))
        .unwrap();
    assert_eq!(owner.review_deadline(), Some(1850));
    assert_eq!(owner.pending.as_ref().unwrap().context[20], 1800);
    let mut io = Io {
        tick: 1849,
        ..Io::default()
    };
    while owner.state() == AuthorizationState::Reviewing {
        assert_eq!(owner.review_deadline(), Some(1850));
        owner.review_step(&mut io).unwrap();
    }
    let before = backend_calls();
    let mut aux = Aux::valid(0);
    let mut output = [0xa5; SIGNED_EVENT_BYTES];
    assert_eq!(
        owner.sign_approved("r", &mut || Some(1850), &mut aux, &mut output),
        Err(AuthorizationError::Expired)
    );
    assert_eq!(aux.calls, 0);
    assert_eq!(backend_calls(), before);
    assert!(output.iter().all(|byte| *byte == 0));
    assert_eq!(owner.review_deadline(), None);
}

#[test]
fn every_local_lifetime_change_revokes_consent_including_invalid_and_identical_values() {
    for ticks in [
        0,
        REVIEW_LIFETIME,
        1800,
        MAX_REVIEW_LIFETIME,
        MAX_REVIEW_LIFETIME + 1,
        u64::MAX,
    ] {
        let mut owner = approved(EMPTY);
        let changed = owner.configure_review_lifetime(ticks);
        assert_eq!(changed.is_ok(), (1..=MAX_REVIEW_LIFETIME).contains(&ticks));
        assert_eq!(owner.review_deadline(), None);
        let before = backend_calls();
        let mut aux = Aux::valid(0);
        let mut output = [0xa5; SIGNED_EVENT_BYTES];
        assert!(owner
            .sign_approved("r", &mut || Some(0), &mut aux, &mut output)
            .is_err());
        assert_eq!(aux.calls, 0);
        assert_eq!(backend_calls(), before);
        assert!(output.iter().all(|byte| *byte == 0));
    }
    let mut owner = session();
    owner
        .configure_review_lifetime(MAX_REVIEW_LIFETIME)
        .unwrap();
    assert_eq!(
        owner.begin_request(request(EMPTY).as_bytes(), Some(u64::MAX - 1)),
        Err(AuthorizationError::Clock)
    );
    assert_eq!(owner.review_deadline(), None);
    owner.reset().unwrap();
    assert_eq!(owner.state(), AuthorizationState::Locked);
    owner.select_key(secret(3)).unwrap();
    owner
        .begin_request(request(EMPTY).as_bytes(), Some(0))
        .unwrap();
    assert_eq!(owner.review_deadline(), Some(MAX_REVIEW_LIFETIME));
}
