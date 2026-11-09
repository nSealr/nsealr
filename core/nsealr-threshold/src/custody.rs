//! One local 2-of-3 share, with authenticated optical setup and signing.
//! The coordinator routes opaque packets. Physical roster comparison supplies
//! authentication; a transport checksum or coordinator assertion does not.
use crate::{
    dkg, frost, transport as wire, Commitment, Participant, ParticipantId, ReviewApproval,
    ReviewAuthority, ReviewBinding, ReviewIntent, RoundIntent, SignatureShare, Signer,
    SigningRound,
};
use alloc::{
    boxed::Box,
    format,
    string::{String, ToString},
    vec,
    vec::Vec,
};
use nsealr_core::{
    event::{Event, Field, CRITICAL, DETAIL, PROSE},
    hash::sha256,
    identity::Identity,
    json as j,
    qr::Collector,
    Error,
};
use serde_json::{json, Value};
use zeroize::{Zeroize, Zeroizing};

pub const MAX_BACKUP: usize = 2048;
const SETUP_MS: u64 = 600_000;
const SIGN_MS: u64 = crate::MAX_ROUND_LIFETIME_MS;
#[cfg(test)]
mod tests;

enum SetupStage {
    First {
        owner: dkg::RoundOne,
        own: Box<dkg::Broadcast>,
        incoming: Vec<dkg::Broadcast>,
    },
    Second {
        owner: dkg::RoundTwo,
        transcript: [u8; 32],
        incoming: Vec<dkg::Delivery>,
    },
}
struct Setup {
    session: [u8; 32],
    fingerprint: [u8; 32],
    binding: [u8; 32],
    stage: SetupStage,
}
struct Signing {
    id: String,
    event: Event,
    intent: RoundIntent,
    peer: [u8; 32],
    own: Commitment,
    round: Option<SigningRound>,
    share: Option<SignatureShare>,
}
struct Recovery {
    participant: Participant,
    identity: Identity,
    members: Vec<[u8; 32]>,
}
enum Action {
    Setup {
        session: [u8; 32],
        members: Vec<[u8; 32]>,
    },
    Restore(Box<Recovery>),
    Sign {
        id: String,
        text: String,
        intent: Box<RoundIntent>,
        peer: [u8; 32],
        confirmation: &'static str,
    },
    PublicKey(String),
}
struct Review {
    action: Action,
    fields: Vec<Field>,
    seen: Vec<bool>,
}

#[derive(Default)]
pub struct Custody {
    identity: Option<Identity>,
    members: Vec<[u8; 32]>,
    signer: Signer,
    group: [u8; 32],
    setup: Option<Setup>,
    signing: Option<Signing>,
    review: Option<Review>,
    outputs: Vec<String>,
    received: Vec<[u8; 32]>,
    generation: u64,
    deadline: u64,
    last_time: u64,
    last_seed: [u8; 32],
    sequence: u64,
    finished: bool,
    backup_scan: Option<bool>,
    pub collector: Collector,
}
fn crypto<T>(result: Result<T, crate::Error>) -> Result<T, Error> {
    result.map_err(|_| Error::Crypto)
}
fn member_id(index: usize) -> ParticipantId {
    frost::Identifier::try_from((index + 1) as u16)
        .expect("member 1..3")
        .serialize()
        .try_into()
        .expect("scalar32")
}
fn member_index(members: &[[u8; 32]], key: &[u8; 32]) -> Result<usize, Error> {
    members.iter().position(|k| k == key).ok_or(Error::Identity)
}
fn setup_fingerprint(session: &[u8; 32], members: &[[u8; 32]]) -> [u8; 32] {
    sha256(
        &serde_json::to_vec(&(
            "nSealr 2-of-3 setup",
            j::hex_string(session),
            wire::list(members),
        ))
        .expect("strings serialize"),
    )
}
fn group_fingerprint(participant: &Participant, members: &[[u8; 32]]) -> [u8; 32] {
    sha256(
        &serde_json::to_vec(&(
            "nSealr 2-of-3 custody",
            j::hex_string(participant.group().identity()),
            wire::list(members),
        ))
        .expect("strings serialize"),
    )
}

