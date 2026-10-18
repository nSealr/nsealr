# Feature Conformance v0

nSealr has multiple signer families with different hardware constraints.
Not every family implements every feature. When two families do implement the
same feature, the user-visible behavior and security boundary must be the same
unless this repository defines an explicit, reviewed equivalent.

The machine-readable source is:

- `vectors/features/signer-feature-matrix-v0.json`

## Rule

Each feature has a canonical `contract_id`. A solution may mark that feature as:

- `required`: part of the product goal and acceptance criteria.
- `optional`: supported only if the implementation chooses to expose it.
- `research`: allowed only as a documented research/prototype path.
- `not_applicable`: outside the product shape.
- `forbidden`: intentionally excluded because it would violate the security
  model.

If a feature is active (`required`, `optional`, or `research`), the solution
must use the canonical `contract_id` and pass the vectors behind that contract.
This keeps shared behavior aligned even when code is written in different
languages for Raspberry, ESP32, smartcard, companion, or custom hardware.

## First-Class Signer Families

- `raspberry_qr_vault`: nSealr Vault — Pi edition.
- `esp32_qr_vault`: nSealr Vault — ESP32 edition.
- `esp32_usb_nip46`: nSealr Key.
- `smartcard`: nSealr Card.
- `custom_hardware_wallet`: nSealr One.

Infrastructure repositories such as `companion`, `specs`, `lab`, `hardware`,
and `website` are not signer families by themselves. They implement, validate,
or document the contracts used by the families above.

Browser extension, npm SDK, CLI, local companion service, desktop UI, and full
NIP-46 relay-session work are also not signer families. They are companion
access surfaces. If an access-surface behavior becomes shared conformance
behavior, it should receive its own specs contract or vector without changing
the signer-family taxonomy.

## Stateless QR Vault Parity

`raspberry_qr_vault` and `esp32_qr_vault` are different platforms for the same
stateless QR vault product behavior. The matrix therefore enforces matching
feature targets for:

- request validation;
- universal Nostr event review;
- review detail pages;
- approval digest binding;
- physical approval;
- BIP-340 `sign_event`;
- static and animated QR request input;
- QR response output;
- RAM-only session custody;
- manual-only signing policy;
- trusted device display review;
- signed response verification.

The current implementation status may differ. For example, Raspberry can pass
more desktop signing fixtures today, while ESP32 keeps real signing disabled
until display, camera, button, provisioning, and firmware-hardening gates pass.
The final behavior target remains shared.

## Status Versus Target

The matrix separates `target` from `current`.

- `target` states whether the final product must support the feature.
- `current` states whether the implementation is implemented, partial, planned,
  hardware-blocked, research-only, disabled until gates pass, not applicable,
  or forbidden.

This distinction allows roadmaps to be honest without weakening the final
compatibility contract.
