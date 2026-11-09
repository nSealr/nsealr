//! RAM-only session source parsing from decoded QR text / CompactSeedQR bytes,
//! plus the review-gated QR import flows layered on top.
//!
//! Ported from the C++ reference `host_core` sources `src/session_source_qr.cpp`
//! and `include/nsealr/session_source_qr.hpp` for behaviour parity. Decoded text
//! dispatches to NIP-19 `nsec`, Standard SeedQR digits, or a plain BIP-39
//! mnemonic; every parsed source is loaded through a temporary RAM-only
//! [`StatelessSessionKeyring`](crate::session::keyring::StatelessSessionKeyring)
//! so it passes exactly the boundary validation an imported source does.
//!
//! The QR-driven *import flows* ([`run_session_source_qr_text_import_flow`],
//! [`run_compact_seedqr_session_import_flow`]) are ported from
//! `src/session_source_qr_import_flow.cpp` +
//! `include/nsealr/session_source_qr_import_flow.hpp` (milestone M-T3.4b, on
//! the M-T3.6 review-controls substrate): parse the scanned material, then run
//! the shared [`run_session_import_flow`] so the keyring loads only after a
//! full-traversal approval.

use crate::bip39::{self, Bip39Error};
use crate::nip19::{self, NsecError};
use crate::review::controls::ReviewButton;
use crate::seedqr::{self, SeedQrError};
use crate::session::import_flow::{
    run_session_import_flow, SessionImportFlowError, SessionImportFlowResult,
};
use crate::session::keyring::{SessionKeySource, SessionKeyringError, StatelessSessionKeyring};

/// Errors reported by session source QR parsing. Each variant corresponds to a
/// distinct C++ `SessionSourceQrError` throw site (the C++ rethrew the wrapped
/// error's message under `SessionSourceQrError`; this port carries the
/// underlying error value).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionSourceQrError {
    /// Text input exceeded the finite local recovery limit before parsing.
    TooLong,
    /// A requested backup format would change the meaning or identity of a source.
    UnsupportedConversion,
    /// The caller did not supply sufficient bounded backup storage.
    OutputTooSmall,
    /// A deliberately selected text format received non-UTF-8 bytes.
    InvalidUtf8,
    /// The decoded text was empty after trimming ASCII whitespace. C++:
    /// "decoded session QR text must not be empty".
    EmptyText,
    /// The `nsec1...` branch failed NIP-19 decoding.
    Nsec(NsecError),
    /// The digit-stream branch failed Standard SeedQR decoding, or the compact
    /// entry point failed CompactSeedQR decoding.
    SeedQr(SeedQrError),
    /// The mnemonic branch failed BIP-39 parsing.
    Bip39(Bip39Error),
    /// The RAM-only keyring boundary rejected the parsed source (for example an
    /// invalid label).
    Keyring(SessionKeyringError),
}

/// Maximum text recovery bytes, including tolerated entry whitespace.
pub const MAX_SESSION_SOURCE_TEXT_BYTES: usize = 512;

/// A locally selected recovery format; byte length never chooses a secret type.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionSourceFormat {
    /// Canonical NIP19 standalone nsec.
    Nsec,
    /// English BIP39 mnemonic, including checksum.
    EnglishMnemonic,
    /// Standard SeedQR decimal word indexes (12 or 24 words).
    StandardSeedQr,
    /// Raw 16/32-byte CompactSeedQR entropy, preserving NUL and all other bytes.
    CompactSeedQr,
}

