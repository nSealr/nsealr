use super::*;

struct GroupTest {
    devices: Vec<Custody>,
    keys: Vec<[u8; 32]>,
    entropy: u8,
    now: u64,
}
impl GroupTest {
    fn new() -> Self {
        let mut devices = Vec::new();
        let mut keys = Vec::new();
        for n in 1..=3 {
            let mut owner = Custody::default();
            let mut entropy = [n; 32];
            owner.start(&mut entropy, 1).unwrap();
            assert_eq!(entropy, [0; 32]);
            let join: Value = serde_json::from_str(&owner.outputs()[0]).unwrap();
            keys.push(j::hex(j::string(&join["key"]).unwrap()).unwrap());
            devices.push(owner);
        }
        Self {
            devices,
            keys,
            entropy: 10,
            now: 2,
        }
    }
    fn next(&mut self) -> [u8; 32] {
        self.entropy += 1;
        self.now += 1;
        [self.entropy; 32]
    }
    fn receive(&mut self, index: usize, message: &str) -> Result<(), Error> {
        let mut entropy = self.next();
        let result = self.devices[index].receive(message.as_bytes(), &mut entropy, self.now);
        assert_eq!(entropy, [0; 32]);
        result
    }
    fn approve(&mut self, index: usize) {
        for field in 0..self.devices[index].fields().len() {
            let generation = self.devices[index].generation();
            self.devices[index].seen(generation, field).unwrap();
        }
        let mut entropy = self.next();
        let generation = self.devices[index].generation();
        self.devices[index]
            .approve(generation, false, &mut entropy, self.now)
            .unwrap();
        assert_eq!(entropy, [0; 32]);
    }
    fn take_outputs(&mut self) -> Vec<String> {
        let mut messages = Vec::new();
        for device in &mut self.devices {
            messages.extend_from_slice(device.outputs());
            device.finish_response();
        }
        messages
    }
    fn route(&mut self, messages: &[String]) {
        for message in messages {
            let value: Value = serde_json::from_str(message).unwrap();
            let recipient = j::hex(j::string(&value["recipient"]).unwrap()).unwrap();
            let index = self.keys.iter().position(|k| k == &recipient).unwrap();
            self.receive(index, message).unwrap();
            // Exact retransmission cannot duplicate a share or advance twice.
            self.receive(index, message).unwrap();
        }
    }
    fn start_setup(&mut self) {
        self.take_outputs();
        let mut keys = self.keys.clone();
        keys.sort();
        let request =
            json!({"type":"nsealr_setup","session":"44".repeat(32),"members":wire::list(&keys)})
                .to_string();
        let mut fingerprint = None;
        for i in 0..3 {
            self.receive(i, &request).unwrap();
            let field = self.devices[i]
                .fields()
                .iter()
                .find(|f| f.label == "Match on all three devices")
                .unwrap();
            if let Some(expected) = &fingerprint {
                assert_eq!(field.value.as_str(), expected);
            } else {
                fingerprint = Some(field.value.to_string());
            }
            self.approve(i);
        }
    }
    fn setup(&mut self) {
        self.start_setup();
        for phase in ["setup1", "setup2"] {
            let messages = self.take_outputs();
            assert_eq!(messages.len(), 6);
            for message in &messages {
                let v: Value = serde_json::from_str(message).unwrap();
                assert_eq!(v["phase"], phase);
            }
            self.route(&messages);
        }
        let key = *self.devices[0].public_key().unwrap();
        let group = *self.devices[0].group().unwrap();
        for device in &self.devices {
            assert_eq!(*device.public_key().unwrap(), key);
            assert_eq!(*device.group().unwrap(), group);
            assert_eq!(device.state(), 4);
        }
        self.take_outputs();
    }
    fn begin_sign(&mut self, pair: [usize; 2], session: u8) {
        let mut keys = vec![self.keys[pair[0]], self.keys[pair[1]]];
        keys.sort();
        let event = json!({"pubkey":j::hex_string(self.devices[0].public_key().unwrap()),"created_at":1700000000,"kind":1,"tags":[],"content":"Two independent approvals"});
        let request=json!({"type":"nsealr_sign","id":"client-operation","session":j::hex_string(&[session;32]),"members":wire::list(&keys),"event":event.to_string()}).to_string();
        for index in pair {
            self.receive(index, &request).unwrap();
            self.approve(index);
        }
    }
    fn finish_sign(&mut self, pair: [usize; 2]) {
        for phase in ["commitment", "share"] {
            let messages = self.take_outputs();
            assert_eq!(messages.len(), 2);
            for message in &messages {
                let v: Value = serde_json::from_str(message).unwrap();
                assert_eq!(v["phase"], phase);
            }
            self.route(&messages);
        }
        let results = self.take_outputs();
        assert_eq!(results.len(), 2);
        assert_eq!(results[0], results[1]);
        let envelope: Value = serde_json::from_str(&results[0]).unwrap();
        assert_eq!(envelope["id"], "client-operation");
        let signed: Value = serde_json::from_str(envelope["result"].as_str().unwrap()).unwrap();
        assert_eq!(signed["content"], "Two independent approvals");
        let key = k256::schnorr::VerifyingKey::from_bytes(
            self.devices[pair[0]].public_key().unwrap().into(),
        )
        .unwrap();
        let sig = j::hex::<64>(signed["sig"].as_str().unwrap()).unwrap();
        key.verify_raw(
            &j::hex::<32>(signed["id"].as_str().unwrap()).unwrap(),
            &k256::schnorr::Signature::try_from(sig.as_slice()).unwrap(),
        )
        .unwrap();
        for index in pair {
            self.devices[index].cancel();
        }
    }
    fn repair_request(&mut self, lost: usize) -> String {
        let old: Value = serde_json::from_str(&self.devices[lost].record().unwrap()).unwrap();
        self.repair_from_record(lost, old)
    }
    fn repair_from_record(&mut self, lost: usize, old: Value) -> String {
        self.devices[lost].lock();
        // Exercise a replacement whose lexical position differs from its ID.
        loop {
            let mut entropy = self.next();
            self.devices[lost].start(&mut entropy, self.now).unwrap();
            let join: Value = serde_json::from_str(&self.devices[lost].outputs()[0]).unwrap();
            let key = j::hex(j::string(&join["key"]).unwrap()).unwrap();
            let mut roster = wire::read_roster(&old["members"]).unwrap();
            roster[old["participant"].as_u64().unwrap() as usize - 1] = key;
            if roster.windows(2).any(|w| w[0] >= w[1]) {
                self.keys[lost] = key;
                break;
            }
        }
        self.take_outputs();
        json!({"type":"nsealr_repair","session":"66".repeat(32),"group":old["group"],
            "descriptor":old["descriptor"],"members":old["members"],"participant":old["participant"],
            "replacement":j::hex_string(&self.keys[lost])}).to_string()
    }
    fn start_repair(&mut self, lost: usize) {
        let request = self.repair_request(lost);
        let mut fingerprint = None;
        for i in 0..3 {
            self.receive(i, &request).unwrap();
            let field = self.devices[i]
                .fields()
                .iter()
                .find(|f| f.label == "Match on all three devices")
                .unwrap();
            if let Some(expected) = &fingerprint {
                assert_eq!(&field.value, expected);
            } else {
                fingerprint = Some(field.value.clone());
            }
            self.approve(i);
        }
    }
}

