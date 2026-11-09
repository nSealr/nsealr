//! Bounded FROST participant ownership for complete, locally reviewed Nostr events.
//!
//! This is a primitive/session foundation, not a device ceremony or QR protocol.
//! The trusted image implements [`ReviewAuthority`]: full event and group review,
//! live local consent, and authenticated peer commitment admission. A host grant
//! cannot implement that authority. All session/nonces are volatile and excluded
//! from share backups. Allocation failure aborts; firmware must provision and
//! qualify its allocator. No hardware erasure or entropy claim follows from this crate.
#![no_std]
#![forbid(unsafe_code)]

extern crate alloc;

use alloc::{collections::BTreeMap, vec::Vec};
use chacha20::ChaCha20Rng;
use frost_secp256k1_tr as frost;
use nsealr_core::event::Event;
use rand_core::SeedableRng;
use sha2::{Digest, Sha256};
use zeroize::{Zeroize, Zeroizing};

pub mod custody;
pub mod dkg;
mod transport;

/// Initial, explicit resource bound. Raising it requires new target measurements.
pub const MAX_PARTICIPANTS: usize = 5;
/// Monotonic milliseconds; all review and round work shares this deadline.
pub const MAX_ROUND_LIFETIME_MS: u64 = 300_000;
/// Exact scheme identity, including the upstream version and no extra Taproot tweak.
pub const SCHEME: &[u8] = b"nsealr/frost-secp256k1-tr/3.0.0/0966bd15/ordinary-sign/v1";
/// Maximum complete secret backup bytes. No nonce serialization exists here.
pub const MAX_BACKUP_BYTES: usize = 4 + 32 + 32 + 35 + 65 * MAX_PARTICIPANTS + 32;
/// Participant identifiers use upstream's canonical 32-byte scalar encoding.
pub type ParticipantId = [u8; 32];

/// A failure never authorizes an operation or permits reuse of a consumed nonce.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    Bounds,
    Encoding,
    Group,
    Participant,
    Binding,
    State,
    Clock,
    Expired,
    Entropy,
    Review,
    Crypto,
    Exhausted,
}

fn hash(parts: &[&[u8]]) -> [u8; 32] {
    let mut h = Sha256::new();
    for part in parts {
        h.update((part.len() as u64).to_be_bytes());
        h.update(part);
    }
    h.finalize().into()
}
fn id(bytes: &ParticipantId) -> Result<frost::Identifier, Error> {
    frost::Identifier::deserialize(bytes).map_err(|_| Error::Participant)
}
fn fixed<const N: usize>(bytes: &[u8]) -> Result<[u8; N], Error> {
    bytes.try_into().map_err(|_| Error::Encoding)
}
fn dimensions(threshold: u16, count: usize) -> Result<(), Error> {
    if !(2..=MAX_PARTICIPANTS).contains(&count) || threshold < 2 || threshold as usize > count {
        return Err(Error::Bounds);
    }
    Ok(())
}

/// Qualified, fallible device source. Fill exactly 32 bytes and cease all writes
/// before returning. Short fills and errors produce no usable RNG or commitment.
/// Source configuration/health/uniqueness and DMA ownership need device evidence.
pub trait EntropySource {
    fn fill(&mut self, seed: &mut [u8; 32]) -> Result<usize, Error>;
}
fn rng(source: &mut impl EntropySource) -> Result<ChaCha20Rng, Error> {
    let mut seed = Zeroizing::new([0; 32]);
    if source.fill(&mut seed) != Ok(32) {
        return Err(Error::Entropy);
    }
    // The upstream API is infallible. Seed its zeroizing CSPRNG only after the
    // qualified source succeeded, without UnwrapErr, panic, or fallback entropy.
    let rng = ChaCha20Rng::from_seed(*seed);
    seed.zeroize();
    Ok(rng)
}