/// Parses bytes only in the recovery format explicitly selected on the device.
/// Caller-owned scan/entry buffers must be wiped separately after use.
pub fn parse_session_source_bytes(
    label: &str,
    format: SessionSourceFormat,
    decoded: &[u8],
) -> Result<SessionKeySource, SessionSourceQrError> {
    if format == SessionSourceFormat::CompactSeedQr {
        return parse_compact_seedqr_session_source(label, decoded);
    }
    if decoded.len() > MAX_SESSION_SOURCE_TEXT_BYTES {
        return Err(SessionSourceQrError::TooLong);
    }
    let text = core::str::from_utf8(decoded).map_err(|_| SessionSourceQrError::InvalidUtf8)?;
    match format {
        SessionSourceFormat::Nsec => source_from_nsec(
            label,
            nip19::decode_nsec(text).map_err(SessionSourceQrError::Nsec)?,
        ),
        SessionSourceFormat::EnglishMnemonic => source_from_bip39_indexes(
            label,
            bip39::parse_mnemonic_indexes(text).map_err(SessionSourceQrError::Bip39)?,
        ),
        SessionSourceFormat::StandardSeedQr => source_from_bip39_indexes(
            label,
            seedqr::decode_standard_indexes(text).map_err(SessionSourceQrError::SeedQr)?,
        ),
        SessionSourceFormat::CompactSeedQr => {
            unreachable!("handled raw bytes before text decoding")
        }
    }
}

/// Encodes an explicitly selected local backup, never a transport response.
///
/// The caller owns secret output and must wipe it after its local display use.
/// Output is cleared on entry and every failure; no partial secret is published.
/// A raw nsec cannot become mnemonic entropy, and a mnemonic cannot export an
/// nsec without the separately selected passphrase/account and derived owner.
pub fn encode_session_source_bytes(
    source: &SessionKeySource,
    format: SessionSourceFormat,
    output: &mut [u8],
) -> Result<usize, SessionSourceQrError> {
    use crate::session::keyring::SessionKeySourceKind;
    use zeroize::{Zeroize, Zeroizing};
    output.zeroize();
    let mut staged = Zeroizing::new([0u8; MAX_SESSION_SOURCE_TEXT_BYTES]);
    let length = match (source.kind(), format) {
        (SessionKeySourceKind::NsecSecretKey, SessionSourceFormat::Nsec) => {
            nip19::encode_nsec(&source.nsec_secret_key, &mut *staged)
                .map_err(SessionSourceQrError::Nsec)?
                .len()
        }
        (SessionKeySourceKind::Bip39WordIndexes, SessionSourceFormat::EnglishMnemonic) => {
            bip39::mnemonic_from_indexes(source.bip39_word_indexes.as_slice(), &mut *staged)
                .map_err(SessionSourceQrError::Bip39)?
                .len()
        }
        (SessionKeySourceKind::Bip39WordIndexes, SessionSourceFormat::CompactSeedQr) => {
            if !matches!(source.bip39_word_indexes.count, 12 | 24) {
                return Err(SessionSourceQrError::UnsupportedConversion);
            }
            bip39::entropy_from_indexes(source.bip39_word_indexes.as_slice(), &mut *staged)
                .map_err(SessionSourceQrError::Bip39)?
                .len()
        }
        (SessionKeySourceKind::Bip39WordIndexes, SessionSourceFormat::StandardSeedQr) => {
            let indexes = source.bip39_word_indexes.as_slice();
            if !matches!(indexes.len(), 12 | 24) {
                return Err(SessionSourceQrError::UnsupportedConversion);
            }
            bip39::require_valid_checksum(indexes).map_err(SessionSourceQrError::Bip39)?;
            for (index, word) in indexes.iter().enumerate() {
                for (digit, divisor) in [1000, 100, 10, 1].into_iter().enumerate() {
                    staged[index * 4 + digit] = b'0' + ((word / divisor) % 10) as u8;
                }
            }
            indexes.len() * 4
        }
        _ => return Err(SessionSourceQrError::UnsupportedConversion),
    };
    if output.len() < length {
        return Err(SessionSourceQrError::OutputTooSmall);
    }
    output[..length].copy_from_slice(&staged[..length]);
    Ok(length)
}

