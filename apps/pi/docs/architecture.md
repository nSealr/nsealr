# Architecture

`nSealr/raspberry` is the Raspberry/Pi signer implementation family. Its
first line is the Pi Zero / SeedSigner-style QR vault flow.

## Responsibilities

- Implement Raspberry/Pi signer software and OS integration.
- Receive signing requests through QR for the QR vault flow.
- Render trusted event review on a Raspberry-connected display.
- Require physical approval or rejection.
- Sign NIP-01 event ids with BIP-340 after approval.
- Return signed events through QR.
- Preserve an air-gapped, minimal-runtime security model where the hardware
  profile supports it.

## Reference Strategy

SeedSigner is a conceptual reference for QR flow, stateless operation, display
review, and minimal OS philosophy. Bitcoin/PSBT assumptions must not leak into
Nostr event signing.

Hardware compatibility should follow the same practical SeedSigner kit shape
before Nostr-specific additions are considered: Raspberry Pi Zero as the first
physical target, Pi/ZeroCam OV5647 camera input, Waveshare-compatible ST7789
240x240 SPI display HAT, HAT joystick/buttons over GPIO, removable microSD
boot media, and a SeedSigner-OS-style minimal runtime. Pi Zero 1.3 is the
high-assurance preference because it has no Wi-Fi/Bluetooth hardware; Pi Zero W
or Zero 2 W can be development targets only with wireless disabled or otherwise
mitigated before signing.

The current local hardware starting point is a Raspberry Pi Zero. That is
sufficient for board/runtime smoke planning, but complete QR vault acceptance
also requires the camera, display HAT, GPIO controls, and OS-profile evidence.

`os/stateless-qr-vault-profile.md` is the implementation-side operating profile
for future Raspberry image work. It mirrors the checked `nSealr/hardware`
OS profile: removable microSD boot media, disabled or absent wireless,
RAM-only session custody, no swap during signing, no remote access during
signing, and no persistent signing-secret storage. It is not a downloadable OS
image or a production security claim.

## Identity And Policy Boundary

The Raspberry route is pinned by the shared
`nSealr/specs` `nsealr-account-descriptor-v0` vector
`raspberry-qr-nip06-account-0`: route type `raspberry_qr_vault`, transport
`qr`, custody `stateless_session`, trusted review `device_display`, and policy
support `manual_only`.

That descriptor references `policy-manual-only-qr-vault`, whose effective
Raspberry rule is `persistent_grants: false`: every `sign_event` requires local
trusted review plus physical approval in the current session. The companion may
store labels, route metadata, account index, and policy profile ids, but it
must not turn the Raspberry QR vault into a policy-automated signer, persistent
grant target, persistent seed store, secure-element unlock path, or TROPIC01
route.
The shared `raspberry-qr-sign-event-account-0` route-selection vector is
consumed as the request-routing contract for that descriptor. It must remain
QR transport, device-display reviewed, physically approved, manual-only,
`stateless_session`, `persistent_grants: false`, and
`contains_secret_material: false`.

The final product key-source model is a RAM-only session keyring. The current
foundation can load manual BIP-39 words, SeedSigner Standard SeedQR digit
streams, SeedSigner CompactSeedQR entropy bytes, plain mnemonic text, and
NIP-19 `nsec` private keys for the current session. It can also generate
12- or 24-word BIP-39 sources and standalone `nsec`-equivalent private-key
sources into the same RAM-only source boundary, using OS randomness in normal
operation and injected entropy in tests. The package now also models the
danger-zone backup ceremony for generated material; physical display/output
acceptance remains pending. BIP-39 passphrases create
separate seed namespaces and are entered separately from public account
metadata. Policies belong to the resulting public key, but QR vault routes have
only the manual-only policy and no persistent policy state.

MicroSD/file transfer of secret material is excluded from the QR vault
acceptance model. The Raspberry microSD remains boot media. Secret export is a
separate danger-zone recovery flow with local review and physical confirmation,
not part of ordinary signing.

