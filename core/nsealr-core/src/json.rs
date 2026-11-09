//! Bounded JSON with duplicate-field rejection before typed interpretation.
use crate::{Error, MAX_MESSAGE};
use alloc::{string::String, vec::Vec};
use core::fmt;
use serde_core::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Number, Value};

struct Unique(Value);
impl<'de> Deserialize<'de> for Unique {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Unique;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("bounded JSON")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> Result<Unique, E> {
                Ok(Unique(Value::Bool(v)))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Unique, E> {
                Ok(Unique(Value::Null))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> Result<Unique, E> {
                Ok(Unique(Value::Number(v.into())))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> Result<Unique, E> {
                Ok(Unique(Value::Number(v.into())))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> Result<Unique, E> {
                Number::from_f64(v)
                    .map(|n| Unique(Value::Number(n)))
                    .ok_or_else(|| E::custom("finite number required"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> Result<Unique, E> {
                Ok(Unique(Value::String(v.into())))
            }
            fn visit_string<E: de::Error>(self, v: String) -> Result<Unique, E> {
                Ok(Unique(Value::String(v)))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut values = Vec::new();
                while let Some(v) = a.next_element::<Unique>()? {
                    if values.len() == 256 {
                        return Err(de::Error::custom("array bound"));
                    }
                    values.push(v.0);
                }
                Ok(Unique(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut map = Map::new();
                while let Some(key) = a.next_key::<String>()? {
                    if map.len() == 64 {
                        return Err(de::Error::custom("object bound"));
                    }
                    if map.contains_key(&key) {
                        return Err(de::Error::custom("duplicate field"));
                    }
                    map.insert(key, a.next_value::<Unique>()?.0);
                }
                Ok(Unique(Value::Object(map)))
            }
        }
        d.deserialize_any(V)
    }
}

pub fn parse(input: &[u8]) -> Result<Value, Error> {
    if input.is_empty() || input.len() > MAX_MESSAGE {
        return Err(Error::Bounds);
    }
    // Bound stack and node overhead before serde allocates. Brackets in strings
    // and escaped quotes do not affect depth. Serde checks actual JSON grammar.
    let (mut depth, mut nodes, mut string, mut escape, mut atom) =
        (0usize, 0usize, false, false, false);
    for &b in input {
        if string {
            if escape {
                escape = false;
            } else if b == b'\\' {
                escape = true;
            } else if b == b'"' {
                string = false;
            }
        } else {
            match b {
                b'"' => {
                    string = true;
                    atom = false;
                    nodes += 1;
                }
                b'[' | b'{' => {
                    atom = false;
                    depth += 1;
                    nodes += 1;
                    if depth > 16 {
                        return Err(Error::Bounds);
                    }
                }
                b']' | b'}' => {
                    atom = false;
                    depth = depth.checked_sub(1).ok_or(Error::Input)?;
                }
                b',' | b':' | b' ' | b'\n' | b'\r' | b'\t' => atom = false,
                _ => {
                    if !atom {
                        nodes += 1;
                        atom = true;
                    }
                }
            }
            if nodes > 2048 {
                return Err(Error::Bounds);
            }
        }
    }
    serde_json::from_slice::<Unique>(input)
        .map(|v| v.0)
        .map_err(|_| Error::Input)
}

pub fn exact_keys(value: &Value, required: &[&str], optional: &[&str]) -> Result<(), Error> {
    let obj = value.as_object().ok_or(Error::Input)?;
    if required.iter().any(|k| !obj.contains_key(*k))
        || obj
            .keys()
            .any(|k| !required.contains(&k.as_str()) && !optional.contains(&k.as_str()))
    {
        return Err(Error::Input);
    }
    Ok(())
}
pub fn string(value: &Value) -> Result<&str, Error> {
    value.as_str().ok_or(Error::Input)
}
pub fn integer(value: &Value) -> Result<u64, Error> {
    value
        .as_u64()
        .filter(|n| *n <= 9_007_199_254_740_991)
        .ok_or(Error::Input)
}
pub fn hex<const N: usize>(text: &str) -> Result<[u8; N], Error> {
    if text.len() != N * 2 {
        return Err(Error::Input);
    }
    let mut out = [0; N];
    for (pair, byte) in text.as_bytes().chunks_exact(2).zip(&mut out) {
        let digit = |b| match b {
            b'0'..=b'9' => Ok(b - b'0'),
            b'a'..=b'f' => Ok(b - b'a' + 10),
            _ => Err(Error::Input),
        };
        *byte = digit(pair[0])? * 16 + digit(pair[1])?;
    }
    Ok(out)
}
pub fn hex_string(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        out.push(DIGITS[(b >> 4) as usize] as char);
        out.push(DIGITS[(b & 15) as usize] as char);
    }
    out
}