impl Custody {
    pub fn loaded(&self) -> bool {
        self.signer.selected().is_some()
    }
    pub fn public_key(&self) -> Result<&[u8; 32], Error> {
        Ok(self
            .signer
            .selected()
            .ok_or(Error::Locked)?
            .group()
            .public_key())
    }
    pub fn group(&self) -> Result<&[u8; 32], Error> {
        self.public_key()?;
        Ok(&self.group)
    }
    pub fn member(&self) -> Result<u32, Error> {
        let id = self.signer.selected().ok_or(Error::Locked)?.identifier();
        (0..3)
            .find(|&i| member_id(i) == id)
            .map(|i| i as u32 + 1)
            .ok_or(Error::Identity)
    }
    pub fn state(&self) -> u32 {
        if self.review.is_some() {
            2
        } else if self.finished {
            5
        } else if self.setup.is_some() || self.signing.is_some() {
            3
        } else if self.loaded() {
            4
        } else if self.identity.is_some() {
            1
        } else {
            0
        }
    }
    pub fn progress(&self) -> u32 {
        match self.setup.as_ref().map(|s| &s.stage) {
            Some(SetupStage::First { incoming, .. }) => incoming.len() as u32,
            Some(SetupStage::Second { incoming, .. }) => incoming.len() as u32,
            None => u32::from(self.signing.as_ref().is_some_and(|s| s.round.is_some())),
        }
    }
    pub fn generation(&self) -> u64 {
        self.generation
    }
    pub fn fields(&self) -> &[Field] {
        self.review.as_ref().map_or(&[], |r| r.fields.as_slice())
    }
    pub fn confirmation(&self) -> Result<&'static str, Error> {
        Ok(match &self.review.as_ref().ok_or(Error::Stale)?.action {
            Action::Setup { .. } => "Create group",
            Action::Restore(_) => "Restore share",
            Action::Sign { confirmation, .. } => confirmation,
            Action::PublicKey(_) => "Share identity",
        })
    }
    pub fn outputs(&self) -> &[String] {
        &self.outputs
    }
    pub fn finish_response(&mut self) {
        if self.review.is_some() || self.collector.received() != 0 || self.backup_scan.is_some() {
            self.cancel();
        } else {
            self.outputs.clear();
        }
    }
    pub fn cancel(&mut self) {
        self.signer.cancel();
        self.setup = None;
        self.signing = None;
        self.review = None;
        self.outputs.clear();
        self.received.clear();
        self.collector.clear();
        self.finished = false;
        self.backup_scan = None;
        self.deadline = 0;
        self.generation = self.generation.saturating_add(1);
        if !self.loaded() {
            self.identity = None;
            self.members.clear();
        }
    }
    pub fn lock(&mut self) {
        self.cancel();
        self.signer.lock();
        self.identity = None;
        self.members.clear();
        self.group.zeroize();
    }
    fn clock(&mut self, now: u64) -> Result<(), Error> {
        if now < self.last_time {
            self.cancel();
            return Err(Error::Stale);
        }
        self.last_time = now;
        Ok(())
    }
    pub fn tick(&mut self, now: u64) -> Result<bool, Error> {
        self.clock(now)?;
        let expired = self.deadline != 0 && now >= self.deadline;
        if expired {
            self.cancel();
        }
        Ok(expired)
    }
    fn random(&mut self, entropy: &[u8]) -> Result<wire::Random, Error> {
        let seed: &[u8; 32] = entropy.try_into().map_err(|_| Error::Entropy)?;
        let tag = sha256(seed);
        if tag == self.last_seed {
            return Err(Error::Entropy);
        }
        self.sequence = self.sequence.checked_add(1).ok_or(Error::Stale)?;
        self.last_seed = tag;
        Ok(wire::Random::new(*seed, self.sequence))
    }
    pub fn start(&mut self, entropy: &mut [u8], now: u64) -> Result<(), Error> {
        self.lock();
        let result = (|| {
            self.clock(now)?;
            let mut random = self.random(entropy)?;
            let mut seed = random.bytes();
            let identity = Identity::generate(0, &mut seed, "", 0)?;
            self.outputs.push(
                json!({"type":"nsealr_join","key":j::hex_string(&identity.public_key())})
                    .to_string(),
            );
            self.identity = Some(identity);
            self.deadline = now.checked_add(SETUP_MS).ok_or(Error::Stale)?;
            Ok(())
        })();
        entropy.zeroize();
        if result.is_err() {
            self.lock();
        }
        result
    }
    fn prepare(&mut self, action: Action, fields: Vec<Field>) -> Result<(), Error> {
        self.generation = self.generation.checked_add(1).ok_or(Error::Stale)?;
        self.review = Some(Review {
            action,
            seen: vec![false; fields.len()],
            fields,
        });
        Ok(())
    }
    pub fn seen(&mut self, generation: u64, index: usize) -> Result<(), Error> {
        if generation != self.generation {
            return Err(Error::Stale);
        }
        *self
            .review
            .as_mut()
            .and_then(|r| r.seen.get_mut(index))
            .ok_or(Error::Stale)? = true;
        Ok(())
    }
    pub fn reject(&mut self, generation: u64) -> Result<(), Error> {
        let matches = generation == self.generation && self.review.is_some();
        self.cancel();
        if matches {
            Ok(())
        } else {
            Err(Error::Stale)
        }
    }
    pub fn receive_frame(
        &mut self,
        frame: &[u8],
        entropy: &mut [u8],
        now: u64,
    ) -> Result<bool, Error> {
        let result = (|| {
            if self.review.is_some() || self.backup_scan.is_some() {
                return Err(Error::Stale);
            }
            if self.tick(now)? {
                return Err(Error::Stale);
            }
            if self.deadline == 0 {
                self.deadline = now.checked_add(SETUP_MS).ok_or(Error::Stale)?;
            }
            match self.collector.accept(frame)? {
                Some(message) => {
                    self.receive(&message, entropy, now)?;
                    Ok(true)
                }
                None => Ok(false),
            }
        })();
        entropy.zeroize();
        if result.is_err() {
            self.cancel();
        }
        result
    }
    pub fn receive(&mut self, input: &[u8], entropy: &mut [u8], now: u64) -> Result<(), Error> {
        let result = (|| {
            if self.backup_scan.is_some() {
                return Err(Error::Stale);
            }
            if self.tick(now)? {
                return Err(Error::Stale);
            }
            let digest = sha256(input);
            if self.received.contains(&digest) {
                return Ok(());
            }
            if self.review.is_some() {
                return Err(Error::Stale);
            }
            let value = j::parse(input)?;
            self.outputs.clear();
            self.finished = false;
            if value.get("method").is_some() {
                return self.public_request(input, now);
            }
            match j::string(&value["type"])? {
                "nsealr_setup" => self.setup_request(&value),
                "nsealr_sign" => self.sign_request(&value, now),
                "nsealr_peer" => {
                    let mut random = self.random(entropy)?;
                    if self.setup.is_some() {
                        self.setup_peer(&value, &mut random)?;
                    } else {
                        self.sign_peer(&value, &mut random, now)?;
                    }
                    if self.received.len() >= 4 {
                        return Err(Error::Bounds);
                    }
                    self.received.push(digest);
                    Ok(())
                }
                _ => Err(Error::Unsupported),
            }
        })();
        entropy.zeroize();
        if result.is_err() {
            self.cancel();
        }
        result
    }
    fn setup_request(&mut self, value: &Value) -> Result<(), Error> {
        if self.loaded() || self.setup.is_some() {
            return Err(Error::Stale);
        }
        j::exact_keys(value, &["type", "session", "members"], &[])?;
        let session = j::hex(j::string(&value["session"])?)?;
        let members = wire::members(&value["members"], 3)?;
        let own = self.identity.as_ref().ok_or(Error::Locked)?.public_key();
        let index = member_index(&members, &own)?;
        let fingerprint = setup_fingerprint(&session, &members);
        let fields=vec![Field::new("Action","Create a 2-of-3 signing group",CRITICAL),
            Field::new("This device",format!("Member {} of 3",index+1),CRITICAL),
            Field::new("Match on all three devices",j::hex_string(&fingerprint),CRITICAL),
            Field::new("Group rule","Any two shares can sign. One share cannot recover the group. Confirm this fingerprint matches on every participant device.",CRITICAL),
            Field::new("Exact participant keys",serde_json::to_string(&wire::list(&members)).expect("strings serialize"),DETAIL)];
        self.prepare(Action::Setup { session, members }, fields)
    }
    fn sign_request(&mut self, value: &Value, now: u64) -> Result<(), Error> {
        j::exact_keys(value, &["type", "id", "session", "members", "event"], &[])?;
        self.signer.cancel();
        self.signing = None;
        self.received.clear();
        let id = j::string(&value["id"])?;
        if id.is_empty() || id.len() > 128 {
            return Err(Error::Input);
        }
        let session = j::hex(j::string(&value["session"])?)?;
        let members = wire::members(&value["members"], 2)?;
        let own = self.identity.as_ref().ok_or(Error::Locked)?.public_key();
        member_index(&members, &own)?;
        let mut ids = Vec::with_capacity(2);
        for key in &members {
            ids.push(member_id(member_index(&self.members, key)?));
        }
        let peer = *members
            .iter()
            .find(|key| *key != &own)
            .ok_or(Error::Identity)?;
        let text = j::string(&value["event"])?;
        let participant = self.signer.selected().ok_or(Error::Locked)?;
        let event = Event::parse(text.as_bytes(), participant.group().public_key())?;
        let intent = crypto(RoundIntent::for_event(
            participant.group(),
            &event,
            session,
            &ids,
        ))?;
        let mut fields = event.review()?;
        fields.push(Field::new(
            "Signing group",
            j::hex_string(&self.group),
            CRITICAL,
        ));
        fields.push(Field::new(
            "Together with",
            format!("Member {} of 3", member_index(&self.members, &peer)? + 1),
            CRITICAL,
        ));
        fields.push(Field::new(
            "Cosigner transport key",
            j::hex_string(&peer),
            DETAIL,
        ));
        self.deadline = now.checked_add(SIGN_MS).ok_or(Error::Stale)?;
        self.prepare(
            Action::Sign {
                id: id.into(),
                text: text.into(),
                intent: Box::new(intent),
                peer,
                confirmation: event.confirmation()?,
            },
            fields,
        )
    }
    pub fn public_request(&mut self, input: &[u8], now: u64) -> Result<(), Error> {
        self.cancel();
        self.clock(now)?;
        let value = j::parse(input)?;
        j::exact_keys(&value, &["id", "method", "params"], &[])?;
        let id = j::string(&value["id"])?;
        if id.is_empty() || id.len() > 128 {
            return Err(Error::Input);
        }
        if j::string(&value["method"])? != "get_public_key"
            || value["params"].as_array().is_none_or(|p| !p.is_empty())
        {
            return Err(Error::Unsupported);
        }
        let key = j::hex_string(self.public_key()?);
        self.deadline = now.checked_add(SIGN_MS).ok_or(Error::Stale)?;
        self.prepare(
            Action::PublicKey(id.into()),
            vec![
                Field::new("Action", "Share group identity", CRITICAL),
                Field::new("Group public key", key, CRITICAL),
            ],
        )
    }
    pub fn approve(
        &mut self,
        generation: u64,
        partial: bool,
        entropy: &mut [u8],
        now: u64,
    ) -> Result<(), Error> {
        let result = (|| {
            let mut review = self.review.take().ok_or(Error::Stale)?;
            if self.tick(now)? || generation != self.generation {
                return Err(Error::Stale);
            }
            for (field, seen) in review.fields.iter().zip(&review.seen) {
                if !seen && (field.flags & CRITICAL != 0 || field.flags & PROSE != 0 && !partial) {
                    return Err(Error::Review);
                }
            }
            review.fields.clear();
            review.seen.clear();
            let mut random = self.random(entropy)?;
            self.outputs.clear();
            match review.action {
                Action::Setup { session, members } => {
                    self.begin_setup(session, members, &mut random)
                }
                Action::Restore(recovery) => {
                    self.install(recovery.participant, recovery.identity, recovery.members);
                    self.ready_output()
                }
                Action::PublicKey(id) => {
                    self.outputs.push(
                        json!({"id":id,"result":j::hex_string(self.public_key()?)}).to_string(),
                    );
                    self.finished = true;
                    Ok(())
                }
                Action::Sign {
                    id,
                    text,
                    intent,
                    peer,
                    ..
                } => {
                    let event = Event::parse(text.as_bytes(), self.public_key()?)?;
                    let retained = Event::parse(text.as_bytes(), self.public_key()?)?;
                    let mut authority = LocalApproval {
                        now,
                        intent: *intent.binding(),
                        round: None,
                    };
                    let own = crypto(self.signer.begin(
                        event,
                        (*intent).clone(),
                        self.deadline,
                        &mut authority,
                        &mut random,
                    ))?;
                    let payload = json!({"intent":j::hex_string(&own.intent),"points":j::hex_string(&own.points)});
                    self.outputs.push(wire::seal(
                        self.identity.as_ref().ok_or(Error::Locked)?,
                        &peer,
                        "commitment",
                        &self.group,
                        intent.session(),
                        &payload,
                        &mut random,
                    )?);
                    self.signing = Some(Signing {
                        id,
                        event: retained,
                        intent: *intent,
                        peer,
                        own,
                        round: None,
                        share: None,
                    });
                    Ok(())
                }
            }
        })();
        entropy.zeroize();
        if result.is_err() {
            self.cancel();
        }
        result
    }
    fn begin_setup(
        &mut self,
        session: [u8; 32],
        members: Vec<[u8; 32]>,
        random: &mut wire::Random,
    ) -> Result<(), Error> {
        let identity = self.identity.as_ref().ok_or(Error::Locked)?;
        let own = member_id(member_index(&members, &identity.public_key())?);
        let ids: Vec<_> = (0..3).map(member_id).collect();
        let fingerprint = setup_fingerprint(&session, &members);
        let (owner, broadcast) = crypto(dkg::RoundOne::start(2, &ids, own, fingerprint, random))?;
        let payload = broadcast_payload(&broadcast)?;
        for peer in members.iter().filter(|key| *key != &identity.public_key()) {
            self.outputs.push(wire::seal(
                identity,
                peer,
                "setup1",
                &fingerprint,
                &session,
                &payload,
                random,
            )?);
        }
        self.members = members;
        self.setup = Some(Setup {
            session,
            fingerprint,
            binding: broadcast.ceremony,
            stage: SetupStage::First {
                owner,
                own: Box::new(broadcast),
                incoming: Vec::new(),
            },
        });
        Ok(())
    }
    fn setup_peer(&mut self, value: &Value, random: &mut wire::Random) -> Result<(), Error> {
        let mut setup = self.setup.take().ok_or(Error::Stale)?;
        let identity = self.identity.as_ref().ok_or(Error::Locked)?;
        let phase = match setup.stage {
            SetupStage::First { .. } => "setup1",
            SetupStage::Second { .. } => "setup2",
        };
        let (peer, payload) = wire::open(
            identity,
            value,
            phase,
            &setup.fingerprint,
            &setup.session,
            &self.members,
        )?;
        let sender = member_id(member_index(&self.members, &peer)?);
        let recipient = member_id(member_index(&self.members, &identity.public_key())?);
        setup.stage = match setup.stage {
            SetupStage::First {
                owner,
                own,
                mut incoming,
            } => {
                if incoming.iter().any(|p| p.sender == sender) {
                    return Err(Error::Input);
                }
                incoming.push(decode_broadcast(&payload, setup.binding, sender)?);
                if incoming.len() < 2 {
                    SetupStage::First {
                        owner,
                        own,
                        incoming,
                    }
                } else {
                    let transcript = transcript(&own, &incoming)?;
                    let (owner, deliveries) = crypto(owner.advance(&incoming))?;
                    for delivery in deliveries {
                        let index = (0..3)
                            .find(|&i| member_id(i) == delivery.recipient)
                            .ok_or(Error::Identity)?;
                        let secret = Zeroizing::new(delivery.package.signing_share().serialize());
                        let payload = json!({"transcript":j::hex_string(&transcript),"share":j::hex_string(&secret)});
                        self.outputs.push(wire::seal(
                            identity,
                            &self.members[index],
                            "setup2",
                            &setup.fingerprint,
                            &setup.session,
                            &payload,
                            random,
                        )?);
                    }
                    SetupStage::Second {
                        owner,
                        transcript,
                        incoming: Vec::new(),
                    }
                }
            }
            SetupStage::Second {
                owner,
                transcript,
                mut incoming,
            } => {
                j::exact_keys(&payload, &["transcript", "share"], &[])?;
                if j::hex::<32>(j::string(&payload["transcript"])?)? != transcript
                    || incoming.iter().any(|p| p.sender == sender)
                {
                    return Err(Error::Input);
                }
                let share = Zeroizing::new(j::hex::<32>(j::string(&payload["share"])?)?);
                let package = frost::keys::dkg::round2::Package::new(
                    frost::keys::SigningShare::deserialize(share.as_ref())
                        .map_err(|_| Error::Crypto)?,
                );
                incoming.push(dkg::Delivery {
                    ceremony: setup.binding,
                    sender,
                    recipient,
                    package,
                });
                if incoming.len() < 2 {
                    SetupStage::Second {
                        owner,
                        transcript,
                        incoming,
                    }
                } else {
                    let participant = crypto(owner.finish(&incoming))?;
                    self.group = group_fingerprint(&participant, &self.members);
                    self.signer.select(participant);
                    self.deadline = 0;
                    self.ready_output()?;
                    return Ok(());
                }
            }
        };
        self.setup = Some(setup);
        Ok(())
    }
    fn sign_peer(
        &mut self,
        value: &Value,
        random: &mut wire::Random,
        now: u64,
    ) -> Result<(), Error> {
        let mut signing = self.signing.take().ok_or(Error::Stale)?;
        let identity = self.identity.as_ref().ok_or(Error::Locked)?;
        let phase = if signing.round.is_none() {
            "commitment"
        } else {
            "share"
        };
        let (peer, payload) = wire::open(
            identity,
            value,
            phase,
            &self.group,
            signing.intent.session(),
            &[signing.peer],
        )?;
        let participant = member_id(member_index(&self.members, &peer)?);
        if phase == "commitment" {
            j::exact_keys(&payload, &["intent", "points"], &[])?;
            let incoming = Commitment {
                intent: j::hex(j::string(&payload["intent"])?)?,
                participant,
                points: j::hex(j::string(&payload["points"])?)?,
            };
            let round = crypto(SigningRound::new(
                &signing.intent,
                &[signing.own.clone(), incoming],
            ))?;
            let mut authority = LocalApproval {
                now,
                intent: *signing.intent.binding(),
                round: Some(*round.binding()),
            };
            let share = crypto(self.signer.sign(&round, &mut authority))?;
            let payload = json!({"intent":j::hex_string(&share.intent),"round":j::hex_string(&share.round),"share":j::hex_string(&share.scalar)});
            self.outputs.push(wire::seal(
                identity,
                &peer,
                "share",
                &self.group,
                signing.intent.session(),
                &payload,
                random,
            )?);
            signing.round = Some(round);
            signing.share = Some(share);
            self.signing = Some(signing);
        } else {
            j::exact_keys(&payload, &["intent", "round", "share"], &[])?;
            let incoming = SignatureShare {
                intent: j::hex(j::string(&payload["intent"])?)?,
                round: j::hex(j::string(&payload["round"])?)?,
                participant,
                scalar: j::hex(j::string(&payload["share"])?)?,
            };
            let round = signing.round.ok_or(Error::Stale)?;
            let signature = crypto(round.aggregate(
                self.signer.selected().ok_or(Error::Locked)?.group(),
                &[signing.share.ok_or(Error::Stale)?, incoming],
            ))?;
            let event = signing.event.signed_json(&signature)?;
            let response = json!({"id":signing.id,"result":event}).to_string();
            if response.len() > nsealr_core::MAX_MESSAGE {
                return Err(Error::Bounds);
            }
            self.outputs.push(response);
            self.finished = true;
        }
        Ok(())
    }
    fn install(&mut self, participant: Participant, identity: Identity, members: Vec<[u8; 32]>) {
        self.group = group_fingerprint(&participant, &members);
        self.signer.select(participant);
        self.identity = Some(identity);
        self.members = members;
        self.deadline = 0;
    }
    fn ready_output(&mut self) -> Result<(), Error> {
        let participant = self.signer.selected().ok_or(Error::Locked)?;
        let index = member_index(
            &self.members,
            &self.identity.as_ref().ok_or(Error::Locked)?.public_key(),
        )?;
        self.outputs.push(json!({"type":"nsealr_group","group":j::hex_string(&self.group),"pubkey":j::hex_string(participant.group().public_key()),"members":wire::list(&self.members),"participant":index+1}).to_string());
        Ok(())
    }
    pub fn backup(&self) -> Result<Zeroizing<String>, Error> {
        if self.setup.is_some() || self.signing.is_some() || self.review.is_some() {
            return Err(Error::Stale);
        }
        let participant = self.signer.selected().ok_or(Error::Locked)?;
        let share = crypto(participant.backup())?;
        let mut nsec = Zeroizing::new([0; 83]);
        let n = self
            .identity
            .as_ref()
            .ok_or(Error::Locked)?
            .backup(1, &mut *nsec)?;
        let mut value = json!({"type":"nsealr_share","group":j::hex_string(&self.group),"descriptor":j::hex_string(participant.group().identity()),"members":wire::list(&self.members),"transport":core::str::from_utf8(&nsec[..n]).map_err(|_|Error::Input)?,"share":j::hex_string(&share)});
        value["checksum"] = j::hex_string(&sha256(value.to_string().as_bytes())).into();
        let backup = Zeroizing::new(value.to_string());
        if backup.len() > MAX_BACKUP {
            return Err(Error::Bounds);
        }
        Ok(backup)
    }
    /// Local secret scan only. A check preserves the selected share; a restore
    /// clears it before collecting. Neither flow passes through peer routing.
    pub fn backup_frame(&mut self, frame: &mut [u8], check: bool, now: u64) -> Result<bool, Error> {
        let result = (|| {
            if self.backup_scan.is_some_and(|mode| mode != check) {
                return Err(Error::Stale);
            }
            if self.backup_scan.is_none() {
                if check {
                    self.cancel();
                    self.public_key()?;
                } else {
                    self.lock();
                }
                self.clock(now)?;
                self.deadline = now.checked_add(SETUP_MS).ok_or(Error::Stale)?;
                self.backup_scan = Some(check);
            }
            if self.tick(now)? {
                return Err(Error::Stale);
            }
            let Some(mut message) = self.collector.accept_limited(frame, MAX_BACKUP)? else {
                return Ok(false);
            };
            self.backup_scan = None;
            self.deadline = 0;
            if check {
                let expected = self.backup()?;
                // Compare digests so timing cannot disclose a matching secret prefix.
                if sha256(&message) != sha256(expected.as_bytes()) {
                    return Err(Error::Crypto);
                }
            } else {
                self.import(&mut message, now)?;
            }
            Ok(true)
        })();
        frame.zeroize();
        if result.is_err() {
            self.cancel();
        }
        result
    }
    pub fn import(&mut self, input: &mut [u8], now: u64) -> Result<(), Error> {
        self.lock();
        let result = (|| {
            self.clock(now)?;
            if input.len() > MAX_BACKUP {
                return Err(Error::Bounds);
            }
            let mut value = j::parse(input)?;
            j::exact_keys(
                &value,
                &[
                    "type",
                    "group",
                    "descriptor",
                    "members",
                    "transport",
                    "share",
                    "checksum",
                ],
                &[],
            )?;
            if j::string(&value["type"])? != "nsealr_share" {
                return Err(Error::Input);
            }
            let checksum = j::hex::<32>(j::string(&value["checksum"])?)?;
            value
                .as_object_mut()
                .ok_or(Error::Input)?
                .remove("checksum");
            if sha256(value.to_string().as_bytes()) != checksum {
                return Err(Error::Crypto);
            }
            let members = wire::members(&value["members"], 3)?;
            let identity = Identity::nsec(j::string(&value["transport"])?)?;
            let index = member_index(&members, &identity.public_key())?;
            let descriptor = j::hex(j::string(&value["descriptor"])?)?;
            let bytes = wire::decode(j::string(&value["share"])?, crate::MAX_BACKUP_BYTES)?;
            let participant = crypto(Participant::restore(&bytes, &descriptor, &member_id(index)))?;
            if participant.group().threshold() != 2
                || participant.group().participant_ids().count() != 3
                || !participant
                    .group()
                    .participant_ids()
                    .eq((0..3).map(member_id))
            {
                return Err(Error::Unsupported);
            }
            let group = group_fingerprint(&participant, &members);
            if j::hex::<32>(j::string(&value["group"])?)? != group {
                return Err(Error::Crypto);
            }
            let fields=vec![Field::new("Action","Restore one group share",CRITICAL),Field::new("Group public key",j::hex_string(participant.group().public_key()),CRITICAL),Field::new("Verify recorded group fingerprint",j::hex_string(&group),CRITICAL),Field::new("This share",format!("Member {} of 3; any two can sign",index+1),CRITICAL),Field::new("Recovery check","Compare the fingerprint with your independently kept group record. A checksum detects damage, not a replaced backup.",CRITICAL)];
            self.deadline = now.checked_add(SETUP_MS).ok_or(Error::Stale)?;
            self.prepare(
                Action::Restore(Box::new(Recovery {
                    participant,
                    identity,
                    members,
                })),
                fields,
            )
        })();
        input.zeroize();
        if result.is_err() {
            self.lock();
        }
        result
    }
}