Feature target and current status are tracked in `nSealr/specs`
`vectors/features/signer-feature-matrix-v0.json`. The Raspberry QR vault is in
the stateless QR vault parity group with the ESP32 QR vault: features can be at
different implementation stages, but shared features must keep the same
behavior through the common `contract_id` and vectors.

## Implemented Foundation

- `nsealr_vault.qr`: v0 `nsealr1:` QR envelope helpers.
- `nsealr_vault.limits`: nSealr v0 constrained-signer implementation
  limits mirrored from `nSealr/specs`.
- `nsealr_vault.crypto`: NIP-01 canonical event serialization, event id
  computation, x-only public key derivation, and BIP-340 signing.
- `nsealr_vault.nip06`: BIP-39 seed and BIP-32 path derivation for
  `m/44'/1237'/<account>'/0/0` NIP-06 keys.
- `nsealr_vault.seed_entry`: hardware-neutral BIP-39 word-entry controller
  for future Pi display/button adapters. It validates English mnemonic words
  and checksum before deriving a one-shot NIP-06 session secret provider.
- `nsealr_vault.review`: deterministic event review model checked against
  shared `nSealr/specs` review vectors.
- `nsealr_vault.display`: deterministic trusted-display page model for raw
  event kind, signer author pubkey, complete content, complete tags, and final
  approval decisions.
- `nsealr_vault.controls`: physical-button approval session model for
  future GPIO adapters. It requires every trusted-review page to be traversed
  before approval can succeed and keeps rejection available before the final
  page.
- `nsealr_vault.hardware_flow`: hardware-agnostic QR signer orchestration
  with injected scan, display, button, and response-QR boundaries. It accepts
  static `nsealr1:` request payloads and complete animated `nsealr1a:` request
  frame sets before deriving review pages and approval digests.
- `nsealr_vault.adapters`: file-backed QR flow adapters used by the CLI and
  integration smoke tests, plus a composed button-flow adapter boundary that
  keeps scanner, trusted display, physical button input, and response QR output
  independently replaceable before real camera/display/GPIO drivers exist.
  These are development and driver-facing adapters, not production Pi drivers.
- `nsealr_vault.seed_signer_hardware`: SeedSigner-compatible 40-pin
  Waveshare-style HAT button profile and optional GPIO input adapter. It pins
  the review actions to BOARD pins from the SeedSigner hardware reference while
  keeping GPIO access injectable for tests. The adapter waits for release after
  a detected press so one held button cannot advance multiple review actions;
  it is not a completed hardware acceptance claim. The same module owns
  driver-facing Pi adapter boundaries for camera QR scanning, ST7789
  trusted-review rendering, and ST7789 response-QR display. The adapters depend
  on injected frame sources, QR decoders, draw targets, and QR matrix
  renderers, so package tests can pin behavior before physical Pi acceptance.
  The camera side now includes optional
  `picamera` JPEG capture and `pyzbar`/zbar decoding adapters that follow the
  SeedSigner Pi Zero software shape without making those libraries mandatory
  outside the Pi image. The scanner ignores unrelated decoded QR payloads and
  accumulates animated request frames until the shared QR decoder accepts the
  full frame set. The display side now includes an optional PIL
  framebuffer draw target that can present rendered review frames to a
  Waveshare/SeedSigner-style display driver object without importing that
  driver in CI, plus an optional `python-qrcode` response matrix renderer for
  signed-event QR output. The response display renders static `nsealr1:`
  responses once and newline-separated `nsealr1a:` animated output as separate
  bounded QR frames only after the static envelope or animated frame set
  decodes through the shared QR envelope parser.
- `nsealr_vault.seed_signer_hardware.SeedSignerSessionSourceQrScanner`: a
  SeedSigner-compatible camera boundary for RAM-only source import. It polls
  injected frames and QR decoder output until package-owned source parsing
  accepts Standard SeedQR, NIP-19 `nsec`, or plain mnemonic text, ignoring
  non-source QR payloads before the existing secret-hidden import-review flow
  handles approval and keyring load.
