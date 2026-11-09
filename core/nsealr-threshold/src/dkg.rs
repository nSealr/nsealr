//! Bounded, consuming upstream DKG owners. The firmware must authenticate the
//! ceremony/participants and provide confidential authenticated round-two
//! delivery. These in-memory packages are not an optical encoding or peer auth.
use super::*;

pub struct Broadcast {
    pub ceremony: [u8; 32],
    pub sender: ParticipantId,
    pub package: frost::keys::dkg::round1::Package,
}
/// Secret participant-to-participant delivery; never broadcast or log.
pub struct Delivery {
    pub ceremony: [u8; 32],
    pub sender: ParticipantId,
    pub recipient: ParticipantId,
    pub package: frost::keys::dkg::round2::Package,
}
struct Context {
    binding: [u8; 32],
    participant: ParticipantId,
    participants: Vec<ParticipantId>,
    threshold: u16,
}
impl Context {
    fn broadcasts(
        &self,
        incoming: &[Broadcast],
    ) -> Result<BTreeMap<frost::Identifier, frost::keys::dkg::round1::Package>, Error> {
        if incoming.len() + 1 != self.participants.len() {
            return Err(Error::Bounds);
        }
        let mut packages = BTreeMap::new();
        for message in incoming {
            if message.ceremony != self.binding
                || message.sender == self.participant
                || !self.participants.contains(&message.sender)
                || message.package.commitment().coefficients().len() != self.threshold as usize
            {
                return Err(Error::Binding);
            }
            if packages
                .insert(id(&message.sender)?, message.package.clone())
                .is_some()
            {
                return Err(Error::Participant);
            }
        }
        Ok(packages)
    }
}
pub struct RoundOne {
    context: Context,
    secret: frost::keys::dkg::round1::SecretPackage,
}
pub struct RoundTwo {
    context: Context,
    secret: frost::keys::dkg::round2::SecretPackage,
    broadcasts: BTreeMap<frost::Identifier, frost::keys::dkg::round1::Package>,
}
impl RoundOne {
    pub fn start(
        threshold: u16,
        participants: &[ParticipantId],
        participant: ParticipantId,
        ceremony: [u8; 32],
        source: &mut impl EntropySource,
    ) -> Result<(Self, Broadcast), Error> {
        dimensions(threshold, participants.len())?;
        let mut participants = participants.to_vec();
        participants.sort();
        if !participants.contains(&participant) {
            return Err(Error::Participant);
        }
        let mut h = Sha256::new();
        h.update(hash(&[
            SCHEME,
            b"dkg-v1",
            &ceremony,
            &threshold.to_be_bytes(),
        ]));
        for (index, member) in participants.iter().enumerate() {
            id(member)?;
            if index > 0 && member == &participants[index - 1] {
                return Err(Error::Participant);
            }
            h.update(member);
        }
        let binding = h.finalize().into();
        let context = Context {
            binding,
            participant,
            participants,
            threshold,
        };
        let mut rng = rng(source)?;
        let (secret, package) = frost::keys::dkg::part1(
            id(&participant)?,
            context.participants.len() as u16,
            threshold,
            &mut rng,
        )
        .map_err(|_| Error::Crypto)?;
        Ok((
            Self { context, secret },
            Broadcast {
                ceremony: binding,
                sender: participant,
                package,
            },
        ))
    }

    /// Consumes round one even on failure; it cannot be retried on changed input.
    pub fn advance(self, incoming: &[Broadcast]) -> Result<(RoundTwo, Vec<Delivery>), Error> {
        let broadcasts = self.context.broadcasts(incoming)?;
        let (secret, packages) =
            frost::keys::dkg::part2(self.secret, &broadcasts).map_err(|_| Error::Crypto)?;
        let deliveries = packages
            .into_iter()
            .map(|(recipient, package)| {
                Ok(Delivery {
                    ceremony: self.context.binding,
                    sender: self.context.participant,
                    recipient: fixed(&recipient.serialize())?,
                    package,
                })
            })
            .collect::<Result<Vec<_>, Error>>()?;
        Ok((
            RoundTwo {
                context: self.context,
                secret,
                broadcasts,
            },
            deliveries,
        ))
    }
}
impl RoundTwo {
    /// Uses the exact retained round-one transcript; no replacement is admitted.
    /// The exact upstream post-DKG group key (already tweaked) is the identity.
    pub fn finish(self, incoming: &[Delivery]) -> Result<Participant, Error> {
        if incoming.len() + 1 != self.context.participants.len() {
            return Err(Error::Bounds);
        }
        let mut packages = BTreeMap::new();
        for message in incoming {
            if message.ceremony != self.context.binding
                || message.sender == self.context.participant
                || message.recipient != self.context.participant
                || !self.context.participants.contains(&message.sender)
            {
                return Err(Error::Binding);
            }
            if packages
                .insert(id(&message.sender)?, message.package.clone())
                .is_some()
            {
                return Err(Error::Participant);
            }
        }
        let (key, public) = frost::keys::dkg::part3(&self.secret, &self.broadcasts, &packages)
            .map_err(|_| Error::Crypto)?;
        Participant::new(key, Group::new(public)?)
    }
}
