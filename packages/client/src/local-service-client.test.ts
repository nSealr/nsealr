import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import { approvalDigestForRequest } from "@nsealr/review";
import {
  createNativeMessagingLocalServiceClient,
  LocalServiceClient,
  validateLocalServiceResponse
} from "./local-service-client.js";
import { decodeNativeMessage, encodeNativeMessage } from "./native-messaging.js";
import {
  EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT,
  clientIdForIdentity,
  handleLocalServiceRequest,
  LOCAL_SERVICE_OPERATIONS,
  type ExternalReviewAcknowledgement,
  type LocalClientGrant,
  type LocalClientIdentity
} from "./service.js";

const specsRoot = resolveSpecsRoot();
const fixtures = loadSpecsFixtures(specsRoot);
const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const response = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));
const routeVector = fixtures.routeSelections.find((selection) => selection.name === "esp32-usb-sign-event-slot-0");
if (!routeVector) throw new Error("route selection fixture is missing");
const smartcardRouteVector = fixtures.routeSelections.find((selection) => selection.name === "smartcard-sign-event-slot-0");
if (!smartcardRouteVector) throw new Error("smartcard route selection fixture is missing");
const client: LocalClientIdentity = {
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "Example Nostr Client",
  instance_id: "extension-test-1"
};
const grant: LocalClientGrant = {
  client_id: clientIdForIdentity(client),
  origin: client.origin,
  surface: client.surface,
  allowed_operations: ["select_account_route", "validate_signer_request", "dispatch_signer_request", "verify_signer_response"],
  expires_at: 2_000_000_000
};

