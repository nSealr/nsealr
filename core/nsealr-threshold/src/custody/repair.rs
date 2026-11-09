//! Lost-share repair using the pinned ZF RTS, not share revocation.
//! Request: nsealr_repair {session,group,descriptor,members:[{id,key};3],
//! participant:1..3,replacement:key}. All three approve the same fingerprint.
//! Two repair_delta packets go between helpers; two repair_sigma packets go
//! to the replacement; two repair_ready packets acknowledge its verified share.
//! Each phase uses the existing authenticated confidential peer envelope, with
//! group=ceremony fingerprint. The companion never receives a bare contribution.
//! Completion emits a new public record. Keep old backups until all records agree.
use super::*;
use crate::{id, Group};
use frost::keys::repairable::{self, Delta, Sigma};

pub(super) struct Plan {
    session: [u8; 32],
    binding: [u8; 32],
    group: Group,
    members: Vec<[u8; 32]>,
    target: usize,
    replacement: [u8; 32],
}
impl Plan {
    fn roster(&self) -> Vec<[u8; 32]> {
        let mut keys = self.members.clone();
        keys[self.target] = self.replacement;
        keys
    }
    fn helpers(&self) -> impl Iterator<Item = usize> + '_ {
        (0..3).filter(|i| *i != self.target)
    }
}
enum Stage {
    Helper {
        delta: Zeroizing<Delta>,
        peer: usize,
    },
    Recipient(Vec<(usize, Zeroizing<Sigma>)>),
    AwaitingReady,
}
pub(super) struct Exchange {
    plan: Plan,
    stage: Stage,
}
impl Exchange {
    pub(super) fn progress(&self) -> u32 {
        match &self.stage {
            Stage::Helper { .. } => 0,
            Stage::Recipient(incoming) => incoming.len() as u32,
            Stage::AwaitingReady => 1,
        }
    }
}

