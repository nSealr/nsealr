import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import { validateRequest } from "@nsealr/protocol";
import {
  approveNip46AuthChallengeReview,
  approveNip46ConnectReview,
  createNip46SessionLifecycleCheckpoint,
  decideNip46BridgeAction,
  evaluateNip46RelayRequestStep,
  evaluateNip46RelayResponseStep,
  evaluateNip46SessionRequestGate,
  isNip46RequestPermitted,
  nip46ResponseFromNSealr,
  nip46PermissionRequirementFromRequest,
  parseNip46ApprovedPermissions,
  parseNip46AuthChallengeApproval,
  parseNip46AuthChallengeReview,
  parseNip46ConnectionUri,
  parseNip46ConnectIntent,
  parseNip46ConnectApproval,
  parseNip46ConnectReview,
  parseNip46PolicyFile,
  parseNip46RelayEventEnvelope,
  parseNip46SessionActive,
  parseNip46SessionLifecycle,
  nsealrRequestFromNip46,
  parseNip46Permissions,
  reviewNip46AuthChallengeStep,
  reviewNip46ConnectMessage,
  respondToLocalNip46Request,
  verifyNip46ConnectionTokenResponse
} from "./nip46.js";

const specsRoot = resolveSpecsRoot();

function load(rel: string): unknown {
  return JSON.parse(readFileSync(resolve(specsRoot, rel), "utf8"));
}

function canonicalJson(value: unknown): string {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    const encoded = JSON.stringify(value);
    if (encoded === undefined) throw new Error("unsupported digest value");
    return encoded;
  }
  if (Array.isArray(value)) return `[${value.map((item) => canonicalJson(item)).join(",")}]`;
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`)
      .join(",")}}`;
  }
  throw new Error("unsupported digest value");
}

function forgedConnectReviewDigest(reviewWithoutDigest: unknown): string {
  return createHash("sha256")
    .update(canonicalJson({
      format: "nsealr-nip46-connect-digest-v0",
      review: reviewWithoutDigest
    }))
    .digest("hex");
}