- `nsealr_vault.st7789_layout`: SeedSigner-compatible 240x240 ST7789 layout
  planner for trusted-review frames. It turns renderer-neutral frame data into
  bounded draw commands before a Pi display library or SPI driver is selected.
- `nsealr_vault.hardware_probe`: non-destructive SeedSigner-compatible
  Raspberry probe reporting for future Pi Zero hardware smoke runs. It checks
  board model, expected GPIO/SPI/camera Python modules, camera/SPI boot config
  markers, swap state, wireless absence/blocking evidence, and SSH/sshd service
  state without producing signatures or claiming hardware acceptance.
- `nsealr_vault.signer`: request handling and explicit approval gate.
- `nsealr_vault.cli`: desktop simulation CLI for JSON and QR file input and
  output.

QR decoding and signing-request validation apply the shared v0 hardening limits
before trusted review or signing. The Raspberry implementation rejects
malformed, padded, invalid UTF-8, or oversized QR envelopes and rejects unsafe
event templates, unknown signing-request fields, and resource-limit violations
using the shared invalid-vector expectations from `nSealr/specs`.

The current CLI is a development harness. It intentionally requires an explicit
`--approve` flag before producing a `sign_event` response so automated tests and
desktop experiments preserve the same approval boundary expected on real
hardware.

The `sign` and `flow` commands can use explicit development `--secret-key`,
stdin-fed `--secret-key-stdin`, NIP-06 `--mnemonic-file`, stdin-fed
`--mnemonic-stdin`, word-by-word stdin `--mnemonic-words-stdin`, Standard
SeedQR stdin `--seedqr-stdin`, or hex-encoded CompactSeedQR stdin
`--compact-seedqr-hex-stdin` plus account index, or NIP-19 `--nsec-stdin`. The
file and argument paths are desktop simulation compatibility paths. The stdin
paths better match the stateless target because session key material can be
supplied without a seed file or a process-list-visible secret argument, but
they are still development harness inputs rather than a final Pi seed-entry UX.
Real Pi adapters must keep seed material RAM-only for the current signing
session.

`MnemonicSessionSecretProvider` is the first package-owned boundary for that
future seed-entry UX. A display/button adapter supplies one BIP-39 word at a
time through `MnemonicWordInput`; package code normalizes case/whitespace,
checks the English BIP-39 wordlist and checksum, derives the NIP-06 account key,
and refuses reuse after one session. This still does not make Python strings
securely erasable memory, so it is an acceptance boundary for stateless flow
ordering rather than a production memory-hardening claim.

`--mnemonic-words-stdin` is the CLI harness for that same boundary. It reads
exactly the selected BIP-39 word count from stdin, one word per line, then
derives the same NIP-06 session key before review. It exists so desktop and lab
smokes can exercise the future display/button seed-entry contract without
introducing a seed file, persistent secret storage, or Pi-specific UI code.

`SeedQrSessionSecretProvider` is the package-owned boundary for
SeedSigner-compatible QR seed import. Standard SeedQR parses one numeric digit
stream as 12 or 24 BIP-39 English wordlist indexes; CompactSeedQR parses 16 or
32 entropy bytes and reconstructs the BIP-39 checksum through the `mnemonic`
library. Both formats are validated as BIP-39 English mnemonics before NIP-06
derivation, and both providers are one-shot RAM-only session inputs. The CLI
uses stdin/hex harnesses for tests; a real Pi camera adapter should pass decoded
QR text or bytes directly without creating seed files.

`NsecSessionSecretProvider` is the matching package-owned boundary for NIP-19
`nsec` imports and is checked against the shared `nSealr/specs` NIP-19 vector.
It decodes canonical lowercase Bech32, verifies the checksum, requires the
`nsec` human-readable prefix, requires a 32-byte private-key payload, and
refuses reuse after one session. The CLI `--nsec-stdin` harness models a future
decoded Nostr private-key QR path without adding seed files, persistent key
slots, or account-index derivation.

