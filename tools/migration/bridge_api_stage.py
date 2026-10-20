#!/usr/bin/env python3
"""Review the sole SDK surface and regenerate its API inventory with exact hashes."""
import argparse,json,re
from pathlib import Path
from admission import Recorder
from rehearse import digest
from transforms import Changes

def apply(target,output,environment):
 output.mkdir(mode=0o700);c=Changes(target)
 path='tools/bridge/check_api_docs.mjs';text=(target/path).read_text().replace('scripts/check_api_docs.mjs','tools/bridge/check_api_docs.mjs').replace('make api-docs-update','pnpm api-docs:update').replace('make api-docs','pnpm api-docs:check')
 text=text.replace('  const symbols = new Set();','''  const symbols = new Set();
  const namespaces = new Map();
  for (const statement of source.statements) {
    if (ts.isImportDeclaration(statement) && ts.isStringLiteral(statement.moduleSpecifier) &&
        statement.importClause?.namedBindings && ts.isNamespaceImport(statement.importClause.namedBindings)) {
      const specifier = statement.moduleSpecifier.text;
      if (specifier.startsWith("@nsealr/")) {
        const parts = specifier.split("/");
        const packageName = parts.slice(0, 2).join("/");
        const subpath = parts.length > 2 ? `./${parts.slice(2).join("/")}` : ".";
        const target = sourceManifest(packageName).exports[subpath];
        if (!target?.import) throw new Error(`unmapped namespace ${specifier}`);
        namespaces.set(statement.importClause.namedBindings.name.text,
          sourcePathForDistImport(packageName, target.import));
      }
    }
  }''')
 text=text.replace('          symbols.add(element.name.text);','''          const name = element.name.text;
          symbols.add(name);
          const namespace = namespaces.get(element.propertyName?.text ?? name);
          if (namespace) for (const symbol of collectExports(namespace, new Set())) symbols.add(`${name}.${symbol}`);''')
 text=text.replace('  const shouldWrite = args.includes("--write");','  const shouldWrite = args.includes("--write");\n  const stdout = args.includes("--stdout");').replace('arg !== "--write"','arg !== "--write" && arg !== "--stdout"').replace('  if (shouldWrite) {','  if (stdout) { process.stdout.write(expected); return; }\n  if (shouldWrite) {')
 c.put(path,text.encode())
 path='tools/bridge/check_api_review.mjs';text=(target/path).read_text();start=text.index('assert(\n  normalizedReview.includes("Test-only APDU');end=text.index('\nassert(',start+1)
 text=text[:start]+'''assert(
  normalizedReview.includes("Smartcard APIs are retired") &&
    normalizedReview.includes("does not expose software signing helpers") &&
    review.includes("@nsealr/sdk/browser") && review.includes("@nsealr/sdk/node"),
  "API review must state the SDK entrypoints and retirement of card signing"
);
'''+text[end:];c.put(path,text.encode())
 path='packages/sdk/README.md';text=(target/path).read_text();begin=text.index('Platform-neutral');end=text.index('```ts nsealr-readme-example')
 text=text[:begin]+'''The sole public nSealr TypeScript package. The root and `@nsealr/sdk/browser`
expose browser-safe provider, local-service client and core/policy/protocol/QR/
review namespaces. `@nsealr/sdk/node` additionally exposes the host client,
framing and NIP-46 namespaces. Owned runtime and declarations are included in
this package; consumers do not install internal workspace packages.

The SDK stores no user identity/signing keys. Device review and approval remain
signer responsibilities. The Node NIP-46 runtime owns a bounded, in-memory
client transport key; it does not persist that key or confer signing approval.
Smartcard APIs are retired. `@nsealr/dev-signer` and fixture loaders stay private
and outside the packed production graph. Real browser, relay and attached-device
qualification remains separate from deterministic package tests.

'''+text[end:];c.put(path,text.encode())
 c.apply(output/'inventory-tooling','Describe SDK root browser Node namespaces and require current API boundary review')
 rec=Recorder(output/'generation');api=rec.run('generate-current-sdk-api',['node','tools/bridge/check_api_docs.mjs','--stdout'],target,env=environment)
 review='''# Public SDK API review

API surface digest: `sha256:DIGEST`

Source: [generated API](api.md). This migration records a proposed pre-release
surface for distinct A02 review. It does not claim a new production-security,
physical-device, live-relay or browser qualification.

## @nsealr/sdk

The root and `@nsealr/sdk/browser` export browserProvider, client, core, policy,
protocol, qr and review namespaces. The explicit `@nsealr/sdk/node` entrypoint
adds framing, nip46 and host client helpers. The generated inventory records
all namespace members as well as entrypoint names, so member drift is checked.
Owned MIT runtime code and declarations are bundled. Exact third-party packages
retain their own distributions and license notices. No unpublished workspace
package is a production dependency. Internal declaration files are included for
type resolution, but package exports reject deep runtime access.

`@nsealr/dev-signer` remains private and test-only. The SDK does not expose
software signing helpers. Fixture loading and host serial port adapters stay
internal. Smartcard APIs are retired; unsupported card routes, old commands and
host acknowledgement bypasses are rejected before dispatch. Trusted device
review remains a signer responsibility; host review output is untrusted.

The browser provider validates requests and verifies successful signed-event
responses before returning them. Native messaging requires an injected exchange;
it does not install a native host, persist grants or authorize signing. Browser
client timeout, cancellation, request correlation and malformed-response checks
remain in force. Browser root does not export file-backed grant stores.

The Node client exposes strict secretless grant history, explicit pairing and
storage review/approval artifacts, request-bound route dispatch and response
verification. A supplied host review acknowledgement is unsupported. Route
selection is metadata only; an injected route dispatcher must enforce device
approval. Native-host execution requires the reviewed install digest and writes
only the approved new manifest through an injected writer. These interfaces do
not establish production storage, installer UX or device transport qualification.

Core owns Nostr serialization, event-id computation and signature verification.
Protocol owns bounded request/response validation and strict raw JSON parsing.
Policy rejects secret fields, wildcard or unsupported grants and invalid route
targets; it does not mutate authoritative device policy. QR and framing encode
validated payloads without signing or custody. Review renders untrusted previews.

The NIP-46 pure helpers parse already-decrypted payloads, produce digest-bound
connect review and approval artifacts, parse descriptor-only connection URIs,
verify secretless connection-token metadata, and enforce approved permission
subsets. The parser parses relay event envelopes and verifies signed relay event
ids/signatures without decrypting NIP-44 content. It evaluates relay request and
response steps only after plaintext is supplied and verifies signed-event result
ids/signatures. Those metadata relay request/response steps run without opening
relays or auth URLs. Pending metadata checkpoints do not restore a live session.

The explicit Node runtime has different side effects: Nip46SessionManager owns
an in-memory client transport key, and NostrToolsRelay opens relays. The manager
pins the authenticated transport author and resolves a separate curve-valid user
key through get_public_key before activation. expectedUserPubkey can constrain
resolution. Signed results bind that user key, the requested template, event ID
and signature. The remote signer owns user custody and approval.

Fresh request namespaces and monotonic counters prevent reuse. Pending requests
and unsettled publications default to 32, capped at 256; one unresolved
subscription acquisition blocks another. Timeouts default to 30 seconds, capped
at 300 seconds. Close is terminal and clears the owned key copy. Failed retries
retain counters; arbitrary adapter promises cannot be forcibly cancelled.
Metadata persistence never stores or restores the runtime secret. Raw JSON rejects
duplicate keys, trailing bytes and depth above 32. Message, encrypted content and
tag limits remain the existing nSealr profile limits. Response metadata v1 binds
result_pubkey independently of the transport author; it does not authenticate a
session on its own.

The actual packed artifact is installed outside the workspace. Node behavior,
browser bundling/execution without Node globals, strict TypeScript imports and
hidden-import rejection are mandatory. Browser-like VM execution is not installed
Firefox or Chromium qualification. Live relay and attached-device checks remain
explicitly resource gated. npm publication and trusted-publishing configuration
require the coordinator's later adoption; no package is published by this review.
'''.replace('DIGEST',digest(api))
 c=Changes(target);c.put('docs/bridge/api.md',api);c.put('docs/bridge/api-review.md',review.encode());return c.apply(output/'inventory-docs','Record exact generated SDK member inventory and proposed current boundary review')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output,json.loads(a.environment.read_bytes())))
