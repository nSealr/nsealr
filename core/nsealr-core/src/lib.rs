//! `nsealr-core` — the portable `no_std` core for the nSealr offline signer.
//!
//! This crate contains the portable Rust protocol, transport framing, review,
//! policy and session foundations used by host tests and device adapters.
//! Compiling this crate does not qualify an MCU application, custody or
//! physical review. See `docs/core-provenance.md` for inherited test fixtures.
//!
//! # Build configuration
//!
//! The crate is `#![no_std]` so it links on bare-metal firmware targets (for
//! example `riscv32imafc-unknown-none-elf`). The opt-in `std` feature links the
//! [`std`] facade for host/desktop consumers and test tooling; it is off by
//! default and pulls in nothing on-device.
//!
//! Implemented modules include: the low-level primitives [`hash`] (SHA-256) and
//! [`base64url`] (URL-safe unpadded Base64), the encoding layer [`bip39`]
//! (English mnemonic parsing), [`nip19`] (`nsec` Bech32), [`seedqr`]
//! (Standard/Compact SeedQR), and [`unicode`] (UTF-8 + JSON `\uXXXX` helpers), the
//! transport layer [`qr`] (QR envelope / animated envelope / response-display
//! framing + shared limits) and [`serial`] (`nsealr1f:` serial framing plus the
//! byte-wise line accumulator with overlong-frame draining), and the
//! session/custody core [`session`] (RAM-only keyring with volatile secret
//! wiping, source parsing/generation, secret-hiding import/backup reviews,
//! account selection) with the fixed-capacity text type [`text`], the
//! policy/approval layer [`policy`] (approval-digest binding gate,
//! signing-readiness gates, policy-change review), the trusted-review layer
//! [`review`] (data model, signer identity, display rendering, physical
//! controls with button debounce classification, review sessions, QR/serial
//! review flows), and the device
//! protocol [`protocol`] (serial frame in, response frame out, trusted-review
//! preview).
#![no_std]
#![deny(missing_docs)]

// The `std` feature links the standard library facade for host/desktop
// consumers. It is opt-in and off by default; on-device builds never pull it in.
#[cfg(feature = "std")]
extern crate std;

// Unit tests always run on a host where libtest already links std; making the
// facade importable under cfg(test) lets fixture-replay tests build dynamic
// inputs (Vec/String) without touching the shipped `no_std` surface.
#[cfg(all(test, not(feature = "std")))]
extern crate std;

#[cfg(test)]
mod board_profile_tests;

pub mod authorization;
pub mod base64url;
pub mod bip39;
pub mod capabilities;
pub mod event;
pub mod hash;
pub mod nip17;
pub mod nip19;
pub mod nip44;
pub mod policy;
pub mod protocol;
pub mod qr;
pub mod review;
pub mod seedqr;
pub mod serial;
pub mod session;
pub mod text;
pub mod unicode;