`session_import_review` is the shared RAM-load review boundary for those QR
vault source inputs. Given a parsed SeedQR/BIP-39 or NIP-19 `nsec` source, it
renders the same two secret-hidden pages, source fingerprint, `review_id`, and
import approval digest pinned in `nSealr/specs/vectors/session-import-reviews`.
It does not show mnemonic words, `nsec`, raw private-key bytes, derived NIP-06
keys, persistent slots, policy state, or signing approval.

Shared NIP-06 account descriptors also carry the reviewed source fingerprint,
so the Raspberry QR vault route can bind account metadata to the same RAM-only
source the user reviewed before deriving a one-shot NIP-06 session key.

`generate_bip39_session_source` and `generate_nsec_session_source` are the
first package-owned local generation boundaries. They produce source objects
for the same secret-hidden review/keyring path instead of bypassing it:
generated BIP-39 sources become checked word indexes, generated standalone
keys must be valid secp256k1 scalars, and neither path persists material or
creates policy state. `session_source_backup_flow` models the visible
backup/export ceremony by reviewing the source fingerprint and revealing
mnemonic/SeedQR or `nsec` payloads only after final-page local approval. A real
Pi UX still needs physical display/output acceptance before treating generated
material as usable user custody.

The `review-import` command is the desktop harness for that boundary. It accepts
only session-source inputs over stdin, validates and normalizes them through
package code, renders the secret-hidden import review, and writes no output
after validation failure. It deliberately excludes development raw-secret
arguments and does not share the `sign` command's approval path.

The `backup-source` command is the desktop harness for the separate
danger-zone recovery ceremony. It accepts the same normalized session-source
inputs, requires a physical-style button sequence, writes a result containing
the hidden review and transcript, and includes the backup payload only after
final-page approval. An approved result contains secret recovery material and
must stay a development/adapter artifact until physical Pi display/output
acceptance exists.

`run_session_source_backup_io_flow` is the adapter-facing version of that same
ceremony. It renders bounded backup review frames before every local button
read and sends the recovery payload to an injected output sink only after
final-page approval. Rejection, early approval, and bounded non-terminal
button streams emit no payload, so future Pi display/QR/word-output adapters
cannot bypass the danger-zone review loop.

`nsealr_vault.session_import_flow` is the package-owned import-approval loop
for future Pi seed-entry screens. It uses the same physical-review controller
shape as event signing, but its terminal action only loads a parsed source into
the stateless RAM-only keyring. Rejection, early approval, and non-terminal
button streams leave the keyring unchanged. It does not derive NIP-06 keys,
sign events, persist material, or create policy state.

The same module also owns the display/button IO loop used by real adapters.
`run_session_import_io_flow` renders a bounded import-review frame before each
local button read and uses the same approval rules and transcript model as the
button-list test harness. This keeps hardware-facing code from reimplementing
the import review, max-step bound, or keyring mutation rules.

`nsealr_vault.session_source_qr` and
`nsealr_vault.session_source_qr_import_flow` are the package-owned boundary for
future Pi camera adapters that have already decoded a session-source QR. Text
QRs are classified as NIP-19 `nsec`, SeedSigner Standard SeedQR, or plain
BIP-39 mnemonic text; CompactSeedQR entropy bytes use the matching byte-input
path. Both paths produce `SessionImportSource` objects and can be composed with
the local import-review loop so camera code does not duplicate source parsing
or load RAM-only custody before physical approval.

