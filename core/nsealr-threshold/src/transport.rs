use alloc::{
    string::{String, ToString},
    vec,
    vec::Vec,
};
use chacha20::ChaCha20Rng;
use nsealr_core::{hash::sha256, identity::Identity, json as j, nip44, Error};
use rand_core::{Rng, SeedableRng};
use serde_json::{json, Value};
use zeroize::Zeroizing;

pub(crate) struct Random(ChaCha20Rng);
impl Random {
    pub(crate) fn new(seed: [u8; 32], sequence: u64) -> Self {
        let mut rng = ChaCha20Rng::from_seed(seed);
        rng.set_stream(sequence);
        Self(rng)
    }
    pub(crate) fn bytes(&mut self) -> Zeroizing<[u8; 32]> {
        let mut bytes = Zeroizing::new([0; 32]);
        self.0.fill_bytes(bytes.as_mut());
        bytes
    }
}
impl crate::EntropySource for Random {
    fn fill(&mut self, seed: &mut [u8; 32]) -> Result<usize, crate::Error> {
        self.0.fill_bytes(seed);
        Ok(32)
    }
}

pub(crate) fn decode(text: &str, limit: usize) -> Result<Zeroizing<Vec<u8>>, Error> {
    if !text.len().is_multiple_of(2) || text.len() > limit * 2 {
        return Err(Error::Bounds);
    }
    let mut out = Zeroizing::new(Vec::with_capacity(text.len() / 2));
    for pair in text.as_bytes().chunks_exact(2) {
        out.push(j::hex::<1>(core::str::from_utf8(pair).map_err(|_| Error::Input)?)?[0]);
    }
    Ok(out)
}
pub(crate) fn key(value: &Value) -> Result<[u8; 32], Error> {
    let key = j::hex(j::string(value)?)?;
    k256::schnorr::VerifyingKey::from_bytes((&key).into()).map_err(|_| Error::Input)?;
    Ok(key)
}
pub(crate) fn members(value: &Value, count: usize) -> Result<Vec<[u8; 32]>, Error> {
    let rows = value.as_array().ok_or(Error::Input)?;
    if rows.len() != count {
        return Err(Error::Bounds);
    }
    let keys: Vec<_> = rows.iter().map(key).collect::<Result<_, _>>()?;
    if keys.windows(2).any(|w| w[0] >= w[1]) {
        return Err(Error::Input);
    }
    Ok(keys)
}
pub(crate) fn list(keys: &[[u8; 32]]) -> Vec<String> {
    keys.iter().map(|k| j::hex_string(k)).collect()
}
/// The slot is a stable FROST identifier, not the key's lexical position.
pub(crate) fn roster(keys: &[[u8; 32]]) -> Vec<Value> {
    keys.iter()
        .enumerate()
        .map(|(i, key)| json!({"id":i+1,"key":j::hex_string(key)}))
        .collect()
}
pub(crate) fn read_roster(value: &Value) -> Result<Vec<[u8; 32]>, Error> {
    let rows = value.as_array().ok_or(Error::Input)?;
    if rows.len() != 3 {
        return Err(Error::Bounds);
    }
    let mut keys = Vec::with_capacity(3);
    for (i, row) in rows.iter().enumerate() {
        j::exact_keys(row, &["id", "key"], &[])?;
        if row["id"].as_u64() != Some(i as u64 + 1) {
            return Err(Error::Identity);
        }
        let key = key(&row["key"])?;
        if keys.contains(&key) {
            return Err(Error::Identity);
        }
        keys.push(key);
    }
    Ok(keys)
}
fn digest(
    phase: &str,
    group: &str,
    session: &str,
    sender: &str,
    recipient: &str,
    content: &str,
) -> [u8; 32] {
    sha256(
        &serde_json::to_vec(&(
            "nSealr threshold peer",
            phase,
            group,
            session,
            sender,
            recipient,
            content,
        ))
        .expect("strings serialize"),
    )
}
pub(crate) fn seal(
    identity: &Identity,
    recipient: &[u8; 32],
    phase: &str,
    group: &[u8; 32],
    session: &[u8; 32],
    payload: &Value,
    random: &mut Random,
) -> Result<String, Error> {
    let plain = Zeroizing::new(payload.to_string());
    let mut out = Zeroizing::new(vec![0; nip44::MAX_PAYLOAD_BYTES]);
    let n = identity.encrypt(recipient, &plain, &random.bytes(), &mut out)?;
    let content = core::str::from_utf8(&out[..n]).map_err(|_| Error::Crypto)?;
    let group = j::hex_string(group);
    let session = j::hex_string(session);
    let sender = j::hex_string(&identity.public_key());
    let recipient = j::hex_string(recipient);
    let sig = identity.sign(
        &digest(phase, &group, &session, &sender, &recipient, content),
        &random.bytes(),
    )?;
    Ok(
        json!({"type":"nsealr_peer","phase":phase,"group":group,"session":session,
        "sender":sender,"recipient":recipient,"content":content,"sig":j::hex_string(&sig)})
        .to_string(),
    )
}
pub(crate) fn open(
    identity: &Identity,
    input: &Value,
    phase: &str,
    group: &[u8; 32],
    session: &[u8; 32],
    roster: &[[u8; 32]],
) -> Result<([u8; 32], Value), Error> {
    j::exact_keys(
        input,
        &[
            "type",
            "phase",
            "group",
            "session",
            "sender",
            "recipient",
            "content",
            "sig",
        ],
        &[],
    )?;
    let sender = key(&input["sender"])?;
    if j::string(&input["type"])? != "nsealr_peer"
        || j::string(&input["phase"])? != phase
        || j::hex::<32>(j::string(&input["group"])?)? != *group
        || j::hex::<32>(j::string(&input["session"])?)? != *session
        || key(&input["recipient"])? != identity.public_key()
        || sender == identity.public_key()
        || !roster.contains(&sender)
    {
        return Err(Error::Identity);
    }
    let content = j::string(&input["content"])?;
    if content.len() > nip44::MAX_PAYLOAD_BYTES {
        return Err(Error::Bounds);
    }
    let signature = j::hex::<64>(j::string(&input["sig"])?)?;
    let sig =
        k256::schnorr::Signature::try_from(signature.as_slice()).map_err(|_| Error::Crypto)?;
    let verifying =
        k256::schnorr::VerifyingKey::from_bytes((&sender).into()).map_err(|_| Error::Crypto)?;
    verifying
        .verify_raw(
            &digest(
                phase,
                j::string(&input["group"])?,
                j::string(&input["session"])?,
                j::string(&input["sender"])?,
                j::string(&input["recipient"])?,
                content,
            ),
            &sig,
        )
        .map_err(|_| Error::Crypto)?;
    let mut plaintext = Zeroizing::new(vec![0; nip44::MAX_PLAINTEXT_BYTES]);
    let n = identity.decrypt(&sender, content, &mut plaintext)?;
    Ok((sender, j::parse(&plaintext[..n])?))
}
