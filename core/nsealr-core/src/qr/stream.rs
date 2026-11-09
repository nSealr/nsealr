//! Bounded public-frame collection. Framing hashes convey no signing authority.
//!
//! The trusted caller owns scan context, cancellation and an absolute deadline.
//! This collector never renews that deadline, including on exact duplicates.

use super::{
    envelope::{
        map_payload_decode_error, parse_animated_qr_frame, require_json_container, QrEnvelopeError,
        ANIMATED_PREFIX,
    },
    limits::{
        MAX_ANIMATED_QR_DECODED_JSON_BYTES, MAX_ANIMATED_QR_FRAME_COUNT,
        MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS,
    },
};
use crate::{
    base64url::{decode_base64url, encoded_len},
    hash::sha256_hex,
    unicode::is_valid_utf8,
};

/// Largest canonical frame: prefix, digest, `:64/64:`, chunk and checksum.
pub const MAX_ANIMATED_FRAME_BYTES: usize =
    ANIMATED_PREFIX.len() + 64 + 7 + MAX_ANIMATED_QR_FRAME_PAYLOAD_CHARS + 1 + 16;
/// Maximum retained base64url text for a complete bounded JSON payload.
pub const MAX_ENCODED_BYTES: usize = encoded_len(MAX_ANIMATED_QR_DECODED_JSON_BYTES);

/// Public caller-owned storage; no allocation and no transferable authorization.
/// Variable-length chunks are packed in arrival order and indexed separately.
pub struct AnimatedQrCollector {
    payload: [u8; MAX_ENCODED_BYTES],
    ranges: [(u16, u16); MAX_ANIMATED_QR_FRAME_COUNT],
    digest: [u8; 64],
    used: u16,
    total: u8,
    received: u8,
    failed: bool,
}

