import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  NATIVE_HOST_NAME,
  createBrowserNativeMessagingLocalServiceClient,
  createLocalServiceBrowserProviderBackend,
  createNip07Provider
} from "@nsealr/browser-provider";
import {
  appendLocalGrantRevocation,
  clientIdForIdentity,
  createLocalGrantStore,
  handleLocalServiceRequest,
  LocalServiceClient,
  parseLocalGrantStore,
  reviewPairingIntent,
  serializeLocalGrantStore,
  type LocalClientGrant,
  type LocalClientIdentity
} from "@nsealr/client";
import {
  computeEventId,
  verifySignedEventResponse,
  type EventTemplate,
  type SignEventRequest,
  type SignEventResponse
} from "@nsealr/core";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import { decodeSerialFrame, encodeSerialFrame } from "@nsealr/framing";
import { decideNip46BridgeAction } from "@nsealr/nip46";
import {
  decidePolicyRequest,
  parseAccountDescriptor,
  parseGrantDescriptor,
  parsePolicyProfile,
  reviewPolicyChangeProposal,
  selectAccountRoute
} from "@nsealr/policy";
import { validateRequest, validateResponse } from "@nsealr/protocol";
import { decodeQrEnvelope, encodeQrEnvelope } from "@nsealr/qr";
import {
  approvalDigestForRequest,
  renderReviewDetailPages,
  reviewEventTemplate
} from "@nsealr/review";
import {
  CommandApdu,
  GET_PUBLIC_KEY_INS,
  NSEALR_CLA,
  ResponseApdu,
  SW_NO_ERROR
} from "@nsealr/smartcard";
import * as sdk from "@nsealr/sdk";
import * as sdkBrowser from "@nsealr/sdk/browser";
import { exchangeSerialLineRequest, type SerialLinePort } from "@nsealr/transport";

const request: SignEventRequest = {
  version: 1,
  request_id: "req-kind-1-basic",
  method: "sign_event",
  params: {
    event_template: {
      created_at: 1_710_000_000,
      kind: 1,
      tags: [],
      content: "nSealr fixture: basic kind 1 event."
    }
  }
};

const response: SignEventResponse = {
  version: 1,
  request_id: "req-kind-1-basic",
  ok: true,
  result: {
    event: {
      id: "2977f107ad2668dbd9f09b8594eff3b5276e21bfe098e60ae3e905e3c861e4d3",
      pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
      created_at: 1_710_000_000,
      kind: 1,
      tags: [],
      content: "nSealr fixture: basic kind 1 event.",
      sig: "2eec0351eb1d651140922d4b1f1bd8135f4474aabf42ec5bda7011087c1a072d71be863646dc162e4d96eacf14afeed2618a4acb0e1134a273a2b8e73039e654"
    }
  }
};
const publicKey = response.result.event.pubkey;
const companionRoot = fileURLToPath(new URL("../../..", import.meta.url));
const siblingSpecsRoot = join(dirname(companionRoot), "specs");

const sdkClient: LocalClientIdentity = {
  surface: "sdk",
  origin: "sdk:example",
  app_name: "nSealr SDK Example",
  instance_id: "sdk-example-1"
};

function assertValidSignerRequest(value: unknown): asserts value is SignEventRequest {
  const validation = validateRequest(value);
  assert.equal(validation.ok, true, validation.error);
}

async function requestAndQrExample(): Promise<void> {
  assertValidSignerRequest(request);

  const signedEvent = response.result.event;
  assert.equal(computeEventId({
    pubkey: signedEvent.pubkey,
    created_at: signedEvent.created_at,
    kind: signedEvent.kind,
    tags: signedEvent.tags,
    content: signedEvent.content
  }), signedEvent.id);
  assert.equal(validateResponse(response).ok, true);
  assert.equal(verifySignedEventResponse(request, response).ok, true);

  const envelope = encodeQrEnvelope(request);
  assert.deepEqual(decodeQrEnvelope(envelope), request);
}