describe("NIP-46 bridge payloads", () => {
  it("maps a decrypted sign_event request to a nSealr signing request", () => {
    const signEventRequest = load("examples/request-kind-1-basic.json") as {
      params: { event_template: unknown };
    };
    const message = {
      id: "nip46-req-1",
      method: "sign_event",
      params: [JSON.stringify(signEventRequest.params.event_template)]
    };

    const request = nsealrRequestFromNip46(message);

    expect(request).toEqual({
      version: 1,
      request_id: "nip46-req-1",
      method: "sign_event",
      params: {
        event_template: signEventRequest.params.event_template
      }
    });
    expect(validateRequest(request).ok).toBe(true);
  });

  it("maps a decrypted get_public_key request to a nSealr public-key request", () => {
    expect(
      nsealrRequestFromNip46({
        id: "nip46-key-1",
        method: "get_public_key",
        params: []
      })
    ).toEqual({
      version: 1,
      request_id: "nip46-key-1",
      method: "get_public_key"
    });
  });

  it("maps nSealr signed-event and public-key responses back to NIP-46 result strings", () => {
    const eventResponse = load("examples/response-kind-1-basic.json");
    const publicKeyResponse = load("examples/response-get-public-key.json");

    const eventMessage = nip46ResponseFromNSealr("nip46-req-1", eventResponse);
    const publicKeyMessage = nip46ResponseFromNSealr("nip46-key-1", publicKeyResponse);

    expect(eventMessage.id).toBe("nip46-req-1");
    expect(JSON.parse(eventMessage.result ?? "{}")).toEqual((eventResponse as { result: { event: unknown } }).result.event);
    expect(publicKeyMessage).toEqual({
      id: "nip46-key-1",
      result: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"
    });
  });

  it("maps nSealr errors to NIP-46 error strings", () => {
    expect(nip46ResponseFromNSealr("nip46-req-1", load("examples/response-error-rejected.json"))).toEqual({
      id: "nip46-req-1",
      error: "user_rejected: User rejected the signing request."
    });
  });

  it("handles ping locally without reaching a signer transport", () => {
    expect(respondToLocalNip46Request({ id: "ping-1", method: "ping", params: [] })).toEqual({
      id: "ping-1",
      result: "pong"
    });
  });

  it("handles switch_relays as local no-change metadata without relay I/O", () => {
    const message = { id: "nip46-switch-relays-1", method: "switch_relays", params: [] };

    expect(nip46PermissionRequirementFromRequest(message)).toEqual({ method: "switch_relays" });
    expect(respondToLocalNip46Request(message)).toEqual({
      id: "nip46-switch-relays-1",
      result: "null"
    });
    expect(decideNip46BridgeAction(message, parseNip46Permissions("switch_relays"))).toEqual({
      type: "local_response",
      permission_requirement: { method: "switch_relays" },
      response_message: {
        id: "nip46-switch-relays-1",
        result: "null"
      }
    });
    expect(() =>
      respondToLocalNip46Request({
        id: "nip46-switch-relays-1",
        method: "switch_relays",
        params: ["wss://relay.example.com/"]
      })
    ).toThrow(/switch_relays params must be empty/u);
  });

  it("matches shared NIP-46 bridge vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(specsRoot);
    const signEvent = fixtures.nip46Payloads.find((vector) => vector.name === "sign-event-kind-1-basic");
    const rejectedSignEvent = fixtures.nip46Payloads.find((vector) => vector.name === "sign-event-user-rejected");
    const connect = fixtures.nip46Payloads.find((vector) => vector.name === "connect-policy-review");
    const getPublicKey = fixtures.nip46Payloads.find((vector) => vector.name === "get-public-key");
    const ping = fixtures.nip46Payloads.find((vector) => vector.name === "ping");
    const switchRelays = fixtures.nip46Payloads.find((vector) => vector.name === "switch-relays-no-change");

    if (connect?.connect_review === undefined || connect.connect_approval === undefined) {
      throw new Error("missing connect review fixture");
    }
    expect(parseNip46ConnectIntent(connect?.request_message)).toEqual(connect?.connect_intent);
    expect(reviewNip46ConnectMessage(connect?.request_message)).toEqual(connect.connect_review);
    expect(
      approveNip46ConnectReview(connect.connect_review, {
        reviewedConnectDigest: connect.connect_review.connect_digest,
        approvedAt: connect.connect_approval.approved_at
      })
    ).toEqual(connect.connect_approval);
    expect(nsealrRequestFromNip46(signEvent?.request_message)).toEqual(signEvent?.nsealr_request);
    expect(nip46ResponseFromNSealr(signEvent?.request_message.id ?? "", signEvent?.nsealr_response)).toEqual(
      signEvent?.response_message
    );
    expect(nsealrRequestFromNip46(rejectedSignEvent?.request_message)).toEqual(rejectedSignEvent?.nsealr_request);
    expect(
      nip46ResponseFromNSealr(
        rejectedSignEvent?.request_message.id ?? "",
        rejectedSignEvent?.nsealr_response
      )
    ).toEqual(rejectedSignEvent?.response_message);
    expect(nsealrRequestFromNip46(getPublicKey?.request_message)).toEqual(getPublicKey?.nsealr_request);
    expect(nip46ResponseFromNSealr(getPublicKey?.request_message.id ?? "", getPublicKey?.nsealr_response)).toEqual(
      getPublicKey?.response_message
    );
    expect(respondToLocalNip46Request(ping?.request_message)).toEqual(ping?.local_response_message);
    expect(respondToLocalNip46Request(switchRelays?.request_message)).toEqual(
      switchRelays?.local_response_message
    );
    for (const vector of [signEvent, rejectedSignEvent, getPublicKey, ping, switchRelays]) {
      expect(nip46PermissionRequirementFromRequest(vector?.request_message)).toEqual(vector?.permission_requirement);
      for (const check of vector?.permission_checks ?? []) {
        expect(isNip46RequestPermitted(vector?.request_message, check.granted_permissions)).toBe(check.permitted);
      }
    }
    for (const vector of fixtures.nip46Payloads) {
      expect(vector.bridge_decisions?.length).toBeGreaterThan(0);
      for (const check of vector.bridge_decisions ?? []) {
        expect(decideNip46BridgeAction(vector.request_message, check.granted_permissions)).toEqual(check.decision);
      }
    }
  });

  it("rejects unsupported or unsafe NIP-46 request payloads", () => {
    expect(() => nsealrRequestFromNip46({ id: "bad id", method: "get_public_key", params: [] })).toThrow(
      /id is invalid/u
    );
    expect(() => nsealrRequestFromNip46({ id: "nip46-req-1", method: "ping", params: [] })).toThrow(
      /handled locally/u
    );
    expect(() =>
      nsealrRequestFromNip46({
        id: "nip46-req-1",
        method: "sign_event",
        params: [JSON.stringify({ created_at: 1710000000, kind: 1, tags: [], content: "", sig: "00" })]
      })
    ).toThrow(/event_template contains forbidden fields/u);
  });

  it("parses NIP-46 permission strings without granting permissions", () => {
    expect(parseNip46Permissions("nip44_encrypt,sign_event:4,sign_event:30023")).toEqual([
      { method: "nip44_encrypt" },
      { method: "sign_event", parameter: "4", event_kind: 4 },
      { method: "sign_event", parameter: "30023", event_kind: 30023 }
    ]);
    expect(parseNip46Permissions("sign_event")).toEqual([{ method: "sign_event" }]);
    expect(parseNip46ApprovedPermissions("get_public_key,sign_event:1")).toEqual([
      { method: "get_public_key" },
      { method: "sign_event", parameter: "1", event_kind: 1 }
    ]);
    expect(() => parseNip46ApprovedPermissions("sign_event")).toThrow(
      /approved sign_event permission must include parameter and event_kind/u
    );
    expect(parseNip46Permissions("")).toEqual([]);
    expect(() => parseNip46Permissions("sign_event:not-a-kind")).toThrow(/sign_event permission kind/u);
    expect(() => parseNip46Permissions("connect")).toThrow(/must not request connect/u);
    expect(() => parseNip46Permissions("unknown_method")).toThrow(/unsupported permission method/u);
  });

  it("parses policy files in package code instead of CLI code", () => {
    const policy = load("vectors/nip46-policy-files/sign-event-kind-1-approved.json");

    expect(parseNip46PolicyFile(policy)).toEqual([{ method: "sign_event", parameter: "1", event_kind: 1 }]);
    expect(() =>
      parseNip46PolicyFile({
        format: "nsealr-nip46-policy-v0",
        approved_permissions: [{ method: "sign_event" }]
      })
    ).toThrow(/approved sign_event permission must include parameter and event_kind/u);
  });

  it("matches shared NIP-46 connection URI descriptor vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46ConnectionUris.map((vector) => vector.name)).toEqual([
      "bunker-remote-signer-token",
      "nostrconnect-client-token"
    ]);
    for (const vector of fixtures.nip46ConnectionUris) {
      const descriptor = parseNip46ConnectionUri(vector.uri);
      expect(descriptor).toEqual(vector.expected_descriptor);
      expect(JSON.stringify(descriptor)).not.toContain(vector.secret_probe);
    }
  });

  it("matches shared NIP-46 connection token response vectors without echoing secrets", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46ConnectionTokenResponses.map((vector) => vector.name)).toEqual([
      "nostrconnect-client-secret-response"
    ]);
    for (const vector of fixtures.nip46ConnectionTokenResponses) {
      const sourceToken = fixtures.nip46ConnectionUris.find(
        (connectionUri) => `vectors/nip46-connection-uris/${connectionUri.name}.json` === vector.source_connection_uri_vector
      );
      if (sourceToken === undefined) throw new Error(`missing source token for ${vector.name}`);
      const verified = verifyNip46ConnectionTokenResponse({
        connectionUri: sourceToken.uri,
        responseStep: vector.response_step
      });
      expect(verified).toEqual(vector.expected_response);
      expect(JSON.stringify(verified)).not.toContain(sourceToken.secret_probe);
      expect(() =>
        verifyNip46ConnectionTokenResponse({
          connectionUri: sourceToken.uri.replace(sourceToken.secret_probe, "wrong-secret"),
          responseStep: vector.response_step
        })
      ).toThrow(/secret mismatch/u);
    }
  });

  it("matches shared NIP-46 relay event envelope vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46RelayEvents.map((vector) => vector.name)).toEqual([
      "sign-event-request-envelope",
      "sign-event-response-envelope"
    ]);
    for (const vector of fixtures.nip46RelayEvents) {
      expect(parseNip46RelayEventEnvelope(vector.event, vector.direction)).toEqual(vector.expected_envelope);
    }
  });

  it("matches shared NIP-46 relay step vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46RelaySteps.map((vector) => vector.name)).toEqual([
      "auth-challenge-response-step",
      "connect-ack-response-step",
      "get-public-key-response-step",
      "ping-request-step",
      "ping-response-step",
      "sign-event-error-response-step",
      "sign-event-request-step",
      "sign-event-response-step",
      "switch-relays-no-change-response-step",
      "switch-relays-response-step"
    ]);
    for (const vector of fixtures.nip46RelaySteps) {
      const actual = vector.format === "nsealr-nip46-relay-response-step-v1"
        ? evaluateNip46RelayResponseStep(vector)
        : evaluateNip46RelayRequestStep(vector);
      expect(actual).toEqual(vector.expected_step);
    }
    const authStep = fixtures.nip46RelaySteps.find((vector) => vector.name === "auth-challenge-response-step");
    expect(authStep?.expected_step).toMatchObject({
      result_type: "auth_challenge",
      auth_url: "https://remote-signer.example.com/auth?challenge=nip46-auth-1",
      opens_relay: false,
      dispatches_signer: false,
      persists_session_state: false
    });
  });

  it("classifies already decrypted connect ack relay responses without activating sessions", () => {
    const step = evaluateNip46RelayResponseStep({
      direction: "remote_signer_to_client",
      event: {
        id: "5b49f326b62609219e3106d02990684c9ff855a5a0f2051afcf7d907c40d66ea",
        kind: 24133,
        pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
        created_at: 1710000006,
        content: "nip44-v2-connect-ack-response-ciphertext-placeholder",
        tags: [
          [
            "p",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          ]
        ],
        sig: "11fe4644fc3f8a09b2d2b61aff883128654b7ea54951052dbf3afbacbf7f014fbd14653f350fc996a010835ec6c3f84cad5ce9f1a5b9b33d7eb06025b233ff2a"
      },
      decrypted_message: {
        id: "nip46-connect-1",
        result: "ack"
      }
    });

    expect(step).toMatchObject({
      result_type: "connect_ack_result",
      response_message: {
        id: "nip46-connect-1",
        result: "ack"
      },
      signed_event_shape_checked: false,
      result_pubkey_bound_to_expected_user: false,
      acknowledges_connect: false,
      opens_relay: false,
      creates_grants: false,
      dispatches_signer: false,
      persists_session_state: false
    });
  });

  it("classifies already decrypted switch_relays responses without opening relays", () => {
    const relayListStep = evaluateNip46RelayResponseStep({
      direction: "remote_signer_to_client",
      event: {
        id: "fb28d105e99a675fad0822b246be6840ed480d77a4dac5ec67f3efbb3acb6a8a",
        kind: 24133,
        pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
        created_at: 1710000007,
        content: "nip44-v2-switch-relays-response-ciphertext-placeholder",
        tags: [
          [
            "p",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          ]
        ],
        sig: "b6f140ddfecb724a0f71e84c498815d6dd2be346675bedece0f6a668e2a96d500432b46eb883cb1e0afd59afe0be62ad826362da6a1fdd07b7d20536cef701c7"
      },
      decrypted_message: {
        id: "nip46-switch-relays-1",
        result: "[\"wss://relay3.example.com/\",\"wss://relay4.example.com/path\"]"
      }
    });
    const noChangeStep = evaluateNip46RelayResponseStep({
      direction: "remote_signer_to_client",
      event: {
        id: "056e0a10bab0c4788aa73e82cad9f2e1dbcb15bb1345dcd0d3dd191dc8637d25",
        kind: 24133,
        pubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
        created_at: 1710000008,
        content: "nip44-v2-switch-relays-no-change-response-ciphertext-placeholder",
        tags: [
          [
            "p",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          ]
        ],
        sig: "96be56d454bb457c722a6bd2aa51c45f50cecc84712741a23f066e47ba08ef9aaf0719a83b4997c718b39b8a14041dd6a838e051f66bdc77d58e57e31dac69c5"
      },
      decrypted_message: {
        id: "nip46-switch-relays-2",
        result: "null"
      }
    });

    expect(relayListStep).toMatchObject({
      result_type: "relay_list_result",
      relay_urls: ["wss://relay3.example.com/", "wss://relay4.example.com/path"],
      opens_relay: false,
      creates_grants: false,
      persists_session_state: false
    });
    expect(noChangeStep).toMatchObject({
      result_type: "relay_no_change_result",
      relay_urls: null,
      opens_relay: false,
      creates_grants: false,
      persists_session_state: false
    });
  });

  it("matches shared NIP-46 auth challenge review and approval vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46AuthChallenges.map((vector) => vector.name)).toEqual([
      "auth-challenge-review"
    ]);
    for (const vector of fixtures.nip46AuthChallenges) {
      const sourceStep = fixtures.nip46RelaySteps.find(
        (relayStep) => `vectors/nip46-relay-steps/${relayStep.name}.json` === vector.source_relay_step_vector
      );
      if (sourceStep === undefined) throw new Error(`missing source relay step for ${vector.name}`);
      expect(reviewNip46AuthChallengeStep(sourceStep)).toEqual(vector.review);
      expect(parseNip46AuthChallengeReview(vector.review)).toEqual(vector.review);
      expect(
        approveNip46AuthChallengeReview(vector.review, {
          reviewedAuthChallengeDigest: (vector.review as { auth_challenge_digest: string }).auth_challenge_digest,
          approvedAt: (vector.approval as { approved_at: number }).approved_at
        })
      ).toEqual(vector.approval);
      expect(parseNip46AuthChallengeApproval(vector.approval)).toEqual(vector.approval);
      expect(vector.approval).toMatchObject({
        opens_url: false,
        opens_relay: false,
        acknowledges_connect: false,
        creates_grants: false,
        dispatches_signer: false,
        persists_session_state: false
      });
    }
  });

  it("matches shared NIP-46 session lifecycle checkpoint vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46Sessions.map((vector) => vector.name)).toEqual([
      "nostrconnect-approved-kind-1-checkpoint"
    ]);
    for (const vector of fixtures.nip46Sessions) {
      const actual = parseNip46SessionLifecycle(vector.session);
      expect(actual).toEqual(vector.session);
      expect(actual.acknowledges_connect).toBe(false);
      expect(actual.derives_nip44_key).toBe(false);
      expect(actual.opens_relay).toBe(false);
      expect(actual.creates_grants).toBe(false);
      expect(actual.dispatches_signer).toBe(false);
      expect(actual.persists_session_state).toBe(false);
      expect(JSON.stringify(actual)).not.toContain("secret-1");
    }
  });

  it("matches shared NIP-46 pending-session request gate vectors", () => {
    const fixtures = loadSpecsFixtures(specsRoot);

    expect(fixtures.nip46SessionGates.map((vector) => vector.name)).toEqual([
      "approved-pending-ack-sign-event-blocked"
    ]);
    for (const vector of fixtures.nip46SessionGates) {
      const sourceSession = fixtures.nip46Sessions.find(
        (session) => `vectors/nip46-sessions/${session.name}.json` === vector.source_session_vector
      );
      if (sourceSession === undefined) throw new Error(`missing source session for ${vector.name}`);
      const actual = evaluateNip46SessionRequestGate({
        format: vector.format,
        session: sourceSession.session,
        evaluated_at: vector.evaluated_at,
        direction: vector.direction,
        event: vector.event,
        decrypted_message: vector.decrypted_message
      });

      expect(actual).toEqual(vector.expected_gate);
      expect(actual.blocked_reason).toBe("connect_ack_pending");
      expect(actual.uses_session_permissions).toBe(false);
      expect(actual.acknowledges_connect).toBe(false);
      expect(actual.dispatches_signer).toBe(false);
      expect(actual.persists_session_state).toBe(false);
    }
  });

  it("creates reviewed-but-not-active NIP-46 session lifecycle checkpoints", () => {
    const connect = loadSpecsFixtures(specsRoot).nip46Payloads.find((vector) => vector.name === "connect-policy-review");
    const sessionVector = loadSpecsFixtures(specsRoot).nip46Sessions[0];
    if (connect === undefined) throw new Error("missing connect-policy-review vector");

    expect(parseNip46ConnectApproval(connect.connect_approval)).toEqual(connect.connect_approval);
    expect(createNip46SessionLifecycleCheckpoint(connect.connect_review, connect.connect_approval, {
      name: sessionVector.session.name,
      clientPubkey: sessionVector.session.client_pubkey,
      relays: sessionVector.session.relays,
      approvedPermissions: sessionVector.session.approved_permissions,
      expiresAt: sessionVector.session.expires_at
    })).toEqual(sessionVector.session);
    expect(() => createNip46SessionLifecycleCheckpoint(connect.connect_review, connect.connect_approval, {
      name: "bad-unapproved",
      clientPubkey: sessionVector.session.client_pubkey,
      relays: sessionVector.session.relays,
      approvedPermissions: [{ method: "sign_event", parameter: "4", event_kind: 4 }],
      expiresAt: sessionVector.session.expires_at
    })).toThrow("approved_permissions must be a subset of requested_permissions");
  });

  it("rejects unsafe or ambiguous NIP-46 connection URIs", () => {
    const pubkey = "c".repeat(64);

    expect(() => parseNip46ConnectionUri(`https://${pubkey}?relay=wss%3A%2F%2Frelay.example.com`)).toThrow(
      /scheme/u
    );
    expect(() => parseNip46ConnectionUri(`bunker://${pubkey}?relay=https%3A%2F%2Frelay.example.com`)).toThrow(
      /wss URL/u
    );
    expect(() => parseNip46ConnectionUri(`bunker://${pubkey}`)).toThrow(/at least one relay/u);
    expect(() =>
      parseNip46ConnectionUri(`bunker://bad-pubkey?relay=${encodeURIComponent("wss://relay.example.com")}`)
    ).toThrow(/remote-signer pubkey/u);
    expect(() =>
      parseNip46ConnectionUri(
        `bunker://${pubkey}?relay=${encodeURIComponent("wss://relay.example.com")}` +
          `&relay=${encodeURIComponent("wss://relay.example.com")}`
      )
    ).toThrow(/relays must be unique/u);
    expect(() =>
      parseNip46ConnectionUri(`nostrconnect://${pubkey}?relay=${encodeURIComponent("wss://relay.example.com")}`)
    ).toThrow(/requires a secret/u);
    expect(() =>
      parseNip46ConnectionUri(
        `nostrconnect://${pubkey}?relay=${encodeURIComponent("wss://relay.example.com")}&secret=secret` +
          `&perms=${encodeURIComponent("sign_event:not-a-kind")}`
      )
    ).toThrow(/sign_event permission kind/u);
    expect(() =>
      parseNip46ConnectionUri(
        `bunker://${pubkey}?relay=${encodeURIComponent("wss://relay.example.com")}&perms=sign_event%3A1`
      )
    ).toThrow(/bunker URI/u);
    expect(() =>
      parseNip46ConnectionUri(
        `nostrconnect://${pubkey}?relay=${encodeURIComponent("wss://relay.example.com")}&secret=secret&unknown=1`
      )
    ).toThrow(/unsupported query parameter/u);
  });

  it("rejects shared invalid NIP-46 hardening vectors deterministically", () => {
    const fixtures = loadSpecsFixtures(specsRoot);
    const vectors = fixtures.invalidVectors.filter(
      (vector) =>
        vector.category === "nip46" ||
        vector.category === "nip46-connection-uri" ||
        vector.category === "nip46-connection-token-response" ||
        vector.category === "nip46-relay-event" ||
        vector.category === "nip46-relay-step" ||
        vector.category === "nip46-session" ||
        vector.category === "nip46-session-gate" ||
        vector.category === "nip46-policy-file"
    );

    expect(vectors.length).toBeGreaterThan(0);
    for (const vector of vectors) {
      const action = () => {
        if (vector.category === "nip46-connection-uri") {
          if (typeof vector.uri !== "string") throw new Error(`${vector.name}: uri must be a string`);
          parseNip46ConnectionUri(vector.uri);
          return;
        }
        if (vector.category === "nip46-connection-token-response") {
          const tokenResponse = vector.connection_token_response as
            | { connection_uri?: unknown; response_step?: unknown }
            | undefined;
          if (
            typeof tokenResponse !== "object" ||
            tokenResponse === null ||
            typeof tokenResponse.connection_uri !== "string"
          ) {
            throw new Error(`${vector.name}: connection_token_response must include connection_uri`);
          }
          verifyNip46ConnectionTokenResponse({
            connectionUri: tokenResponse.connection_uri,
            responseStep: tokenResponse.response_step
          });
          return;
        }
        if (vector.category === "nip46-relay-event") {
          parseNip46RelayEventEnvelope(vector.relay_event, "client_to_remote_signer");
          return;
        }
        if (vector.category === "nip46-relay-step") {
          const relayStep = vector.relay_step;
          if (
            typeof relayStep === "object" &&
            relayStep !== null &&
            "format" in relayStep &&
            relayStep.format === "nsealr-nip46-relay-response-step-v1"
          ) {
            evaluateNip46RelayResponseStep(relayStep);
            return;
          }
          evaluateNip46RelayRequestStep(relayStep);
          return;
        }
        if (vector.category === "nip46-policy-file") {
          parseNip46PolicyFile(vector.policy_file);
          return;
        }
        if (vector.category === "nip46-session") {
          parseNip46SessionLifecycle(vector.session);
          return;
        }
        if (vector.category === "nip46-session-gate") {
          evaluateNip46SessionRequestGate(vector.session_gate);
          return;
        }
        decideNip46BridgeAction(vector.request_message, []);
      };
      expect(action, vector.name).toThrow(vector.expected_error);
    }
  });

  it("parses connect requests as policy-review intents without acknowledging them", () => {
    const remoteSignerPubkey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

    expect(
      parseNip46ConnectIntent({
        id: "connect-1",
        method: "connect",
        params: [remoteSignerPubkey, "secret-1", "sign_event:1,nip44_encrypt"]
      })
    ).toEqual({
      id: "connect-1",
      remote_signer_pubkey: remoteSignerPubkey,
      secret: "secret-1",
      requested_permissions: [{ method: "sign_event", parameter: "1", event_kind: 1 }, { method: "nip44_encrypt" }]
    });
    expect(() =>
      nsealrRequestFromNip46({ id: "connect-1", method: "connect", params: [remoteSignerPubkey] })
    ).toThrow(/requires policy review/u);
    expect(() =>
      parseNip46ConnectIntent({ id: "connect-1", method: "connect", params: ["bad-pubkey"] })
    ).toThrow(/remote-signer pubkey/u);
  });

  it("renders connect review pages without echoing the secret value", () => {
    const remoteSignerPubkey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

    const review = reviewNip46ConnectMessage({
      id: "connect-1",
      method: "connect",
      params: [remoteSignerPubkey, "secret-1", "sign_event:1,nip44_encrypt"]
    });

    expect(review).toEqual({
      format: "nsealr-nip46-connect-review-v0",
      id: "connect-1",
      remote_signer_pubkey: remoteSignerPubkey,
      secret_present: true,
      requested_permissions: [{ method: "sign_event", parameter: "1", event_kind: 1 }, { method: "nip44_encrypt" }],
      pages: [
        {
          title: "Connect",
          page_indicator: "Page 1/2",
          body_lines: ["Remote signer", remoteSignerPubkey, "Secret: provided"]
        },
        {
          title: "Permissions",
          page_indicator: "Page 2/2",
          body_lines: ["sign_event:1", "nip44_encrypt"]
        }
      ],
      connect_digest: "33425617fb26f264de60b825386701fd278676db71e3010f4230d8fa475f391b"
    });
    expect(JSON.stringify(review)).not.toContain("secret-1");
  });

  it("creates connect approval artifacts only after digest confirmation", () => {
    const remoteSignerPubkey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";
    const review = reviewNip46ConnectMessage({
      id: "connect-1",
      method: "connect",
      params: [remoteSignerPubkey, "secret-1", "sign_event:1,nip44_encrypt"]
    });

    expect(parseNip46ConnectReview(review)).toEqual(review);
    expect(approveNip46ConnectReview(review, {
      reviewedConnectDigest: review.connect_digest,
      approvedAt: 1_900_000_001
    })).toEqual({
      format: "nsealr-nip46-connect-approval-v0",
      id: "connect-1",
      connect_digest: review.connect_digest,
      approved_at: 1_900_000_001,
      acknowledges_connect: false,
      creates_grants: false,
      opens_relay: false,
      persists_session_state: false,
      stores_production_secrets: false,
      exposes_secret: false
    });
    expect(() =>
      approveNip46ConnectReview(review, {
        reviewedConnectDigest: "0".repeat(64),
        approvedAt: 1_900_000_001
      })
    ).toThrow(/reviewed connect digest/u);
    expect(() =>
      parseNip46ConnectReview({
        ...review,
        pages: [
          ...review.pages.slice(0, 1),
          {
            ...review.pages[1],
            body_lines: ["sign_event:30023", "nip44_encrypt"]
          }
        ]
      })
    ).toThrow(/digest mismatch/u);
    const nonCanonicalReview = {
      ...review,
      pages: [
        {
          ...review.pages[0],
          body_lines: ["Remote signer", "hidden", "Secret: provided"]
        },
        review.pages[1]
      ]
    };
    const reviewWithoutDigest = {
      format: nonCanonicalReview.format,
      id: nonCanonicalReview.id,
      remote_signer_pubkey: nonCanonicalReview.remote_signer_pubkey,
      secret_present: nonCanonicalReview.secret_present,
      requested_permissions: nonCanonicalReview.requested_permissions,
      pages: nonCanonicalReview.pages
    };
    expect(() =>
      parseNip46ConnectReview({
        ...reviewWithoutDigest,
        connect_digest: forgedConnectReviewDigest(reviewWithoutDigest)
      })
    ).toThrow(/not canonical/u);
  });

  it("matches request permissions without granting policy", () => {
    const signEventRequest = load("examples/request-kind-1-basic.json") as {
      params: { event_template: unknown };
    };
    const signEventMessage = {
      id: "nip46-req-1",
      method: "sign_event",
      params: [JSON.stringify(signEventRequest.params.event_template)]
    };

    expect(nip46PermissionRequirementFromRequest(signEventMessage)).toEqual({
      method: "sign_event",
      parameter: "1",
      event_kind: 1
    });
    expect(isNip46RequestPermitted(signEventMessage, parseNip46Permissions("sign_event:1"))).toBe(true);
    expect(isNip46RequestPermitted(signEventMessage, parseNip46Permissions("sign_event:4"))).toBe(false);
    expect(isNip46RequestPermitted(signEventMessage, parseNip46Permissions("sign_event"))).toBe(true);
    expect(
      isNip46RequestPermitted(
        {
          id: "nip46-key-1",
          method: "get_public_key",
          params: []
        },
        parseNip46Permissions("get_public_key")
      )
    ).toBe(true);
    expect(
      isNip46RequestPermitted(
        {
          id: "nip46-key-1",
          method: "get_public_key",
          params: []
        },
        []
      )
    ).toBe(false);
    expect(() =>
      nip46PermissionRequirementFromRequest({
        id: "connect-1",
        method: "connect",
        params: ["4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa"]
      })
    ).toThrow(/connect requires policy review/u);
  });

  it("decides whether a NIP-46 request may reach signer transport", () => {
    const signEventRequest = load("examples/request-kind-1-basic.json") as {
      params: { event_template: unknown };
    };
    const signEventMessage = {
      id: "nip46-req-1",
      method: "sign_event",
      params: [JSON.stringify(signEventRequest.params.event_template)]
    };

    expect(decideNip46BridgeAction(signEventMessage, parseNip46Permissions("sign_event:1"))).toEqual({
      type: "signer_request",
      permission_requirement: {
        method: "sign_event",
        parameter: "1",
        event_kind: 1
      },
      nsealr_request: {
        version: 1,
        request_id: "nip46-req-1",
        method: "sign_event",
        params: {
          event_template: signEventRequest.params.event_template
        }
      }
    });

    expect(decideNip46BridgeAction(signEventMessage, parseNip46Permissions("sign_event:4"))).toEqual({
      type: "permission_denied",
      permission_requirement: {
        method: "sign_event",
        parameter: "1",
        event_kind: 1
      },
      response_message: {
        id: "nip46-req-1",
        error: "permission_denied: request requires approved permission sign_event:1"
      }
    });
  });

  it("keeps local ping and connect inside the NIP-46 policy boundary", () => {
    const remoteSignerPubkey = "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa";

    expect(
      decideNip46BridgeAction(
        {
          id: "ping-1",
          method: "ping",
          params: []
        },
        parseNip46Permissions("ping")
      )
    ).toEqual({
      type: "local_response",
      permission_requirement: {
        method: "ping"
      },
      response_message: {
        id: "ping-1",
        result: "pong"
      }
    });

    expect(decideNip46BridgeAction({ id: "ping-1", method: "ping", params: [] }, [])).toEqual({
      type: "permission_denied",
      permission_requirement: {
        method: "ping"
      },
      response_message: {
        id: "ping-1",
        error: "permission_denied: request requires approved permission ping"
      }
    });

    expect(
      decideNip46BridgeAction(
        {
          id: "switch-relays-1",
          method: "switch_relays",
          params: []
        },
        parseNip46Permissions("switch_relays")
      )
    ).toEqual({
      type: "local_response",
      permission_requirement: {
        method: "switch_relays"
      },
      response_message: {
        id: "switch-relays-1",
        result: "null"
      }
    });

    expect(
      decideNip46BridgeAction(
        {
          id: "connect-1",
          method: "connect",
          params: [remoteSignerPubkey, "secret-1", "sign_event:1"]
        },
        []
      )
    ).toEqual({
      type: "connect_review",
      connect_intent: {
        id: "connect-1",
        remote_signer_pubkey: remoteSignerPubkey,
        secret: "secret-1",
        requested_permissions: [{ method: "sign_event", parameter: "1", event_kind: 1 }]
      }
    });
  });
});

