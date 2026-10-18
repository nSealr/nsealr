import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import { approvalDigestForRequest } from "@nsealr/review";
import {
  EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT,
  approvePairingIntent,
  clientIdForIdentity,
  createRouteDispatcher,
  handleLocalServiceRequestAsync,
  handleLocalServiceRequest,
  LOCAL_SERVICE_OPERATIONS,
  LOCAL_SERVICE_PROTOCOL,
  SignerTransportError,
  type LocalClientGrant,
  type LocalClientIdentity
} from "./service.js";
import { parseLocalClientIdentity } from "./client-identity.js";

const specsRoot = resolveSpecsRoot();
const fixtures = loadSpecsFixtures(specsRoot);
const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const response = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));
const routeVector = fixtures.routeSelections.find((selection) => selection.name === "esp32-usb-sign-event-slot-0");
if (!routeVector) throw new Error("route selection fixture is missing");
const routeAccountId = routeVector.selection.account_id;
const externalNip46RouteVector = fixtures.routeSelections.find(
  (selection) => selection.name === "external-nip46-sign-event-bunker"
);
if (!externalNip46RouteVector) throw new Error("external NIP-46 route selection fixture is missing");
const smartcardRouteVector = fixtures.routeSelections.find((selection) => selection.name === "smartcard-sign-event-slot-0");
if (!smartcardRouteVector) throw new Error("smartcard route selection fixture is missing");
const routeRefusalContract = fixtures.routeRefusals.find((contract) => contract.name === "signer-route-refusals-v0");
if (!routeRefusalContract) throw new Error("route-refusal contract fixture is missing");
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
  allowed_operations: ["validate_signer_request", "dispatch_signer_request", "verify_signer_response"],
  expires_at: 2_000_000_000
};
const routeGrant: LocalClientGrant = {
  ...grant,
  allowed_operations: ["select_account_route"]
};

function externalReviewAcknowledgement(approvalDigest = approvalDigestForRequest(request)) {
  return {
    format: EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT,
    acknowledged: true,
    source: "external-review",
    approval_digest: approvalDigest,
    stores_production_secrets: false,
    contains_secret_material: false
  };
}

function accountsWithSelectedRoutePublicKey(publicKey: string) {
  return fixtures.accounts.map((account) => account.account_id === routeAccountId
    ? { ...account, public_key: publicKey }
    : account);
}

