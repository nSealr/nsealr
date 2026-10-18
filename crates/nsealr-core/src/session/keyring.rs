//! Bounded, owned session secrets. Current storage is wiped on clear/drop.
//!
//! Sources and scalars cannot be cloned or publicly inspected. Import consumes
//! the pending source; extraction transfers it. Fixed inline storage introduces
//! no allocator, but placement in internal RAM is a device/linker obligation.
//! Rust moves may leave copies; this does not guarantee physical erasure.

use crate::bip39;
use crate::nip19::{self, SecretKey};
use crate::text::FixedStr;
use core::str::FromStr;

/// Maximum number of sources the stateless keyring holds. Mirrors the C++
/// `kMaxStatelessSessionKeySources`.
pub const MAX_STATELESS_SESSION_KEY_SOURCES: usize = 8;
/// Maximum session key source label length in bytes. Mirrors the C++
/// `kMaxSessionKeySourceLabelLength`.
pub const MAX_SESSION_KEY_SOURCE_LABEL_CHARS: usize = 64;

/// A session key source label, bounded by
/// [`MAX_SESSION_KEY_SOURCE_LABEL_CHARS`].
pub type SessionKeySourceLabel = FixedStr<MAX_SESSION_KEY_SOURCE_LABEL_CHARS>;

/// Errors reported by the session keyring. Each variant corresponds to a
/// distinct C++ `SessionKeyringError` throw site.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionKeyringError {
    /// The label was empty. C++: "session key source label must not be empty".
    EmptyLabel,
    /// The label exceeded [`MAX_SESSION_KEY_SOURCE_LABEL_CHARS`]. C++: "session
    /// key source label exceeds max length".
    LabelTooLong,
    /// The nsec secret was zero or not below the secp256k1 order. C++: "NIP-19
    /// nsec session source must be a valid secp256k1 scalar".
    InvalidNsecScalar,
    /// The seed word count was not one of `{12, 15, 18, 21, 24}`. C++: "BIP-39
    /// session seed must contain 12, 15, 18, 21, or 24 word indexes".
    InvalidSeedWordCount,
    /// A seed word index was `>= 2048`. C++: "BIP-39 session seed word index is
    /// outside the English wordlist".
    SeedWordIndexOutOfRange,
    /// BIP-39 checksum does not match the encoded entropy.
    InvalidSeedChecksum,
    /// The keyring already held [`MAX_STATELESS_SESSION_KEY_SOURCES`] sources.
    /// C++: "stateless session keyring is full".
    KeyringFull,
    /// A source index was `>=` the active size. C++: "session key source index
    /// is out of range".
    IndexOutOfRange,
}

/// The kind of key material a session source holds. Mirrors the C++
/// `SessionKeySourceKind`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionKeySourceKind {
    /// A raw 32-byte secret key imported from a NIP-19 `nsec`.
    NsecSecretKey,
    /// A BIP-39 seed held as validated word indexes.
    Bip39WordIndexes,
}

/// Private fixed-capacity BIP-39 storage; tests inspect only live storage.
#[derive(PartialEq, Eq)]
pub(crate) struct SessionSeedWordIndexes {
    /// The word index slots; unused slots are kept zeroed.
    pub(crate) values: [u16; bip39::MAX_MNEMONIC_WORDS],
    /// The number of active indexes in `values`.
    pub(crate) count: usize,
}

impl SessionSeedWordIndexes {
    /// Creates an empty index list.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            values: [0; bip39::MAX_MNEMONIC_WORDS],
            count: 0,
        }
    }

    /// Returns the active indexes as a slice.
    #[must_use]
    pub fn as_slice(&self) -> &[u16] {
        &self.values[..self.count]
    }
}

impl Default for SessionSeedWordIndexes {
    fn default() -> Self {
        Self::new()
    }
}

