//! Public fixture recovery through actual custody and authorization ownership.
use nsealr_core::{
    authorization::{AuthorizationError, AuthorizationSession, AuthorizationState},
    event::OperationLimits,
    nip19::{self, NsecError},
    review::event::InspectionGeometry,
    seedqr::SeedQrError,
    session::{
        recovery::{derive_source_key, source_public_key, RecoveryError},
        source_qr::{
            parse_session_source_bytes, SessionSourceFormat as Format,
            SessionSourceQrError as Error, MAX_SESSION_SOURCE_TEXT_BYTES,
        },
    },
};
fn hex(input: &str) -> Vec<u8> {
    input
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| u8::from_str_radix(core::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}

#[test]
fn all_nine_published_seedqr_vectors_preserve_binary_and_same_identity() {
    let vectors: serde_json::Value =
        serde_json::from_str(include_str!("../testdata/recovery/seedqr-published.json")).unwrap();
    let mut saw_nul = false;
    let mut saw_crlf = false;
    for row in vectors.as_array().unwrap() {
        let bytes = hex(row["compact_hex"].as_str().unwrap());
        saw_nul |= bytes.contains(&0);
        saw_crlf |= bytes.windows(2).any(|p| p == b"\r\n");
        let words = parse_session_source_bytes(
            "public fixture",
            Format::EnglishMnemonic,
            row["mnemonic"].as_str().unwrap().as_bytes(),
        )
        .unwrap();
        let digits = parse_session_source_bytes(
            "public fixture",
            Format::StandardSeedQr,
            row["standard"].as_str().unwrap().as_bytes(),
        )
        .unwrap();
        let binary =
            parse_session_source_bytes("public fixture", Format::CompactSeedQr, &bytes).unwrap();
        let expected = source_public_key(&derive_source_key(&words, "TREZOR", 1).unwrap()).unwrap();
        for source in [&digits, &binary] {
            assert_eq!(
                source_public_key(&derive_source_key(source, "TREZOR", 1).unwrap()).unwrap(),
                expected
            );
        }
    }
    assert!(saw_nul && saw_crlf);
}

#[test]
fn typed_import_rejects_wrong_format_bounds_checksum_and_prefix() {
    assert_eq!(
        parse_session_source_bytes(
            "x",
            Format::EnglishMnemonic,
            &vec![b' '; MAX_SESSION_SOURCE_TEXT_BYTES + 1]
        )
        .unwrap_err(),
        Error::TooLong
    );
    assert_eq!(
        parse_session_source_bytes("x", Format::EnglishMnemonic, &[0xff]).unwrap_err(),
        Error::InvalidUtf8
    );
    assert_eq!(
        parse_session_source_bytes("x", Format::CompactSeedQr, &[0; 15]).unwrap_err(),
        Error::SeedQr(SeedQrError::InvalidByteLength)
    );
    assert_eq!(
        parse_session_source_bytes(
            "x",
            Format::StandardSeedQr,
            b"204800000000000000000000000000000000000000000000"
        )
        .unwrap_err(),
        Error::SeedQr(SeedQrError::IndexOutOfRange)
    );
    assert_eq!(
        parse_session_source_bytes(
            "x",
            Format::StandardSeedQr,
            b"000000000000000000000000000000000000000000000000"
        )
        .unwrap_err(),
        Error::SeedQr(SeedQrError::Bip39(
            nsealr_core::bip39::Bip39Error::InvalidChecksum
        ))
    );
    let npub = b"npub1zutzeysacnf9rru6zqwmxd54mud0k44tst6l70ja5mhv8jjumytsd2x7nu";
    assert_eq!(
        parse_session_source_bytes("x", Format::Nsec, npub).unwrap_err(),
        Error::Nsec(NsecError::WrongPrefix)
    );
    // The same 32 bytes have meaning only in the deliberately selected context.
    assert!(parse_session_source_bytes("x", Format::CompactSeedQr, &[0; 32]).is_ok());
    assert!(parse_session_source_bytes("x", Format::Nsec, &[0; 32]).is_err());
}

#[test]
fn recovered_custody_and_nsec_backup_preserve_identity_and_invalidate_old_work() {
    let mut source = parse_session_source_bytes(
        "NIP06",
        Format::EnglishMnemonic,
        b"leader monkey parrot ring guide accident before fence cannon height naive bean",
    )
    .unwrap();
    let secret = derive_source_key(&source, "", 0).unwrap();
    let expected = source_public_key(&secret).unwrap();
    assert_eq!(
        expected.as_slice(),
        hex("17162c921dc4d2518f9a101db33695df1afb56ab82f5ff3e5da6eec3ca5cd917")
    );
    let mut nsec_buf = [0; 90];
    let nsec = nip19::encode_nsec(&secret, &mut nsec_buf).unwrap();
    assert_eq!(
        nsec,
        "nsec10allq0gjx7fddtzef0ax00mdps9t2kmtrldkyjfs8l5xruwvh2dq0lhhkp"
    );
    let standalone =
        parse_session_source_bytes("same nsec", Format::Nsec, nsec.as_bytes()).unwrap();
    assert_eq!(
        source_public_key(&derive_source_key(&standalone, "", 0).unwrap()).unwrap(),
        expected
    );
    assert_eq!(
        derive_source_key(&standalone, "not a BIP39 source", 0).unwrap_err(),
        RecoveryError::UnexpectedDerivation
    );
    assert_eq!(
        derive_source_key(&standalone, "", 1).unwrap_err(),
        RecoveryError::UnexpectedDerivation
    );
    source.wipe();
    assert_eq!(
        derive_source_key(&source, "", 0).unwrap_err(),
        RecoveryError::InvalidSource
    );
    let mut owner = AuthorizationSession::new(
        OperationLimits::conformance(),
        InspectionGeometry {
            columns: 32,
            lines: 8,
        },
    )
    .unwrap();
    owner.select_key(secret).unwrap();
    assert_eq!(owner.public_key(), Some(expected));
    let request = br#"{"version":2,"request_id":"r","method":"sign_event","params":{"event_template":{"created_at":0,"kind":1,"tags":[],"content":"recovery test"}}}"#;
    owner.begin_request(request, Some(0)).unwrap();
    assert_eq!(owner.state(), AuthorizationState::Reviewing);
    // Even selecting identical recovered custody discards the old operation.
    owner
        .select_key(derive_source_key(&standalone, "", 0).unwrap())
        .unwrap();
    assert_eq!(owner.state(), AuthorizationState::Idle);
    assert_eq!(
        owner.attempt_sign("r", Some(1)),
        Err(AuthorizationError::InvalidState)
    );
    owner.lock().unwrap();
    assert_eq!(owner.public_key(), None);
    assert_eq!(
        owner.begin_request(request, Some(2)),
        Err(AuthorizationError::Locked)
    );
}