/// Public group descriptor, hashed in full into every round and backup identity.
#[derive(Clone)]
pub struct Group {
    public: frost::keys::PublicKeyPackage,
    descriptor: Vec<u8>,
    identity: [u8; 32],
    public_key: [u8; 32],
    threshold: u16,
    members: Vec<ParticipantId>,
}
impl Group {
    fn new(public: frost::keys::PublicKeyPackage) -> Result<Self, Error> {
        let threshold = public.min_signers().ok_or(Error::Group)?;
        dimensions(threshold, public.verifying_shares().len())?;
        let key: [u8; 33] = fixed(
            &public
                .verifying_key()
                .serialize()
                .map_err(|_| Error::Crypto)?,
        )?;
        let public_key = fixed(&key[1..])?;
        let mut descriptor = Vec::with_capacity(35 + 65 * public.verifying_shares().len());
        descriptor.push(threshold as u8);
        descriptor.push(public.verifying_shares().len() as u8);
        descriptor.extend_from_slice(&key);
        let mut members = Vec::with_capacity(public.verifying_shares().len());
        for (participant, share) in public.verifying_shares() {
            let identifier = fixed(&participant.serialize())?;
            members.push(identifier);
            descriptor.extend_from_slice(&identifier);
            descriptor.extend_from_slice(&share.serialize().map_err(|_| Error::Crypto)?);
        }
        let identity = hash(&[SCHEME, &descriptor]);
        Ok(Self {
            public,
            descriptor,
            identity,
            public_key,
            threshold,
            members,
        })
    }
    pub fn identity(&self) -> &[u8; 32] {
        &self.identity
    }
    /// Exact returned group x-only key. No second Taproot tweak is applied.
    pub fn public_key(&self) -> &[u8; 32] {
        &self.public_key
    }
    pub fn threshold(&self) -> u16 {
        self.threshold
    }
    pub fn participant_ids(&self) -> impl ExactSizeIterator<Item = ParticipantId> + '_ {
        self.members.iter().copied()
    }
    /// Complete public confirmation bytes (threshold, count, compressed group
    /// key and sorted identifier/verifying-share pairs); scheme is [`SCHEME`].
    pub fn descriptor(&self) -> &[u8] {
        &self.descriptor
    }
}

/// Long-term secret owner. It is deliberately neither Clone nor Debug.
pub struct Participant {
    key: frost::keys::KeyPackage,
    group: Group,
    identifier: ParticipantId,
}
impl Participant {
    fn new(key: frost::keys::KeyPackage, group: Group) -> Result<Self, Error> {
        let verifying_share = frost::keys::VerifyingShare::from(*key.signing_share());
        if key.verifying_key() != group.public.verifying_key()
            || *key.min_signers() != group.threshold
            || group.public.verifying_shares().get(key.identifier()) != Some(&verifying_share)
            || key.verifying_share() != &verifying_share
        {
            return Err(Error::Group);
        }
        let identifier = fixed(&key.identifier().serialize())?;
        Ok(Self {
            key,
            group,
            identifier,
        })
    }
    pub fn group(&self) -> &Group {
        &self.group
    }
    pub fn identifier(&self) -> ParticipantId {
        self.identifier
    }

    /// Local secret export boundary; the device must separately obtain physical
    /// backup consent and clear displayed/camera copies. Never send to companion.
    /// Contains only scheme-bound long-term share/group metadata and checksum.
    pub fn backup(&self) -> Result<Zeroizing<Vec<u8>>, Error> {
        let mut bytes = Zeroizing::new(Vec::with_capacity(MAX_BACKUP_BYTES));
        bytes.extend_from_slice(b"NST1");
        bytes.extend_from_slice(&self.identifier());
        let share = Zeroizing::new(self.key.signing_share().serialize());
        bytes.extend_from_slice(&share);
        bytes.extend_from_slice(&self.group.descriptor);
        let checksum = hash(&[SCHEME, &bytes]);
        bytes.extend_from_slice(&checksum);
        Ok(bytes)
    }