After a source has been locally approved and loaded,
`StatelessSessionSecretProvider` can feed the existing button-driven signing
flow exactly once. BIP-39/SeedQR sources derive a NIP-06 key from the explicit
account and passphrase supplied for that signing session; NIP-19 `nsec` sources
use the imported 32-byte key. The matching source public-key proof helper
derives the reviewed public key from the same source before signing, so
account descriptors and source fingerprints are binding metadata, not proof
substitutes. This keeps source import, account/passphrase selection, event
review, approval digest binding, and response emission as separate
package-owned steps without adding persistent QR-vault custody.
`StatelessSessionKeyring.public_key_at()` and
`StatelessSessionSecretProvider.public_key()` expose that proof boundary
directly for future adapter/account-selection code without consuming the
one-shot signing provider.

The Python keyring stores its internal copy of imported source material in
mutable slots and wipes those slots on `clear()` and destruction. This is a
best-effort package boundary for the desktop/Pi process, not a claim that
Python can erase every caller-owned immutable string, tuple, QR decode buffer,
or interpreter copy. Final Pi acceptance still has to prove process lifecycle
and power-cycle loss on the real image.

The `review` command is intentionally separate from `sign`: it takes a request,
produces deterministic review JSON, and does not sign. In desktop-only mode it
uses the deterministic fixture author pubkey; the hardware flow derives the
author pubkey from the RAM-only session key before review so the displayed
author is signer-derived and bound into the `approval_digest`.

The review model is not a UI. It is the deterministic data contract that a Pi
Zero display flow must render before approval: raw event kind, created_at,
signer author pubkey, complete content, and complete structured tags. It does
not infer kind meanings, abbreviate tag values, or add heuristic warnings. The
shared vectors prevent the Pi display flow, companion harness, and future ESP32
display work from drifting on review semantics.

The display page model is the next contract above the raw review data. It
orders the pages that a small trusted screen must show and marks the final page
as `approve_or_reject`. It is still renderer-neutral: real Pi code can map the
same page objects onto GPIO buttons, a camera loop, and the selected display
library without changing the signing contract.

`render_display_frame` is the bounded frame contract above the page model. It
turns one trusted page into a title, page indicator, wrapped body lines, and an
action hint while enforcing maximum title, body-line, and line-width limits.
This gives future ST7789/Waveshare/OLED adapters a deterministic pre-driver
oracle for text fitting before graphical rendering is implemented.

`render_review_detail_pages` is the complete constrained-display page contract
for future display adapters that need the same top-level Event/Content/Tags/
Decision model as ESP32 without forcing every wrapped line to become a top-level
approval page. It pins scroll-window indicators, compact body styles, long tag
continuation indentation, visible JSON-style escapes for decoded control
characters, and explicit codepoint fallback while preserving the existing
`screen-pages` approval digest. The CLI exposes it through
`nsealr-vault review --output-format detail-pages-json` for adapter harnesses
and manual review experiments.

`nsealr_vault.controls` is the first renderer-neutral model for that button
loop. A session starts on the first page, records which pages have been shown,
maps `next`, `approve`, and `reject` button actions, and refuses approval until
the final `approve_or_reject` page has been reached after all pages were seen.
This gives the future GPIO implementation a tested approval state machine
before any Raspberry-specific display or button driver is selected.

The button-driven hardware flow now renders those page states through
`render_display_frame` before each physical-style input. The file-backed CLI can
record the displayed frames with `--display-frame-log`, giving display adapters
a deterministic acceptance trace before real Pi display drivers are wired in.
The in-process flow result also carries the exact frame/button/decision
transcript produced during the review loop, which lets tests compare future
adapter harnesses with shared `nSealr/specs` review-transcript vectors.
The file-backed CLI can write this trace with `--review-transcript-log`, giving
cross-repo smoke tests the same oracle without importing Raspberry internals.

The SeedSigner-compatible GPIO profile is the first concrete Pi HAT attachment
point: GPIO BOARD pin 37 maps to `next`, BOARD pin 35 maps to `scroll`, BOARD
pin 33 maps to `approve`, and BOARD pin 40 maps to `reject`. The adapter checks
`reject` before `approve` when multiple pins are low so simultaneous presses do
not accidentally prefer signing.

