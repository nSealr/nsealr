//! One offline identity and one locally reviewed operation. The firmware owns
//! trusted input, rendering, time and entropy; the network owns none of them.
#![no_std]
extern crate alloc;
#[cfg(any(test, feature = "std"))]
extern crate std;

pub mod bip39;
pub mod event;
pub mod generation;
pub mod hash;
pub mod identity;
pub mod json;
pub mod nip19;
pub mod nip44;
pub mod owner;
mod private;
pub mod qr;
mod recovery;
pub mod seedqr;
pub mod staged;

pub const MAX_MESSAGE: usize = 32768;
pub const MAX_CONTENT: usize = 8192;
pub const MAX_TAGS: usize = 256;
pub const MAX_TAG_FIELDS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(i32)]
pub enum Error {
    Input = -1,
    Bounds = -2,
    Locked = -3,
    Unsupported = -4,
    Identity = -5,
    Review = -6,
    Stale = -7,
    Crypto = -8,
    Entropy = -9,
    Output = -10,
}
impl Error {
    pub const fn message(self) -> &'static str {
        match self {
            Self::Input => "Malformed input",
            Self::Bounds => "Request exceeds device limits",
            Self::Locked => "Load an identity first",
            Self::Unsupported => "Unsupported operation or event semantics",
            Self::Identity => "Request identity does not match this session",
            Self::Review => "Review all required fields before approval",
            Self::Stale => "Request cancelled, replaced or expired",
            Self::Crypto => "Cryptographic verification failed",
            Self::Entropy => "Fresh qualified randomness is required",
            Self::Output => "Output buffer is too small",
        }
    }
}