/// One RAM-only session key source. Mirrors the C++ `SessionKeySource` field
/// for field; see the module docs for the secret-wiping model.
///
/// ```compile_fail
/// use nsealr_core::session::keyring::SessionKeySource;
/// fn require_clone<T: Clone>() {}
/// require_clone::<SessionKeySource>();
/// ```
/// ```compile_fail
/// use nsealr_core::session::keyring::SessionKeySource;
/// let source = SessionKeySource::new();
/// let _ = source.nsec_secret_key;
/// ```
/// ```compile_fail
/// use nsealr_core::session::keyring::SessionKeySource;
/// let source = SessionKeySource::new();
/// let _ = source.bip39_word_indexes;
/// ```
#[derive(PartialEq, Eq)]
pub struct SessionKeySource {
    /// The kind of material held (C++ `kind`).
    pub(crate) kind: SessionKeySourceKind,
    /// The user-facing label (C++ `label`).
    pub(crate) label: SessionKeySourceLabel,
    /// The raw nsec secret key; all-zero unless `kind` is
    /// [`SessionKeySourceKind::NsecSecretKey`] (C++ `nsec_secret_key`).
    pub(crate) nsec_secret_key: SecretKey,
    /// The BIP-39 word indexes; empty unless `kind` is
    /// [`SessionKeySourceKind::Bip39WordIndexes`] (C++ `bip39_word_indexes`).
    pub(crate) bip39_word_indexes: SessionSeedWordIndexes,
}

impl SessionKeySource {
    /// Creates an empty nsec-kind source (the C++ default-constructed state).
    #[must_use]
    pub const fn new() -> Self {
        Self {
            kind: SessionKeySourceKind::NsecSecretKey,
            label: SessionKeySourceLabel::new(),
            nsec_secret_key: SecretKey::empty(),
            bip39_word_indexes: SessionSeedWordIndexes::new(),
        }
    }

    /// Volatile-zeroes every field back to the default state. Mirrors the C++
    /// `SessionKeySource::wipe()`.
    pub fn wipe(&mut self) {
        use zeroize::Zeroize;
        self.nsec_secret_key.wipe();
        self.bip39_word_indexes.values.zeroize();
        self.bip39_word_indexes.count.zeroize();
        self.label.wipe();
        self.kind = SessionKeySourceKind::NsecSecretKey;
    }
}

impl core::fmt::Debug for SessionSeedWordIndexes {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.write_str("SessionSeedWordIndexes([REDACTED])")
    }
}

impl Drop for SessionSeedWordIndexes {
    fn drop(&mut self) {
        use zeroize::Zeroize;
        self.values.zeroize();
        self.count.zeroize();
    }
}

impl core::fmt::Debug for SessionKeySource {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.write_str("SessionKeySource([REDACTED])")
    }
}

impl SessionKeySource {
    /// Returns the source kind, without exposing material.
    pub fn kind(&self) -> SessionKeySourceKind {
        self.kind
    }

    /// Returns the local user-provided label. Treat it as untrusted text.
    pub fn label(&self) -> &str {
        self.label.as_str()
    }
}

impl Default for SessionKeySource {
    fn default() -> Self {
        Self::new()
    }
}

impl Drop for SessionKeySource {
    fn drop(&mut self) {
        self.wipe();
    }
}

/// The stateless RAM-only session keyring. Mirrors the C++
/// `StatelessSessionKeyring` (which deleted copy and move; this type is simply
/// not `Clone`). Dropping the keyring wipes every active source.
pub struct StatelessSessionKeyring {
    sources: [SessionKeySource; MAX_STATELESS_SESSION_KEY_SOURCES],
    len: usize,
}

impl core::fmt::Debug for StatelessSessionKeyring {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.write_str("StatelessSessionKeyring([REDACTED])")
    }
}

impl StatelessSessionKeyring {
    /// Creates an empty keyring.
    #[must_use]
    pub const fn new() -> Self {
        Self {
            sources: [const { SessionKeySource::new() }; MAX_STATELESS_SESSION_KEY_SOURCES],
            len: 0,
        }
    }