The ST7789 layout planner is the matching display attachment point. It does not
draw pixels yet; it produces bounded commands for a 240x240 screen so the later
PIL/Waveshare/spidev adapter can be tested against positions, styles, and body
area limits before physical display acceptance.
The file-backed button harness can write that same layout trace through
`nsealr-vault flow --st7789-layout-log`, keeping display adapter acceptance tied
to the exact frames shown during review.

For future Raspberry display adapters that need the complete no-ellipsis review
body, `run_detail_button_qr_vault_flow` and `nsealr-vault flow --review-mode
detail` use the `review-detail-pages-v0` page model. `next` advances between
Event, Content, Tags, and Decision; `scroll` moves through additional windows
inside the current logical page. This mirrors the ESP32 T-Display S3 review UX
without changing the signing digest: approval is still bound to the shared
`screen-pages` `approval_digest`, and signing still requires terminal physical
approval on the Decision page.

The `screen-json` output also includes an `approval_digest`. The digest is a
SHA-256 hash of canonical request metadata, the exact event template, the
review model, and the rendered page model. It is not a secret and is not shown
as a user-authentication primitive. It gives the CLI and future device state
machine a deterministic way to reject an approved signing step if it is no
longer bound to the request that was reviewed.

The screen page model and digest calculation are checked against shared
`nSealr/specs` review-screen vectors so Raspberry and ESP32 QR vault targets
can implement the same review-to-approval contract without copying platform
code.

`review_transcript_for_screen_review` records the renderer-neutral frame shown
before each physical-style button input, the terminal decision, and the
approval state. It is checked against shared `nSealr/specs`
review-transcript vectors so Raspberry display/GPIO adapters and ESP32 firmware
adapter tests can use the same frame/button/decision oracle.
The stricter `run_detail_button_qr_vault_flow` path also consumes detail-mode
review-transcript vectors, including `scroll` actions inside long Content or
Tags windows. This keeps the no-ellipsis constrained-display path aligned with
ESP32 without forcing every scroll window before the Decision page.

## Hardware Flow Boundary

`nsealr_vault.hardware_flow` defines the first Raspberry QR vault flow
orchestrator. It is intentionally pure Python and hardware-agnostic:

- camera drivers provide `scan_request_qr`;
- display/button drivers provide `show_review`;
- QR output drivers provide `emit_response_qr`.

The flow decodes one request QR, renders trusted screen pages, obtains physical
approval through the injected I/O boundary, signs with the displayed
`approval_digest`, and emits one response QR. Real camera, display, and GPIO
drivers must attach to this boundary rather than bypassing the review model.

The `nsealr-vault flow` command is the current file-backed harness for this
boundary. It reads a QR request from a file, writes the exact screen-review JSON
that a trusted display must render, requires explicit `--approve`, and writes a
QR response. It is for desktop integration and hardware-adapter development,
not for production key custody.

`run_button_qr_vault_flow` is the stricter hardware-facing boundary. Instead of
accepting one boolean from `show_review`, it renders one page at a time through
`display_review_frame`, reads `next`, `approve`, or `reject` through
`read_review_button`, and delegates the state machine to
`ReviewControlSession`. This keeps physical approval impossible until every
trusted page has been displayed and the final approve/reject page has been
reached. The loop also bounds non-terminal button streams so an adapter cannot
hang forever by repeatedly returning `next` on the final page. Its result
includes the review transcript actually shown and acted on. Real GPIO/display
adapters should attach to this boundary first.

`run_button_qr_vault_flow_with_secret_provider` is the stateless hardware-facing
variant for future Pi flows. The secret provider is called after request QR
decode and before review so the signer-derived author pubkey can be displayed
and bound into the `approval_digest`. That key material must remain RAM-only for
the current signing session; early rejection still refuses to sign and emits a
rejection response, but it is not a no-key-loaded path. The older
`run_button_qr_vault_flow` helper stays as a compatibility wrapper for the
desktop harness.

