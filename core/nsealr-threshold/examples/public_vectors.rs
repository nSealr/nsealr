//! Public deterministic test fixtures. This authority is not a device adapter.
use nsealr_core::event::Event;
use nsealr_threshold::*;
use serde_json::{json, Value};
use zeroize::Zeroizing;
struct FixtureEntropy(u8);
impl EntropySource for FixtureEntropy {
    fn fill(&mut self, seed: &mut [u8; 32]) -> Result<usize, Error> {
        seed.fill(self.0);
        self.0 = self.0.wrapping_add(1);
        Ok(32)
    }
}
struct FixtureReview;
impl ReviewAuthority for FixtureReview {
    fn now_ms(&mut self) -> Option<u64> {
        Some(1)
    }
    fn review(&mut self, i: ReviewIntent<'_>) -> Result<ReviewApproval, Error> {
        Ok(i.approve())
    }
    fn check_live(&mut self, _: &ReviewBinding) -> Result<(), Error> {
        Ok(())
    }
    fn admit_round(&mut self, _: &ReviewBinding, _: &SigningRound) -> Result<(), Error> {
        Ok(())
    }
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn dkg(threshold: u16, count: u8) -> Vec<Participant> {
    let ids: Vec<_> = (1..=count)
        .map(|n| {
            let mut id = [0; 32];
            id[31] = n;
            id
        })
        .collect();
    let mut broadcasts = Vec::new();
    let mut one = Vec::new();
    for (i, participant) in ids.iter().enumerate() {
        let (o, b) = dkg::RoundOne::start(
            threshold,
            &ids,
            *participant,
            [44; 32],
            &mut FixtureEntropy(90 + i as u8),
        )
        .unwrap();
        one.push(o);
        broadcasts.push(b);
    }
    let mut two = Vec::new();
    let mut deliveries = Vec::new();
    for (o, participant) in one.into_iter().zip(&ids) {
        let incoming: Vec<_> = broadcasts
            .iter()
            .filter(|b| &b.sender != participant)
            .map(|b| dkg::Broadcast {
                ceremony: b.ceremony,
                sender: b.sender,
                package: b.package.clone(),
            })
            .collect();
        let (o, d) = o.advance(&incoming).unwrap();
        two.push(o);
        deliveries.extend(d);
    }
    two.into_iter()
        .zip(&ids)
        .map(|(o, participant)| {
            let incoming: Vec<_> = deliveries
                .iter()
                .filter(|d| &d.recipient == participant)
                .map(|d| dkg::Delivery {
                    ceremony: d.ceremony,
                    sender: d.sender,
                    recipient: d.recipient,
                    package: d.package.clone(),
                })
                .collect();
            o.finish(&incoming).unwrap()
        })
        .collect()
}
fn signed(label: &str, participants: Vec<Participant>, source: Option<[u8; 32]>) -> Value {
    let group = participants[0].group().clone();
    let threshold = group.threshold() as usize;
    let ids: Vec<_> = participants
        .iter()
        .rev()
        .take(threshold)
        .map(Participant::identifier)
        .collect();
    let template = json!({"created_at":1700000000,"kind":1,"tags":[["p","79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"],["t","threshold"]],"content":"Nostr threshold café\nfull \"event\" intent"});
    let mut template = template;
    template["pubkey"] = json!(hex(group.public_key()));
    let bytes = serde_json::to_vec(&template).unwrap();
    let event = || Event::parse(&bytes, group.public_key()).unwrap();
    let intent = RoundIntent::for_event(&group, &event(), [55; 32], &ids).unwrap();
    let mut signers: Vec<_> = participants
        .into_iter()
        .rev()
        .take(threshold)
        .map(|p| {
            let backup = p.backup().unwrap();
            let p = Participant::restore(&backup, group.identity(), &p.identifier()).unwrap();
            let mut s = Signer::new();
            s.select(p);
            s
        })
        .collect();
    let commitments: Vec<_> = signers
        .iter_mut()
        .enumerate()
        .map(|(i, s)| {
            s.begin(
                event(),
                intent.clone(),
                100,
                &mut FixtureReview,
                &mut FixtureEntropy(150 + i as u8),
            )
            .unwrap()
        })
        .collect();
    let round = SigningRound::new(&intent, &commitments).unwrap();
    let shares: Vec<_> = signers
        .iter_mut()
        .map(|s| s.sign(&round, &mut FixtureReview).unwrap())
        .collect();
    let signature = round.aggregate(&group, &shares).unwrap();
    let mut event = template;
    event["pubkey"] = json!(hex(group.public_key()));
    event["id"] = json!(hex(intent.event_id()));
    event["sig"] = json!(hex(&signature));
    json!({"label":label,"scheme":String::from_utf8_lossy(SCHEME),"group":hex(group.identity()),"group_descriptor":hex(group.descriptor()),"threshold":threshold,"source_secret_fixture":source.map(|s|hex(&s)),"event":event})
}
fn main() {
    let mut rows = Vec::new();
    for n in [1, 2, 3, 6, 31] {
        let mut secret = [0; 32];
        secret[31] = n;
        let p = dealer(2, 3, Some(Zeroizing::new(secret)), &mut FixtureEntropy(n)).unwrap();
        rows.push(signed(&format!("dealer-existing-{n}"), p, Some(secret)));
    }
    rows.push(signed(
        "dealer-new-3-of-5",
        dealer(3, 5, None, &mut FixtureEntropy(80)).unwrap(),
        None,
    ));
    rows.push(signed("dkg-2-of-3", dkg(2, 3), None));
    rows.push(signed("dkg-3-of-5", dkg(3, 5), None));
    println!("{}", serde_json::to_string_pretty(&rows).unwrap());
}