    /// Adds a raw nsec secret under `label`. Mirrors the C++ `add_nsec`
    /// (validation order: label, scalar, capacity).
    ///
    /// # Errors
    ///
    /// [`SessionKeyringError::EmptyLabel`], [`SessionKeyringError::LabelTooLong`],
    /// [`SessionKeyringError::InvalidNsecScalar`] or
    /// [`SessionKeyringError::KeyringFull`].
    pub fn add_nsec(&mut self, label: &str, secret: SecretKey) -> Result<(), SessionKeyringError> {
        let label = validated_label(label)?;
        if !nip19::is_valid_secret_key(secret.as_bytes()) {
            return Err(SessionKeyringError::InvalidNsecScalar);
        }
        self.require_capacity()?;
        let slot = &mut self.sources[self.len];
        slot.kind = SessionKeySourceKind::NsecSecretKey;
        slot.label = label;
        slot.nsec_secret_key = secret;
        slot.bip39_word_indexes = SessionSeedWordIndexes::new();
        self.len += 1;
        Ok(())
    }

    /// Adds a BIP-39 seed as word indexes under `label`. Mirrors the C++
    /// `add_bip39_seed`. Validates label, capacity, index shape and checksum.
    ///
    /// # Errors
    ///
    /// [`SessionKeyringError::EmptyLabel`], [`SessionKeyringError::LabelTooLong`],
    /// [`SessionKeyringError::KeyringFull`],
    /// [`SessionKeyringError::InvalidSeedWordCount`] or
    /// [`SessionKeyringError::SeedWordIndexOutOfRange`].
    pub fn add_bip39_seed(
        &mut self,
        label: &str,
        word_indexes: bip39::WordIndexes,
    ) -> Result<(), SessionKeyringError> {
        let label = validated_label(label)?;
        self.require_capacity()?;
        if !bip39::is_valid_word_count(word_indexes.len()) {
            return Err(SessionKeyringError::InvalidSeedWordCount);
        }
        if word_indexes
            .as_slice()
            .iter()
            .any(|&index| usize::from(index) >= bip39::WORD_COUNT)
        {
            return Err(SessionKeyringError::SeedWordIndexOutOfRange);
        }
        bip39::require_valid_checksum(word_indexes.as_slice())
            .map_err(|_| SessionKeyringError::InvalidSeedChecksum)?;
        let slot = &mut self.sources[self.len];
        slot.kind = SessionKeySourceKind::Bip39WordIndexes;
        slot.label = label;
        slot.nsec_secret_key = SecretKey::empty();
        slot.bip39_word_indexes = SessionSeedWordIndexes::new();
        slot.bip39_word_indexes.values[..word_indexes.len()]
            .copy_from_slice(word_indexes.as_slice());
        slot.bip39_word_indexes.count = word_indexes.len();
        self.len += 1;
        Ok(())
    }

    /// Transfers a pending source into this keyring. On error it is dropped.
    ///
    /// ```compile_fail
    /// use nsealr_core::session::{keyring::StatelessSessionKeyring, source_qr::parse_session_source_qr_text};
    /// let source = parse_session_source_qr_text("fixture", "nsec1zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs4rm7hz").unwrap();
    /// let mut ring = StatelessSessionKeyring::new();
    /// ring.add_source(source).unwrap();
    /// ring.add_source(source).unwrap(); // ownership was consumed
    /// ```
    ///
    /// # Errors
    /// Invalid label/scalar/indexes or exhausted capacity.
    pub fn add_source(&mut self, source: SessionKeySource) -> Result<(), SessionKeyringError> {
        validated_label(source.label.as_str())?;
        self.require_capacity()?;
        match source.kind {
            SessionKeySourceKind::NsecSecretKey => {
                if !nip19::is_valid_secret_key(source.nsec_secret_key.as_bytes()) {
                    return Err(SessionKeyringError::InvalidNsecScalar);
                }
            }
            SessionKeySourceKind::Bip39WordIndexes => {
                if !bip39::is_valid_word_count(source.bip39_word_indexes.count) {
                    return Err(SessionKeyringError::InvalidSeedWordCount);
                }
                if source
                    .bip39_word_indexes
                    .as_slice()
                    .iter()
                    .any(|&v| usize::from(v) >= bip39::WORD_COUNT)
                {
                    return Err(SessionKeyringError::SeedWordIndexOutOfRange);
                }
                bip39::require_valid_checksum(source.bip39_word_indexes.as_slice())
                    .map_err(|_| SessionKeyringError::InvalidSeedChecksum)?;
            }
        }
        self.sources[self.len] = source;
        self.len += 1;
        Ok(())
    }