    /// Restore only against independently confirmed group and participant IDs.
    /// The checksum detects transcription damage; it does not authenticate a peer.
    pub fn restore(
        bytes: &[u8],
        expected_group: &[u8; 32],
        expected_participant: &ParticipantId,
    ) -> Result<Self, Error> {
        if bytes.len() > MAX_BACKUP_BYTES
            || bytes.len() < 4 + 64 + 35 + 2 * 65 + 32
            || &bytes[..4] != b"NST1"
        {
            return Err(Error::Encoding);
        }
        let end = bytes.len() - 32;
        if hash(&[SCHEME, &bytes[..end]]) != bytes[end..] {
            return Err(Error::Encoding);
        }
        let participant = fixed(&bytes[4..36])?;
        if &participant != expected_participant {
            return Err(Error::Participant);
        }
        let descriptor = &bytes[68..end];
        let threshold = descriptor[0] as u16;
        let count = descriptor[1] as usize;
        dimensions(threshold, count)?;
        if descriptor.len() != 35 + count * 65 {
            return Err(Error::Encoding);
        }
        let verifying_key =
            frost::VerifyingKey::deserialize(&descriptor[2..35]).map_err(|_| Error::Encoding)?;
        let mut shares = BTreeMap::new();
        let mut last = None;
        for entry in descriptor[35..].chunks_exact(65) {
            let member = id(&fixed(&entry[..32])?)?;
            if last.is_some_and(|previous| previous >= member) {
                return Err(Error::Participant);
            }
            last = Some(member);
            let share = frost::keys::VerifyingShare::deserialize(&entry[32..])
                .map_err(|_| Error::Encoding)?;
            shares.insert(member, share);
        }
        let group = Group::new(frost::keys::PublicKeyPackage::new(
            shares,
            verifying_key,
            Some(threshold),
        ))?;
        if group.identity() != expected_group {
            return Err(Error::Group);
        }
        let identifier = id(&participant)?;
        let signing_share =
            frost::keys::SigningShare::deserialize(&bytes[36..68]).map_err(|_| Error::Encoding)?;
        let verifying_share = *group
            .public
            .verifying_shares()
            .get(&identifier)
            .ok_or(Error::Participant)?;
        let key = frost::keys::KeyPackage::new(
            identifier,
            signing_share,
            verifying_share,
            verifying_key,
            threshold,
        );
        Self::new(key, group)
    }
}

/// Dealer splitting preserves an existing Nostr identity (including odd-Y keys).
/// The full key existed: this does not remove a possible full-key custody bypass.
/// Passing None generates a new dealer key. Dealer share delivery needs a local,
/// confidential, authenticated ceremony; this function supplies no transport.
pub fn dealer(
    threshold: u16,
    count: u16,
    secret: Option<Zeroizing<[u8; 32]>>,
    source: &mut impl EntropySource,
) -> Result<Vec<Participant>, Error> {
    dimensions(threshold, count as usize)?;
    let mut rng = rng(source)?;
    let (shares, public) = if let Some(secret) = secret {
        let key = frost::SigningKey::deserialize(secret.as_ref()).map_err(|_| Error::Encoding)?;
        frost::keys::split(
            &key,
            count,
            threshold,
            frost::keys::IdentifierList::Default,
            &mut rng,
        )
    } else {
        frost::keys::generate_with_dealer(
            count,
            threshold,
            frost::keys::IdentifierList::Default,
            &mut rng,
        )
    }
    .map_err(|_| Error::Crypto)?;
    let group = Group::new(public)?;
    shares
        .into_values()
        .map(|share| {
            let key = frost::keys::KeyPackage::try_from(share).map_err(|_| Error::Crypto)?;
            Participant::new(key, group.clone())
        })
        .collect()
}

/// Shared, immutable round identity. The event ID is constructed by the core
/// from the complete event and selected group key, never supplied as a hash.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RoundIntent {
    group: [u8; 32],
    public_key: [u8; 32],
    event_id: [u8; 32],
    session: [u8; 32],
    participants: Vec<ParticipantId>,
    binding: [u8; 32],
}
impl RoundIntent {
    pub fn for_event(
        group: &Group,
        event: &Event,
        session: [u8; 32],
        participants: &[ParticipantId],
    ) -> Result<Self, Error> {
        if participants.len() < group.threshold as usize || participants.len() > MAX_PARTICIPANTS {
            return Err(Error::Bounds);
        }
        let mut participants = participants.to_vec();
        participants.sort();
        for (index, participant) in participants.iter().enumerate() {
            if index > 0 && participant == &participants[index - 1]
                || !group
                    .public
                    .verifying_shares()
                    .contains_key(&id(participant)?)
            {
                return Err(Error::Participant);
            }
        }
        if event.public_key() != group.public_key() {
            return Err(Error::Binding);
        }
        event.review().map_err(|_| Error::Review)?;
        let event_id = event.id();
        let mut h = Sha256::new();
        h.update(hash(&[
            b"nsealr.threshold.intent.v1",
            group.identity(),
            group.public_key(),
            &event_id,
            &session,
        ]));
        h.update([participants.len() as u8]);
        for participant in &participants {
            h.update(participant);
        }
        let binding = h.finalize().into();
        Ok(Self {
            group: *group.identity(),
            public_key: *group.public_key(),
            event_id,
            session,
            participants,
            binding,
        })
    }
    pub fn group(&self) -> &[u8; 32] {
        &self.group
    }
    pub fn public_key(&self) -> &[u8; 32] {
        &self.public_key
    }
    pub fn event_id(&self) -> &[u8; 32] {
        &self.event_id
    }
    pub fn session(&self) -> &[u8; 32] {
        &self.session
    }
    pub fn participants(&self) -> &[ParticipantId] {
        &self.participants
    }
    pub fn binding(&self) -> &[u8; 32] {
        &self.binding
    }
}