/// Parses decoded QR text into a RAM-only session source. Mirrors the C++
/// `parse_session_source_qr_text` (trim, then dispatch on `nsec1` prefix /
/// digit stream / mnemonic).
///
/// # Errors
///
/// [`SessionSourceQrError::EmptyText`], or the wrapped decoder/keyring error
/// for the dispatched branch.
pub fn parse_session_source_qr_text(
    label: &str,
    decoded_text: &str,
) -> Result<SessionKeySource, SessionSourceQrError> {
    if decoded_text.len() > MAX_SESSION_SOURCE_TEXT_BYTES {
        return Err(SessionSourceQrError::TooLong);
    }
    let text = decoded_text.trim_matches(is_session_qr_whitespace);
    if text.is_empty() {
        return Err(SessionSourceQrError::EmptyText);
    }

    if text.starts_with("nsec1") {
        let secret = nip19::decode_nsec(text).map_err(SessionSourceQrError::Nsec)?;
        return source_from_nsec(label, secret);
    }
    if is_standard_seedqr_digit_stream(text) {
        let indexes =
            seedqr::decode_standard_indexes(text).map_err(SessionSourceQrError::SeedQr)?;
        return source_from_bip39_indexes(label, indexes);
    }
    let indexes = bip39::parse_mnemonic_indexes(text).map_err(SessionSourceQrError::Bip39)?;
    source_from_bip39_indexes(label, indexes)
}

/// ASCII whitespace as recognised by the C++ `is_ascii_whitespace`: space,
/// `\n`, `\r`, `\t` only.
fn is_session_qr_whitespace(ch: char) -> bool {
    matches!(ch, ' ' | '\n' | '\r' | '\t')
}

/// Mirrors the C++ `is_standard_seedqr_digit_stream`: at least one decimal
/// digit and nothing but digits and ASCII whitespace.
fn is_standard_seedqr_digit_stream(text: &str) -> bool {
    let mut saw_digit = false;
    for ch in text.chars() {
        if is_session_qr_whitespace(ch) {
            continue;
        }
        if !ch.is_ascii_digit() {
            return false;
        }
        saw_digit = true;
    }
    saw_digit
}

/// Mirrors the C++ `source_from_nsec` (temporary boundary keyring).
fn source_from_nsec(
    label: &str,
    secret: crate::nip19::SecretKey,
) -> Result<SessionKeySource, SessionSourceQrError> {
    let mut keyring = crate::session::keyring::StatelessSessionKeyring::new();
    keyring
        .add_nsec(label, secret)
        .map_err(SessionSourceQrError::Keyring)?;
    source_from_single_entry_keyring(&mut keyring)
}

/// Mirrors the C++ `source_from_bip39_indexes` (temporary boundary keyring).
fn source_from_bip39_indexes(
    label: &str,
    indexes: crate::bip39::WordIndexes,
) -> Result<SessionKeySource, SessionSourceQrError> {
    let mut keyring = crate::session::keyring::StatelessSessionKeyring::new();
    keyring
        .add_bip39_seed(label, indexes)
        .map_err(SessionSourceQrError::Keyring)?;
    source_from_single_entry_keyring(&mut keyring)
}

/// Moves the single source out of the temporary boundary keyring (the C++
/// `source_from_single_entry_keyring`; the keyring wipes itself on drop).
fn source_from_single_entry_keyring(
    keyring: &mut crate::session::keyring::StatelessSessionKeyring,
) -> Result<SessionKeySource, SessionSourceQrError> {
    keyring.take_last().map_err(SessionSourceQrError::Keyring)
}

/// Parses CompactSeedQR entropy bytes into a RAM-only session source. Mirrors
/// the C++ `parse_compact_seedqr_session_source`.
///
/// # Errors
///
/// [`SessionSourceQrError::SeedQr`] or [`SessionSourceQrError::Keyring`].
pub fn parse_compact_seedqr_session_source(
    label: &str,
    entropy: &[u8],
) -> Result<SessionKeySource, SessionSourceQrError> {
    let indexes = seedqr::decode_compact_indexes(entropy).map_err(SessionSourceQrError::SeedQr)?;
    source_from_bip39_indexes(label, indexes)
}

/// Errors reported by the QR-driven import flows. The C++ let the parse
/// (`SessionSourceQrError`) and flow (`SessionImportFlowError` + propagated
/// review-controls/keyring) exceptions escape separately; this port carries
/// each cause as a typed variant.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionSourceQrImportFlowError {
    /// The scanned material failed session-source parsing.
    Parse(SessionSourceQrError),
    /// The review-gated import flow failed.
    Flow(SessionImportFlowError),
}

