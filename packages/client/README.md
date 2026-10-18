# @nsealr/client

Local companion service protocol and client wrappers.

## Purpose

- Encode and decode native-messaging frames.
- Build validated Chromium and Firefox native-host manifest objects from
  explicit host path and extension-id inputs.
- Build digest-bound native-host install plans, approval artifacts, and
  explicit approval-bound manifest installation execution through an injected
  write-new adapter.
- Validate local service requests and responses.
- Route signer requests through an explicit injected dispatcher only after
  client authorization, request validation, route selection, and response
  verification.
- Compose route-aware dispatcher registries for host apps that support multiple
  signer routes, without opening transport drivers by default.
- Await asynchronous host-owned dispatchers through the async local-service
  boundary while keeping the synchronous boundary deterministic.
- Provide a high-level client wrapper for future browser, SDK, desktop, and CLI
  callers.
- Enforce explicit client identity parsing, request-id correlation, and
  deterministic malformed-response rejection.
- Bound local-service exchanges with shared optional timeout and
  `AbortSignal` cancellation handling so browser, SDK, desktop, and extension
  callers do not fork stalled-request behavior.
- Expose `@nsealr/client/browser` as the reviewed browser-runtime subpath for
  browser-provider and browser-extension code that needs local-service client
  contracts without importing Node-only native-host manifest helpers.
- Expose `@nsealr/client/client-identity` as the minimal identity-only subpath
  for access surfaces that only need origin/app binding.

## Example

```ts nsealr-readme-example
import assert from "node:assert/strict";
import {
  LocalServiceClient,
  NATIVE_HOST_NAME,
  appendLocalGrantRevocation,
  approveNativeHostInstallPlan,
  approveLocalStorageReview,
  approvePairingIntent,
  buildNativeHostInstallPlan,
  buildNativeHostManifest,
  createLocalGrantStore,
  createLocalStorageReview,
  executeNativeHostInstallApproval,
  handleLocalServiceRequest,
  parseLocalClientIdentity,
  reviewPairingIntent
} from "@nsealr/client";

const identity = parseLocalClientIdentity({
  surface: "sdk",
  origin: "sdk:readme",
  app_name: "README client"
});
const client = new LocalServiceClient({
  exchange: (message) => handleLocalServiceRequest(message, { now: 1_710_000_000 })
});

const status = await client.serviceStatus("readme-client-status");
const pairing = await client.requestPairing(identity, ["validate_signer_request"], "readme-client-pair");
const nativeHostManifest = buildNativeHostManifest({
  browser: "firefox",
  hostPath: "/Applications/nSealr/nsealr-service",
  extensionIds: ["extension@nsealr.dev"]
});
const nativeHostInstallPlan = buildNativeHostInstallPlan({
  browser: "firefox",
  hostPath: "/Applications/nSealr/nsealr-service",
  extensionIds: ["extension@nsealr.dev"],
  manifestPath: "/Users/example/Library/Application Support/Mozilla/NativeMessagingHosts/dev.nsealr.companion.json"
});

assert.equal(status.ok, true);
assert.equal(nativeHostManifest.name, NATIVE_HOST_NAME);
assert.equal(nativeHostInstallPlan.writes_files, false);
if (pairing.ok !== true || !("pairing_intent" in pairing.result)) {
  throw new Error("pairing intent missing");
}
const approval = approvePairingIntent(pairing.result.pairing_intent, {
  approvedAt: 1_710_000_000,
  expiresAt: 1_710_086_400
});
assert.equal(reviewPairingIntent(pairing.result.pairing_intent).requires_user_approval, true);
assert.equal(approval.stores_production_secrets, false);
const grantStore = createLocalGrantStore([approval.grant], {
  updatedAt: 1_710_000_000
});
const storageReview = createLocalStorageReview([{
  purpose: "grant_store",
  path: "/Applications/nSealr/local-grants.json",
  access: "write_new",
  contains_secret_material: false
}]);
const storageApproval = approveLocalStorageReview(storageReview, {
  approvedAt: 1_710_000_000
});
const nativeHostInstallApproval = approveNativeHostInstallPlan(nativeHostInstallPlan, {
  reviewedInstallDigest: nativeHostInstallPlan.install_digest,
  approvedAt: 1_710_000_000
});
const nativeHostInstallWrites: string[] = [];
const nativeHostInstallExecution = await executeNativeHostInstallApproval(nativeHostInstallApproval, {
  reviewedInstallDigest: nativeHostInstallApproval.install_digest,
  writer: {
    ensureDirectory(path) {
      nativeHostInstallWrites.push(`dir:${path}`);
    },
    writeFileNew(path) {
      nativeHostInstallWrites.push(`file:${path}`);
    }
  }
});
assert.equal(grantStore.contains_secret_material, false);
assert.equal(storageReview.requires_user_approval, true);
assert.equal(storageApproval.storage_digest, storageReview.storage_digest);
assert.equal(nativeHostInstallApproval.install_digest, nativeHostInstallPlan.install_digest);
assert.equal(nativeHostInstallExecution.writes_files, true);
assert.equal(nativeHostInstallWrites.some((entry) => entry.startsWith("file:")), true);
assert.equal(appendLocalGrantRevocation(grantStore, {
  clientId: approval.grant.client_id,
  origin: approval.grant.origin,
  surface: approval.grant.surface
}, {
  revokedAt: 1_710_000_100
}).grants.at(-1)?.revoked, true);
```