function externalReviewAcknowledgement(): ExternalReviewAcknowledgement {
  return {
    format: EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT,
    acknowledged: true,
    source: "external-review" as const,
    approval_digest: approvalDigestForRequest(request),
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

describe("local service client", () => {
  it("wraps service-status and pairing calls with generated request ids", async () => {
    const requestIds = ["client-status-1", "client-pair-1"];
    const service = new LocalServiceClient({
      nextRequestId: () => requestIds.shift() ?? "unexpected-request",
      exchange: (message) => handleLocalServiceRequest(message)
    });

    await expect(service.serviceStatus()).resolves.toMatchObject({
      request_id: "client-status-1",
      ok: true,
      result: {
        service: {
          requires_pairing: true,
          stores_production_secrets: false
        }
      }
    });

    await expect(service.requestPairing(client, ["validate_signer_request"])).resolves.toMatchObject({
      request_id: "client-pair-1",
      ok: true,
      result: {
        pairing_intent: {
          client_id: clientIdForIdentity(client),
          requested_operations: ["validate_signer_request"],
          requires_user_approval: true
        }
      }
    });
  });

  it("returns deterministic service errors without throwing", async () => {
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message)
    });

    await expect(service.validateSignerRequest(client, request, "client-unpaired")).resolves.toEqual({
      version: 1,
      request_id: "client-unpaired",
      ok: false,
      error: {
        code: "unauthorized_client",
        message: "client is not paired",
        retryable: false
      }
    });
  });

  it("validates and verifies through authorized service exchanges", async () => {
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [grant],
        now: 1_900_000_000
      })
    });

    await expect(service.validateSignerRequest(client, request, "client-validate")).resolves.toMatchObject({
      request_id: "client-validate",
      ok: true,
      result: { validation: { valid: true } }
    });

    await expect(service.verifySignerResponse(client, request, response, "client-verify")).resolves.toMatchObject({
      request_id: "client-verify",
      ok: true,
      result: { validation: { valid: true } }
    });

    await expect(service.selectAccountRoute(client, routeVector.request, "client-route")).resolves.toEqual({
      version: 1,
      request_id: "client-route",
      ok: true,
      result: {
        route_selection: routeVector.selection
      }
    });

    await expect(service.dispatchSignerRequest(client, routeVector.request, request, {
      requestId: "client-dispatch"
    })).resolves.toMatchObject({
      request_id: "client-dispatch",
      ok: false,
      error: {
        code: "signer_route_unavailable",
        message: "signer dispatch is not configured"
      }
    });
  });

  it("passes external review acknowledgement through dispatch options for display-less routes", async () => {
    const acknowledgement = externalReviewAcknowledgement();
    const dispatched: unknown[] = [];
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [grant],
        now: 1_900_000_000,
        signerDispatcher: (dispatchRequest) => {
          dispatched.push(dispatchRequest);
          return response;
        }
      })
    });

    await expect(service.dispatchSignerRequest(client, smartcardRouteVector.request, request, {
      requestId: "client-smartcard-dispatch",
      externalReviewAcknowledgement: acknowledgement
    })).resolves.toEqual({
      version: 1,
      request_id: "client-smartcard-dispatch",
      ok: true,
      result: {
        signer_response: response
      }
    });
    expect(dispatched).toEqual([{
      client,
      route_selection: smartcardRouteVector.selection,
      request,
      external_review_acknowledgement: acknowledgement
    }]);
  });

  it("rejects malformed or mismatched service responses before callers trust them", async () => {
    const mismatchedResponseClient = new LocalServiceClient({
      exchange: (message) => ({
        ...handleLocalServiceRequest(message),
        request_id: "other-request"
      })
    });

    await expect(mismatchedResponseClient.serviceStatus("expected-request")).rejects.toThrow(/does not match/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: { validation: { valid: "yes" } }
    }, "expected-request")).toThrow(/validation flag/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        validation: { valid: true },
        service: {
          protocol: "nsealr-local-service-v0"
        }
      }
    }, "expected-request")).toThrow(/result type/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        service: {
          protocol: "nsealr-local-service-v0",
          name: "nsealr-companion-service",
          operations: [...LOCAL_SERVICE_OPERATIONS],
          requires_pairing: true,
          stores_production_secrets: true
        }
      }
    }, "expected-request")).toThrow(/secret-storage flag/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        route_selection: {
          ...routeVector.selection,
          contains_secret_material: true
        }
      }
    }, "expected-request")).toThrow(/contains_secret_material/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        route_selection: {
          ...routeVector.selection,
          repository: "raspberry"
        }
      }
    }, "expected-request")).toThrow(/repository does not match/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        route_selection: {
          ...routeVector.selection,
          nsec: "nsec1notallowed"
        }
      }
    }, "expected-request")).toThrow(/secret field nsec/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        signer_response: {
          ...response,
          request_id: "bad request id"
        }
      }
    }, "expected-request")).toThrow(/signer response/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        pairing_intent: {
          format: "nsealr-local-pairing-intent-v0",
          client_id: clientIdForIdentity(client),
          client: {
            ...client,
            origin: "https://example.com/path"
          },
          requested_operations: ["validate_signer_request"],
          pairing_digest: "0".repeat(64),
          requires_user_approval: true,
          stores_production_secrets: false
        }
      }
    }, "expected-request")).toThrow(/pairing client/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        pairing_intent: {
          format: "nsealr-local-pairing-intent-v0",
          client_id: clientIdForIdentity(client),
          client,
          requested_operations: ["request_pairing"],
          pairing_digest: "0".repeat(64),
          requires_user_approval: true,
          stores_production_secrets: false
        }
      }
    }, "expected-request")).toThrow(/pairing operations/u);
    expect(() => validateLocalServiceResponse({
      version: 1,
      request_id: "expected-request",
      ok: true,
      result: {
        pairing_intent: {
          format: "nsealr-local-pairing-intent-v0",
          client_id: clientIdForIdentity(client),
          client,
          requested_operations: ["validate_signer_request"],
          pairing_digest: "0".repeat(64),
          requires_user_approval: true,
          stores_production_secrets: false
        }
      }
    }, "expected-request")).toThrow(/digest mismatch/u);
  });

  it("rejects valid but operation-mismatched service results before callers trust them", async () => {
    const serviceResultForEveryOperation = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest({
        version: 1,
        request_id: message.request_id,
        operation: "service_status"
      })
    });

    await expect(
      serviceResultForEveryOperation.requestPairing(client, ["validate_signer_request"], "pairing-mismatch")
    ).rejects.toThrow(/request_pairing returned unexpected local service result/u);
    await expect(
      serviceResultForEveryOperation.validateSignerRequest(client, request, "validation-mismatch")
    ).rejects.toThrow(/validate_signer_request returned unexpected local service result/u);
    await expect(
      serviceResultForEveryOperation.verifySignerResponse(client, request, response, "verify-mismatch")
    ).rejects.toThrow(/verify_signer_response returned unexpected local service result/u);
    await expect(
      serviceResultForEveryOperation.selectAccountRoute(client, routeVector.request, "route-mismatch")
    ).rejects.toThrow(/select_account_route returned unexpected local service result/u);
    await expect(
      serviceResultForEveryOperation.dispatchSignerRequest(client, routeVector.request, request, {
        requestId: "dispatch-mismatch"
      })
    ).rejects.toThrow(/dispatch_signer_request returned unexpected local service result/u);

    const pairingResultForStatus = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest({
        version: 1,
        request_id: message.request_id,
        operation: "request_pairing",
        params: {
          client,
          requested_operations: ["validate_signer_request"]
        }
      })
    });

    await expect(
      pairingResultForStatus.serviceStatus("status-mismatch")
    ).rejects.toThrow(/service_status returned unexpected local service result/u);
  });

  it("bounds local service exchanges with deterministic timeout and cancellation", async () => {
    expect(() => new LocalServiceClient({
      timeoutMs: 0,
      exchange: (message) => handleLocalServiceRequest(message)
    })).toThrow(/timeout/u);

    const timeoutClient = new LocalServiceClient({
      timeoutMs: 1,
      exchange: () => new Promise(() => undefined)
    });
    await expect(timeoutClient.serviceStatus("client-timeout")).rejects.toThrow(/response timed out/u);

    const alreadyCancelled = new AbortController();
    alreadyCancelled.abort();
    let called = false;
    const alreadyCancelledClient = new LocalServiceClient({
      abortSignal: alreadyCancelled.signal,
      exchange: () => {
        called = true;
        return {};
      }
    });
    await expect(alreadyCancelledClient.serviceStatus("client-already-cancelled")).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);

    const inFlightAbort = new AbortController();
    const seenSignals: AbortSignal[] = [];
    const inFlightClient = new LocalServiceClient({
      abortSignal: inFlightAbort.signal,
      exchange: (_message, options) => {
        if (options?.abortSignal !== undefined) seenSignals.push(options.abortSignal);
        return new Promise(() => undefined);
      }
    });
    const requestPromise = inFlightClient.serviceStatus("client-in-flight-cancelled");
    inFlightAbort.abort();
    await expect(requestPromise).rejects.toThrow(/cancelled/u);
    expect(seenSignals).toEqual([inFlightAbort.signal]);
  });

  it("wraps native-messaging frame exchanges without exposing signer IO", async () => {
    const service = createNativeMessagingLocalServiceClient({
      exchange: (frame) => encodeNativeMessage(handleLocalServiceRequest(decodeNativeMessage(frame)))
    });

    await expect(service.serviceStatus("native-status")).resolves.toMatchObject({
      request_id: "native-status",
      ok: true,
      result: {
        service: {
          stores_production_secrets: false
        }
      }
    });
  });
});
