import { readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  loadSpecsFixtures,
  validateAccessSurfaceFixture,
  validateFeatureMatrixFixture,
  validatePersistentSecretCustodyFixture,
  validateReviewTranscriptFixture,
  validateRouteRefusalContractFixture,
  validateSourcePublicKeyProofFixture
} from "./fixtures.js";
import { resolveSpecsRoot } from "./specs-root.js";

describe("fixture loading", () => {
  it("loads deterministic event vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.events.map((event) => event.name)).toEqual(expect.arrayContaining(["kind-1-basic", "kind-1-tags"]));
    expect(fixtures.key.name).toBe("test-key-1");
  });

  it("loads trusted review vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.reviews.map((review) => review.name)).toEqual(expect.arrayContaining([
      "kind-1-basic",
      "kind-1-long-events-many-tags",
      "kind-1-tags",
      "kind-1-unicode-boundary",
      "kind-30078-empty"
    ]));
    const longEvents = fixtures.reviews.find((review) => review.name === "kind-1-long-events-many-tags");
    const emptyParameterEvent = fixtures.reviews.find((review) => review.name === "kind-30078-empty");
    const unicodeBoundary = fixtures.reviews.find((review) => review.name === "kind-1-unicode-boundary");
    expect(longEvents?.review.content).toHaveLength(281);
    expect(longEvents?.review.tags).toHaveLength(9);
    expect(emptyParameterEvent?.review.kind).toBe(30078);
    expect(emptyParameterEvent?.review.content).toBe("");
    expect(unicodeBoundary?.review.content_utf8_bytes).toBe(8);
    expect(unicodeBoundary?.review.tags).toEqual([["t", "caffè"]]);
  });

  it("loads QR review transcript vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.reviewTranscripts.map((transcript) => transcript.name)).toEqual(expect.arrayContaining([
      "kind-1-basic-approve",
      "kind-1-basic-reject",
      "kind-1-long-events-many-tags-detail-scroll-approve"
    ]));
    expect(fixtures.reviewTranscripts[0].buttons).toEqual(["next", "next", "next", "approve"]);
    expect(fixtures.reviewTranscripts[1].transcript[0].decision).toBe(false);
    const detailScroll = fixtures.reviewTranscripts.find(
      (transcript) => transcript.name === "kind-1-long-events-many-tags-detail-scroll-approve"
    );
    expect(detailScroll?.buttons).toContain("scroll");
    expect(detailScroll?.transcript[0].frame.body_line_styles).toEqual(["meta", "meta", "meta", "value", "value"]);
  });

  it("validates QR review transcript fixtures in package code", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const detailScroll = structuredClone(
      fixtures.reviewTranscripts.find(
        (transcript) => transcript.name === "kind-1-long-events-many-tags-detail-scroll-approve"
      )
    );
    if (detailScroll === undefined) throw new Error("missing detail scroll transcript fixture");

    expect(() => validateReviewTranscriptFixture(detailScroll.name, detailScroll)).not.toThrow();

    const invalidButton = structuredClone(detailScroll);
    invalidButton.buttons[2] = "sideways";
    expect(() => validateReviewTranscriptFixture(invalidButton.name, invalidButton)).toThrow(/unsupported button/u);

    const invalidStyles = structuredClone(detailScroll);
    invalidStyles.transcript[0].frame.body_line_styles = ["meta"];
    expect(() => validateReviewTranscriptFixture(invalidStyles.name, invalidStyles)).toThrow(/body_line_styles mismatch/u);
  });

  it("loads trusted review-screen vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.reviewScreens.map((screen) => screen.name)).toEqual(expect.arrayContaining(["kind-1-basic", "kind-1-tags"]));
    expect(fixtures.reviewScreens[0].screen_review.approval_digest).toBe(
      "a09ddd564e439fdd4756da6863156eddcfc50c295af453af1c78c35986c303a5"
    );
  });

  it("loads review display-frame vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.reviewDisplayFrames.map((frame) => frame.name)).toEqual(expect.arrayContaining([
      "kind-1-long-content-page-1-20x3",
      "kind-1-unicode-boundary-content-4x3"
    ]));
    const longContentFrame = fixtures.reviewDisplayFrames.find(
      (frame) => frame.name === "kind-1-long-content-page-1-20x3"
    );
    const unicodeFrame = fixtures.reviewDisplayFrames.find(
      (frame) => frame.name === "kind-1-unicode-boundary-content-4x3"
    );
    expect(longContentFrame?.frame.body_lines).toEqual([
      "xxxxxxxxxxxxxxxxxxxx",
      "xxxxxxxxxxxxxxxxxxxx",
      "xxxxxxxxxxxxxxxxx..."
    ]);
    expect(unicodeFrame?.frame.body_lines).toEqual(["abcè", "def"]);
  });

  it("loads complete review detail-page vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.reviewDetailPages.map((pageSet) => pageSet.name)).toEqual(expect.arrayContaining([
      "kind-1-long-events-many-tags-t-display-s3",
      "kind-1-tags-t-display-s3",
      "kind-1-control-escapes-t-display-s3",
      "kind-1-unicode-boundary-t-display-s3"
    ]));
    const tagged = fixtures.reviewDetailPages.find((pageSet) => pageSet.name === "kind-1-tags-t-display-s3");
    const longTags = fixtures.reviewDetailPages.find(
      (pageSet) => pageSet.name === "kind-1-long-events-many-tags-t-display-s3"
    );
    const unicodeBoundary = fixtures.reviewDetailPages.find(
      (pageSet) => pageSet.name === "kind-1-unicode-boundary-t-display-s3"
    );
    const controlEscapes = fixtures.reviewDetailPages.find(
      (pageSet) => pageSet.name === "kind-1-control-escapes-t-display-s3"
    );
    expect(tagged?.display_profile).toBe("ascii-safe-codepoint-fallback-v0");
    expect(tagged?.pages.find((page) => page.title === "Tags")?.lines).toContain("nsealr");
    expect(longTags?.pages.map((page) => page.page_indicator)).toContain("Page 3/4 Lines 28-29/29");
    expect(unicodeBoundary?.pages.find((page) => page.title === "Content")?.lines).toEqual(["abcU+00E8def"]);
    expect(controlEscapes?.pages.find((page) => page.title === "Tags")?.lines).toContain("line\\nbreak");
  });

  it("loads NIP-46 decrypted payload bridge vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46Payloads.map((vector) => vector.name)).toEqual(expect.arrayContaining([
      "connect-policy-review",
      "get-public-key",
      "ping",
      "sign-event-kind-1-basic",
      "sign-event-user-rejected",
      "switch-relays-no-change"
    ]));
    expect(fixtures.nip46Payloads[0].format).toBe("nip46-decrypted-payload-v0");
  });

  it("loads NIP-46 policy-file vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46PolicyFiles.map((policy) => policy.name)).toEqual(["sign-event-kind-1-approved"]);
    expect(fixtures.nip46PolicyFiles[0].format).toBe("nsealr-nip46-policy-v0");
  });

  it("loads NIP-46 connection URI vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46ConnectionUris.map((vector) => vector.name)).toEqual([
      "bunker-remote-signer-token",
      "nostrconnect-client-token"
    ]);
    expect(fixtures.nip46ConnectionUris[0].format).toBe("nsealr-nip46-connection-uri-v0");
    expect(JSON.stringify(fixtures.nip46ConnectionUris[0].expected_descriptor)).not.toContain(
      fixtures.nip46ConnectionUris[0].secret_probe
    );
  });

  it("loads NIP-46 connection token response vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46ConnectionTokenResponses.map((vector) => vector.name)).toEqual([
      "nostrconnect-client-secret-response"
    ]);
    expect(fixtures.nip46ConnectionTokenResponses[0].format).toBe(
      "nsealr-nip46-connection-token-response-vector-v0"
    );
    expect(JSON.stringify(fixtures.nip46ConnectionTokenResponses[0].expected_response)).not.toContain("client-secret");
  });

  it("loads NIP-46 relay event envelope vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46RelayEvents.map((vector) => vector.name)).toEqual([
      "sign-event-request-envelope",
      "sign-event-response-envelope"
    ]);
    expect(fixtures.nip46RelayEvents[0].format).toBe("nsealr-nip46-relay-event-envelope-v0");
    expect(JSON.stringify(fixtures.nip46RelayEvents[0].expected_envelope)).toContain("decrypts_content");
  });

  it("loads NIP-46 relay step vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
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
    const requestStep = fixtures.nip46RelaySteps.find((vector) => vector.name === "ping-request-step");
    const responseStep = fixtures.nip46RelaySteps.find((vector) => vector.name === "sign-event-response-step");
    const authStep = fixtures.nip46RelaySteps.find((vector) => vector.name === "auth-challenge-response-step");
    expect(requestStep?.format).toBe("nsealr-nip46-relay-request-step-v0");
    expect(JSON.stringify(requestStep?.expected_step)).toContain("persists_session_state");
    expect(responseStep?.format).toBe("nsealr-nip46-relay-response-step-v1");
    expect(JSON.stringify(responseStep?.expected_step)).toContain("relay_event_signature_verified");
    const authExpectedStep = authStep?.expected_step as { result_type?: unknown; auth_url?: unknown } | undefined;
    expect(authExpectedStep?.result_type).toBe("auth_challenge");
    expect(authExpectedStep?.auth_url).toBe("https://remote-signer.example.com/auth?challenge=nip46-auth-1");
  });

  it("loads NIP-46 session lifecycle checkpoint vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    expect(fixtures.nip46Sessions.map((vector) => vector.name)).toEqual([
      "nostrconnect-approved-kind-1-checkpoint"
    ]);
    expect(fixtures.nip46Sessions[0].format).toBe("nsealr-nip46-session-lifecycle-vector-v0");
    expect(fixtures.nip46Sessions[0].source_connect_review_vector).toBe("vectors/nip46/connect-policy-review.json");
    expect(fixtures.nip46Sessions[0].session.format).toBe("nsealr-nip46-session-lifecycle-v0");
    expect(fixtures.nip46Sessions[0].session.phase).toBe("approved_pending_ack");
    expect(fixtures.nip46Sessions[0].session.acknowledges_connect).toBe(false);
    expect(fixtures.nip46Sessions[0].session.derives_nip44_key).toBe(false);
    expect(fixtures.nip46Sessions[0].session.persists_session_state).toBe(false);
  });

  it("loads NIP-46 pending-session request gate vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());

    expect(fixtures.nip46SessionGates.map((vector) => vector.name)).toEqual([
      "approved-pending-ack-sign-event-blocked"
    ]);
    expect(fixtures.nip46SessionGates[0].format).toBe("nsealr-nip46-session-request-gate-v0");
    expect(fixtures.nip46SessionGates[0].source_session_vector).toBe(
      "vectors/nip46-sessions/nostrconnect-approved-kind-1-checkpoint.json"
    );
    expect(fixtures.nip46SessionGates[0].expected_gate).toMatchObject({
      blocked_reason: "connect_ack_pending",
      uses_session_permissions: false,
      acknowledges_connect: false,
      dispatches_signer: false,
      persists_session_state: false
    });
  });

  it("loads identity, policy, and grant descriptors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());

    expect(fixtures.accounts.map((account) => account.account_id)).toEqual(expect.arrayContaining([
      "acct-custom-hardware-wallet-slot-0",
      "acct-esp32-qr-nip06-account-0",
      "acct-esp32-usb-slot-0",
      "acct-external-nip46-bunker",
      "acct-raspberry-qr-nip06-account-0",
      "acct-smartcard-slot-0"
    ]));
    expect(fixtures.policyProfiles.map((policy) => policy.policy_id)).toEqual(expect.arrayContaining([
      "policy-manual-only-displayless-smartcard",
      "policy-manual-only-persistent-device",
      "policy-manual-only-qr-vault",
      "policy-scoped-automation-daily-use"
    ]));
    const expectedGrantIds = readdirSync(resolve(resolveSpecsRoot(), "vectors/grants"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => `grant-${file.replace(/\.json$/u, "")}`)
      .sort();
    expect(fixtures.grants.map((grant) => grant.grant_id)).toEqual(expectedGrantIds);
    for (const account of fixtures.accounts) {
      const policy = fixtures.policyProfiles.find((candidate) => candidate.policy_id === account.policy_profile_id);
      expect(policy?.route_types).toContain(account.signer_route.type);
    }
  });

  it("loads policy change review vectors from the specs repository", () => {
    const specsRoot = resolveSpecsRoot();
    const fixtures = loadSpecsFixtures(specsRoot);
    const expectedNames = readdirSync(resolve(specsRoot, "vectors/policy-changes"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => file.replace(/\.json$/u, ""))
      .sort();

    expect(fixtures.policyChanges.map((change) => change.name)).toEqual(expectedNames);
    expect(fixtures.policyChanges[0].format).toBe("nsealr-policy-change-review-v0");
    expect(fixtures.policyChanges[0].proposal.companion_authoritative).toBe(false);
  });

  it("loads policy decision vectors from the specs repository", () => {
    const specsRoot = resolveSpecsRoot();
    const fixtures = loadSpecsFixtures(specsRoot);
    const expectedNames = readdirSync(resolve(specsRoot, "vectors/policy-decisions"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => file.replace(/\.json$/u, ""))
      .sort();

    expect(fixtures.policyDecisions.map((decision) => decision.name)).toEqual(expectedNames);
    expect(fixtures.policyDecisions[0].format).toBe("nsealr-policy-decision-vector-v0");
  });

  it("loads route selection vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());

    expect(fixtures.routeSelections.map((selection) => selection.name)).toEqual([
      "custom-hardware-wallet-sign-event-slot-0",
      "esp32-qr-sign-event-account-0",
      "esp32-usb-sign-event-slot-0",
      "external-nip46-sign-event-bunker",
      "raspberry-qr-sign-event-account-0",
      "smartcard-sign-event-slot-0"
    ]);
    expect(fixtures.routeSelections[0].format).toBe("nsealr-route-selection-vector-v0");
    expect(fixtures.routeSelections[0].selection.contains_secret_material).toBe(false);
  });

  it("loads source public-key proof vectors from the specs repository", () => {
    const specsRoot = resolveSpecsRoot();
    const fixtures = loadSpecsFixtures(specsRoot);
    const expectedNames = readdirSync(resolve(specsRoot, "vectors/source-public-key-proofs"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => file.replace(/\.json$/u, ""))
      .sort();

    expect(fixtures.sourcePublicKeyProofs.map((proof) => proof.name)).toEqual(expectedNames);
    expect(fixtures.sourcePublicKeyProofs.map((proof) => proof.proof_type)).toEqual(["nip06", "nip19_nsec"]);
    for (const proof of fixtures.sourcePublicKeyProofs) {
      expect(() => validateSourcePublicKeyProofFixture(proof.name, proof)).not.toThrow();
      expect(JSON.stringify(proof)).not.toMatch(/mnemonic|secret_key|nsec1/u);
    }
  });

  it("rejects source public-key proof fixtures that carry source secrets", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const proof = structuredClone(fixtures.sourcePublicKeyProofs[0]) as Record<string, unknown>;
    proof.secret_key = "1".repeat(64);

    expect(() => validateSourcePublicKeyProofFixture(String(proof.name), proof)).toThrow(/must not contain source secret/u);
  });

  it("loads access-surface vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());

    expect(fixtures.accessSurfaces.map((surface) => surface.name)).toEqual([
      "browser-provider-local-service-esp32-usb-unavailable"
    ]);
    expect(fixtures.accessSurfaces[0].format).toBe("nsealr-access-surface-vector-v0");
    expect(fixtures.accessSurfaces[0].surface).toBe("browser_provider_nip07");
    expect(fixtures.accessSurfaces[0].safety.stores_production_secrets).toBe(false);
    expect(() => validateAccessSurfaceFixture(fixtures.accessSurfaces[0].name, fixtures.accessSurfaces[0])).not.toThrow();
  });

  it("loads route-refusal contract vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const contract = fixtures.routeRefusals[0];

    expect(fixtures.routeRefusals.map((fixture) => fixture.name)).toEqual(["signer-route-refusals-v0"]);
    expect(contract.format).toBe("nsealr-route-refusal-contract-v0");
    expect(contract.cases.map((routeCase) => routeCase.route_selection_vector).sort()).toEqual(
      fixtures.routeSelections.map((selection) => selection.name).sort()
    );
    expect(contract.cases.find((routeCase) => routeCase.route_type === "smartcard")?.external_review_acknowledgement.mode)
      .toBe("required");
    expect(contract.cases.find((routeCase) => routeCase.route_type === "esp32_usb_nip46")?.external_review_acknowledgement.mode)
      .toBe("unsupported");
    expect(() => validateRouteRefusalContractFixture(contract.name, contract)).not.toThrow();
  });

  it("loads and validates signer feature matrix vectors from the specs repository", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const matrix = fixtures.featureMatrices.find((candidate) => candidate.name === "signer-feature-matrix-v0");

    expect(matrix?.format).toBe("nsealr-signer-feature-matrix-v0");
    expect(Object.keys(matrix?.solutions ?? {}).sort()).toEqual([
      "custom_hardware_wallet",
      "esp32_qr_vault",
      "esp32_usb_nip46",
      "raspberry_qr_vault",
      "smartcard"
    ]);
    expect(matrix?.solutions.raspberry_qr_vault.features.qr_response.target).toBe(
      matrix?.solutions.esp32_qr_vault.features.qr_response.target
    );
    expect(() => validateFeatureMatrixFixture(matrix?.name ?? "missing", matrix)).not.toThrow();
  });

  it("rejects feature matrix shared contract drift in package code", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const matrix = structuredClone(
      fixtures.featureMatrices.find((candidate) => candidate.name === "signer-feature-matrix-v0")
    );
    if (matrix === undefined) throw new Error("missing feature matrix fixture");

    matrix.solutions.esp32_qr_vault.features.nostr_event_review_universal.contract_id = "esp32-special-review";

    expect(() => validateFeatureMatrixFixture(matrix.name, matrix)).toThrow(/shared feature contract drift/u);
  });

  it("loads and validates persistent-secret custody contracts from the specs repository", () => {
    const specsRoot = resolveSpecsRoot();
    const fixtures = loadSpecsFixtures(specsRoot);
    const expectedNames = readdirSync(resolve(specsRoot, "vectors/custody"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => file.replace(/\.json$/u, ""))
      .sort();

    expect(fixtures.custodyContracts.map((contract) => contract.name)).toEqual(expectedNames);
    expect(fixtures.custodyContracts[0].contract_id).toBe("persistent-secret-custody-v0");
    expect(fixtures.custodyContracts[0].repository).toBe("hardware");
    expect(fixtures.custodyContracts[0].requirements.secret_at_rest.plaintext_allowed).toBe(false);
    expect(fixtures.custodyContracts[0].non_claims.join("\n")).toContain("stateless QR vault");
    expect(() =>
      validatePersistentSecretCustodyFixture(fixtures.custodyContracts[0].name, fixtures.custodyContracts[0])
    ).not.toThrow();
  });

  it("rejects persistent-secret custody contract drift in package code", () => {
    const fixtures = loadSpecsFixtures(resolveSpecsRoot());
    const contract = structuredClone(fixtures.custodyContracts[0]) as Record<string, unknown>;
    const requirements = contract.requirements as {
      secret_at_rest: {
        plaintext_allowed: boolean;
      };
    };

    requirements.secret_at_rest.plaintext_allowed = true;

    expect(() => validatePersistentSecretCustodyFixture(String(contract.name), contract)).toThrow(
      /plaintext-at-rest boundary drift/u
    );
  });

  it("loads implementation limits and invalid hardening vectors from the specs repository", () => {
    const specsRoot = resolveSpecsRoot();
    const fixtures = loadSpecsFixtures(specsRoot);
    expect(fixtures.limits.format).toBe("nsealr-implementation-limits-v0");
    expect(fixtures.limits.name).toBe("nsealr-v0");
    expect(fixtures.limits.limits.max_request_id_length).toBe(128);
    const expectedInvalidNames = readdirSync(resolve(specsRoot, "vectors/invalid"))
      .filter((file) => file.endsWith(".json"))
      .map((file) => file.replace(/\.json$/u, ""))
      .sort();
    expect(fixtures.invalidVectors.map((vector) => vector.name)).toEqual(expectedInvalidNames);
  });
});