#[test]
fn lost_share_repair_preserves_ids_npub_and_all_signing_pairs() {
    for lost in 0..3 {
        let mut group = GroupTest::new();
        group.setup();
        let public = *group.devices[0].public_key().unwrap();
        let before = *group.devices[0].group().unwrap();
        let ids: Vec<_> = group.devices.iter().map(|d| d.member().unwrap()).collect();
        group.start_repair(lost);
        for phase in ["repair_delta", "repair_sigma"] {
            let packets = group.take_outputs();
            assert_eq!(packets.len(), 2);
            for message in &packets {
                let value: Value = serde_json::from_str(message).unwrap();
                assert_eq!(value["phase"], phase);
            }
            group.route(&packets);
        }
        let outputs = group.take_outputs();
        assert_eq!(outputs.len(), 3);
        group.route(&outputs[..2]);
        let mut records = vec![outputs[2].clone()];
        records.extend(group.take_outputs());
        assert_eq!(records.len(), 3);
        let after = *group.devices[0].group().unwrap();
        assert_ne!(before, after);
        for (i, device) in group.devices.iter().enumerate() {
            assert_eq!(device.member().unwrap(), ids[i]);
            assert_eq!(device.public_key().unwrap(), &public);
            assert_eq!(device.group().unwrap(), &after);
            assert!(device.record().unwrap().len() < 1024);
        }
        for i in 0..3 {
            let mut backup = group.devices[i].backup().unwrap().as_bytes().to_vec();
            group.devices[i].lock();
            group.now += 1;
            group.devices[i].import(&mut backup, group.now).unwrap();
            assert!(backup.iter().all(|b| *b == 0));
            group.approve(i);
        }
        group.take_outputs();
        for (pair, session) in [([0, 1], 21), ([0, 2], 22), ([1, 2], 23)] {
            group.begin_sign(pair, session);
            let generation = group.devices[pair[0]].generation();
            let pending = group.devices[pair[0]].outputs().to_vec();
            group.devices[pair[0]].record().unwrap();
            assert_eq!(group.devices[pair[0]].generation(), generation);
            assert_eq!(group.devices[pair[0]].outputs(), pending);
            group.finish_sign(pair);
        }
    }
}