The file-backed adapters live in package code rather than private CLI classes.
This keeps the CLI as a thin adapter and gives future Raspberry camera,
display, and GPIO drivers a concrete behavioral reference for when review JSON,
display-frame logs, button input, and response QR output are allowed to occur.

`ComposedButtonQrVaultIO` is the first non-file adapter boundary for that same
flow. It delegates request scanning, frame display, button reads, and response
QR output to four small interfaces, so a future Pi camera, display library,
GPIO button module, and QR response renderer can be swapped independently while
the review/signing state machine stays unchanged.

The first real adapter pass should map that boundary to SeedSigner-compatible
hardware rather than inventing a separate Raspberry kit: camera scanning from
the Pi CSI camera path, review rendering onto the ST7789 240x240 display,
navigation/approve/reject through the Waveshare HAT GPIO button layout, and
response QR rendering on the same display. SeedSigner code remains a reference
for hardware behavior and OS shape; nSealr owns the Nostr event parser,
review contract, signing contract, and stateless session flow.

`PiCameraJpegFrameSource` and `PyzbarQrDecoder` are the first concrete optional
camera pieces for that path. On a Pi image they compose into
`create_seed_signer_camera_qr_scanner()` using `picamera`, PIL, and
`pyzbar`/zbar; in CI they are tested through fakes and remain absent unless the
Pi runtime installs them.

`SeedSignerSessionSourceQrScanner` reuses the same camera and QR-decoder
boundary for the session-source side of the product. It does not load a key by
itself. It only converts a supported decoded source QR into a
`SessionImportSource`; raw CompactSeedQR byte payloads are tried before the
UTF-8 text fallback so binary SeedSigner exports can use the same review gate.
`SeedSignerSessionSourceImportIO` and
`run_seed_signer_session_source_qr_import_flow` then compose that scanner with
the ST7789 review-display boundary, SeedSigner-compatible buttons, and the
stateless keyring. The composed flow displays the secret-hidden review before
every button read and loads the RAM-only source only after final-page approval.
This is still an adapter contract tested with fakes; real Pi camera/display/
GPIO acceptance remains a separate hardware smoke step.

`PillowSt7789DrawTarget` is the matching optional framebuffer bridge for the
trusted-review display path. It consumes the already bounded ST7789 layout
commands, draws rectangles and text into a 240x240 PIL image, and hands that
image to an injected presenter. A later Pi-specific presenter can wrap a
Waveshare or SeedSigner ST7789 driver, while tests keep the framebuffer path
independent from physical SPI/display libraries.

`PythonQrcodeMatrixRenderer` is the matching optional renderer for signed-event
response QR output. It uses `python-qrcode` when available in the Pi image,
validates the resulting matrix, and feeds the same centered ST7789 response
display adapter that tests already exercise with injected matrices. Animated
responses are split into their individual `nsealr1a:` frames before rendering,
so the hardware path cycles validated QR frames instead of encoding a
multi-line frame list as one QR or displaying malformed frame data.

`nsealr-vault hardware-probe` is the first command intended for a later physical
Pi Zero session. It is deliberately read-only and conservative: missing files,
missing modules, or unverifiable wireless evidence produce `blocked` checks
rather than implicit success. It also checks SSH/sshd systemd service state and
returns deterministic `acceptance_blockers` plus `human_actions_required` for
anything that still needs operator setup. A passing probe is only setup
evidence; camera QR quality, trusted display readability, GPIO approval
behavior, OS image acceptance, and production security still need separate
reports.

The hardware repo now carries the matching full-flow report template for that
later Pi Zero session. A completed Raspberry QR-flow report must prove the
camera scanned `nsealr1` request QR frames, the trusted display rendered the
Event/Content/Tags/Decision review, GPIO buttons drove
`next`/`scroll`/`approve`/`reject`, the device emitted the signed-event
response QR only after approval, the companion verified the response against
the request, and the session used no USB data transport, persistent secret, or
TROPIC01.