    /// Transfers the last source out of this keyring without cloning it.
    ///
    /// # Errors
    /// [`SessionKeyringError::IndexOutOfRange`] if empty.
    pub fn take_last(&mut self) -> Result<SessionKeySource, SessionKeyringError> {
        if self.len == 0 {
            return Err(SessionKeyringError::IndexOutOfRange);
        }
        self.len -= 1;
        Ok(core::mem::take(&mut self.sources[self.len]))
    }

    /// Wipes every active source and empties the keyring. Mirrors the C++
    /// `clear()` (which wiped only the active slots; inactive slots are already
    /// zeroed by construction).
    pub fn clear(&mut self) {
        for slot in &mut self.sources[..self.len] {
            slot.wipe();
        }
        self.len = 0;
    }

    /// Returns `true` if the keyring holds no sources. Mirrors the C++
    /// `empty()`.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Returns the number of active sources. Mirrors the C++ `size()`.
    #[must_use]
    pub fn len(&self) -> usize {
        self.len
    }

    /// Returns the source at `index`. Mirrors the C++ `source_at`.
    ///
    /// # Errors
    ///
    /// [`SessionKeyringError::IndexOutOfRange`] if `index >= len()`.
    pub fn source_at(&self, index: usize) -> Result<&SessionKeySource, SessionKeyringError> {
        if index >= self.len {
            return Err(SessionKeyringError::IndexOutOfRange);
        }
        Ok(&self.sources[index])
    }

    /// Mirrors the C++ `require_capacity`.
    fn require_capacity(&self) -> Result<(), SessionKeyringError> {
        if self.len >= MAX_STATELESS_SESSION_KEY_SOURCES {
            return Err(SessionKeyringError::KeyringFull);
        }
        Ok(())
    }
}

/// Mirrors the C++ `require_valid_label` (empty / max-length checks); the
/// length check is the [`FixedStr`] capacity itself.
fn validated_label(label: &str) -> Result<SessionKeySourceLabel, SessionKeyringError> {
    if label.is_empty() {
        return Err(SessionKeyringError::EmptyLabel);
    }
    SessionKeySourceLabel::from_str(label).map_err(|_| SessionKeyringError::LabelTooLong)
}

impl Default for StatelessSessionKeyring {
    fn default() -> Self {
        Self::new()
    }
}

