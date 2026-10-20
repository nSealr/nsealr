#!/usr/bin/env python3
"""Make current navigation and contract prose match the declared migrated product."""
import argparse,json,re
from pathlib import Path
from rehearse import canonical,digest
from transforms import Changes

def apply(target,output):
 output.mkdir(mode=0o700);c=Changes(target)
 path='README.md';s=(target/path).read_text().replace('- `boards/`, `tests/`, `ci/`, `scripts/`: experimental profiles, fixtures and checks inherited from the measured baseline. A profile file is not hardware qualification.','''- `apps/bridge/`, `packages/`: host clients, CLI, service, browser integration and the sole public TypeScript SDK. Internal packages are private.
- `apps/pi/`: retained Python QR reference/application harness; engine adoption and physical Pi qualification remain separate tasks.
- `protocols/contracts/v1/`: one authoritative artifact shared by independent Python, Rust and TypeScript consumers.
- `boards/`, `tests/`, `ci/`, `scripts/`: experimental profiles and software checks. A profile file is not hardware qualification.''').replace('- `docs/restart/`: the accepted restart direction, migration gates and resumable work graph.','- `plan/work-items.json`: the sole task graph; `plan/evidence-index.json` binds immutable historical evidence.\n- `docs/product/`: current product requirements; `docs/restart/` preserves decisions and historical review evidence.')
 s=s.replace('Host and Pi code currently remain in their original repositories until selected code has migrated and passed its gates. We are consolidating ownership, not claiming consolidation has already happened.','Selected host and Pi code now share this source checkout. Their original licensed source identities and declared migration changes remain recorded in A02 evidence. The Board SDK stays independent and Nostr-free; custom hardware is not a product build prerequisite.')
 start=s.index('## Build the existing Rust baseline');end=s.index('## Project boundaries',start)
 s=s[:start]+'''## Build and verify

Use the [pinned product bootstrap](tools/baseline/README.md) for a clean Linux
x86_64/glibc runtime. With those tools on PATH:

```sh
pnpm install --frozen-lockfile
make ci
```

The complete gate covers independent contracts, core and host Rust workspaces,
Bridge packages and packed consumers, Pi, source/evidence integrity and the
17-step product integration. `make integration` runs that integration separately.
Rust target compilation, coverage floors and reproducibility remain mandatory.
Installed browsers, live relays, attached boards and physical security require
separate evidence; successful software checks do not qualify a device release.

'''+s[end:];c.put(path,s.encode())
 path='crates/nsealr-core/Cargo.toml';s=(target/path).read_text().replace('no_std backbone crate for the nSealr firmware family (empty scaffold; logic ported in later tasks).','Portable no_std Nostr protocol, review, policy and session core for nSealr.');c.put(path,s.encode())
 path='crates/nsealr-core/src/lib.rs';s=(target/path).read_text();start=s.index('//! This crate is');end=s.index('//! # Build configuration',start);s=s[:start]+'''//! This crate contains the portable Rust protocol, transport framing, review,
//! policy and session foundations used by the host conformance harness and
//! intended device adapters. The separate Python Pi implementation remains an
//! independent oracle until its explicitly reviewed engine adoption. Compiling
//! this crate does not qualify an MCU application, custody or physical review.
//!
'''+s[end:];s=s.replace('//! Phase 03 ports the C++ `host_core` logic into this crate one milestone at a\n//! time. Ported so far:','//! Implemented modules include:');c.put(path,s.encode())
 c.put('docs/bridge/architecture.md',b'''# Bridge implementation boundaries

Current product requirements live in [the product contract](../product/contract.md).
This document describes the integrated host implementation. The generated
[SDK API inventory](api.md) and [API boundary review](api-review.md) identify the
actual public surface and its limits. Original companion architecture prose is
preserved in source history at commit 678796900e462f5504e47fe934e2e5f23d85824f.

`apps/bridge` owns the CLI, local service, browser extension and development
consumer examples. `packages` contains private implementation modules and the
sole public `@nsealr/sdk`. The SDK root and browser entrypoint contain browser-safe
namespaces. The explicit Node entrypoint adds host client, framing and NIP-46
helpers. Packed runtime and declarations contain owned code, with explicit
third-party production dependencies and their original license distributions.
Fixtures and development signing helpers are outside the production package.

Bridge prepares requests and untrusted previews, transports messages and verifies
responses. It cannot approve device actions or hold user signing keys. Identity
selection, origin permission, local grants and device consent are separate
boundaries. Host policy metadata cannot silently mutate authoritative device
policy. Route dispatch is unavailable until an explicit dispatcher is supplied;
responses bind the original request and selected public key before acceptance.

The local client keeps bounded request correlation, cancellation and timeout
handling. Native messaging is an explicitly injected exchange. Pairing, storage
and native-host installation use digest-bound review and approval artifacts;
file output uses the reviewed destination. These software APIs do not establish
production installer UX, storage custody or physical transport qualification.
Card routes and APDU implementations are retired. Host review acknowledgements
are unsupported and cannot bypass an active route's review requirements.

The protocol module owns request and response validation. Core owns event
serialization, hashing and verification. QR and serial framing handle bounded
encoding, checksums and payload parsing before routing. Serial stream adapters
retain their byte, line, pending-operation and lifecycle bounds. The Pi harness
and Rust host harness consume the same authoritative contracts while preserving
independent cryptographic/review implementations. No sibling fixture snapshot is
an accepted fallback.

Pure NIP-46 helpers parse descriptor or already-decrypted metadata and validate
request/response steps. The explicit Node session manager and relay adapter have
separate runtime side effects: authenticated transport authors, independently
resolved user identity, signed encrypted messages, bounded pending requests,
terminal close and wiping of the owned client transport-key copy. Metadata does
not restore or authenticate a runtime session. Transport credentials are not
user signing-key custody. Detailed S01 identity, retry and resource bounds remain
in the API boundary review and retained tests.

Browser extension permission, review and approval controls remain secretless.
Deterministic package manifests and VM/DOM checks do not prove installed browser
compatibility. The retained Firefox target still uses a service-worker manifest;
Firefox background execution needs separate C01/P02 qualification and repair.
No universal Firefox compatibility is claimed by package test success.
''')
 c.put('docs/bridge/testing.md',b'''# Bridge verification

Run `pnpm ci` from the product root after the frozen dependency install. This
executes build/type checking, all retained Vitest cases, consumer/examples/README
checks, generated API and boundary review checks, registry/import/browser gates,
release-output safety and an actual isolated packed SDK consumer.

The packed check installs the tarball outside the workspace and verifies Node
behavior, root/browser namespace boundaries, strict TypeScript imports, browser
bundling/execution without Node globals and rejected hidden imports. Runtime
external imports must each have an explicit production dependency. Browser VM
execution is not installed-browser qualification.

`make integration` executes all seventeen retained product integration steps in
one invocation, including the independent Pi review/sign/verify flow. Source
and contract tamper controls, optional Chromium/serial helper unit tests and
admitted production-claim, validator-ownership, CLI-guide and recipe guardrails
run in ordinary product CI. Optional actual browser/device commands are separate.

Card implementation cases are deliberately retired; retained ordinary route
checks and new card-command/route rejection cases preserve active safety bounds.
The exact before/after case correspondence is migration evidence, not a replacement
for running tests. The unchanged live-relay case requires explicit
`NSEALR_LIVE_E2E=1` and a real local Docker relay; its default skip stays visible.
No passing unit test closes physical resource or security admission gates.
''')
 c.put('docs/bridge/release.md',b'''# SDK release policy

`@nsealr/sdk` is the sole public package. Internal modules, apps, fixture tooling
and `@nsealr/dev-signer` stay private. The current package is pre-release; there
is no compatibility obligation for experimental APIs. External Nostr protocol
interoperability and source/license provenance remain required.

Before publication, `make ci`, `make integration` and `pnpm release-artifacts`
must pass against the exact reviewed source. The generated API digest and
boundary review must match. The tarball includes dist, README, MIT notice and
package metadata, with no test signer, fixture loader or unpublished dependency.
Its root/browser/Node entrypoints must pass isolated runtime and type consumers.
Release output paths reject source directories and traversal before cleanup.

Publication, version selection and trusted-publishing configuration are later
coordinator actions. Migration rehearsals generate local artifacts only and do
not publish to a registry. Software acceptance does not imply installed-browser,
relay, hardware, production custody or physical security qualification.
''')
 path='docs/bridge/sdk-examples.md';s=(target/path).read_text().replace('make examples-smoke','pnpm examples-smoke').replace('make readme-examples','pnpm readme-examples:check').replace('The examples import public packages through their package entrypoints after\n`dist` artifacts are built. The examples import every publishable public\npackage and cover:','The development examples use retained internal modules and the public SDK after\n`dist` artifacts are built. The separate packed SDK check proves independent\npublic consumption. Examples cover:').replace('core, protocol, and smartcard namespaces;','core and protocol namespaces;').replace('- smartcard APDU command/response round-trip and package-owned serial-line','- package-owned serial-line');c.put(path,s.encode())
 path='docs/bridge/audit-checklist.md';s=(target/path).read_text().replace('`nSealr/specs`','the authoritative `protocols/contracts/v1` artifact');c.put(path,s.encode())
 # Documentation and refusal text are declared artifact changes. Cryptographic
 # fixtures and independently computed expected answers are untouched.
 prefix='protocols/contracts/v1/';modified={}
 path='protocols/identity-policy-v0.md';s=(target/(prefix+path)).read_text().replace('the five existing signer families','the retained signer components').replace('private key, a smartcard\nslot, a future persistent device slot','private key, a future persistent device slot').replace('card/device slot','device slot').replace('- `smartcard`\n','').replace('ESP32/device slot, display-less smartcard slot,','ESP32/device slot,').replace('device vault, card applet, QR session','device vault, QR session').replace('devices, or explicit external review acknowledgement for display-less custody.','devices. Host review acknowledgements are unsupported.').replace('It does not apply to stateless QR vaults or\ndisplay-less smartcards.','It does not apply to stateless QR vaults.').replace('trusted display. Display-less routes must keep an explicit external-review\nacknowledgement boundary.','trusted display. Card routes are retired; a host acknowledgement cannot replace\ndevice review or approval.').replace('QR vault policies and display-less smartcard policies must remain','QR vault policies must remain');modified[path]=s.encode()
 path='protocols/feature-conformance-v0.md';s=(target/(prefix+path)).read_text().replace('Raspberry, ESP32, smartcard, companion, or custom hardware','Pi, ESP32, Bridge, or custom hardware').replace('## First-Class Signer Families','## Retained Conformance Components').replace('- `smartcard`: nSealr Card.\n','');start=s.index('Infrastructure repositories such as');end=s.index('\nBrowser extension',start);s=s[:start]+'''These existing identifiers describe conformance fixtures, not a new public
profile or compatibility promise. Product software is owned by nsealr. Generic
board software is owned by board-sdk; hardware, website and .github retain their
separate responsibilities. A02 does not qualify a physical implementation or
introduce the later capability/profile contract.
'''+s[end:];modified[path]=s.encode()
 path='protocols/signing-request-v0.md';s=(target/(prefix+path)).read_text().replace('ESP32 signers, smartcard\n','ESP32 signers,\n');modified[path]=s.encode()
 old='external review acknowledgement is only supported for display-less sign_event dispatch';new='host review acknowledgements are unsupported for signer dispatch'
 path='vectors/route-refusals/signer-route-refusals-v0.json';modified[path]=(target/(prefix+path)).read_text().replace(old,new).encode()
 path='packages/client/src/service.ts';c.put(path,(target/path).read_text().replace(old,new).encode())
 path='vectors/features/signer-feature-matrix-v0.json';s=(target/(prefix+path)).read_text().replace('through local physical approval on trusted-display devices or external review acknowledgement for display-less custody','through local physical approval on trusted-display devices');modified[path]=s.encode()
 manifest=json.loads((target/(prefix+'manifest.json')).read_bytes());adaptation=json.loads((target/(prefix+'adaptation.json')).read_bytes())
 for path,data in modified.items():
  oldbytes=(target/(prefix+path)).read_bytes()
  if oldbytes==data:continue
  c.put(prefix+path,data);record=next(r for r in manifest['files'] if r['path']==path);record['sha256']=digest(data);record['adaptation']='current-owner-and-retired-card-prose/refusal-text';adaptation.append({'path':path,'before_sha256':digest(oldbytes),'after_sha256':digest(data),'reason':record['adaptation']})
 c.put(prefix+'manifest.json',canonical(manifest));c.put(prefix+'adaptation.json',canonical(adaptation));baseline=c.apply(output/'current-docs-and-artifact','Reconcile active guides core metadata and authoritative contract prose with retired card routes')
 c=Changes(target);path='scripts/verify_contracts.py';s=(target/path).read_text();s=re.sub(r"BASELINE='[0-9a-f]{40}'",f"BASELINE='{baseline}'",s);c.put(path,s.encode());return c.apply(output/'artifact-baseline','Bind documented card-retirement and refusal-text transition to its immutable artifact postimage')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