impl Default for AnimatedQrCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl AnimatedQrCollector {
    /// Starts empty. The adapter must separately bind a fresh scan deadline.
    pub const fn new() -> Self {
        Self {
            payload: [0; MAX_ENCODED_BYTES],
            ranges: [(0, 0); MAX_ANIMATED_QR_FRAME_COUNT],
            digest: [0; 64],
            used: 0,
            total: 0,
            received: 0,
            failed: false,
        }
    }
    /// Clears all retained public frame bytes and permits a fresh collection.
    pub fn clear(&mut self) {
        self.payload.fill(0);
        self.ranges.fill((0, 0));
        self.digest.fill(0);
        self.used = 0;
        self.total = 0;
        self.received = 0;
        self.failed = false;
    }
    fn refuse(&mut self) {
        self.clear();
        self.failed = true;
    }
    /// Number of unique accepted frames, for a local progress indicator only.
    pub fn received(&self) -> usize {
        usize::from(self.received)
    }
    /// Total declared frames, zero until the first valid frame.
    pub fn total(&self) -> usize {
        usize::from(self.total)
    }
    /// Accepts out-of-order frames and exact repeated indexes. Any malformed,
    /// mixed or conflicting frame clears/closes this collection until `clear`.
    /// `true` means all unique frames are present; JSON/digest still need `decode`.
    pub fn push(&mut self, frame: &[u8]) -> Result<bool, QrEnvelopeError> {
        let result = self.accept(frame);
        if result.is_err() {
            self.refuse();
        }
        result
    }
    fn accept(&mut self, frame: &[u8]) -> Result<bool, QrEnvelopeError> {
        if self.failed {
            return Err(QrEnvelopeError::AnimatedCollectionClosed);
        }
        if frame.len() > MAX_ANIMATED_FRAME_BYTES {
            return Err(QrEnvelopeError::AnimatedFrameTooLong);
        }
        let parsed = parse_animated_qr_frame(frame)?;
        if self.total == 0 {
            self.digest.copy_from_slice(parsed.digest);
            self.total = parsed.total as u8;
        } else if self.digest != parsed.digest || self.total() != parsed.total {
            return Err(QrEnvelopeError::AnimatedFrameSetMismatch);
        }
        let (start, len) = self.ranges[parsed.index - 1];
        if len != 0 {
            if &self.payload[usize::from(start)..usize::from(start + len)] != parsed.chunk {
                return Err(QrEnvelopeError::AnimatedFrameSetMismatch);
            }
            return Ok(self.received == self.total);
        }
        let start = usize::from(self.used);
        let end = start + parsed.chunk.len();
        if end > self.payload.len() {
            return Err(QrEnvelopeError::ExceedsAnimatedJsonBytes);
        }
        self.payload[start..end].copy_from_slice(parsed.chunk);
        self.ranges[parsed.index - 1] = (self.used, parsed.chunk.len() as u16);
        self.used = end as u16;
        self.received += 1;
        Ok(self.received == self.total)
    }
    /// Validates complete canonical base64url, full digest, UTF-8 and container
    /// shape. Strict operation JSON parsing remains the authorization owner's job.
    /// Every error clears output and closes the collector without partial output.
    pub fn decode<'a>(&mut self, json_out: &'a mut [u8]) -> Result<&'a [u8], QrEnvelopeError> {
        json_out.fill(0);
        let result = (|| {
            if self.failed {
                return Err(QrEnvelopeError::AnimatedCollectionClosed);
            }
            if self.total == 0 || self.received != self.total {
                return Err(QrEnvelopeError::AnimatedFramesNotContiguous);
            }
            let mut ordered = [0u8; MAX_ENCODED_BYTES];
            let mut at = 0;
            for &(start, len) in &self.ranges[..self.total()] {
                let len = usize::from(len);
                let start = usize::from(start);
                ordered[at..at + len].copy_from_slice(&self.payload[start..start + len]);
                at += len;
            }
            if at % 4 == 1 {
                return Err(QrEnvelopeError::InvalidBase64UrlLength);
            }
            let decoded =
                decode_base64url(&ordered[..at], json_out).map_err(map_payload_decode_error)?;
            if sha256_hex(decoded) != self.digest {
                return Err(QrEnvelopeError::AnimatedDigestMismatch);
            }
            if !is_valid_utf8(decoded) {
                return Err(QrEnvelopeError::InvalidUtf8);
            }
            require_json_container(decoded)?;
            Ok(decoded.len())
        })();
        match result {
            Ok(len) => Ok(&json_out[..len]),
            Err(error) => {
                json_out.fill(0);
                self.refuse();
                Err(error)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::qr::envelope::encode_animated_qr_envelope_json;
    use std::{vec, vec::Vec};

    fn frames(json: &[u8], chunk: usize) -> Vec<Vec<u8>> {
        let mut frames = Vec::new();
        encode_animated_qr_envelope_json(json, chunk, &mut |frame, _, _| {
            frames.push(frame.to_vec())
        })
        .unwrap();
        frames
    }
    #[test]
    fn reversed_and_repeated_frames_decode_once_without_extra_retention() {
        let json = b"{\"content\":\"abcdefghijklmnopqrstuvwxyz\"}";
        let frames = frames(json, 7);
        let mut owner = AnimatedQrCollector::new();
        for (at, frame) in frames.iter().rev().enumerate() {
            assert_eq!(owner.push(frame), Ok(at + 1 == frames.len()));
            assert_eq!(owner.push(frame), Ok(at + 1 == frames.len()));
            assert_eq!(owner.received(), at + 1);
        }
        let mut output = [0xa5; 4096];
        assert_eq!(owner.decode(&mut output).unwrap(), json);
        owner.clear();
        assert!(owner.payload.iter().all(|b| *b == 0));
        assert_eq!(owner.received(), 0);
    }
    #[test]
    fn malformed_mixed_conflicting_and_incomplete_close_and_clear_collection() {
        let a = frames(b"{\"a\":12345}", 4);
        let b = frames(b"{\"b\":12345}", 4);
        for bad in [&b[0][..], &b"nsealr1a:bad"[..], &a[0][..a[0].len() - 1]] {
            let mut owner = AnimatedQrCollector::new();
            owner.push(&a[0]).unwrap();
            assert!(owner.push(bad).is_err());
            assert!(owner.payload.iter().all(|b| *b == 0));
            assert_eq!(
                owner.push(&a[0]),
                Err(QrEnvelopeError::AnimatedCollectionClosed)
            );
            owner.clear();
            assert!(owner.push(&a[0]).is_ok());
        }
        let mut owner = AnimatedQrCollector::new();
        owner.push(&a[0]).unwrap();
        let mut output = [0xa5; 4096];
        assert!(owner.decode(&mut output).is_err());
        assert!(output.iter().all(|b| *b == 0));
        assert!(owner.payload.iter().all(|b| *b == 0));
    }
    #[test]
    fn exact_maximum_and_small_output_are_bounded() {
        let mut json = vec![b'a'; 4096];
        json[..2].copy_from_slice(b"[\"");
        json[4094..].copy_from_slice(b"\"]");
        let frames = frames(&json, 256);
        let mut owner = AnimatedQrCollector::new();
        for frame in &frames {
            owner.push(frame).unwrap();
        }
        let mut output = [0; 4096];
        assert_eq!(owner.decode(&mut output).unwrap(), json);
        let mut small = [0xa5; 4095];
        assert_eq!(
            owner.decode(&mut small),
            Err(QrEnvelopeError::OutputTooSmall)
        );
        assert!(small.iter().all(|b| *b == 0));
        assert!(owner.payload.iter().all(|b| *b == 0));
    }
}