async function fixturesPolicyReviewAndFramingExample(): Promise<void> {
  const fixtures = loadSpecsFixtures(specsRootForExamples());
  assert(fixtures.events.length > 0);
  assert(fixtures.reviewDetailPages.length > 0);
  assert(fixtures.policyDecisions.length > 0);
  assert(fixtures.routeSelections.length > 0);

  const policyVector = fixtures.policyDecisions.find((candidate) => candidate.decision.decision === "allow");
  if (!policyVector) throw new Error("SDK example could not find an allowed policy-decision vector");
  const sourceAccount = fixtures.accounts.find((candidate) => candidate.account_id === policyVector.request.account_id);
  if (!sourceAccount) throw new Error("SDK example policy vector references an unknown account");
  const sourcePolicy = fixtures.policyProfiles.find((candidate) => candidate.policy_id === policyVector.policy_profile_id);
  if (!sourcePolicy) throw new Error("SDK example policy vector references an unknown policy profile");
  const sourceGrant = fixtures.grants.find((candidate) => policyVector.request.grant_ids.includes(candidate.grant_id));
  if (!sourceGrant) throw new Error("SDK example policy vector references an unknown grant");
  const account = parseAccountDescriptor(JSON.parse(JSON.stringify(sourceAccount)));
  const policy = parsePolicyProfile(JSON.parse(JSON.stringify(sourcePolicy)));
  const grant = parseGrantDescriptor(JSON.parse(JSON.stringify(sourceGrant)));
  assert.deepEqual(decidePolicyRequest({
    policy,
    grants: [grant],
    request: policyVector.request
  }), policyVector.decision);
  assert.equal(account.account_id, policyVector.request.account_id);
  assert.equal(account.policy_profile_id, "policy-manual-only-persistent-device");
  assert.equal(grant.account_id, account.account_id);
  assert.equal(policy.route_types.includes(policyVector.request.route_type), true);

  const policyChange = fixtures.policyChanges.find((candidate) => candidate.proposal.account_id === account.account_id);
  if (!policyChange) throw new Error("SDK example could not find a matching policy-change vector");
  assert.equal(policyChange.proposal.current_policy_id, account.policy_profile_id);
  assert.equal(policyChange.proposal.proposed_policy_id, policyVector.policy_profile_id);
  assert.deepEqual(reviewPolicyChangeProposal(policyChange.proposal, {
    accounts: fixtures.accounts,
    policyProfiles: fixtures.policyProfiles,
    grants: fixtures.grants
  }), policyChange.review);

  const routeVector = fixtures.routeSelections.find((candidate) => candidate.request.account_id === account.account_id);
  if (!routeVector) throw new Error("SDK example could not find a matching route-selection vector");
  assert.deepEqual(selectAccountRoute(fixtures.accounts, routeVector.request), routeVector.selection);
  assert.equal(routeVector.selection.contains_secret_material, false);

  const review = reviewEventTemplate(request.params.event_template, publicKey);
  const detailPages = renderReviewDetailPages(review, {
    max_title_chars: 18,
    max_body_lines: 5,
    max_line_chars: 26,
    max_compact_body_lines: 9,
    max_compact_line_chars: 48
  });
  assert(detailPages.length > 0);
  assert.equal(approvalDigestForRequest(request, publicKey).length, 64);

  const frame = encodeSerialFrame({ type: "request", payload: request });
  assert.deepEqual(decodeSerialFrame(frame), { type: "request", payload: request });
}