impl Custody {
    pub(super) fn repair_request(&mut self, value: &Value, now: u64) -> Result<(), Error> {
        if self.setup.is_some() || self.signing.is_some() || self.repair.is_some() {
            return Err(Error::Stale);
        }
        j::exact_keys(
            value,
            &[
                "type",
                "session",
                "group",
                "descriptor",
                "members",
                "participant",
                "replacement",
            ],
            &[],
        )?;
        let target = value["participant"]
            .as_u64()
            .filter(|n| (1..=3).contains(n))
            .ok_or(Error::Input)? as usize
            - 1;
        let members = wire::read_roster(&value["members"])?;
        let descriptor = wire::decode(j::string(&value["descriptor"])?, 35 + 65 * 3)?;
        let group = crypto(Group::from_descriptor(&descriptor))?;
        if group.threshold() != 2 || !group.participant_ids().eq((0..3).map(member_id)) {
            return Err(Error::Identity);
        }
        let old_group = roster_fingerprint(&group, &members);
        if j::hex::<32>(j::string(&value["group"])?)? != old_group {
            return Err(Error::Identity);
        }
        let replacement = wire::key(&value["replacement"])?;
        if members.contains(&replacement) {
            return Err(Error::Identity);
        }
        let own = self.identity.as_ref().ok_or(Error::Locked)?.public_key();
        if let Some(participant) = self.signer.selected() {
            if participant.group().descriptor() != group.descriptor()
                || self.members != members
                || own == members[target]
                || self.group != old_group
            {
                return Err(Error::Identity);
            }
            member_index(&members, &own)?;
        } else if own != replacement {
            return Err(Error::Identity);
        }
        let session = j::hex(j::string(&value["session"])?)?;
        let binding = sha256(
            &serde_json::to_vec(&(
                "nSealr 2-of-3 repair",
                j::hex_string(&session),
                j::hex_string(&old_group),
                target + 1,
                j::hex_string(&replacement),
            ))
            .expect("values serialize"),
        );
        let fields = vec![
            Field::new("Action", "Repair one lost group share", CRITICAL),
            Field::new("Group public key", j::hex_string(group.public_key()), CRITICAL),
            Field::new("Lost member", format!("Member {} of 3", target + 1), CRITICAL),
            Field::new("Replacement device", j::hex_string(&replacement), CRITICAL),
            Field::new("Match on all three devices", j::hex_string(&binding), CRITICAL),
            Field::new("Recovery effect", "Keep the same npub. Old copies of the lost share remain valid. This does not revoke a stolen share.", CRITICAL),
            Field::new("Backups", "Keep old backups until all three devices show the new group record; then save new backups.", CRITICAL),
            Field::new("Exact participant keys", serde_json::to_string(&wire::roster(&members)).expect("values serialize"), DETAIL),
        ];
        self.received.clear();
        self.deadline = now.checked_add(SETUP_MS).ok_or(Error::Stale)?;
        self.prepare(
            Action::Repair(Box::new(Plan {
                session,
                binding,
                group,
                members,
                target,
                replacement,
            })),
            fields,
        )
    }
    pub(super) fn begin_repair(
        &mut self,
        plan: Plan,
        random: &mut wire::Random,
    ) -> Result<(), Error> {
        let identity = self.identity.as_ref().ok_or(Error::Locked)?;
        let stage = if let Some(participant) = self.signer.selected() {
            let own = member_index(&plan.members, &identity.public_key())?;
            let helpers: Vec<_> = plan
                .helpers()
                .map(|i| id(&member_id(i)))
                .collect::<Result<_, _>>()
                .map_err(|_| Error::Identity)?;
            let mut rng = crypto(crate::rng(random))?;
            let mut deltas = crypto(
                repairable::repair_share_part1::<frost::Secp256K1Sha256TR, _>(
                    &helpers,
                    &participant.key,
                    &mut rng,
                    crypto(id(&member_id(plan.target)))?,
                ),
            )?;
            let delta = Zeroizing::new(
                deltas
                    .remove(&crypto(id(&member_id(own)))?)
                    .ok_or(Error::Crypto)?,
            );
            let peer = plan.helpers().find(|i| *i != own).ok_or(Error::Identity)?;
            let other = Zeroizing::new(
                deltas
                    .remove(&crypto(id(&member_id(peer)))?)
                    .ok_or(Error::Crypto)?,
            );
            let encoded = Zeroizing::new(other.serialize());
            self.outputs.push(wire::seal(
                identity,
                &plan.members[peer],
                "repair_delta",
                &plan.binding,
                &plan.session,
                &json!({"delta":j::hex_string(&encoded)}),
                random,
            )?);
            Stage::Helper { delta, peer }
        } else {
            Stage::Recipient(Vec::with_capacity(2))
        };
        self.repair = Some(Exchange { plan, stage });
        Ok(())
    }
    pub(super) fn repair_peer(
        &mut self,
        value: &Value,
        random: &mut wire::Random,
    ) -> Result<(), Error> {
        let Exchange { plan, stage } = self.repair.take().ok_or(Error::Stale)?;
        let phase = match &stage {
            Stage::Helper { .. } => "repair_delta",
            Stage::Recipient(_) => "repair_sigma",
            Stage::AwaitingReady => "repair_ready",
        };
        let identity = self.identity.as_ref().ok_or(Error::Locked)?;
        let (sender, payload) = wire::open(
            identity,
            value,
            phase,
            &plan.binding,
            &plan.session,
            &plan.roster(),
        )?;
        let next = match stage {
            Stage::Helper { delta, peer } => {
                if sender != plan.members[peer] {
                    return Err(Error::Identity);
                }
                j::exact_keys(&payload, &["delta"], &[])?;
                let bytes = Zeroizing::new(j::hex::<32>(j::string(&payload["delta"])?)?);
                let incoming = Zeroizing::new(crypto(Delta::deserialize(bytes.as_ref()))?);
                let deltas = Zeroizing::new(vec![*delta, *incoming]);
                let sigma = Zeroizing::new(repairable::repair_share_part2(&deltas));
                let encoded = Zeroizing::new(sigma.serialize());
                self.outputs.push(wire::seal(
                    identity,
                    &plan.replacement,
                    "repair_sigma",
                    &plan.binding,
                    &plan.session,
                    &json!({"sigma":j::hex_string(&encoded)}),
                    random,
                )?);
                Stage::AwaitingReady
            }
            Stage::Recipient(mut sigmas) => {
                let index = member_index(&plan.members, &sender)?;
                if index == plan.target || sigmas.iter().any(|(i, _)| *i == index) {
                    return Err(Error::Identity);
                }
                j::exact_keys(&payload, &["sigma"], &[])?;
                let bytes = Zeroizing::new(j::hex::<32>(j::string(&payload["sigma"])?)?);
                sigmas.push((
                    index,
                    Zeroizing::new(crypto(Sigma::deserialize(bytes.as_ref()))?),
                ));
                if sigmas.len() == 2 {
                    let values = Zeroizing::new(vec![*sigmas[0].1, *sigmas[1].1]);
                    let key = crypto(repairable::repair_share_part3(
                        &values,
                        crypto(id(&member_id(plan.target)))?,
                        &plan.group.public,
                    ))?;
                    // RTS sums inputs but does not validate the resulting share.
                    let participant = crypto(Participant::new(key, plan.group.clone()))?;
                    let members = plan.roster();
                    let group = roster_fingerprint(&plan.group, &members);
                    for helper in plan.helpers() {
                        self.outputs.push(wire::seal(
                            identity,
                            &plan.members[helper],
                            "repair_ready",
                            &plan.binding,
                            &plan.session,
                            &json!({"group":j::hex_string(&group)}),
                            random,
                        )?);
                    }
                    let identity = self.identity.take().ok_or(Error::Locked)?;
                    self.install(participant, identity, members);
                    self.ready_output()?;
                    return Ok(());
                }
                Stage::Recipient(sigmas)
            }
            Stage::AwaitingReady => {
                j::exact_keys(&payload, &["group"], &[])?;
                let members = plan.roster();
                let group = roster_fingerprint(&plan.group, &members);
                if sender != plan.replacement
                    || j::hex::<32>(j::string(&payload["group"])?)? != group
                {
                    return Err(Error::Identity);
                }
                self.members = members;
                self.group = group;
                self.deadline = 0;
                self.ready_output()?;
                return Ok(());
            }
        };
        self.repair = Some(Exchange { plan, stage: next });
        Ok(())
    }
}