/// Public round-one optical payload, with no signing nonce material.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Commitment {
    pub intent: [u8; 32],
    pub participant: ParticipantId,
    /// Compressed hiding then binding point (33 bytes each).
    pub points: [u8; 66],
}
impl Commitment {
    fn decode(&self) -> Result<frost::round1::SigningCommitments, Error> {
        Ok(frost::round1::SigningCommitments::new(
            frost::round1::NonceCommitment::deserialize(&self.points[..33])
                .map_err(|_| Error::Encoding)?,
            frost::round1::NonceCommitment::deserialize(&self.points[33..])
                .map_err(|_| Error::Encoding)?,
        ))
    }
}

/// Checked, bounded complete commitment transcript. It cannot hide another message.
pub struct SigningRound {
    intent: RoundIntent,
    commitments: Vec<Commitment>,
    package: frost::SigningPackage,
    binding: [u8; 32],
}
impl SigningRound {
    pub fn new(intent: &RoundIntent, commitments: &[Commitment]) -> Result<Self, Error> {
        if commitments.len() != intent.participants.len() {
            return Err(Error::Bounds);
        }
        let mut commitments = commitments.to_vec();
        commitments.sort_by_key(|commitment| commitment.participant);
        let mut map = BTreeMap::new();
        let mut h = Sha256::new();
        h.update(hash(&[
            b"nsealr.threshold.commitments.v1",
            intent.binding(),
        ]));
        for (commitment, expected) in commitments.iter().zip(&intent.participants) {
            if &commitment.participant != expected || &commitment.intent != intent.binding() {
                return Err(Error::Binding);
            }
            map.insert(id(expected)?, commitment.decode()?);
            h.update(commitment.participant);
            h.update(commitment.points);
        }
        Ok(Self {
            package: frost::SigningPackage::new(map, intent.event_id()),
            intent: intent.clone(),
            commitments,
            binding: h.finalize().into(),
        })
    }
    pub fn intent(&self) -> &RoundIntent {
        &self.intent
    }
    pub fn commitments(&self) -> &[Commitment] {
        &self.commitments
    }
    pub fn binding(&self) -> &[u8; 32] {
        &self.binding
    }

    /// Verify exact share set/transcript and aggregate with upstream share checking.
    /// The companion must still independently verify the resulting complete event.
    pub fn aggregate(&self, group: &Group, shares: &[SignatureShare]) -> Result<[u8; 64], Error> {
        if group.identity() != self.intent.group() {
            return Err(Error::Group);
        }
        if shares.len() != self.intent.participants.len() {
            return Err(Error::Bounds);
        }
        let mut map = BTreeMap::new();
        for share in shares {
            if share.intent != self.intent.binding
                || share.round != self.binding
                || !self.intent.participants.contains(&share.participant)
            {
                return Err(Error::Binding);
            }
            let decoded = frost::round2::SignatureShare::deserialize(&share.scalar)
                .map_err(|_| Error::Encoding)?;
            if map.insert(id(&share.participant)?, decoded).is_some() {
                return Err(Error::Participant);
            }
        }
        let signature =
            frost::aggregate(&self.package, &map, &group.public).map_err(|_| Error::Crypto)?;
        group
            .public
            .verifying_key()
            .verify(self.intent.event_id(), &signature)
            .map_err(|_| Error::Crypto)?;
        fixed(&signature.serialize().map_err(|_| Error::Crypto)?)
    }
}

/// Public round-two output. Re-emission is the adapter's bounded public cache's
/// job; calling the signer again cannot emit a second share.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SignatureShare {
    pub intent: [u8; 32],
    pub round: [u8; 32],
    pub participant: ParticipantId,
    pub scalar: [u8; 32],
}