async function localServiceExample(): Promise<void> {
  const fixtures = loadSpecsFixtures(specsRootForExamples());
  const routeVector = fixtures.routeSelections.find((candidate) => candidate.name === "esp32-usb-sign-event-slot-0");
  if (!routeVector) throw new Error("local service example could not find a route-selection vector");
  const grantStore = createLocalGrantStore([exampleGrant()], { updatedAt: 1_900_000_000 });
  assert.deepEqual(parseLocalGrantStore(JSON.parse(serializeLocalGrantStore(grantStore))), grantStore);
  const service = new LocalServiceClient({
    exchange: (message) => handleLocalServiceRequest(message, {
      accounts: fixtures.accounts,
      grants: grantStore.grants,
      now: 1_900_000_000
    }),
    nextRequestId: sequence("sdk-service")
  });

  const status = await service.serviceStatus();
  if (status.ok !== true) throw new Error(status.error.message);
  if (!("service" in status.result)) throw new Error("service status example returned wrong result type");
  assert.equal(status.result.service.stores_production_secrets, false);

  const pairing = await service.requestPairing(sdkClient, [
    "select_account_route",
    "validate_signer_request",
    "dispatch_signer_request",
    "verify_signer_response"
  ]);
  if (pairing.ok !== true) throw new Error(pairing.error.message);
  if (!("pairing_intent" in pairing.result)) throw new Error("pairing example returned wrong result type");
  assert.equal(pairing.result.pairing_intent.requires_user_approval, true);
  assert.equal(pairing.result.pairing_intent.stores_production_secrets, false);
  const pairingReview = reviewPairingIntent(pairing.result.pairing_intent);
  assert.equal(pairingReview.contains_secret_material, false);
  assert.equal(pairingReview.requested_operations.length, 4);

  const routeSelection = await service.selectAccountRoute(sdkClient, routeVector.request);
  if (routeSelection.ok !== true) throw new Error(routeSelection.error.message);
  if (!("route_selection" in routeSelection.result)) throw new Error("route selection example returned wrong result type");
  assert.deepEqual(routeSelection.result.route_selection, routeVector.selection);

  const validation = await service.validateSignerRequest(sdkClient, request);
  if (validation.ok !== true) throw new Error(validation.error.message);
  if (!("validation" in validation.result)) throw new Error("validation example returned wrong result type");
  assert.equal(validation.result.validation.valid, true);

  const verification = await service.verifySignerResponse(sdkClient, request, response);
  if (verification.ok !== true) throw new Error(verification.error.message);
  if (!("validation" in verification.result)) throw new Error("verification example returned wrong result type");
  assert.equal(verification.result.validation.valid, true);

  const revokedStore = appendLocalGrantRevocation(grantStore, {
    clientId: grantStore.grants[0].client_id,
    origin: grantStore.grants[0].origin,
    surface: grantStore.grants[0].surface
  }, { revokedAt: 1_900_000_010 });
  const revokedService = new LocalServiceClient({
    exchange: (message) => handleLocalServiceRequest(message, {
      grants: revokedStore.grants,
      now: 1_900_000_011
    }),
    nextRequestId: sequence("sdk-revoked-service")
  });
  const revokedValidation = await revokedService.validateSignerRequest(sdkClient, request);
  assert.equal(revokedValidation.ok, false);
}

async function browserProviderExample(): Promise<void> {
  const fixtures = loadSpecsFixtures(specsRootForExamples());
  const accessSurface = fixtures.accessSurfaces.find(
    (candidate) => candidate.name === "browser-provider-local-service-esp32-usb-unavailable"
  );
  if (!accessSurface) throw new Error("browser provider example could not find an access-surface vector");
  const routeVector = fixtures.routeSelections.find((candidate) => candidate.name === accessSurface.route_selection_vector);
  if (!routeVector) throw new Error("browser provider example could not find a route-selection vector");
  const browserClient = accessSurface.client as LocalClientIdentity;
  const accessSurfaceRequest = JSON.parse(
    readFileSync(resolve(specsRootForExamples(), accessSurface.sign_event_request_vector), "utf8")
  ) as SignEventRequest;
  const signerUnavailable = accessSurface.expected.sign_event_without_dispatcher.response as {
    error: { message: string };
  };
  const service = createBrowserNativeMessagingLocalServiceClient({
    sendNativeMessage: (hostName, message) => {
      assert.equal(hostName, NATIVE_HOST_NAME);
      return handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [accessSurface.client_grant as LocalClientGrant],
        now: 1_900_000_000
      });
    },
    nextRequestId: sequence("sdk-provider-native-service")
  });
  const nativeStatus = await service.serviceStatus();
  assert.equal(nativeStatus.ok, true);
  const provider = createNip07Provider({
    client: browserClient,
    backend: createLocalServiceBrowserProviderBackend({
      service,
      routeRequest: routeVector.request
    }),
    nextRequestId: () => accessSurfaceRequest.request_id
  });

  assert.equal(await provider.getPublicKey(), accessSurface.expected.get_public_key.public_key);
  await assert.rejects(
    provider.signEvent(accessSurfaceRequest.params.event_template as EventTemplate),
    (error) => error instanceof Error && error.message.includes(signerUnavailable.error.message)
  );
}

async function nip46BridgeExample(): Promise<void> {
  const eventTemplate = request.params.event_template;
  const decision = decideNip46BridgeAction({
    id: "sdk-nip46-sign-event",
    method: "sign_event",
    params: [JSON.stringify(eventTemplate)]
  }, [{
    method: "sign_event",
    parameter: String(eventTemplate.kind),
    event_kind: eventTemplate.kind
  }]);

  assert.equal(decision.type, "signer_request");
  if (decision.type === "signer_request") {
    assert.equal(validateRequest(decision.nsealr_request).ok, true);
    if (decision.nsealr_request.method !== "sign_event") {
      throw new Error("NIP-46 example returned non-sign_event signer request");
    }
    assert.deepEqual(decision.nsealr_request.params.event_template, eventTemplate);
  }

  const denied = decideNip46BridgeAction({
    id: "sdk-nip46-get-public-key",
    method: "get_public_key",
    params: []
  }, []);
  assert.equal(denied.type, "permission_denied");
}

