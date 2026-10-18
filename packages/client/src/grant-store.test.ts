import { describe, expect, it } from "vitest";
import {
  appendLocalGrant,
  appendLocalGrantRevocation,
  createLocalGrantStore,
  LOCAL_GRANT_STORE_FORMAT,
  parseLocalGrant,
  parseLocalGrantStore,
  parseLocalPairingApproval,
  revokeLocalGrant,
  serializeLocalGrantStore
} from "./grant-store.js";
import {
  approvePairingIntent,
  handleLocalServiceRequest,
  type LocalClientIdentity
} from "./service.js";

const client: LocalClientIdentity = {
  surface: "browser_extension",
  origin: "https://example.com",
  app_name: "Example Nostr Client",
  instance_id: "grant-store-test"
};

const request = {
  version: 1,
  request_id: "grant-store-request",
  method: "sign_event",
  params: {
    event_template: {
      kind: 1,
      created_at: 1_710_000_000,
      tags: [],
      content: "grant-store test"
    }
  }
};

function approvedPairingApproval() {
  const pairing = handleLocalServiceRequest({
    version: 1,
    request_id: "grant-store-pairing",
    operation: "request_pairing",
    params: {
      client,
      requested_operations: ["validate_signer_request", "verify_signer_response"]
    }
  });
  if (pairing.ok !== true || !("pairing_intent" in pairing.result)) {
    throw new Error("pairing intent was not returned");
  }
  return approvePairingIntent(pairing.result.pairing_intent, {
    approvedAt: 1_900_000_000,
    expiresAt: 2_000_000_000
  });
}

function approvedGrant() {
  return approvedPairingApproval().grant;
}

describe("local grant store", () => {
  it("serializes a strict secretless grant history", () => {
    const grant = approvedGrant();
    const store = createLocalGrantStore([grant], { updatedAt: 1_900_000_001 });

    expect(store).toEqual({
      format: LOCAL_GRANT_STORE_FORMAT,
      updated_at: 1_900_000_001,
      contains_secret_material: false,
      grants: [grant]
    });
    expect(JSON.parse(serializeLocalGrantStore(store))).toEqual(store);
  });

  it("appends grant history without approving service operations", () => {
    const grant = approvedGrant();
    const store = createLocalGrantStore([], { updatedAt: 1_900_000_000 });
    const appended = appendLocalGrant(store, grant, { updatedAt: 1_900_000_001 });

    expect(appended.updated_at).toBe(1_900_000_001);
    expect(appended.grants).toEqual([grant]);
  });

  it("parses pairing approval artifacts before grant-store persistence", () => {
    const approval = approvedPairingApproval();

    expect(parseLocalPairingApproval(approval)).toEqual(approval);
    expect(() => parseLocalPairingApproval({
      ...approval,
      private_key: "nope"
    })).toThrow(/unsupported fields/u);
    expect(() => parseLocalPairingApproval({
      ...approval,
      stores_production_secrets: true
    })).toThrow(/production secrets/u);
    expect(() => parseLocalPairingApproval({
      ...approval,
      grant: {
        ...approval.grant,
        pairing_digest: "0".repeat(64)
      }
    })).toThrow(/pairing_digest mismatch/u);
    expect(() => parseLocalPairingApproval({
      ...approval,
      grant: {
        ...approval.grant,
        approved_at: approval.approved_at + 1
      }
    })).toThrow(/approved_at mismatch/u);
  });

  it("turns a latest persistent revocation into deterministic authorization denial", () => {
    const grant = approvedGrant();
    const revocation = revokeLocalGrant(grant, { revokedAt: 1_900_000_010 });
    const store = createLocalGrantStore([grant, revocation], { updatedAt: 1_900_000_010 });

    expect(revocation).toEqual({
      client_id: grant.client_id,
      origin: grant.origin,
      surface: grant.surface,
      allowed_operations: grant.allowed_operations,
      pairing_digest: grant.pairing_digest,
      approved_at: 1_900_000_010,
      revoked: true
    });
    expect(handleLocalServiceRequest({
      version: 1,
      request_id: "grant-store-revoked",
      operation: "validate_signer_request",
      params: { client, request }
    }, {
      grants: store.grants,
      now: 1_900_000_011
    })).toMatchObject({
      ok: false,
      error: {
        code: "unauthorized_client",
        message: "client pairing is revoked"
      }
    });
  });

  it("appends latest-client revocations to grant stores without mutating history", () => {
    const grant = approvedGrant();
    const store = createLocalGrantStore([grant], { updatedAt: 1_900_000_000 });
    const revokedStore = appendLocalGrantRevocation(store, {
      clientId: grant.client_id,
      origin: grant.origin,
      surface: grant.surface
    }, {
      revokedAt: 1_900_000_010
    });

    expect(store.grants).toEqual([grant]);
    expect(revokedStore.updated_at).toBe(1_900_000_010);
    expect(revokedStore.grants).toEqual([
      grant,
      {
        client_id: grant.client_id,
        origin: grant.origin,
        surface: grant.surface,
        allowed_operations: grant.allowed_operations,
        pairing_digest: grant.pairing_digest,
        approved_at: 1_900_000_010,
        revoked: true
      }
    ]);
    expect(() => appendLocalGrantRevocation(revokedStore, {
      clientId: grant.client_id,
      origin: grant.origin,
      surface: grant.surface
    }, {
      revokedAt: 1_900_000_011
    })).toThrow(/already revoked/u);
    expect(() => appendLocalGrantRevocation(store, {
      clientId: "0".repeat(64),
      origin: grant.origin,
      surface: grant.surface
    }, {
      revokedAt: 1_900_000_011
    })).toThrow(/no matching grant/u);
    expect(() => appendLocalGrantRevocation(store, {
      clientId: grant.client_id,
      origin: grant.origin,
      surface: grant.surface
    }, {
      revokedAt: 1_900_000_011,
      updatedAt: 1_900_000_010
    })).toThrow(/updatedAt/u);
  });

  it("rejects unsupported fields and secret material claims", () => {
    const grant = approvedGrant();

    expect(() => parseLocalGrantStore({
      format: LOCAL_GRANT_STORE_FORMAT,
      updated_at: 1_900_000_000,
      grants: [grant],
      contains_secret_material: true
    })).toThrow(/secret material/u);
    expect(() => parseLocalGrantStore({
      format: LOCAL_GRANT_STORE_FORMAT,
      updated_at: 1_900_000_000,
      grants: [grant],
      contains_secret_material: false,
      private_key: "nope"
    })).toThrow(/unsupported fields/u);
    expect(() => parseLocalGrant({
      ...grant,
      approved_at: undefined
    })).toThrow(/approved_at/u);
  });

  it("rejects malformed persistent grants before they can authorize a client", () => {
    const grant = approvedGrant();

    expect(() => parseLocalGrant({
      ...grant,
      allowed_operations: ["validate_signer_request", "validate_signer_request"]
    })).toThrow(/duplicated/u);
    expect(() => parseLocalGrant({
      ...grant,
      allowed_operations: ["request_pairing"]
    })).toThrow(/does not require pairing/u);
    expect(() => parseLocalGrant({
      ...grant,
      origin: "http://localhost.evil.example"
    })).toThrow(/origin scheme/u);
    expect(() => parseLocalGrant({
      ...grant,
      expires_at: grant.approved_at
    })).toThrow(/greater than approved_at/u);
  });
});