struct LocalApproval {
    now: u64,
    intent: [u8; 32],
    round: Option<[u8; 32]>,
}
impl ReviewAuthority for LocalApproval {
    fn now_ms(&mut self) -> Option<u64> {
        Some(self.now)
    }
    fn review(&mut self, intent: ReviewIntent<'_>) -> Result<ReviewApproval, crate::Error> {
        if intent.binding.intent.binding() != &self.intent {
            return Err(crate::Error::Review);
        }
        Ok(intent.approve())
    }
    fn check_live(&mut self, binding: &ReviewBinding) -> Result<(), crate::Error> {
        if binding.intent.binding() != &self.intent || self.now >= binding.deadline_ms {
            return Err(crate::Error::Review);
        }
        Ok(())
    }
    fn admit_round(
        &mut self,
        binding: &ReviewBinding,
        round: &SigningRound,
    ) -> Result<(), crate::Error> {
        self.check_live(binding)?;
        if self.round.as_ref() != Some(round.binding()) {
            return Err(crate::Error::Binding);
        }
        Ok(())
    }
}
fn broadcast_payload(message: &dkg::Broadcast) -> Result<Value, Error> {
    Ok(
        json!({"commitment":j::hex_string(&message.package.commitment().serialize_whole().map_err(|_|Error::Crypto)?),"proof":j::hex_string(&message.package.proof_of_knowledge().serialize().map_err(|_|Error::Crypto)?)}),
    )
}
fn decode_broadcast(
    value: &Value,
    ceremony: [u8; 32],
    sender: ParticipantId,
) -> Result<dkg::Broadcast, Error> {
    j::exact_keys(value, &["commitment", "proof"], &[])?;
    let commitment = j::hex::<66>(j::string(&value["commitment"])?)?;
    let proof = j::hex::<64>(j::string(&value["proof"])?)?;
    let commitment =
        frost::keys::VerifiableSecretSharingCommitment::deserialize(commitment.chunks_exact(33))
            .map_err(|_| Error::Crypto)?;
    let proof = frost::Signature::deserialize(&proof).map_err(|_| Error::Crypto)?;
    Ok(dkg::Broadcast {
        ceremony,
        sender,
        package: frost::keys::dkg::round1::Package::new(commitment, proof),
    })
}
fn transcript(own: &dkg::Broadcast, incoming: &[dkg::Broadcast]) -> Result<[u8; 32], Error> {
    let mut all: Vec<_> = incoming.iter().chain(core::iter::once(own)).collect();
    all.sort_by_key(|b| b.sender);
    let rows: Vec<_> = all
        .iter()
        .map(|b| Ok(json!([j::hex_string(&b.sender), broadcast_payload(b)?])))
        .collect::<Result<_, Error>>()?;
    Ok(sha256(
        &serde_json::to_vec(&(j::hex_string(&own.ceremony), rows)).expect("values serialize"),
    ))
}
