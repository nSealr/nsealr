import { describe, expect, it } from "vitest";
import { LOCAL_PAIRING_REVIEW_FORMAT, reviewPairingIntent } from "./pairing-review.js";
import {
  approvePairingIntent,
  clientIdForIdentity,
  handleLocalServiceRequest,
  parsePairingIntent,
  type LocalClientIdentity,
  type PairingIntent
} from "./service.js";

const client: LocalClientIdentity = {
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "Example Nostr Client",
  instance_id: "pairing-review-test"
};

function pairingIntent() {
  const response = handleLocalServiceRequest({
    version: 1,
    request_id: "pairing-review-request",
    operation: "request_pairing",
    params: {
      client,
      requested_operations: ["select_account_route", "dispatch_signer_request"]
    }
  });
  if (response.ok !== true || !("pairing_intent" in response.result)) {
    throw new Error("pairing intent was not returned");
  }
  return response.result.pairing_intent;
}

describe("local pairing review", () => {
  it("projects a pairing intent into deterministic user-review metadata", () => {
    const intent = pairingIntent();

    expect(reviewPairingIntent(intent)).toEqual({
      format: LOCAL_PAIRING_REVIEW_FORMAT,
      client_id: clientIdForIdentity(client),
      client,
      requested_operations: [
        {
          operation: "select_account_route",
          label: "Read selected account route",
          effect: "The client can read selected account public key and route metadata."
        },
        {
          operation: "dispatch_signer_request",
          label: "Dispatch signer requests",
          effect: "The client can ask the service to validate, route, dispatch, and verify signer requests through an approved signer route."
        }
      ],
      pairing_digest: intent.pairing_digest,
      requires_user_approval: true,
      stores_production_secrets: false,
      contains_secret_material: false
    });
  });

  it("shares the same tamper checks as approval", () => {
    const intent = pairingIntent();
    const tampered = {
      ...intent,
      requested_operations: ["verify_signer_response"]
    };

    expect(() => parsePairingIntent(tampered)).toThrow(/digest mismatch/u);
    expect(() => reviewPairingIntent(tampered as unknown as PairingIntent)).toThrow(/digest mismatch/u);
    expect(() => approvePairingIntent(tampered as unknown as PairingIntent, { approvedAt: 1_900_000_000 })).toThrow(/digest mismatch/u);
  });

  it("rejects unsupported pairing-intent fields before review", () => {
    expect(() => reviewPairingIntent({
      ...pairingIntent(),
      private_key: "nope"
    } as unknown as PairingIntent)).toThrow(/unsupported fields/u);
  });

  it("refuses service operations that do not require pairing", () => {
    const intent = {
      ...pairingIntent(),
      requested_operations: ["service_status"]
    };

    expect(() => reviewPairingIntent(intent as unknown as PairingIntent)).toThrow(/does not require pairing/u);
  });
});
