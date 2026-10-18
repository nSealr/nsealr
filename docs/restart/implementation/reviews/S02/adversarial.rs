//! Independent external-API probe. Every value is deterministic public test material.
use nsealr_core::{
    bip39::WordIndexes,
    nip19::{NsecError, SecretKey},
    review::controls::ReviewButton,
    session::{
        import_flow::{run_session_import_flow, SessionImportFlowError},
        import_review::session_key_source_fingerprint,
        keyring::{SessionKeyringError, StatelessSessionKeyring},
        source_backup::run_session_source_backup_flow,
        source_generation::generate_nsec_session_source,
    },
};

fn scalar(n: u8) -> SecretKey {
    let mut bytes = [0; 32];
    bytes[31] = n;
    let key = SecretKey::take_from(&mut bytes).unwrap();
    assert_eq!(bytes, [0; 32]);
    key
}

fn main() {
    let fixture = std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
    let mut tested = 0;
    let mut accepted = 0;
    let mut rejected = 0;
    let mut exported = 0;
    for line in fixture.lines().skip(1) {
        let fields: Vec<_> = line.split(',').collect();
        let count: usize = fields[0].parse().unwrap();
        let last: u16 = fields[1].parse().unwrap();
        let valid = fields[2] == "1";
        let mut indexes = vec![0; count];
        indexes[count - 1] = last;
        let mut ring = StatelessSessionKeyring::new();
        ring.add_nsec("existing source", scalar(9)).unwrap();
        let original = session_key_source_fingerprint(ring.source_at(0).unwrap());
        let result = ring.add_bip39_seed("adversarial suffix", WordIndexes::from_slice(&indexes).unwrap());
        assert_eq!(result.is_ok(), valid, "count={count}, suffix={last}");
        assert_eq!(session_key_source_fingerprint(ring.source_at(0).unwrap()), original);
        if valid {
            accepted += 1;
            assert_eq!(ring.len(), 2);
            let moved = ring.take_last().unwrap();
            assert_eq!(ring.len(), 1);
            let source_fingerprint = session_key_source_fingerprint(&moved);
            ring.add_source(moved).unwrap();
            assert_eq!(session_key_source_fingerprint(ring.source_at(1).unwrap()), source_fingerprint);
            let result = run_session_source_backup_flow(
                ring.source_at(1).unwrap(), &[ReviewButton::Next, ReviewButton::Approve], 2,
            );
            if count == 12 || count == 24 {
                let payload = result.unwrap().backup_payload.unwrap();
                assert_eq!(payload.reveal_compact_seedqr_hex(), fields[3]);
                let expected_digits: String = indexes.iter().map(|v| format!("{v:04}")).collect();
                assert_eq!(payload.reveal_standard_seedqr_digits(), expected_digits);
                exported += 1;
            } else {
                assert!(result.is_err()); // Existing SeedQR backup contract only supports 12/24.
            }
        } else {
            rejected += 1;
            assert_eq!(result, Err(SessionKeyringError::InvalidSeedChecksum));
            assert_eq!(ring.len(), 1);
        }
        ring.clear();
        assert!(ring.source_at(0).is_err());
        assert!(ring.source_at(1).is_err());
        tested += 1;
    }
    assert_eq!((tested, accepted, rejected, exported), (10240, 248, 9992, 136));

    // Mixed-source full-capacity rejection must be transactional, including the
    // moved pending source and a transcript-capacity failure at the decision step.
    let mut ring = StatelessSessionKeyring::new();
    for n in 1..=8 { ring.add_nsec(&format!("public scalar {n}"), scalar(n)).unwrap(); }
    let before: Vec<_> = (0..8).map(|i| session_key_source_fingerprint(ring.source_at(i).unwrap())).collect();
    let pending = generate_nsec_session_source("public pending", scalar(9)).unwrap();
    assert_eq!(run_session_import_flow(&mut ring, pending, &[ReviewButton::Next, ReviewButton::Approve], 2), Err(SessionImportFlowError::Keyring(SessionKeyringError::KeyringFull)));
    for (i, fingerprint) in before.iter().enumerate() {
        assert_eq!(&session_key_source_fingerprint(ring.source_at(i).unwrap()), fingerprint);
    }
    ring.clear();
    let mut buttons = vec![ReviewButton::Next; 32];
    buttons.push(ReviewButton::Approve);
    let pending = generate_nsec_session_source("public pending", scalar(9)).unwrap();
    assert_eq!(run_session_import_flow(&mut ring, pending, &buttons, 33), Err(SessionImportFlowError::Capacity));
    assert!(ring.is_empty());

    // Exact group-order neighborhood, checked against published secp256k1 n.
    let order_hex = "fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141";
    let order: [u8; 32] = std::array::from_fn(|i| u8::from_str_radix(&order_hex[i*2..i*2+2], 16).unwrap());
    for delta in [-1i16, 0, 1] {
        let mut value = order;
        value[31] = (i16::from(value[31]) + delta) as u8;
        let result = SecretKey::take_from(&mut value);
        assert_eq!(value, [0; 32]);
        assert_eq!(result.is_ok(), delta < 0);
        if delta >= 0 { assert_eq!(result, Err(NsecError::InvalidScalar)); }
    }
    println!("PASS: {tested} independently-oracled checksum endings; {accepted} valid, {rejected} rejected, {exported} exact backup round trips; source transfer, retained-source integrity, capacity and decision-step transcript failure atomicity; scalar n-1/n/n+1 intake cleanup.");
}
