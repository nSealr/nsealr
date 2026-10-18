# Persistent Secret Custody V0

`persistent-secret-custody-v0` defines the minimum custody gate for the
nSealr One (`custom_hardware_wallet`) family.

This is a nSealr product-safety contract, not a Nostr protocol rule. It exists
so hardware, firmware, companion routing, and lab docs cannot drift into
production secret-storage claims before the custody lifecycle is explicit and
testable.

## Current Boundary

- Applies to `custom_hardware_wallet` only.
- Current status is research.
- Rev A signing remains on the host MCU unless a later public vendor path proves
  non-exportable TROPIC01 secp256k1 Schnorr/BIP-340 signing.
- The contract does not apply to the nSealr Vault editions (the Pi or ESP32
  stateless QR vaults).

## Required Lifecycle

- Plaintext Nostr private keys, `nsec` values, mnemonics, and passphrases are
  forbidden at rest.
- Allowed at-rest shapes are a TROPIC01-wrapped secret blob or an ESP32
  flash-encrypted blob after provisioning is accepted.
- Plaintext signing material may enter ESP32-S3 RAM only after local unlock,
  TROPIC01-assisted unwrap or unlock-material release, and successful local
  review state checks.
- Plaintext material is RAM-only during the unlocked session and must never be
  written to flash, logs, crash dumps, USB reports, companion descriptors, or
  debug output.
- Required wipe events are manual lock, power loss, PIN-attempt exhaustion,
  session timeout, firmware error, and debug-policy violation.
- PIN-attempt hardening must use TROPIC01 MAC-and-Destroy or a
  vendor-confirmed equivalent before production secret storage is enabled.
- Any backup/export path must be disabled by default and require local device
  review, physical approval, and explicit danger-zone copy.

The machine-readable contract is
`vectors/custody/persistent-secret-custody-v0.json`.