#[test]
fn repair_requires_matching_roster_fresh_permission_and_live_round() {
    let mut group = GroupTest::new();
    group.setup();
    let original = group.devices[1].record().unwrap();
    let request = group.repair_request(0);
    for field in ["group", "descriptor"] {
        let mut changed: Value = serde_json::from_str(&request).unwrap();
        let mut text = changed[field].as_str().unwrap().as_bytes().to_vec();
        text[0] = if text[0] == b'0' { b'1' } else { b'0' };
        changed[field] = String::from_utf8(text).unwrap().into();
        assert!(group.receive(1, &changed.to_string()).is_err());
        assert_eq!(group.devices[1].record().unwrap(), original);
    }
    group.receive(1, &request).unwrap();
    let generation = group.devices[1].generation();
    let mut entropy = group.next();
    assert_eq!(
        group.devices[1].approve(generation, true, &mut entropy, group.now),
        Err(Error::Review)
    );
    assert_eq!(entropy, [0; 32]);
    assert_eq!(group.devices[1].record().unwrap(), original);
    for i in 0..3 {
        group.receive(i, &request).unwrap();
        group.approve(i);
    }
    let packets = group.take_outputs();
    let mut mixed: Value = serde_json::from_str(&packets[0]).unwrap();
    let recipient = j::hex::<32>(mixed["recipient"].as_str().unwrap()).unwrap();
    let index = group.keys.iter().position(|k| k == &recipient).unwrap();
    mixed["session"] = "77".repeat(32).into();
    assert!(group.receive(index, &mixed.to_string()).is_err());
    assert!(group.devices[index].loaded());
    assert!(group.receive(index, &packets[0]).is_err());
    group.now += SETUP_MS;
    assert!(group.devices[0].tick(group.now).unwrap());
    assert!(!group.devices[0].loaded());
    assert!(group.devices[0].identity.is_none());
    for device in &mut group.devices[1..] {
        device.cancel();
        assert!(device.loaded());
        assert!(device.repair.is_none());
    }
}

