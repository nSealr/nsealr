# Identity, Recovery, And Policy Contracts v0

nSealr v0 separates signer custody from companion routing. These contracts
describe which signer owns an identity, how that identity can be recovered, and
which policy or grant metadata may be stored by the companion or test harnesses.

These files do not authorize companion-side production private-key custody. They
are routing and safety metadata for the five existing signer families.

## Current Product Model

The current official nSealr model is key-source first and account second. A
key source can be a BIP-39 mnemonic, the same mnemonic with a BIP-39
passphrase, a standalone imported or generated Nostr private key, a smartcard
slot, a future persistent device slot, or an external NIP-46 signer route. The
signing account is the resulting public key. Policy attaches to that final
public key and signer route, not to the mnemonic container itself.

NIP-06 seed-based accounts use the path
`m/44'/1237'/<account>'/0/0`. A BIP-39 passphrase is a separate seed namespace,
not an extra word stored in the account descriptor. The same mnemonic with a
different passphrase produces different Nostr public keys, and each resulting
public key has its own policy profile.

Generated versus imported material is provenance metadata. The functional
custody distinction is whether a key source is a seed profile that can derive
multiple NIP-06 accounts, a standalone Nostr private key for one identity, a
card/device slot, or an external signer route.

## QR Vault Session Keyring

Raspberry and ESP32 stateless QR vaults use a RAM-only session keyring. During a
single power/session window, that keyring may contain multiple BIP-39
mnemonics, optional passphrase namespaces, NIP-06 account selections,
standalone imported `nsec`/private keys, and locally generated mnemonic or
standalone-key material. None of that material may be persisted by the QR vault.

The QR vault import goals are:

- manual BIP-39 word entry;
- SeedSigner Standard SeedQR;
- SeedSigner CompactSeedQR;
- plain BIP-39 mnemonic QR;
- Nostr `nsec` QR or equivalent private-key QR;
- local generation of BIP-39 mnemonics and standalone Nostr keys.

Secret export from a QR vault, when implemented, is an advanced recovery path:
BIP-39 words, SeedQR/CompactSeedQR, or `nsec` QR output must require explicit
danger-zone review and physical confirmation. Normal signing flows do not need
secret export. MicroSD/file import or export of secret material is outside the
stateless QR vault product model; Raspberry microSD is boot media only.

SeedSigner-compatible SeedQR support is intended to let users who already hold a
BIP-39 mnemonic for Bitcoin derive Nostr identities with NIP-06. This does not
import Bitcoin descriptors, xpubs, PSBT state, or wallet policy, and it must
warn that compromise of the shared mnemonic compromises both Bitcoin and Nostr
identities even though derivation paths differ.

## Persistent Device Vault

ESP32 USB/NIP-46 and custom persistent-secret hardware wallets are persistent
device-vault lines. Their product goal is an encrypted device vault that can
hold seed profiles, passphrase namespaces, NIP-06 account selections,
standalone private-key slots, account labels, and per-public-key policy state.

The v0 product decision is one device-level unlock PIN or equivalent unlock
ceremony for the device vault, not separate PINs per mnemonic or standalone
key. A later product version can add per-profile locks only if the threat model
and UX justify the added complexity.

Persistent-device policy state is authoritative only at the signing
authorization boundary. The companion may cache labels, routes, capabilities,
policy ids, pending proposals, and audit pointers, but it is not the authority
that can silently change a device policy.
Persistent-device accounts start from a manual-only policy profile; scoped
automation is a separately reviewed policy state, not the default.

## Files

- Account descriptors: `vectors/accounts/*.json`
- Policy profiles: `vectors/policies/*.json`
- Grant descriptors: `vectors/grants/*.json`
- Policy-decision transcripts: `vectors/policy-decisions/*.json`
- Policy-change review transcripts: `vectors/policy-changes/*.json`
- Schemas:
  - `schemas/account-descriptor-v0.schema.json`
  - `schemas/policy-profile-v0.schema.json`
  - `schemas/grant-descriptor-v0.schema.json`
  - `schemas/policy-decision-vector-v0.schema.json`
  - `schemas/policy-change-review-v0.schema.json`

## Account Descriptor

`nsealr-account-descriptor-v0` binds an `account_id` and public key to an
explicit signer route, recovery metadata, capability metadata, and a policy
profile id.

Allowed route types are:

- `raspberry_qr_vault`
- `esp32_qr_vault`
- `esp32_usb_nip46`
- `smartcard`
- `custom_hardware_wallet`
- `external_nip46`

Account descriptors must not contain `secret_key`, `private_key`, `nsec`,
`mnemonic`, `seed`, `passphrase`, or `nip49_ciphertext` fields. Recovery data
may identify a NIP-06 path, ESP32/device slot, display-less smartcard slot,
custom hardware-wallet slot, or external signer, but it must not embed the
recoverable secret.