impl Drop for StatelessSessionKeyring {
    fn drop(&mut self) {
        self.clear();
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::nip19;

    // NIP-19 fixture copied from the READ-ONLY
    // specs/vectors/nip19/nsec-test-key-1.json (`nsec`).
    pub(crate) const NSEC_TEST_KEY_1: &str =
        "nsec1zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs4rm7hz";

    // SeedQR fixture copied from the READ-ONLY
    // specs/vectors/seedqr/seedsigner-vector-1.json (`standard_word_indexes`).
    pub(crate) const SEEDQR_VECTOR_1_INDEXES: [u16; 24] = [
        115, 1325, 1154, 127, 1190, 771, 415, 742, 1289, 1906, 2008, 870, 266, 1343, 1420, 2016,
        1792, 614, 896, 1929, 300, 1524, 801, 643,
    ];

    fn all_zero_u8(values: &[u8]) -> bool {
        values.iter().all(|&value| value == 0)
    }

    fn all_zero_u16(values: &[u16]) -> bool {
        values.iter().all(|&value| value == 0)
    }

    // Port of the C++ `test_stateless_session_keyring_accepts_parsed_key_sources`.
    #[test]
    fn accepts_parsed_key_sources() {
        let mut keyring = StatelessSessionKeyring::new();
        let secret = nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap();

        assert!(keyring.is_empty());
        assert!(StatelessSessionKeyring::default().is_empty());
        assert_eq!(SessionKeySource::default(), SessionKeySource::new());
        assert_eq!(
            SessionSeedWordIndexes::default(),
            SessionSeedWordIndexes::new(),
        );
        keyring
            .add_nsec(
                "nsec test vector",
                nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
            )
            .unwrap();
        keyring
            .add_bip39_seed(
                "SeedQR vector 1",
                crate::bip39::WordIndexes::from_slice(&SEEDQR_VECTOR_1_INDEXES).unwrap(),
            )
            .unwrap();

        assert_eq!(keyring.len(), 2);
        let nsec_source = keyring.source_at(0).unwrap();
        assert_eq!(nsec_source.kind, SessionKeySourceKind::NsecSecretKey);
        assert_eq!(nsec_source.label, "nsec test vector");
        assert_eq!(nsec_source.nsec_secret_key, secret);
        assert_eq!(nsec_source.bip39_word_indexes.count, 0);
        let seed_source = keyring.source_at(1).unwrap();
        assert_eq!(seed_source.kind, SessionKeySourceKind::Bip39WordIndexes);
        assert_eq!(seed_source.label, "SeedQR vector 1");
        assert_eq!(
            seed_source.bip39_word_indexes.as_slice(),
            &SEEDQR_VECTOR_1_INDEXES,
        );
        assert_eq!(
            keyring.source_at(2),
            Err(SessionKeyringError::IndexOutOfRange),
        );

        keyring.clear();
        assert!(keyring.is_empty());
    }

    // Port of the C++ `test_stateless_session_keyring_clear_wipes_active_sources`.
    // The C++ observed the wiped state through retained references; the borrow
    // checker forbids holding `&source` across `clear()`, so this test observes
    // the same post-clear slot state through the private `sources` field.
    #[test]
    fn clear_wipes_active_sources() {
        let mut keyring = StatelessSessionKeyring::new();

        keyring
            .add_nsec(
                "nsec test vector",
                nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
            )
            .unwrap();
        keyring
            .add_bip39_seed(
                "SeedQR vector 1",
                crate::bip39::WordIndexes::from_slice(&SEEDQR_VECTOR_1_INDEXES).unwrap(),
            )
            .unwrap();

        assert!(!all_zero_u8(keyring.sources[0].nsec_secret_key.as_bytes()));
        assert_eq!(
            keyring.sources[1].bip39_word_indexes.count,
            SEEDQR_VECTOR_1_INDEXES.len(),
        );
        assert!(!all_zero_u16(&keyring.sources[1].bip39_word_indexes.values));

        keyring.clear();

        assert!(keyring.is_empty());
        for slot in [&keyring.sources[0], &keyring.sources[1]] {
            assert!(slot.label.is_empty());
            assert!(all_zero_u8(slot.nsec_secret_key.as_bytes()));
            assert_eq!(slot.bip39_word_indexes.count, 0);
            assert!(all_zero_u16(&slot.bip39_word_indexes.values));
        }
        assert_eq!(
            keyring.source_at(0),
            Err(SessionKeyringError::IndexOutOfRange),
        );
    }

    #[test]
    fn transfer_and_live_wipe() {
        let mut source_ring = StatelessSessionKeyring::new();
        source_ring
            .add_nsec(
                "public fixture",
                nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
            )
            .unwrap();
        let mut source = source_ring.take_last().unwrap();
        assert!(source_ring.is_empty());
        assert_eq!(source.nsec_secret_key.as_bytes(), &[0x11; 32]);
        assert_eq!(source.kind(), SessionKeySourceKind::NsecSecretKey);
        assert_eq!(source.label(), "public fixture");
        source.wipe();
        assert_eq!(source.nsec_secret_key.as_bytes(), &[0; 32]);
        assert!(source.label().is_empty());
        assert_eq!(source.bip39_word_indexes.count, 0);
        assert_eq!(
            source_ring.take_last(),
            Err(SessionKeyringError::IndexOutOfRange)
        );
        assert_eq!(
            std::format!("{:?}", source.bip39_word_indexes),
            "SessionSeedWordIndexes([REDACTED])"
        );
    }

    #[test]
    fn consumed_source_revalidates_corrupted_internal_seed() {
        let mut ring = StatelessSessionKeyring::new();
        for (count, last, expected) in [
            (3, 0, SessionKeyringError::InvalidSeedWordCount),
            (12, 2048, SessionKeyringError::SeedWordIndexOutOfRange),
            (12, 0, SessionKeyringError::InvalidSeedChecksum),
        ] {
            let mut source = SessionKeySource::new();
            source.label = SessionKeySourceLabel::from_str("corrupted fixture").unwrap();
            source.kind = SessionKeySourceKind::Bip39WordIndexes;
            source.bip39_word_indexes.count = count;
            source.bip39_word_indexes.values[count - 1] = last;
            assert_eq!(ring.add_source(source), Err(expected));
            assert!(ring.is_empty());
        }
    }

    // Port of the C++ `test_stateless_session_keyring_rejects_invalid_sources`.
    #[test]
    fn rejects_invalid_sources() {
        let mut keyring = StatelessSessionKeyring::new();

        assert_eq!(
            keyring.add_nsec("", nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap()),
            Err(SessionKeyringError::EmptyLabel),
        );
        let long_label =
            core::str::from_utf8(&[b'x'; MAX_SESSION_KEY_SOURCE_LABEL_CHARS + 1]).unwrap();
        assert_eq!(
            keyring.add_nsec(long_label, nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap()),
            Err(SessionKeyringError::LabelTooLong),
        );
        assert_eq!(
            keyring.add_nsec("zero nsec", SecretKey::empty()),
            Err(SessionKeyringError::InvalidNsecScalar),
        );
        assert_eq!(
            keyring.add_bip39_seed(
                "short seed",
                crate::bip39::WordIndexes::from_slice(&[0, 1, 2]).unwrap()
            ),
            Err(SessionKeyringError::InvalidSeedWordCount),
        );
        let mut bad_indexes = [0u16; 12];
        bad_indexes[11] = 2048;
        assert_eq!(
            keyring.add_bip39_seed(
                "bad seed index",
                crate::bip39::WordIndexes::from_slice(&bad_indexes).unwrap()
            ),
            Err(SessionKeyringError::SeedWordIndexOutOfRange),
        );

        for index in 0..MAX_STATELESS_SESSION_KEY_SOURCES {
            let mut label = SessionKeySourceLabel::from_str("nsec source ").unwrap();
            label.try_push_usize(index).unwrap();
            keyring
                .add_nsec(label.as_str(), nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap())
                .unwrap();
        }
        assert_eq!(
            keyring.add_nsec("overflow", nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap()),
            Err(SessionKeyringError::KeyringFull),
        );
    }

    // Direct port-completeness test for `add_source` (the C++ exercised it only
    // through `run_session_import_flow`, which is deferred to M-T3.4b with the
    // review-controls substrate; the dispatch itself is session-keyring logic).
    #[test]
    fn add_source_revalidates_both_kinds() {
        let mut keyring = StatelessSessionKeyring::new();
        let secret = nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap();
        keyring
            .add_nsec(
                "nsec test vector",
                nip19::decode_nsec(NSEC_TEST_KEY_1).unwrap(),
            )
            .unwrap();
        keyring
            .add_bip39_seed(
                "SeedQR vector 1",
                crate::bip39::WordIndexes::from_slice(&SEEDQR_VECTOR_1_INDEXES).unwrap(),
            )
            .unwrap();

        let mut copy = StatelessSessionKeyring::new();
        copy.add_source(keyring.take_last().unwrap()).unwrap();
        copy.add_source(keyring.take_last().unwrap()).unwrap();
        assert_eq!(copy.len(), 2);
        assert!(keyring.is_empty());
        assert_eq!(
            copy.source_at(0).unwrap().kind(),
            SessionKeySourceKind::Bip39WordIndexes
        );
        assert_eq!(copy.source_at(1).unwrap().nsec_secret_key, secret);

        // Re-validation: a hand-built invalid source is rejected, not copied.
        let invalid = SessionKeySource::new();
        assert_eq!(
            copy.add_source(invalid),
            Err(SessionKeyringError::EmptyLabel),
        );
        let mut zero_scalar = SessionKeySource::new();
        zero_scalar.label = SessionKeySourceLabel::from_str("zero nsec").unwrap();
        assert_eq!(
            copy.add_source(zero_scalar),
            Err(SessionKeyringError::InvalidNsecScalar),
        );
    }
}