#[test]
fn authenticated_bad_repair_contribution_cannot_install_a_share() {
    let mut group = GroupTest::new();
    group.setup();
    group.start_repair(0);
    let deltas = group.take_outputs();
    group.route(&deltas);
    let mut sigmas = group.take_outputs();
    let packet: Value = serde_json::from_str(&sigmas[0]).unwrap();
    let sender = j::hex::<32>(packet["sender"].as_str().unwrap()).unwrap();
    let helper = group.keys.iter().position(|k| k == &sender).unwrap();
    sigmas[0] = wire::seal(
        group.devices[helper].identity.as_ref().unwrap(),
        &group.keys[0],
        "repair_sigma",
        &j::hex(packet["group"].as_str().unwrap()).unwrap(),
        &j::hex(packet["session"].as_str().unwrap()).unwrap(),
        &json!({"sigma":"00".repeat(32)}),
        &mut wire::Random::new([80; 32], 1),
    )
    .unwrap();
    group.receive(0, &sigmas[0]).unwrap();
    assert_eq!(group.receive(0, &sigmas[1]), Err(Error::Crypto));
    assert!(!group.devices[0].loaded());
    assert!(group.devices[0].outputs().is_empty());
    assert!(group.devices[0].repair.is_none());
    assert!(group.devices[0].identity.is_none());
    assert!(group.devices[1].loaded() && group.devices[2].loaded());
}

#[test]
fn interrupted_repair_converges_from_old_backups_or_a_matching_live_quorum() {
    for restore_backups in [false, true] {
        for delivered in 0..=2 {
            let mut group = GroupTest::new();
            group.setup();
            let public = *group.devices[0].public_key().unwrap();
            let original: Value =
                serde_json::from_str(&group.devices[0].record().unwrap()).unwrap();
            let backups: Vec<_> = group.devices.iter().map(|d| d.backup().unwrap()).collect();
            group.start_repair(0);
            for _ in 0..2 {
                let packets = group.take_outputs();
                group.route(&packets);
            }
            let ready = group.take_outputs();
            group.route(&ready[..delivered]);
            // Losing the companion transcript means no pending packets survive.
            for device in &mut group.devices {
                device.cancel();
            }
            let (target, record) = if restore_backups {
                for (i, backup) in backups.iter().enumerate().skip(1) {
                    let mut bytes = backup.as_bytes().to_vec();
                    group.now += 1;
                    group.devices[i].import(&mut bytes, group.now).unwrap();
                    assert!(bytes.iter().all(|b| *b == 0));
                    group.approve(i);
                }
                (0, original)
            } else {
                let pair = [(0, 1), (0, 2), (1, 2)]
                    .into_iter()
                    .find(|(a, b)| {
                        group.devices[*a].group().unwrap() == group.devices[*b].group().unwrap()
                    })
                    .unwrap();
                let target = (0..3).find(|i| *i != pair.0 && *i != pair.1).unwrap();
                let mut record: Value =
                    serde_json::from_str(&group.devices[pair.0].record().unwrap()).unwrap();
                record["participant"] = group.devices[target].member().unwrap().into();
                (target, record)
            };
            let request = group.repair_from_record(target, record);
            for i in 0..3 {
                group.receive(i, &request).unwrap();
                group.approve(i);
            }
            for _ in 0..2 {
                let packets = group.take_outputs();
                group.route(&packets);
            }
            let ready = group.take_outputs();
            group.route(&ready[..2]);
            group.take_outputs();
            let fingerprint = *group.devices[0].group().unwrap();
            for device in &group.devices {
                assert_eq!(device.public_key().unwrap(), &public);
                assert_eq!(device.group().unwrap(), &fingerprint);
            }
            group.begin_sign([0, 1], 90);
            group.finish_sign([0, 1]);
        }
    }
}