async function smartcardAndTransportExample(): Promise<void> {
  const command = new CommandApdu(NSEALR_CLA, GET_PUBLIC_KEY_INS);
  assert.equal(CommandApdu.fromHex(command.toHex()).toHex(), command.toHex());

  const apduResponse = new ResponseApdu(Uint8Array.of(1, 2, 3), SW_NO_ERROR);
  assert.equal(ResponseApdu.fromHex(apduResponse.toHex()).statusWord, SW_NO_ERROR);

  let writtenLine: string | undefined;
  let closed = false;
  const port: SerialLinePort = {
    async writeLine(line: string): Promise<void> {
      writtenLine = line;
    },
    async readLine(): Promise<string | null> {
      assert(writtenLine);
      return encodeSerialFrame({
        type: "response",
        payload: {
          version: 1,
          request_id: request.request_id,
          ok: false,
          error: {
            code: "signing_disabled",
            message: "SDK example has no signer transport",
            retryable: false
          }
        }
      });
    },
    close(): void {
      closed = true;
    }
  };

  const transportResponse = await exchangeSerialLineRequest({
    path: "memory",
    request,
    openPort: () => port,
    responseTimeoutMs: 10
  });
  assert.equal(validateResponse(transportResponse).ok, true);
  assert.equal((transportResponse as { error?: { code?: string } }).error?.code, "signing_disabled");
  assert.equal(closed, true);
}

function sdkFacadeExample(): void {
  const identity = sdk.client.parseLocalClientIdentity({
    surface: "browser_extension",
    origin: "https://example.com",
    app_name: "SDK Facade Example",
    instance_id: "sdk-facade"
  });

  assert.equal(identity.origin, "https://example.com");
  assert.equal(sdk.protocol.validateRequest({
    version: 1,
    request_id: "sdk-facade-get-public-key",
    method: "get_public_key"
  }).ok, true);
  assert.equal(sdk.core.computeEventId({
    pubkey: "0".repeat(64),
    created_at: 1,
    kind: 1,
    tags: [],
    content: "sdk facade"
  }).length, 64);
  assert.equal(typeof sdk.browserProvider.createNip07Provider, "function");
  assert.equal(typeof sdk.smartcard.CommandApdu, "function");
  assert.equal(sdkBrowser.client.NATIVE_HOST_NAME, NATIVE_HOST_NAME);
  assert.equal(typeof sdkBrowser.browserProvider.createNip07Provider, "function");
  assert.equal(sdkBrowser.protocol.validateRequest({
    version: 1,
    request_id: "sdk-browser-facade-get-public-key",
    method: "get_public_key"
  }).ok, true);
  assert.deepEqual(sdkBrowser.qr.decodeQrEnvelope(sdkBrowser.qr.encodeQrEnvelope(request)), request);
}

function exampleGrant(): LocalClientGrant {
  return {
    client_id: clientIdForIdentity(sdkClient),
    origin: sdkClient.origin,
    surface: sdkClient.surface,
    allowed_operations: ["select_account_route", "validate_signer_request", "dispatch_signer_request", "verify_signer_response"],
    approved_at: 1_900_000_000,
    expires_at: 2_000_000_000
  };
}

function sequence(prefix: string): () => string {
  let next = 0;
  return () => {
    next += 1;
    return `${prefix}-${next}`;
  };
}

function specsRootForExamples(): string {
  if (existsSync(join(siblingSpecsRoot, "vectors")) && existsSync(join(siblingSpecsRoot, "examples"))) {
    return resolveSpecsRoot(siblingSpecsRoot);
  }
  return resolveSpecsRoot(join(companionRoot, "tests", "fixtures", "specs"));
}

await requestAndQrExample();
await fixturesPolicyReviewAndFramingExample();
await localServiceExample();
await browserProviderExample();
await nip46BridgeExample();
await smartcardAndTransportExample();
sdkFacadeExample();

console.log("nSealr SDK examples passed");