## Boundary

The local service boundary is secretless. It currently supports status, pairing
intent generation, deterministic pairing-review projection, explicit manual
approval into a grant, request validation, secretless route selection, response
verification, a dispatcher boundary that is unavailable by default, and a
strict JSON grant-store contract for persisting approved/revoked local client
grants without destructive history edits. It also owns digest-bound
storage-location review and approval artifacts for explicit grant, account, and
route-driver paths. Grant-store artifact builders can require those approvals
before writing a new output path, while the artifacts themselves do not choose
defaults, approve clients, or open signer transports.
Display-less `sign_event` routes, such as smartcard slots, also require a
`nsealr-external-review-acknowledgement-v0` artifact whose `approval_digest`
matches the signer request before dispatch reaches the injected handler. The
same acknowledgement is rejected on routes with their own trusted review UI, so
external review cannot weaken device-local review requirements.
`LocalServiceClient` owns response validation, request-id correlation, optional
deterministic response timeout, and optional cancellation for any injected
exchange. Its dispatch wrapper accepts that explicit external-review
acknowledgement as an option for display-less routes, then lets the service
enforce the same matching and route-scope checks. Route-selection results are
validated through the shared `@nsealr/policy` parser, not a client-local route
taxonomy. Browser adapters forward an `AbortSignal` into their injected
transport but do not reimplement this boundary.
`createRouteDispatcher` is only a registry helper for host-owned dispatch
functions; it selects an explicitly configured route handler and otherwise
returns the same unavailable or configuration-error boundary.
`SignerTransportError` is the typed boundary for host-owned signer transports
to return deterministic local-service error codes for open, timeout, protocol,
I/O, close, or fallback transport failures.
`handleLocalServiceRequestAsync` is the boundary future native hosts should use
when a reviewed signer driver needs asynchronous I/O; the synchronous handler
rejects async dispatchers deterministically instead of treating promises as
signer responses.
It does not store production keys, open relays, or include real signer
transport drivers. A host app still has to own backup policy, signer transport
wiring, production storage writes, and user approval UX.
The package can build native-host manifest objects, digest-bound dry-run install
plans, digest-confirmed install approval artifacts, and explicit install
execution reports for an approved manifest path. The execution helper still
requires an injected writer, uses the reviewed `write_new` path from the plan,
and does not choose a host file location.