#[test]
fn repair_cleanup_keeps_the_pinned_upstream_answer() {
    use frost::keys::repairable::{repair_share_part2, Delta, Sigma};
    let vector: Value = serde_json::from_str(include_str!(
        "../../../../vendor/frost-secp256k1-tr/tests/helpers/repair-share.json"
    ))
    .unwrap();
    let values = &vector["scalar_generation"];
    let mut deltas = Zeroizing::new(Vec::new());
    for key in ["random_scalar_1", "random_scalar_2", "random_scalar_3"] {
        deltas.push(
            Delta::deserialize(&j::hex::<32>(values[key].as_str().unwrap()).unwrap()).unwrap(),
        );
    }
    let mut sigma = Zeroizing::new(repair_share_part2(&deltas));
    assert_eq!(
        sigma.serialize(),
        j::hex::<32>(values["random_scalar_sum"].as_str().unwrap()).unwrap()
    );
    deltas[0].zeroize();
    assert_eq!(deltas[0].serialize(), [0; 32]);
    sigma.zeroize();
    assert_eq!(
        sigma.serialize(),
        Sigma::deserialize(&[0; 32]).unwrap().serialize()
    );
}

#[test]
fn three_device_ceremony_share_recovery_and_every_two_member_subset_sign() {
    let mut group = GroupTest::new();
    group.setup();
    let public = *group.devices[0].public_key().unwrap();
    let backups: Vec<_> = group.devices.iter().map(|d| d.backup().unwrap()).collect();
    assert!(backups.windows(2).all(|w| w[0] != w[1]));
    for (i, backup) in backups.iter().enumerate() {
        let mut input = backup.as_bytes().to_vec();
        group.devices[i].lock();
        group.now += 1;
        group.devices[i].import(&mut input, group.now).unwrap();
        assert!(input.iter().all(|b| *b == 0));
        assert!(!group.devices[i].loaded());
        group.approve(i);
        assert_eq!(*group.devices[i].public_key().unwrap(), public);
    }
    group.take_outputs();
    for (pair, session) in [([0, 1], 1), ([0, 2], 2), ([1, 2], 3)] {
        group.begin_sign(pair, session);
        group.finish_sign(pair);
    }
    for device in &mut group.devices {
        device.lock();
        assert!(!device.loaded());
        assert!(device.backup().is_err());
    }
    let mut damaged = backups[0].as_bytes().to_vec();
    let index = damaged.iter().position(|b| *b == b'a').unwrap();
    damaged[index] = b'b';
    group.now += 1;
    assert!(group.devices[0].import(&mut damaged, group.now).is_err());
    assert!(damaged.iter().all(|b| *b == 0));
    assert!(!group.devices[0].loaded());
}

#[test]
fn roster_authentication_and_ciphertext_tampering_fail_closed() {
    let mut group = GroupTest::new();
    let mut keys = group.keys.clone();
    keys.sort();
    let request =
        json!({"type":"nsealr_setup","session":"44".repeat(32),"members":wire::list(&keys)})
            .to_string();
    group.receive(0, &request).unwrap();
    let generation = group.devices[0].generation();
    assert_eq!(
        group.devices[0].approve(generation, true, &mut [50; 32], group.now + 1),
        Err(Error::Review)
    );
    assert_eq!(group.devices[0].state(), 0);
    let mut group = GroupTest::new();
    group.start_setup();
    let messages = group.take_outputs();
    let mut changed: Value = serde_json::from_str(&messages[0]).unwrap();
    let recipient = j::hex::<32>(changed["recipient"].as_str().unwrap()).unwrap();
    let index = group.keys.iter().position(|k| k == &recipient).unwrap();
    let content = changed["content"].as_str().unwrap().to_string();
    let mut forged = content.into_bytes();
    forged[80] = if forged[80] == b'A' { b'B' } else { b'A' };
    changed["content"] = String::from_utf8(forged).unwrap().into();
    assert_eq!(
        group.receive(index, &changed.to_string()),
        Err(Error::Crypto)
    );
    assert_eq!(group.devices[index].state(), 0);
}

