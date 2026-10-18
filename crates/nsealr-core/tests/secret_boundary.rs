//! Only published fixture material is ever formatted or exported by these tests.
use nsealr_core::{
    bip39::{parse_mnemonic_indexes, WordIndexes},
    nip19::{decode_nsec, SecretKey},
    review::controls::ReviewButton,
    session::{
        import_flow::run_session_import_flow,
        keyring::{SessionKeyringError, StatelessSessionKeyring},
        source_backup::run_session_source_backup_flow,
        source_qr::parse_session_source_qr_text,
    },
};

const NSEC: &str = include_str!(concat!(
    env!("OUT_DIR"),
    "/field-0ba18333d64bc1b3cabb124c.txt"
));
const MNEMONIC: &str =
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about";

#[test]
fn owned_types_have_fixed_redacted_formatting() {
    let scalar = decode_nsec(NSEC).unwrap();
    assert_eq!(format!("{scalar:?}"), "SecretKey([REDACTED])");
    let indexes = parse_mnemonic_indexes(MNEMONIC).unwrap();
    assert_eq!(format!("{indexes:?}"), "WordIndexes([REDACTED])");
    let source = parse_session_source_qr_text("public fixture", NSEC).unwrap();
    assert_eq!(format!("{source:?}"), "SessionKeySource([REDACTED])");
    let mut ring = StatelessSessionKeyring::new();
    ring.add_source(source).unwrap();
    assert_eq!(format!("{ring:?}"), "StatelessSessionKeyring([REDACTED])");
    let result = run_session_source_backup_flow(
        ring.source_at(0).unwrap(),
        &[ReviewButton::Next, ReviewButton::Approve],
        2,
    )
    .unwrap();
    assert_eq!(
        format!("{result:?}"),
        "SessionSourceBackupFlowResult([REDACTED])"
    );
    let payload = result.backup_payload.unwrap();
    assert_eq!(
        format!("{payload:?}"),
        "SessionSourceBackupPayload([REDACTED])"
    );
    assert_eq!(payload.reveal_nsec(), NSEC);
    assert!(payload.reveal_mnemonic().is_empty());
    assert!(payload.reveal_standard_seedqr_digits().is_empty());
    assert!(payload.reveal_compact_seedqr_hex().is_empty());
}

#[test]
fn local_scalar_intake_clears_input_on_success_and_failure() {
    let mut fixture = [0x11; 32];
    let scalar = SecretKey::take_from(&mut fixture).unwrap();
    assert_eq!(fixture, [0; 32]);
    assert_eq!(scalar, decode_nsec(NSEC).unwrap());
    for mut invalid in [[0; 32], [0xff; 32]] {
        assert!(SecretKey::take_from(&mut invalid).is_err());
        assert_eq!(invalid, [0; 32]);
    }
}

#[test]
fn malformed_seed_is_rejected_at_owned_insertion() {
    // BIP39's published zero-entropy vector ends with index 3 ("about").
    // Twelve zero indexes encode "abandon" twelve times: wrong checksum.
    let mut ring = StatelessSessionKeyring::new();
    assert_eq!(
        ring.add_bip39_seed("bad", WordIndexes::from_slice(&[0; 12]).unwrap()),
        Err(SessionKeyringError::InvalidSeedChecksum)
    );
    assert!(ring.is_empty());
    ring.add_bip39_seed("valid", parse_mnemonic_indexes(MNEMONIC).unwrap())
        .unwrap();
    let source = ring.take_last().unwrap();
    assert!(ring.is_empty());
    ring.add_source(source).unwrap();
    assert_eq!(ring.len(), 1);
    ring.clear();
    assert!(ring.source_at(0).is_err());
}

#[test]
fn cancelled_and_failed_import_or_backup_has_no_retained_output() {
    for buttons in [
        &[ReviewButton::Reject][..],
        &[ReviewButton::Approve][..],
        &[][..],
    ] {
        let mut ring = StatelessSessionKeyring::new();
        let source = parse_session_source_qr_text("fixture", NSEC).unwrap();
        let _ = run_session_import_flow(&mut ring, source, buttons, 2);
        assert!(ring.is_empty());
        let source = parse_session_source_qr_text("fixture", NSEC).unwrap();
        if let Ok(result) = run_session_source_backup_flow(&source, buttons, 2) {
            assert!(!result.revealed);
            assert!(result.backup_payload.is_none());
        }
    }
}