/// A local authority handle bound to this selected participant and owner epoch.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReviewBinding {
    pub intent: RoundIntent,
    pub participant: ParticipantId,
    pub epoch: u64,
    pub deadline_ms: u64,
    token: [u8; 32],
}
impl ReviewBinding {
    pub fn token(&self) -> &[u8; 32] {
        &self.token
    }
}

/// Only the synchronous full-event callback receives this approval constructor.
pub struct ReviewIntent<'a> {
    pub event: &'a Event,
    pub group: &'a Group,
    pub binding: &'a ReviewBinding,
}
pub struct ReviewApproval([u8; 32]);
impl ReviewIntent<'_> {
    /// Call only after complete local review and a fresh physical approval.
    pub fn approve(&self) -> ReviewApproval {
        ReviewApproval(self.binding.token)
    }
}

/// Trusted-image boundary, analogous to the core's synchronous local display IO.
/// `review` must admit the unchanged event under the device review policy and
/// display the group, selected participants and operation before approval.
/// Partial prose review is an explicit local choice; authority fields remain mandatory.
/// `check_live` checks the same physical authority/context has not been revoked.
/// `admit_round` authenticates every peer commitment and binds the full transcript;
/// checksums/host claims alone are not authentication. No method is a host grant.
pub trait ReviewAuthority {
    fn now_ms(&mut self) -> Option<u64>;
    fn review(&mut self, intent: ReviewIntent<'_>) -> Result<ReviewApproval, Error>;
    fn check_live(&mut self, binding: &ReviewBinding) -> Result<(), Error>;
    fn admit_round(&mut self, binding: &ReviewBinding, round: &SigningRound) -> Result<(), Error>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    Locked,
    Ready,
    Committed,
    Spent,
}
struct Pending {
    binding: ReviewBinding,
    commitment: Commitment,
    nonces: frost::round1::SigningNonces,
}

/// One selected participant and at most one volatile nonce owner. Neither Clone
/// nor serialization is implemented. Every signing attempt first takes the nonce.
pub struct Signer {
    selected: Option<Participant>,
    pending: Option<Pending>,
    state: State,
    epoch: u64,
    last_time: Option<u64>,
    last_seed_tag: [u8; 32],
}
impl Default for Signer {
    fn default() -> Self {
        Self::new()
    }
}
impl Signer {
    pub fn new() -> Self {
        Self {
            selected: None,
            pending: None,
            state: State::Locked,
            epoch: 0,
            last_time: None,
            last_seed_tag: [0; 32],
        }
    }
    pub fn state(&self) -> State {
        self.state
    }
    pub fn selected(&self) -> Option<&Participant> {
        self.selected.as_ref()
    }
    pub fn select(&mut self, participant: Participant) {
        self.lock();
        self.selected = Some(participant);
        self.state = State::Ready;
    }
    pub fn cancel(&mut self) {
        self.pending = None;
        self.state = if self.selected.is_some() {
            State::Ready
        } else {
            State::Locked
        };
    }
    pub fn lock(&mut self) {
        self.pending = None;
        self.selected = None;
        self.state = State::Locked;
    }
    fn clock(&mut self, authority: &mut impl ReviewAuthority, deadline: u64) -> Result<(), Error> {
        let now = authority.now_ms().ok_or(Error::Clock)?;
        if self.last_time.is_some_and(|last| now < last) {
            return Err(Error::Clock);
        }
        self.last_time = Some(now);
        if now >= deadline {
            return Err(Error::Expired);
        }
        if deadline - now > MAX_ROUND_LIFETIME_MS {
            return Err(Error::Bounds);
        }
        Ok(())
    }
    /// Complete local review precedes fresh nonce creation and its sole emission.
    pub fn begin(
        &mut self,
        event: Event,
        intent: RoundIntent,
        deadline_ms: u64,
        authority: &mut impl ReviewAuthority,
        source: &mut impl EntropySource,
    ) -> Result<Commitment, Error> {
        let result = self.begin_inner(event, intent, deadline_ms, authority, source);
        if result.is_err() {
            self.pending = None;
            self.state = if self.selected.is_some() {
                State::Spent
            } else {
                State::Locked
            };
        }
        result
    }
    fn begin_inner(
        &mut self,
        event: Event,
        intent: RoundIntent,
        deadline_ms: u64,
        authority: &mut impl ReviewAuthority,
        source: &mut impl EntropySource,
    ) -> Result<Commitment, Error> {
        if self.pending.is_some() {
            return Err(Error::State);
        }
        self.epoch = self.epoch.checked_add(1).ok_or(Error::Exhausted)?;
        self.clock(authority, deadline_ms)?;
        let participant = self.selected.as_ref().ok_or(Error::State)?;
        if intent.group() != participant.group.identity()
            || intent.public_key() != participant.group.public_key()
            || !intent.participants.contains(&participant.identifier())
            || event.public_key() != participant.group.public_key()
            || event.id() != intent.event_id
        {
            return Err(Error::Binding);
        }
        let token = hash(&[
            b"nsealr.threshold.authority.v1",
            intent.binding(),
            &participant.identifier(),
            &self.epoch.to_be_bytes(),
            &deadline_ms.to_be_bytes(),
        ]);
        let binding = ReviewBinding {
            intent,
            participant: participant.identifier(),
            epoch: self.epoch,
            deadline_ms,
            token,
        };
        let approval = authority.review(ReviewIntent {
            event: &event,
            group: &participant.group,
            binding: &binding,
        })?;
        if approval.0 != binding.token {
            return Err(Error::Review);
        }
        self.clock(authority, deadline_ms)?;
        authority.check_live(&binding)?;
        let mut seed = Zeroizing::new([0; 32]);
        if source.fill(&mut seed) != Ok(32) {
            return Err(Error::Entropy);
        }
        // Detect consecutive repeated seeds even across cancel/select/lock. This
        // supplements source qualification, not a persistent entropy health test.
        let seed_tag = hash(&[b"nsealr.threshold.entropy-check.v1", seed.as_ref()]);
        if seed_tag == self.last_seed_tag {
            return Err(Error::Entropy);
        }
        self.last_seed_tag = seed_tag;
        let mut rng = ChaCha20Rng::from_seed(*seed);
        // Distinct streams also separate nonconsecutive seed repeats during this
        // owner's lifetime. Firmware keeps one owner until reset; fresh qualified
        // entropy is still required after reset and cannot be proved in software.
        rng.set_stream(self.epoch);
        seed.zeroize();
        let participant = self.selected.as_ref().ok_or(Error::State)?;
        let (nonces, commitments) =
            frost::round1::commit(participant.key.signing_share(), &mut rng);
        let mut points = [0; 66];
        points[..33].copy_from_slice(
            &commitments
                .hiding()
                .serialize()
                .map_err(|_| Error::Crypto)?,
        );
        points[33..].copy_from_slice(
            &commitments
                .binding()
                .serialize()
                .map_err(|_| Error::Crypto)?,
        );
        self.clock(authority, deadline_ms)?;
        authority.check_live(&binding)?;
        let commitment = Commitment {
            intent: *binding.intent.binding(),
            participant: binding.participant,
            points,
        };
        self.pending = Some(Pending {
            binding,
            commitment: commitment.clone(),
            nonces,
        });
        self.state = State::Committed;
        Ok(commitment)
    }

    pub fn sign(
        &mut self,
        round: &SigningRound,
        authority: &mut impl ReviewAuthority,
    ) -> Result<SignatureShare, Error> {
        // Consume before parsing/admission/checking or calling any external code.
        let pending = self.pending.take().ok_or(Error::State)?;
        self.state = State::Spent;
        self.clock(authority, pending.binding.deadline_ms)?;
        authority.check_live(&pending.binding)?;
        if round.intent != pending.binding.intent
            || !round
                .commitments
                .iter()
                .any(|commitment| commitment == &pending.commitment)
        {
            return Err(Error::Binding);
        }
        authority.admit_round(&pending.binding, round)?;
        self.clock(authority, pending.binding.deadline_ms)?;
        authority.check_live(&pending.binding)?;
        let participant = self.selected.as_ref().ok_or(Error::State)?;
        let share = frost::round2::sign(&round.package, &pending.nonces, &participant.key)
            .map_err(|_| Error::Crypto)?;
        self.clock(authority, pending.binding.deadline_ms)?;
        authority.check_live(&pending.binding)?;
        Ok(SignatureShare {
            intent: *round.intent.binding(),
            round: round.binding,
            participant: pending.binding.participant,
            scalar: fixed(&share.serialize())?,
        })
    }
}