#[test]
fn an_authenticated_but_inconsistent_setup_transcript_is_rejected() {
    let mut group = GroupTest::new();
    group.start_setup();
    let first = group.take_outputs();
    group.route(&first);
    let second = group.take_outputs();
    let value: Value = serde_json::from_str(&second[0]).unwrap();
    let sender = j::hex::<32>(value["sender"].as_str().unwrap()).unwrap();
    let recipient = j::hex::<32>(value["recipient"].as_str().unwrap()).unwrap();
    let from = group.keys.iter().position(|k| k == &sender).unwrap();
    let to = group.keys.iter().position(|k| k == &recipient).unwrap();
    let setup = group.devices[to].setup.as_ref().unwrap();
    let (_, mut payload) = wire::open(
        group.devices[to].identity.as_ref().unwrap(),
        &value,
        "setup2",
        &setup.fingerprint,
        &setup.session,
        &group.devices[to].members,
    )
    .unwrap();
    payload["transcript"] = "00".repeat(32).into();
    let changed = wire::seal(
        group.devices[from].identity.as_ref().unwrap(),
        &recipient,
        "setup2",
        &setup.fingerprint,
        &setup.session,
        &payload,
        &mut wire::Random::new([99; 32], 1),
    )
    .unwrap();
    assert_eq!(group.receive(to, &changed), Err(Error::Input));
    assert!(!group.devices[to].loaded());
}

#[test]
fn cancellation_expiry_and_wrong_round_consume_nonces_without_losing_share() {
    let mut group = GroupTest::new();
    group.setup();
    group.begin_sign([0, 1], 1);
    let commitments = group.take_outputs();
    group.devices[0].cancel();
    let peer = commitments
        .iter()
        .find(|m| {
            let v: Value = serde_json::from_str(m).unwrap();
            v["recipient"] == j::hex_string(&group.keys[0])
        })
        .unwrap();
    assert!(group.receive(0, peer).is_err());
    assert!(group.devices[0].loaded());
    group.devices[1].cancel();
    group.begin_sign([0, 1], 2);
    let commitments = group.take_outputs();
    group.now += SIGN_MS;
    assert!(group.devices[0].tick(group.now).unwrap());
    let peer = commitments
        .iter()
        .find(|m| {
            let v: Value = serde_json::from_str(m).unwrap();
            v["recipient"] == j::hex_string(&group.keys[0])
        })
        .unwrap();
    assert!(group.receive(0, peer).is_err());
    assert!(group.devices[0].loaded());
    group.devices[1].cancel();
    group.begin_sign([0, 1], 3);
    let commitments = group.take_outputs();
    let mut changed: Value = serde_json::from_str(&commitments[0]).unwrap();
    changed["session"] = "00".repeat(32).into();
    let recipient = j::hex::<32>(changed["recipient"].as_str().unwrap()).unwrap();
    let to = group.keys.iter().position(|k| k == &recipient).unwrap();
    assert_eq!(
        group.receive(to, &changed.to_string()),
        Err(Error::Identity)
    );
    assert!(group.devices[to].loaded());
    assert!(group.receive(to, &commitments[0]).is_err());
    for device in &mut group.devices {
        device.cancel();
    }
    group.begin_sign([0, 1], 4);
    group.finish_sign([0, 1]);
    let request=json!({"id":"no-ecdh","method":"nip44_encrypt","params":[j::hex_string(&group.keys[1]),"hello"]}).to_string();
    assert_eq!(
        group.devices[0].public_request(request.as_bytes(), group.now + 1),
        Err(Error::Unsupported)
    );
}