/// Parses decoded QR text and drives the review-gated import flow, loading the
/// source into `keyring` only after approval. Mirrors the C++
/// `run_session_source_qr_text_import_flow`.
///
/// # Errors
///
/// See [`SessionSourceQrImportFlowError`]; on any error the keyring is
/// untouched.
pub fn run_session_source_qr_text_import_flow(
    keyring: &mut StatelessSessionKeyring,
    label: &str,
    decoded_text: &str,
    buttons: &[ReviewButton],
    max_button_steps: usize,
) -> Result<SessionImportFlowResult, SessionSourceQrImportFlowError> {
    let source = parse_session_source_qr_text(label, decoded_text)
        .map_err(SessionSourceQrImportFlowError::Parse)?;
    run_session_import_flow(keyring, source, buttons, max_button_steps)
        .map_err(SessionSourceQrImportFlowError::Flow)
}

/// Parses CompactSeedQR entropy bytes and drives the review-gated import flow,
/// loading the source into `keyring` only after approval. Mirrors the C++
/// `run_compact_seedqr_session_import_flow`.
///
/// # Errors
///
/// See [`SessionSourceQrImportFlowError`]; on any error the keyring is
/// untouched.
pub fn run_compact_seedqr_session_import_flow(
    keyring: &mut StatelessSessionKeyring,
    label: &str,
    entropy: &[u8],
    buttons: &[ReviewButton],
    max_button_steps: usize,
) -> Result<SessionImportFlowResult, SessionSourceQrImportFlowError> {
    let source = parse_compact_seedqr_session_source(label, entropy)
        .map_err(SessionSourceQrImportFlowError::Parse)?;
    run_session_import_flow(keyring, source, buttons, max_button_steps)
        .map_err(SessionSourceQrImportFlowError::Flow)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::session::import_review::build_session_import_review;
    use crate::session::import_review::tests::{pages_contain_text, NSEC_TEST_KEY_1_SECRET_HEX};
    use crate::session::keyring::tests::{NSEC_TEST_KEY_1, SEEDQR_VECTOR_1_INDEXES};
    use crate::session::keyring::SessionKeySourceKind;

    // Mnemonic copied from the READ-ONLY
    // specs/vectors/keys/nip06-account-0-leader.json (`mnemonic`).
    const NIP06_ACCOUNT_0_MNEMONIC: &str = include_str!(concat!(
        env!("OUT_DIR"),
        "/field-674779247edd20ec33c77f12.txt"
    ));
    // Standard digits + compact hex copied from the READ-ONLY
    // specs/vectors/seedqr/seedsigner-vector-1.json (`standard_seedqr_digits`,
    // `compact_seedqr_hex`).
    const SEEDQR_VECTOR_1_DIGITS: &str = include_str!(concat!(
        env!("OUT_DIR"),
        "/field-de90d1677498ead6f9e1bb73.txt"
    ));
    pub(crate) const SEEDQR_VECTOR_1_COMPACT: [u8; 32] = [
        0x0e, 0x74, 0xb6, 0x41, 0x07, 0xf9, 0x4c, 0xc0, 0xcc, 0xfa, 0xe6, 0xa1, 0x3d, 0xcb, 0xec,
        0x36, 0x62, 0x15, 0x4f, 0xec, 0x67, 0xe0, 0xe0, 0x09, 0x99, 0xc0, 0x78, 0x92, 0x59, 0x7d,
        0x19, 0x0a,
    ];

    // Port of the C++ `test_session_source_qr_parses_ram_only_sources`.
    #[test]
    fn parses_ram_only_sources() {
        let mut wrapped_nsec = std::string::String::from("\n");
        wrapped_nsec.push_str(NSEC_TEST_KEY_1);
        wrapped_nsec.push('\t');
        let nsec_source = parse_session_source_qr_text("nsec QR", &wrapped_nsec).unwrap();
        let mnemonic_source =
            parse_session_source_qr_text("plain mnemonic QR", NIP06_ACCOUNT_0_MNEMONIC).unwrap();
        // Whitespace inside the digit stream is skipped by the dispatch check
        // and by the Standard SeedQR decoder (C++ parity).
        let mut spaced_digits = std::string::String::from(&SEEDQR_VECTOR_1_DIGITS[..4]);
        spaced_digits.push(' ');
        spaced_digits.push_str(&SEEDQR_VECTOR_1_DIGITS[4..8]);
        spaced_digits.push('\n');
        spaced_digits.push_str(&SEEDQR_VECTOR_1_DIGITS[8..]);
        let standard_seedqr_source =
            parse_session_source_qr_text("Standard SeedQR", &spaced_digits).unwrap();
        let compact_seedqr_source =
            parse_compact_seedqr_session_source("CompactSeedQR", &SEEDQR_VECTOR_1_COMPACT).unwrap();

        assert_eq!(nsec_source.kind, SessionKeySourceKind::NsecSecretKey);
        assert_eq!(nsec_source.label, "nsec QR");
        assert_eq!(
            nsec_source.nsec_secret_key,
            crate::nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
        );
        assert_eq!(nsec_source.bip39_word_indexes.count, 0);

        assert_eq!(mnemonic_source.kind, SessionKeySourceKind::Bip39WordIndexes);
        assert_eq!(mnemonic_source.label, "plain mnemonic QR");
        assert_eq!(
            mnemonic_source.bip39_word_indexes.as_slice(),
            crate::bip39::parse_mnemonic_indexes(NIP06_ACCOUNT_0_MNEMONIC)
                .unwrap()
                .as_slice(),
        );

        assert_eq!(
            standard_seedqr_source.kind,
            SessionKeySourceKind::Bip39WordIndexes,
        );
        assert_eq!(standard_seedqr_source.label, "Standard SeedQR");
        assert_eq!(
            standard_seedqr_source.bip39_word_indexes.as_slice(),
            &SEEDQR_VECTOR_1_INDEXES,
        );
        assert_eq!(
            compact_seedqr_source.kind,
            SessionKeySourceKind::Bip39WordIndexes,
        );
        assert_eq!(compact_seedqr_source.label, "CompactSeedQR");
        assert_eq!(
            compact_seedqr_source.bip39_word_indexes.as_slice(),
            &SEEDQR_VECTOR_1_INDEXES,
        );

        let nsec_review = build_session_import_review(&nsec_source);
        let mnemonic_review = build_session_import_review(&mnemonic_source);
        assert!(pages_contain_text(&nsec_review.pages, "Secret: hidden"));
        assert!(pages_contain_text(&mnemonic_review.pages, "Secret: hidden"));
        assert!(!pages_contain_text(
            &nsec_review.pages,
            NSEC_TEST_KEY_1_SECRET_HEX,
        ));
        assert!(!pages_contain_text(&mnemonic_review.pages, "leader"));
    }

    // Port of the C++ `test_session_source_qr_rejects_invalid_inputs`.
    #[test]
    fn rejects_invalid_inputs() {
        assert_eq!(
            parse_session_source_qr_text("empty QR", " \n\t"),
            Err(SessionSourceQrError::EmptyText),
        );
        assert_eq!(
            parse_session_source_qr_text("", NSEC_TEST_KEY_1),
            Err(SessionSourceQrError::Keyring(
                SessionKeyringError::EmptyLabel,
            )),
        );
        assert_eq!(
            parse_session_source_qr_text("bad nsec QR", "nsec1short"),
            Err(SessionSourceQrError::Nsec(NsecError::Malformed)),
        );
        assert_eq!(
            parse_session_source_qr_text("bad Standard SeedQR", "000"),
            Err(SessionSourceQrError::SeedQr(SeedQrError::NotFourPerWord)),
        );
        assert_eq!(
            parse_session_source_qr_text("bad mnemonic QR", "not a valid session source!"),
            Err(SessionSourceQrError::Bip39(Bip39Error::NonAsciiWord)),
        );
        assert_eq!(
            parse_compact_seedqr_session_source("bad CompactSeedQR", &[0x00, 0x01]),
            Err(SessionSourceQrError::SeedQr(SeedQrError::InvalidByteLength)),
        );
    }

    use crate::session::import_flow::SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS;

    // Port of the C++ `test_session_source_qr_import_flow_loads_only_after_review_approval`.
    // The expected review_id is copied from the READ-ONLY
    // specs/vectors/session-import-reviews/nsec-test-key-1.json (`review_id`).
    #[test]
    fn import_flow_loads_only_after_review_approval() {
        let mut keyring = StatelessSessionKeyring::new();
        let result = run_session_source_qr_text_import_flow(
            &mut keyring,
            "nsec QR",
            NSEC_TEST_KEY_1,
            &[ReviewButton::Next, ReviewButton::Approve],
            SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
        )
        .unwrap();

        assert!(result.approved);
        assert!(result.loaded);
        assert_eq!(
            result.review.review_id,
            include_str!(concat!(
                env!("OUT_DIR"),
                "/field-2d4d3d3dc78fd3f8fd1e0b12.txt"
            ))
        );
        assert_eq!(result.transcript.len(), 2);
        assert!(!result.transcript.step(0).loaded);
        assert!(result.transcript.step(1).loaded);
        assert_eq!(keyring.len(), 1);
        assert_eq!(
            keyring.source_at(0).unwrap().kind,
            SessionKeySourceKind::NsecSecretKey,
        );
        assert_eq!(
            keyring.source_at(0).unwrap().nsec_secret_key,
            crate::nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
        );
    }

    // Port of the C++ `test_session_source_qr_import_flow_rejects_without_keyring_load`.
    #[test]
    fn import_flow_rejects_without_keyring_load() {
        let mut keyring = StatelessSessionKeyring::new();
        let rejected = run_session_source_qr_text_import_flow(
            &mut keyring,
            "SeedQR vector 1",
            SEEDQR_VECTOR_1_DIGITS,
            &[ReviewButton::Reject],
            SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
        )
        .unwrap();

        assert!(!rejected.approved);
        assert!(!rejected.loaded);
        assert!(keyring.is_empty());

        assert_eq!(
            run_session_source_qr_text_import_flow(
                &mut keyring,
                "bad Standard SeedQR",
                "000",
                &[ReviewButton::Next, ReviewButton::Approve],
                SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
            ),
            Err(SessionSourceQrImportFlowError::Parse(
                SessionSourceQrError::SeedQr(SeedQrError::NotFourPerWord),
            )),
        );
        assert!(keyring.is_empty());
    }

    // Port of the C++ `test_compact_seedqr_import_flow_loads_after_review_approval`.
    #[test]
    fn compact_seedqr_import_flow_loads_after_review_approval() {
        let mut keyring = StatelessSessionKeyring::new();
        let result = run_compact_seedqr_session_import_flow(
            &mut keyring,
            "CompactSeedQR",
            &SEEDQR_VECTOR_1_COMPACT,
            &[ReviewButton::Next, ReviewButton::Approve],
            SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
        )
        .unwrap();

        assert!(result.approved);
        assert!(result.loaded);
        assert_eq!(keyring.len(), 1);
        assert_eq!(
            keyring.source_at(0).unwrap().kind,
            SessionKeySourceKind::Bip39WordIndexes,
        );
        assert_eq!(
            keyring.source_at(0).unwrap().bip39_word_indexes.as_slice(),
            &SEEDQR_VECTOR_1_INDEXES,
        );
    }

    #[test]
    fn local_backup_encoders_match_all_nine_published_vectors_and_fail_without_partial_output() {
        let rows: serde_json::Value = serde_json::from_str(include_str!(
            "../../testdata/recovery/seedqr-published.json"
        ))
        .unwrap();
        assert_eq!(rows.as_array().unwrap().len(), 9);
        for row in rows.as_array().unwrap() {
            let source = parse_session_source_bytes(
                "published",
                SessionSourceFormat::EnglishMnemonic,
                row["mnemonic"].as_str().unwrap().as_bytes(),
            )
            .unwrap();
            let compact = row["compact_hex"].as_str().unwrap();
            let compact: std::vec::Vec<u8> = compact
                .as_bytes()
                .chunks_exact(2)
                .map(|p| u8::from_str_radix(core::str::from_utf8(p).unwrap(), 16).unwrap())
                .collect();
            for (format, expected) in [
                (
                    SessionSourceFormat::EnglishMnemonic,
                    row["mnemonic"].as_str().unwrap().as_bytes(),
                ),
                (
                    SessionSourceFormat::StandardSeedQr,
                    row["standard"].as_str().unwrap().as_bytes(),
                ),
                (SessionSourceFormat::CompactSeedQr, compact.as_slice()),
            ] {
                let mut output = [0xa7; 512];
                let n = encode_session_source_bytes(&source, format, &mut output).unwrap();
                assert_eq!(&output[..n], expected);
                assert!(output[n..].iter().all(|b| *b == 0));
                let recovered =
                    parse_session_source_bytes("published", format, &output[..n]).unwrap();
                assert_eq!(source, recovered);
                for cap in 0..n {
                    output.fill(0xa7);
                    assert_eq!(
                        encode_session_source_bytes(&source, format, &mut output[..cap]),
                        Err(SessionSourceQrError::OutputTooSmall)
                    );
                    assert!(output[..cap].iter().all(|b| *b == 0));
                    assert!(output[cap..].iter().all(|b| *b == 0xa7));
                }
            }
            let mut output = [0xa7; 512];
            assert_eq!(
                encode_session_source_bytes(&source, SessionSourceFormat::Nsec, &mut output),
                Err(SessionSourceQrError::UnsupportedConversion)
            );
            assert!(output.iter().all(|b| *b == 0));
        }
        let source = parse_session_source_bytes(
            "nsec",
            SessionSourceFormat::Nsec,
            NSEC_TEST_KEY_1.as_bytes(),
        )
        .unwrap();
        for format in [
            SessionSourceFormat::EnglishMnemonic,
            SessionSourceFormat::StandardSeedQr,
            SessionSourceFormat::CompactSeedQr,
        ] {
            let mut output = [0xa7; 512];
            assert_eq!(
                encode_session_source_bytes(&source, format, &mut output),
                Err(SessionSourceQrError::UnsupportedConversion)
            );
            assert!(output.iter().all(|b| *b == 0));
        }
        let mut output = [0xa7; 512];
        assert_eq!(
            encode_session_source_bytes(&source, SessionSourceFormat::Nsec, &mut output).unwrap(),
            63
        );
        assert_eq!(&output[..63], NSEC_TEST_KEY_1.as_bytes());
    }

    // Beyond the named C++ cases: the compact entry point's parse-error wrapping
    // and the flow-error wrapping of both entry points.
    #[test]
    fn import_flow_error_wrapping_branches() {
        let mut keyring = StatelessSessionKeyring::new();
        assert_eq!(
            run_compact_seedqr_session_import_flow(
                &mut keyring,
                "bad CompactSeedQR",
                &[0x00, 0x01],
                &[ReviewButton::Next, ReviewButton::Approve],
                SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
            ),
            Err(SessionSourceQrImportFlowError::Parse(
                SessionSourceQrError::SeedQr(SeedQrError::InvalidByteLength),
            )),
        );
        assert_eq!(
            run_session_source_qr_text_import_flow(
                &mut keyring,
                "nsec QR",
                NSEC_TEST_KEY_1,
                &[ReviewButton::Next],
                SESSION_IMPORT_DEFAULT_MAX_BUTTON_STEPS,
            ),
            Err(SessionSourceQrImportFlowError::Flow(
                crate::session::import_flow::SessionImportFlowError::NoTerminalDecision,
            )),
        );
        assert_eq!(
            run_compact_seedqr_session_import_flow(
                &mut keyring,
                "CompactSeedQR",
                &SEEDQR_VECTOR_1_COMPACT,
                &[ReviewButton::Reject],
                0,
            ),
            Err(SessionSourceQrImportFlowError::Flow(
                crate::session::import_flow::SessionImportFlowError::ZeroMaxButtonSteps,
            )),
        );
        assert!(keyring.is_empty());
    }
}