describe("parseNip46SessionActive", () => {
  const loadActiveSession = (stem: string): Record<string, unknown> =>
    (load(`vectors/nip46-sessions-active/${stem}.json`) as { session: Record<string, unknown> }).session;

  it("accepts every official active-session phase vector", () => {
    for (const stem of ["connect-ack-kind-1", "session-active-kind-1", "session-closed-kind-1"]) {
      const parsed = parseNip46SessionActive(loadActiveSession(stem));
      expect(parsed.format).toBe("nsealr-nip46-session-active-v0");
      expect(parsed.persists_session_state).toBe(true);
    }
  });

  it("rejects an unknown phase", () => {
    const session = loadActiveSession("connect-ack-kind-1");
    expect(() => parseNip46SessionActive({ ...session, phase: "warming_up" })).toThrow("phase must be one of");
  });

  it("rejects production-secret storage and secret persisted fields", () => {
    const session = loadActiveSession("connect-ack-kind-1");
    expect(() => parseNip46SessionActive({ ...session, stores_production_secrets: true })).toThrow(
      "stores_production_secrets must be false"
    );
    expect(() =>
      parseNip46SessionActive({ ...session, persisted_state: { fields: ["nip44_key"], contains_secret_material: false } })
    ).toThrow("persisted_state.fields must not include secret field nip44_key");
  });
});