#[test]
fn replacement_frames_and_finish_consume_pending_authority_and_collection() {
    let mut group = GroupTest::new();
    group.setup();
    let mut peers = vec![group.keys[0], group.keys[1]];
    peers.sort();
    let event = json!({"pubkey":j::hex_string(group.devices[0].public_key().unwrap()),"created_at":1,"kind":1,"tags":[],"content":"Old request"});
    let request = json!({"type":"nsealr_sign","id":"old","session":"22".repeat(32),"members":wire::list(&peers),"event":event.to_string()}).to_string();
    group.receive(0, &request).unwrap();
    let device = &mut group.devices[0];
    let generation = device.generation();
    for index in 0..device.fields().len() {
        device.seen(generation, index).unwrap();
    }
    let frame = nsealr_core::qr::encode(&vec![b'x'; 500], 0).unwrap();
    assert_eq!(
        device.receive_frame(frame.as_bytes(), &mut [60; 32], group.now + 1),
        Err(Error::Stale)
    );
    assert_eq!(
        device.approve(generation, false, &mut [61; 32], group.now + 2),
        Err(Error::Stale)
    );
    assert!(device.outputs().is_empty());
    assert!(device.loaded());
    assert_eq!(
        device.receive_frame(frame.as_bytes(), &mut [62; 32], group.now + 3),
        Ok(false)
    );
    device.finish_response();
    assert_eq!(device.collector.received(), 0);
    let backup = device.backup().unwrap();
    let mut frame = nsealr_core::qr::encode(backup.as_bytes(), 0)
        .unwrap()
        .into_bytes();
    assert_eq!(
        device.backup_frame(&mut frame, true, group.now + 4),
        Ok(false)
    );
    device.finish_response();
    assert_eq!(device.collector.received(), 0);
    assert_eq!(device.backup_scan, None);
    assert!(device.loaded());
}

#[test]
fn secret_backup_frames_are_bounded_wiped_and_check_never_replaces_the_share() {
    let mut group = GroupTest::new();
    group.setup();
    let backup = group.devices[0].backup().unwrap();
    let other = group.devices[1].backup().unwrap();
    for (bytes, valid) in [(backup.as_bytes(), true), (other.as_bytes(), false)] {
        for i in 0..bytes.len().div_ceil(nsealr_core::qr::CHUNK) {
            let mut frame = nsealr_core::qr::encode(bytes, i).unwrap().into_bytes();
            group.now += 1;
            let result = group.devices[0].backup_frame(&mut frame, true, group.now);
            assert!(frame.iter().all(|b| *b == 0));
            if i + 1 == bytes.len().div_ceil(nsealr_core::qr::CHUNK) {
                assert_eq!(result, if valid { Ok(true) } else { Err(Error::Crypto) });
            } else {
                assert_eq!(result, Ok(false));
            }
        }
        assert_eq!(group.devices[0].backup().unwrap(), backup);
    }
    let mut oversized = nsealr_core::qr::encode(&vec![b'x'; MAX_BACKUP + 1], 5)
        .unwrap()
        .into_bytes();
    group.now += 1;
    assert_eq!(
        group.devices[0].backup_frame(&mut oversized, true, group.now),
        Err(Error::Bounds)
    );
    assert!(oversized.iter().all(|b| *b == 0));
    assert!(group.devices[0].loaded());
    let mut partial = nsealr_core::qr::encode(backup.as_bytes(), 0)
        .unwrap()
        .into_bytes();
    group.now += 1;
    assert_eq!(
        group.devices[0].backup_frame(&mut partial, true, group.now),
        Ok(false)
    );
    group.now += SETUP_MS;
    assert!(group.devices[0].tick(group.now).unwrap());
    assert_eq!(group.devices[0].collector.received(), 0);
    assert!(group.devices[0].loaded());
}

#[test]
fn setup_replacement_cancels_pending_recipient_repair() {
    let mut group = GroupTest::new();
    group.setup();
    group.start_repair(0);
    let deltas = group.take_outputs();
    assert_eq!(deltas.len(), 2);
    let mut members = group.keys.clone();
    members.sort();
    let setup =
        json!({"type":"nsealr_setup","session":"99".repeat(32),"members":wire::list(&members)})
            .to_string();
    assert_eq!(group.receive(0, &setup), Err(Error::Stale));
    assert!(group.devices[0].repair.is_none());
    assert!(group.devices[0].setup.is_none());
    assert!(group.devices[0].review.is_none());
    group.route(&deltas);
    let sigmas = group.take_outputs();
    assert_eq!(sigmas.len(), 2);
    for sigma in sigmas {
        assert!(group.receive(0, &sigma).is_err());
    }
    assert!(!group.devices[0].loaded());
}
