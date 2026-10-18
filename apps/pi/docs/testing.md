# Testing

## Current Baseline

```sh
make ci
```

The baseline runs repository verification, Python unit tests, bytecode
compilation, and `pip check`.

`make setup` installs the local package with pip's in-tree build mode when the
local pip still exposes that feature flag, so lab integration logs do not
include the legacy out-of-tree build deprecation warning from older Python 3.9
virtual environments. Newer pip releases that already use in-tree builds by
default are left unchanged.

## Implemented Tests

- QR envelope round-trip tests.
- QR envelope encode-side limit tests proving static v0 QR writers reject
  payloads that would exceed `max_static_qr_decoded_json_bytes` before emitting
  an envelope.
- Animated QR frame-set tests against the shared specs vector, including
  reversed input order, missing-frame rejection, checksum rejection, and
  `nsealr-vault` CLI `qr-animated` request/response output.
- NIP-06 derivation tests against the canonical account `0` shared vector.
- Shared identity/policy boundary tests proving the Raspberry account
  descriptor uses `nsealr-account-descriptor-v0`, route `raspberry_qr_vault`,
  `policy-manual-only-qr-vault`, stateless custody, manual-only policy support,
  `persistent_grants: false`, and the shared
  `raspberry-qr-sign-event-account-0` route-selection vector with secretless QR
  transport routing.
- Signing tests against `nSealr/specs` fixtures.
- Review model tests against every shared review vector for raw event kind,
  created_at, signer author pubkey, complete content, and complete structured
  tags.
- Desktop CLI smoke test for QR request review output without a secret key.
- Trusted-display page tests for event, content, tag, and final
  approval-decision pages.
- Trusted-display screen review tests against every shared
  `nSealr/specs` review-screen vector.
- Bounded trusted-display frame tests for deterministic title truncation,
  body-line wrapping, page indicators, and action hints before real display
  drivers exist.
- Trusted-display frame conformance tests against shared `nSealr/specs`
  review-display-frame vectors.
- Trusted-display detail-page conformance tests against shared
  `nSealr/specs` review-detail-page vectors, covering complete physical
  Event/Content/Tags/Decision pages, scroll-window indicators, compact line
  styles, continuation indentation, visible JSON-style control escapes,
  explicit codepoint fallback, and unchanged approval digests.
- Physical-button approval session tests that require all trusted-review pages
  to be traversed before approval while allowing early rejection.
- Review transcript tests against shared `nSealr/specs` vectors, covering
  displayed frame, button sequence, terminal decision, and approval state.
- Detail-mode review transcript tests against shared `nSealr/specs` vectors,
  covering `Next/Scroll` traversal across long tag windows without changing the
  `screen-pages` approval digest.
- Approval-digest tests proving an approved signing request is rejected when
  the digest no longer matches the rendered review pages.
- Desktop CLI smoke test for QR request review output as `screen-json`.
- Desktop CLI smoke test for QR request review output as one bounded
  `display-frame-json` frame.
- Desktop CLI smoke test for QR request review output as complete
  `detail-pages-json` constrained-display pages.
- Negative CLI review test proving host-supplied `id` fields are rejected
  before review output is written.
- Approval rejection tests.
- Approved signing response tests.
- Hardware-agnostic QR vault flow test with in-memory camera, display/button,
  and response-QR I/O.
- Button-driven QR vault flow tests proving page-by-page traversal before
  approval, early rejection without signing, animated request scan decoding,
  and bounded failure for non-terminal button streams.
- RAM-only secret-provider tests proving future stateless Pi adapters load
  session key material before review to derive the displayed author pubkey,
  while still refusing to sign unless complete review traversal and physical
  approval succeed.
- BIP-39 seed-entry boundary tests proving word-by-word mnemonic input is
  normalized, checked against the English wordlist/checksum, consumed once, and
  usable as the NIP-06 session secret provider for the button-driven flow.
- Button-driven display-frame log tests proving future display adapters receive
  bounded frames before physical-style input is consumed.
- Button-driven flow transcript tests proving the displayed frame/button/
  decision trace can match shared `nSealr/specs` review-transcript vectors
  under transcript-compatible display limits.
- CLI transcript-log tests proving the file-backed button harness can export
  that trace for cross-repo integration and future adapter acceptance tests.
- Detail button-flow tests proving complete Event/Content/Tags/Decision pages
  can use top-level `next` navigation, intra-page `scroll`, preserved
  detail-page indicators/body styles, and the CLI `--review-mode detail` path
  without changing the shared `screen-pages` approval digest.
- File-backed adapter tests proving request scanning, review JSON writes,
  display-frame log writes, button exhaustion, and response QR output are owned
  by package code rather than private CLI classes.
- Composed adapter tests proving future scanner, trusted-display,
  physical-button, and response-QR components can plug into the button-driven
  QR flow without bypassing review traversal or approval-digest binding.