describe("local service boundary", () => {
  it("parses local client identities through the shared origin boundary", () => {
    expect(parseLocalClientIdentity(client)).toEqual(client);
    expect(clientIdForIdentity(parseLocalClientIdentity(client))).toBe(clientIdForIdentity(client));
    expect(parseLocalClientIdentity({
      surface: "browser_extension",
      origin: "http://localhost",
      app_name: "Local Demo",
      instance_id: "local-demo-1"
    })).toEqual({
      surface: "browser_extension",
      origin: "http://localhost",
      app_name: "Local Demo",
      instance_id: "local-demo-1"
    });
    expect(parseLocalClientIdentity({
      surface: "browser_extension",
      origin: "https://example.com",
      app_name: "Firefox Extension",
      instance_id: "extension@nsealr.dev"
    })).toEqual({
      surface: "browser_extension",
      origin: "https://example.com",
      app_name: "Firefox Extension",
      instance_id: "extension@nsealr.dev"
    });
  });

  it("rejects ambiguous local client identities before pairing or route checks", () => {
    expect(() => parseLocalClientIdentity({
      ...client,
      extra: "not allowed"
    })).toThrow(/unsupported fields/u);
    expect(() => parseLocalClientIdentity({
      ...client,
      origin: "https://example.com/path"
    })).toThrow(/origin scheme/u);
    expect(() => parseLocalClientIdentity({
      ...client,
      origin: "http://localhost.evil.example"
    })).toThrow(/origin scheme/u);
    expect(() => parseLocalClientIdentity({
      ...client,
      app_name: "x".repeat(81)
    })).toThrow(/app_name/u);
    expect(() => parseLocalClientIdentity({
      ...client,
      instance_id: "bad instance id"
    })).toThrow(/instance_id/u);
  });

  it("reports secretless service status and pairing requirement", () => {
    const result = handleLocalServiceRequest({
      version: 1,
      request_id: "svc-status-1",
      operation: "service_status"
    });

    expect(result).toEqual({
      version: 1,
      request_id: "svc-status-1",
      ok: true,
      result: {
        service: {
          protocol: LOCAL_SERVICE_PROTOCOL,
          name: "nsealr-companion-service",
          operations: [...LOCAL_SERVICE_OPERATIONS],
          requires_pairing: true,
          stores_production_secrets: false
        }
      }
    });
  });

  it("creates a deterministic pairing intent without approving the client", () => {
    const result = handleLocalServiceRequest({
      version: 1,
      request_id: "svc-pair-1",
      operation: "request_pairing",
      params: {
        client,
        requested_operations: ["validate_signer_request", "verify_signer_response"]
      }
    });

    expect(result).toMatchObject({
      version: 1,
      request_id: "svc-pair-1",
      ok: true,
      result: {
        pairing_intent: {
          format: "nsealr-local-pairing-intent-v0",
          client_id: clientIdForIdentity(client),
          client,
          requested_operations: ["validate_signer_request", "verify_signer_response"],
          requires_user_approval: true,
          stores_production_secrets: false
        }
      }
    });
    if (result.ok === true && "pairing_intent" in result.result) {
      expect(result.result.pairing_intent.pairing_digest).toMatch(/^[0-9a-f]{64}$/u);
      const repeatedResult = handleLocalServiceRequest({
        version: 1,
        request_id: "svc-pair-2",
        operation: "request_pairing",
        params: {
          client,
          requested_operations: ["validate_signer_request", "verify_signer_response"]
        }
      });
      expect(repeatedResult.ok).toBe(true);
      if (repeatedResult.ok === true && "pairing_intent" in repeatedResult.result) {
        expect(result.result.pairing_intent.pairing_digest).toBe(repeatedResult.result.pairing_intent.pairing_digest);
      }
    }
  });

  it("turns a manually approved pairing intent into an in-memory grant", () => {
    const pairing = handleLocalServiceRequest({
      version: 1,
      request_id: "svc-pair-approve",
      operation: "request_pairing",
      params: {
        client,
        requested_operations: ["validate_signer_request"]
      }
    });
    expect(pairing.ok).toBe(true);
    if (pairing.ok !== true || !("pairing_intent" in pairing.result)) {
      throw new Error("pairing intent was not returned");
    }

    const approval = approvePairingIntent(pairing.result.pairing_intent, {
      approvedAt: 1_900_000_000,
      expiresAt: 2_000_000_000
    });

    expect(approval).toMatchObject({
      format: "nsealr-local-pairing-approval-v0",
      pairing_digest: pairing.result.pairing_intent.pairing_digest,
      approved_at: 1_900_000_000,
      stores_production_secrets: false,
      grant: {
        client_id: clientIdForIdentity(client),
        origin: client.origin,
        surface: client.surface,
        allowed_operations: ["validate_signer_request"],
        expires_at: 2_000_000_000
      }
    });
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-approved-validation",
      operation: "validate_signer_request",
      params: { client, request }
    }, { grants: [approval.grant], now: 1_900_000_000 })).toMatchObject({
      ok: true,
      result: { validation: { valid: true } }
    });
  });

  it("rejects tampered pairing intents and invalid approval expiry", () => {
    const pairing = handleLocalServiceRequest({
      version: 1,
      request_id: "svc-pair-tampered",
      operation: "request_pairing",
      params: {
        client,
        requested_operations: ["validate_signer_request"]
      }
    });
    if (pairing.ok !== true || !("pairing_intent" in pairing.result)) {
      throw new Error("pairing intent was not returned");
    }
    const intent = pairing.result.pairing_intent;
    expect(() => approvePairingIntent({
      ...intent,
      requested_operations: ["verify_signer_response"]
    }, { approvedAt: 1_900_000_000 })).toThrow(/digest mismatch/u);
    expect(() => approvePairingIntent({
      ...intent,
      client_id: "0".repeat(64)
    }, { approvedAt: 1_900_000_000 })).toThrow(/client_id mismatch/u);
    expect(() => approvePairingIntent({
      ...intent,
      requested_operations: ["service_status"]
    } as unknown as typeof intent, { approvedAt: 1_900_000_000 })).toThrow(/does not require pairing/u);
    expect(() => approvePairingIntent(intent, {
      approvedAt: 1_900_000_000,
      expiresAt: 1_900_000_000
    })).toThrow(/greater than approvedAt/u);
  });

  it("rejects validation requests from unpaired clients before parsing signer payloads", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-validate-unpaired",
      operation: "validate_signer_request",
      params: {
        client,
        request
      }
    })).toEqual({
      version: 1,
      request_id: "svc-validate-unpaired",
      ok: false,
      error: {
        code: "unauthorized_client",
        message: "client is not paired",
        retryable: false
      }
    });
  });

  it("validates signer requests only after explicit in-memory authorization", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-validate-1",
      operation: "validate_signer_request",
      params: { client, request }
    }, { grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: true,
      result: { validation: { valid: true } }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-validate-2",
      operation: "validate_signer_request",
      params: { client, request: { ...request, request_id: "bad request id" } }
    }, { grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: true,
      result: { validation: { valid: false, error: "request_id is invalid" } }
    });
  });

  it("selects a secretless account route only after explicit in-memory authorization", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-route-unpaired",
      operation: "select_account_route",
      params: {
        client,
        route_request: routeVector.request
      }
    }, { accounts: fixtures.accounts, now: 1_900_000_000 })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client is not paired" }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-route-1",
      operation: "select_account_route",
      params: {
        client,
        route_request: routeVector.request
      }
    }, { accounts: fixtures.accounts, grants: [routeGrant], now: 1_900_000_000 })).toEqual({
      version: 1,
      request_id: "svc-route-1",
      ok: true,
      result: {
        route_selection: routeVector.selection
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-route-unknown",
      operation: "select_account_route",
      params: {
        client,
        route_request: {
          ...routeVector.request,
          account_id: "acct-missing"
        }
      }
    }, { accounts: fixtures.accounts, grants: [routeGrant], now: 1_900_000_000 })).toMatchObject({
      ok: false,
      error: {
        code: "route_selection_failed",
        message: "route selection account_id is unknown"
      }
    });
  });

  it("rejects revoked, expired, and operation-scoped pairings deterministically", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-revoked",
      operation: "validate_signer_request",
      params: { client, request }
    }, { grants: [{ ...grant, revoked: true }], now: 1_900_000_000 })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client pairing is revoked" }
    });
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-expired",
      operation: "validate_signer_request",
      params: { client, request }
    }, { grants: [grant], now: 2_000_000_000 })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client pairing is expired" }
    });
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-scope",
      operation: "verify_signer_response",
      params: { client, request, response }
    }, {
      grants: [{ ...grant, allowed_operations: ["validate_signer_request"] }],
      now: 1_900_000_000
    })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client is not authorized for operation" }
    });
  });

  it("uses the latest matching in-memory grant when grant history is supplied", () => {
    const oldValidationGrant: LocalClientGrant = {
      ...grant,
      allowed_operations: ["validate_signer_request"],
      approved_at: 100
    };
    const newerVerificationGrant: LocalClientGrant = {
      ...grant,
      allowed_operations: ["verify_signer_response"],
      approved_at: 200
    };

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-latest-scope",
      operation: "validate_signer_request",
      params: { client, request }
    }, {
      grants: [oldValidationGrant, newerVerificationGrant],
      now: 1_900_000_000
    })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client is not authorized for operation" }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-latest-verify",
      operation: "verify_signer_response",
      params: { client, request, response }
    }, {
      grants: [oldValidationGrant, newerVerificationGrant],
      now: 1_900_000_000
    })).toMatchObject({
      ok: true,
      result: { validation: { valid: true } }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-latest-revoked",
      operation: "validate_signer_request",
      params: { client, request }
    }, {
      grants: [
        oldValidationGrant,
        {
          ...grant,
          allowed_operations: ["validate_signer_request", "verify_signer_response"],
          approved_at: 300,
          revoked: true
        }
      ],
      now: 1_900_000_000
    })).toMatchObject({
      ok: false,
      error: { code: "unauthorized_client", message: "client pairing is revoked" }
    });
  });

  it("verifies signer responses against their original request", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-verify-1",
      operation: "verify_signer_response",
      params: { client, request, response }
    }, { grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: true,
      result: { validation: { valid: true } }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-verify-2",
      operation: "verify_signer_response",
      params: { client, request, response: { ...response, request_id: "other-request" } }
    }, { grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: true,
      result: { validation: { valid: false, error: "response request_id does not match request" } }
    });
  });

  it("dispatches signer requests only through an explicit route dispatcher", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-unavailable",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, { accounts: fixtures.accounts, grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: false,
      error: {
        code: "signer_route_unavailable",
        message: "signer dispatch is not configured"
      }
    });

    const dispatched: unknown[] = [];
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-1",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: (dispatchRequest) => {
        dispatched.push(dispatchRequest);
        return response;
      }
    })).toEqual({
      version: 1,
      request_id: "svc-dispatch-1",
      ok: true,
      result: {
        signer_response: response
      }
    });
    expect(dispatched).toEqual([{
      client,
      route_selection: routeVector.selection,
      request
    }]);
  });

  it("requires explicit external review acknowledgement for display-less smartcard dispatch", () => {
    let called = false;
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-smartcard-dispatch-no-review",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: smartcardRouteVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        called = true;
        return response;
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "external_review_acknowledgement_required",
        message: "display-less signer dispatch requires external review acknowledgement"
      }
    });
    expect(called).toBe(false);

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-smartcard-dispatch-wrong-review",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: smartcardRouteVector.request,
        request,
        external_review_acknowledgement: externalReviewAcknowledgement("0".repeat(64))
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        called = true;
        return response;
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "external_review_acknowledgement_mismatch",
        message: "external review approval_digest does not match signer request"
      }
    });
    expect(called).toBe(false);
  });

  it("passes acknowledged display-less smartcard requests through the injected dispatcher", () => {
    const acknowledgement = externalReviewAcknowledgement();
    const dispatched: unknown[] = [];

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-smartcard-dispatch-reviewed",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: smartcardRouteVector.request,
        request,
        external_review_acknowledgement: acknowledgement
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: (dispatchRequest) => {
        dispatched.push(dispatchRequest);
        return response;
      }
    })).toEqual({
      version: 1,
      request_id: "svc-smartcard-dispatch-reviewed",
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

  it("rejects external review acknowledgement on non-display-less dispatch routes", () => {
    let called = false;
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-esp32-dispatch-unexpected-review",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request,
        external_review_acknowledgement: externalReviewAcknowledgement()
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        called = true;
        return response;
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "external_review_acknowledgement_unsupported",
        message: "external review acknowledgement is only supported for display-less sign_event dispatch"
      }
    });
    expect(called).toBe(false);
  });

  it("matches the shared route-refusal contract for every signer route", () => {
    for (const routeCase of routeRefusalContract.cases) {
      const selectionVector = fixtures.routeSelections.find(
        (candidate) => candidate.name === routeCase.route_selection_vector
      );
      if (selectionVector === undefined) throw new Error(`missing route selection ${routeCase.route_selection_vector}`);
      const serviceRequestId = `svc-refusal-${routeCase.route_type}`;
      const baseRequest = {
        version: 1 as const,
        request_id: serviceRequestId,
        operation: "dispatch_signer_request" as const,
        params: {
          client,
          route_request: selectionVector.request,
          request
        }
      };

      const withoutAcknowledgement = handleLocalServiceRequest(baseRequest, {
        accounts: fixtures.accounts,
        grants: [grant],
        now: 1_900_000_000
      });

      if (routeCase.external_review_acknowledgement.mode === "required") {
        expect(withoutAcknowledgement).toMatchObject({
          ok: false,
          error: {
            code: routeCase.external_review_acknowledgement.missing_error.error_code,
            message: routeCase.external_review_acknowledgement.missing_error.message,
            retryable: routeCase.external_review_acknowledgement.missing_error.retryable
          }
        });
        expect(handleLocalServiceRequest({
          ...baseRequest,
          params: {
            ...baseRequest.params,
            external_review_acknowledgement: externalReviewAcknowledgement("0".repeat(64))
          }
        }, {
          accounts: fixtures.accounts,
          grants: [grant],
          now: 1_900_000_000
        })).toMatchObject({
          ok: false,
          error: {
            code: routeCase.external_review_acknowledgement.mismatch_error.error_code,
            message: routeCase.external_review_acknowledgement.mismatch_error.message,
            retryable: routeCase.external_review_acknowledgement.mismatch_error.retryable
          }
        });
        expect(handleLocalServiceRequest({
          ...baseRequest,
          params: {
            ...baseRequest.params,
            external_review_acknowledgement: externalReviewAcknowledgement()
          }
        }, {
          accounts: fixtures.accounts,
          grants: [grant],
          now: 1_900_000_000
        })).toMatchObject({
          ok: false,
          error: {
            code: routeCase.without_dispatcher_after_ack?.error_code,
            message: routeCase.without_dispatcher_after_ack?.message,
            retryable: routeCase.without_dispatcher_after_ack?.retryable
          }
        });
      } else {
        expect(withoutAcknowledgement).toMatchObject({
          ok: false,
          error: {
            code: routeCase.without_dispatcher?.error_code,
            message: routeCase.without_dispatcher?.message,
            retryable: routeCase.without_dispatcher?.retryable
          }
        });
        expect(handleLocalServiceRequest({
          ...baseRequest,
          params: {
            ...baseRequest.params,
            external_review_acknowledgement: externalReviewAcknowledgement()
          }
        }, {
          accounts: fixtures.accounts,
          grants: [grant],
          now: 1_900_000_000
        })).toMatchObject({
          ok: false,
          error: {
            code: routeCase.external_review_acknowledgement.unsupported_error.error_code,
            message: routeCase.external_review_acknowledgement.unsupported_error.message,
            retryable: routeCase.external_review_acknowledgement.unsupported_error.retryable
          }
        });
      }
    }
  });

  it("rejects malformed external review acknowledgements before route dispatch", () => {
    let called = false;
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-smartcard-dispatch-malformed-review",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: smartcardRouteVector.request,
        request,
        external_review_acknowledgement: {
          ...externalReviewAcknowledgement(),
          contains_secret_material: true
        }
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        called = true;
        return response;
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "external review acknowledgement must not contain secret material"
      }
    });
    expect(called).toBe(false);
  });

  it("keeps external NIP-46 routes as secretless adapter metadata", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-external-nip46-route",
      operation: "select_account_route",
      params: {
        client,
        route_request: externalNip46RouteVector.request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [routeGrant],
      now: 1_900_000_000
    })).toEqual({
      version: 1,
      request_id: "svc-external-nip46-route",
      ok: true,
      result: {
        route_selection: externalNip46RouteVector.selection
      }
    });
    expect(externalNip46RouteVector.selection).toMatchObject({
      route_type: "external_nip46",
      transport: "nip46_relay",
      custody: "external_signer",
      trusted_review: "external_policy",
      policy_support: "external",
      physical_review: false,
      physical_approval: false,
      persistent_grants: false,
      contains_secret_material: false
    });
    expect("repository" in externalNip46RouteVector.selection).toBe(false);

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-external-nip46-dispatch-unavailable",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: externalNip46RouteVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000
    })).toMatchObject({
      ok: false,
      error: {
        code: "signer_route_unavailable",
        message: "signer dispatch is not configured"
      }
    });

    const dispatched: unknown[] = [];
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-external-nip46-dispatch-injected",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: externalNip46RouteVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: (dispatchRequest) => {
        dispatched.push(dispatchRequest);
        return response;
      }
    })).toMatchObject({
      ok: true,
      result: {
        signer_response: response
      }
    });
    expect(dispatched).toEqual([{
      client,
      route_selection: externalNip46RouteVector.selection,
      request
    }]);
  });

  it("builds route-aware dispatchers without opening real transports", () => {
    const calls: string[] = [];
    const dispatcher = createRouteDispatcher([
      {
        route_type: "raspberry_qr_vault",
        dispatch: () => {
          calls.push("wrong-route");
          return response;
        }
      },
      {
        route_type: routeVector.selection.route_type,
        dispatch: () => {
          calls.push("route-type");
          return response;
        }
      },
      {
        account_id: routeVector.selection.account_id,
        route_type: routeVector.selection.route_type,
        dispatch: () => {
          calls.push("account-specific");
          return response;
        }
      }
    ]);

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-registry",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: dispatcher
    })).toMatchObject({
      ok: true,
      result: {
        signer_response: response
      }
    });
    expect(calls).toEqual(["account-specific"]);
  });

  it("reports unavailable or ambiguous route dispatcher registry matches deterministically", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-registry-missing",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: createRouteDispatcher([{
        route_type: "raspberry_qr_vault",
        dispatch: () => response
      }])
    })).toMatchObject({
      ok: false,
      error: {
        code: "signer_route_unavailable",
        message: "no signer dispatcher for route esp32_usb_nip46"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-registry-ambiguous",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: createRouteDispatcher([
        {
          route_type: routeVector.selection.route_type,
          dispatch: () => response
        },
        {
          route_type: routeVector.selection.route_type,
          dispatch: () => response
        }
      ])
    })).toMatchObject({
      ok: false,
      error: {
        code: "signer_dispatch_failed",
        message: "ambiguous signer dispatcher for route esp32_usb_nip46"
      }
    });
  });

  it("reports signer transport failures with deterministic transport codes", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-transport-timeout",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        throw new SignerTransportError(
          "signer_transport_timeout",
          "serial line transport timed out before response after 1000ms"
        );
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "signer_transport_timeout",
        message: "serial line transport timed out before response after 1000ms"
      }
    });
  });

  it("awaits async signer dispatchers through the async service boundary", async () => {
    const result = await handleLocalServiceRequestAsync({
      version: 1,
      request_id: "svc-dispatch-async",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: async (dispatchRequest) => {
        expect(dispatchRequest.route_selection.route_type).toBe("esp32_usb_nip46");
        return response;
      }
    });

    expect(result).toMatchObject({
      ok: true,
      result: {
        signer_response: response
      }
    });
  });

  it("keeps async signer dispatchers out of the synchronous service boundary", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-async-sync-boundary",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: async () => response
    })).toMatchObject({
      ok: false,
      error: {
        code: "signer_dispatch_failed",
        message: "async signer dispatcher requires handleLocalServiceRequestAsync"
      }
    });
  });

  it("rejects unsafe dispatch input before route dispatch", () => {
    let called = false;
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-unsafe",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request: { ...request, request_id: "bad request id" }
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => {
        called = true;
        return response;
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_signer_request",
        message: "request_id is invalid"
      }
    });
    expect(called).toBe(false);
  });

  it("rejects route/request mismatches and malformed dispatch responses", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-method-mismatch",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: { ...routeVector.request, method: "get_public_key" },
        request
      }
    }, { accounts: fixtures.accounts, grants: [grant], now: 1_900_000_000 })).toMatchObject({
      ok: false,
      error: {
        code: "route_selection_failed",
        message: "route selection method does not match signer request"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-bad-response",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => ({ ...response, request_id: "other-request" })
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_signer_response",
        message: "response request_id does not match request"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-wrong-route-pubkey",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request
      }
    }, {
      accounts: accountsWithSelectedRoutePublicKey("dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"),
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => response
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_signer_response",
        message: "signer response public key does not match selected route"
      }
    });

    const publicKeyRequest = {
      version: 1,
      request_id: "req-route-pubkey",
      method: "get_public_key"
    };
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-dispatch-wrong-get-public-key",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: { ...routeVector.request, method: "get_public_key" },
        request: publicKeyRequest
      }
    }, {
      accounts: accountsWithSelectedRoutePublicKey("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"),
      grants: [grant],
      now: 1_900_000_000,
      signerDispatcher: () => ({
        version: 1,
        request_id: "req-route-pubkey",
        ok: true,
        result: {
          public_key: response.result.event.pubkey
        }
      })
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_signer_response",
        message: "signer response public key does not match selected route"
      }
    });
  });

  it("rejects malformed local service requests deterministically", () => {
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-bad-origin",
      operation: "request_pairing",
      params: {
        client: {
          ...client,
          origin: "http://localhost.evil.example"
        },
        requested_operations: ["validate_signer_request"]
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "client origin scheme is unsupported"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-url-with-path",
      operation: "request_pairing",
      params: {
        client: {
          ...client,
          origin: "https://example.com/path"
        },
        requested_operations: ["validate_signer_request"]
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "client origin scheme is unsupported"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "bad service id",
      operation: "service_status"
    })).toEqual({
      version: 1,
      request_id: "invalid-service-request",
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "service request_id is invalid",
        retryable: false
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-extra-top-level",
      operation: "request_pairing",
      params: {
        client,
        requested_operations: ["validate_signer_request"]
      },
      unsigned_metadata: "not allowed"
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "service request has unsupported fields"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-extra-request-pairing-param",
      operation: "request_pairing",
      params: {
        client,
        requested_operations: ["validate_signer_request"],
        route_request: routeVector.request
      }
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "request_pairing params have unsupported fields"
      }
    });

    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "svc-extra-dispatch-param",
      operation: "dispatch_signer_request",
      params: {
        client,
        route_request: routeVector.request,
        request,
        signer_hint: "not allowed"
      }
    }, {
      accounts: fixtures.accounts,
      grants: [grant],
      now: 1_900_000_000
    })).toMatchObject({
      ok: false,
      error: {
        code: "invalid_service_request",
        message: "dispatch_signer_request params have unsupported fields"
      }
    });
  });
});
