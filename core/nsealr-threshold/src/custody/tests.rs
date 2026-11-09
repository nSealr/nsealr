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