- SeedSigner-compatible GPIO profile tests proving the 40-pin HAT BOARD pin
  map is stable, all buttons are configured as pull-up inputs, right/down/
  center/KEY1 map to `next`/`scroll`/`approve`/`reject`, and no press times out
  deterministically under injected GPIO. The GPIO adapter tests also prove a
  physical button must be released before the action is returned, preventing a
  held button from becoming multiple review actions, and stuck buttons fail
  deterministically when a release timeout is configured.
- SeedSigner-compatible ST7789 layout tests proving trusted-review draw
  commands stay within the 240x240 display, preserve meta/value/normal body
  styles, and reject body layouts that would overlap the footer/action area.
- SeedSigner-compatible driver-facing adapter tests proving camera QR scanning
  polls injected frames until a nSealr request payload is decoded, ignores
  unrelated QR payloads, collects complete animated request frame sets, ST7789
  review rendering applies bounded layout commands to an injected draw target,
  and ST7789 response-QR rendering draws a validated centered matrix with a
  quiet zone, including bounded cycling for decoded-valid animated `nsealr1a:`
  response frame sets and rejection of malformed static, malformed animated,
  mixed, or non-nSealr response payloads.
- SeedSigner-compatible session-source camera scanner tests proving non-source
  QR payloads are ignored until a supported RAM-only source QR is decoded into
  a package-owned `SessionImportSource`, including CompactSeedQR byte payloads,
  and unsupported streams time out deterministically without loading the
  keyring.
- SeedSigner-compatible session-source import IO tests proving the camera
  scanner output is displayed through the bounded import-review frame path
  before each local button read, final-page approval loads the stateless
  keyring, rejection leaves it empty, and bounded non-terminal button streams
  fail without loading source material.
- Optional Pi camera adapter tests proving `PiCameraJpegFrameSource` captures
  JPEG bytes through a `picamera`-style object and `PyzbarQrDecoder` preserves
  raw QR payload bytes for CompactSeedQR while text callers decode UTF-8 only
  at the scanner boundary, returns `None` when no QR is present, and rejects
  unsupported QR payload objects.
- Optional ST7789 framebuffer tests proving `PillowSt7789DrawTarget` maps
  bounded layout rectangles/text to a PIL-style image and calls an injected
  presenter without requiring a physical display driver.
- Optional response QR renderer tests proving `PythonQrcodeMatrixRenderer`
  calls a `python-qrcode`-style factory, returns a square boolean matrix, and
  rejects non-boolean matrix values before the display adapter draws them.
- CLI ST7789 layout-log test proving the button-driven flow can export bounded
  SeedSigner-compatible draw commands for every displayed review frame.
- File-backed `nsealr-vault flow` CLI test proving the hardware-style path writes
  screen-review JSON and a signed response QR.
- Cross-repo lab integration verifies the file-backed QR flow output through
  `nSealr/companion` `nsealr verify-response`, proving the signed response QR
  can be checked by the host-side companion contract.
- Desktop CLI smoke test for QR request input and QR response output.
- Desktop CLI smoke test for QR request signing from a NIP-06 mnemonic file.
- Desktop CLI smoke tests for stdin-fed secret key and stdin-fed NIP-06
  mnemonic inputs on both `sign` and button-driven `flow`, keeping development
  harnesses closer to the stateless RAM-only target than shell-argument or
  seed-file-only paths.
- Desktop CLI smoke tests for word-by-word BIP-39 stdin input on both `sign`
  and button-driven `flow`, proving the package-owned seed-entry validator is
  reachable through the CLI without introducing seed files or persistent
  storage.
- SeedSigner Standard SeedQR and CompactSeedQR import tests for RAM-only
  BIP-39/NIP-06 session loading. The tests use SeedSigner-published vector 1
  for both the Standard digit stream and Compact entropy bytes, cover one-shot
  session-provider behavior, and exercise `sign`/`flow` stdin harnesses without
  importing Bitcoin descriptors, xpubs, PSBTs, wallet policy, or microSD/file
  secret transfer.
- NIP-19 `nsec` import tests proving lowercase Bech32 checksum validation,
  `nsec` prefix enforcement, 32-byte payload enforcement, one-shot RAM-only
  session-provider behavior, consumption of the shared `nSealr/specs` NIP-19
  vector, and `sign`/`flow` stdin harness coverage without writing output after
  invalid input.
- Session import review tests proving SeedQR/BIP-39 and NIP-19 `nsec` session
  sources produce the shared secret-hidden review pages, `review_id`,
  fingerprint, and import approval digest from
  `nSealr/specs/vectors/session-import-reviews` without leaking mnemonic words,
  `nsec`, raw private-key bytes, persistence, derivation, or signing approval.
- Identity tests also assert the Raspberry NIP-06 account descriptor's recovery
  fingerprint matches the same shared RAM-only import-review fingerprint for
  the canonical account-0 source.