Account descriptors identify public routing state for a resulting signing
identity. They are not key-source backup files and are not a substitute for a
device vault, card applet, QR session, or external signer.

Stateless QR vault routes must use:

- `transport: "qr"`
- `custody: "stateless_session"`
- `policy_support: "manual_only"`
- `persistent_grants: false`

They must not reference TROPIC01 or any persistent key-at-rest mechanism.

## Policy Profile

`nsealr-policy-profile-v0` describes the policy mode for one or more route
types. `manual_only` means every signing operation needs route-specific
explicit approval: local review and physical approval on trusted-display
devices, or explicit external review acknowledgement for display-less custody.
`scoped_automation` is only allowed for route families that have an explicit
policy authority, expiry, rate-limit, revocation, audit-log, and
device-policy confirmation constraints. In v0 this means ESP32 USB/NIP-46 and
custom hardware-wallet routes, plus external NIP-46 interoperability where the
external signer owns the policy. It does not apply to stateless QR vaults or
display-less smartcards.

Policy profiles are internal nSealr records. They are not Nostr events, are
not accepted from relays as authority, and are not updated by the companion
alone. Installing, updating, disabling, or deleting an authoritative device
policy requires local device review and physical approval on routes that have a
trusted display. Display-less routes must keep an explicit external-review
acknowledgement boundary.

The exact user-facing policy menu is intentionally not frozen in v0, but the
policy-profile vocabulary is closed. `manual_review_required`,
`forbidden_permissions`, and `risk_tiers` must use the enum sets in
`policy-profile-v0.schema.json`; adding a new knob requires a specs revision,
vectors, and downstream parser updates. The current `scoped_automation` fixture
is a minimal safety contract used to test the boundary: scoped account, route,
client, method, event kind when relevant, expiry, rate limit, revocation, audit
event, and device confirmation. It is not a final product claim that kind `1`
is the only useful grant or that every future route should expose many policy
knobs. Default product behavior remains manual review through
`policy-manual-only-persistent-device` unless a device locally accepts a
digest-bound policy-change proposal.

QR vault policies and display-less smartcard policies must remain
`manual_only` with `grants_allowed: false`.

Policy profiles must forbid wildcard grants and secret export. Decrypt,
unknown, relay-switching, delete, and other high-risk methods remain manual
until a later risk model adds stricter source-backed semantics.

## Grant Descriptor

`nsealr-grant-descriptor-v0` records one explicit grant for a non-QR route.
Grants must be scoped by account, route, client pubkey, method, and method
parameter when relevant. `sign_event` grants must pin both the string
permission parameter and the integer event kind.

Grant descriptors are deliberately narrow v0 session grants. They must include:

- expiry;
- rate limit;
- device policy confirmation;
- revocation support;
- audit event format.

Wildcards are invalid. Stateless QR vault routes are invalid grant targets.
There is no separate "allow once" grant mode in v0; a one-use grant is modeled
as the same scoped session grant with `rate_limit.max_uses: 1`, avoiding a
second grant decision field whose lifetime cannot be audited without extra
state.

## Policy Decision Transcript

`nsealr-policy-decision-vector-v0` records deterministic policy outcomes for
future persistent-route automation without creating a grant store or relay
session. v0 decisions are:

- `allow` when a matching grant is scoped to the account, route, client,
  method, event kind, and is neither expired nor revoked;
- `deny` when the permission is forbidden, the matching grant is expired, or
  the matching grant is revoked;
- `manual_review` when decrypt requests, unknown methods, manual-only routes,
  or requests without a matching grant must stay outside automation.

Every decision carries a deterministic `nsealr-grant-audit-event-v0` object so
future stores can be audited without changing the decision semantics. These
vectors do not authorize companion-side private-key custody, persistent grant
storage, `connect` acknowledgements, or NIP-46 relay sessions.

## Policy Change Review

`nsealr-policy-change-review-v0` records the minimum contract for changing a
persistent device account from the default manual-only profile to a scoped
automation profile. The proposal is secretless and can be transported by the
companion, browser extension, SDK, CLI, or desktop app, but it is never
authoritative by itself.

The v0 action is deliberately narrow: `set_policy`. A proposal binds:

- account id and route type;
- current and proposed policy ids;
- proposed grant descriptor ids;
- requesting surface and client public key;
- `device_review_required: true`;
- `physical_approval_required: true`;
- `companion_authoritative: false`;
- `contains_secret_material: false`.

The review pages and `approval_digest` are deterministic, so a device can show
the exact policy transition and grant ids before accepting the change. This
does not create a grant store, does not enable production signing, and does not
let the companion mutate device policy without local review.

## Change Control

Changing identity, policy, or grant semantics requires updating schemas,
vectors, `scripts/verify_specs.py`, downstream companion validation, and lab
integration. Compatibility paths are allowed only when attached to an explicit
route type and tested; stale or unowned legacy behavior must be removed or
rewritten.