- Desktop CLI `review-import` smoke tests proving stdin-fed Standard SeedQR
  and NIP-19 `nsec` sources write those same secret-hidden RAM-load reviews,
  and invalid import sources fail before output files are created.
- Session import flow tests proving a parsed source loads into the stateless
  RAM-only keyring only after local traversal to the final import decision page
  and approval, while rejection, early approval, and non-terminal button
  streams leave the keyring empty. Keyring tests also prove the package-owned
  mutable source slots are wiped on `clear()`.
- Decoded session-source QR tests proving future Pi camera adapters can route
  text QRs for NIP-19 `nsec`, SeedSigner Standard SeedQR, and plain BIP-39
  mnemonic text, plus CompactSeedQR entropy bytes, through package-owned
  parsing and the same local import-review/keyring gate.
- Session-source generation tests proving generated 12-word BIP-39 and
  standalone `nsec`-equivalent sources enter the same secret-hidden RAM-only
  source boundary, deterministic test entropy is supported, invalid
  secp256k1 scalar material is rejected, and generated secrets do not appear
  in the source review output.
- Session-source backup tests proving BIP-39 words/SeedQR and NIP-19 `nsec`
  recovery payloads match shared `nSealr/specs` backup vectors and are revealed
  only after the separate danger-zone review reaches the final approval page.
- Session-source backup IO tests proving bounded danger-zone review frames are
  displayed before local button reads, approved flows emit the recovery payload
  to an injected output sink only after final-page approval, and rejection or
  bounded non-terminal button streams emit nothing.
- Desktop CLI `backup-source` smoke tests proving the same danger-zone recovery
  ceremony is reachable through stdin-fed session sources, rejected flows do
  not reveal payloads, early approval writes no output, and approved review
  pages still do not leak secret material.
- Imported-source secret-provider tests proving approved BIP-39/SeedQR and
  NIP-19 `nsec` sources can feed the existing button-driven signing flow once,
  with NIP-06 account/passphrase selection explicit and no persistent storage.
- Source public-key proof tests consume shared
  `vectors/source-public-key-proofs/*.json` fixtures and derive the expected
  reviewed public key from NIP-06 and NIP-19 `nsec` session sources.
- Stateless keyring/provider public-key tests prove future account-selection
  code can derive the reviewed author public key from the selected RAM-only
  source before the one-shot signing provider is consumed.
- Shared nSealr v0 implementation-limit conformance test against the
  `nSealr/specs` limits profile.
- Shared pre-signing invalid-vector rejection for unsafe event templates,
  resource-limit violations, and malformed QR requests where the Raspberry
  parser owns the boundary.
- Project tooling test requiring `make setup` to use pip in-tree builds for
  clean cross-repo integration logs.
- OS profile note test requiring future Raspberry image work to preserve the
  stateless QR vault operating boundary: removable microSD, no swap, no remote
  access, RAM-only custody, no persistent signing-secret storage, and no
  TROPIC01 requirement.
- SeedSigner-compatible hardware probe tests proving a complete fake Pi Zero
  profile reports ready with remote access disabled, a non-Pi environment
  reports blocked, active SSH fails readiness, blocker IDs map to human-action
  prompts, and the `nsealr-vault hardware-probe --out` CLI writes a safe report
  without requiring hardware.

## Next Tests

- SeedSigner-compatible Pi Zero board/runtime smoke planning against the
  available Raspberry Pi Zero using `nsealr-vault hardware-probe`.
- Fill the validated
  `nSealr/hardware/templates/raspberry-qr-vault-full-flow-smoke.json`
  template only after a real Pi Zero run proves camera `nsealr1` QR scanning,
  trusted display review, GPIO `next`/`scroll`/`approve`/`reject`, response QR
  output, companion `verify-response`, request id and `approval_digest`
  binding, no USB data transport, and RAM-only custody.
- Physical OV5647/ZeroCam camera scan testing with the optional
  `picamera`/`pyzbar` adapters, physical ST7789 presenter integration on a
  Waveshare-compatible 240x240 display HAT, response-QR readability/scan-back,
  and GPIO approval/navigation tests before Raspberry Pi hardware acceptance
  testing.
- Real hardware adapter tests against the existing transcript oracle once
  camera/display drivers are selected, the ST7789 layout plan is rendered on
  the display HAT, and the SeedSigner-compatible GPIO profile is exercised on
  the Pi HAT.
Hardware tests must record board, camera, display, OS image, commit, and exact
procedure.

## Single-Repository CI

Unit tests prefer the sibling `nSealr/specs` repository when the full local
workspace is present. GitHub Actions checks out `nSealr/raspberry` by itself,
so tests fall back to fixture snapshots under `tests/fixtures/specs` in
single-repository CI. Cross-repository drift remains guarded by
`nSealr/lab` integration, which runs against the live sibling repositories.

The Raspberry QR vault must remain stateless and RAM-only while consuming those
hardening vectors. Rejection conformance must not introduce persistent secret
storage or TROPIC01 dependencies.
