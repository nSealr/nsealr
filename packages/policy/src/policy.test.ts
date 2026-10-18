import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  decidePolicyRequest,
  parseAccountDescriptor,
  parseGrantDescriptor,
  parsePolicyChangeProposal,
  parsePolicyChangeReviewVector,
  parsePolicyDecisionRequest,
  parsePolicyProfile,
  parseRouteSelection,
  reviewPolicyChangeProposal,
  parseRouteSelectionRequest,
  selectAccountRoute
} from "./policy.js";

const specsRoot = resolveSpecsRoot();

function resolveSpecsRoot(preferredRoot = resolve("../specs")): string {
  if (existsSync(resolve(preferredRoot, "vectors")) && existsSync(resolve(preferredRoot, "examples"))) {
    return preferredRoot;
  }
  const fallbackRoot = resolve(process.cwd(), "tests/fixtures/specs");
  if (existsSync(resolve(fallbackRoot, "vectors")) && existsSync(resolve(fallbackRoot, "examples"))) {
    return fallbackRoot;
  }
  return preferredRoot;
}

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

function loadPolicyChangeContext(): {
  accounts: unknown[];
  policyProfiles: unknown[];
  grants: unknown[];
} {
  return {
    accounts: readdirSync(resolve(specsRoot, "vectors/accounts"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => loadJson(resolve(specsRoot, "vectors/accounts", name))),
    policyProfiles: readdirSync(resolve(specsRoot, "vectors/policies"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => loadJson(resolve(specsRoot, "vectors/policies", name))),
    grants: readdirSync(resolve(specsRoot, "vectors/grants"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => loadJson(resolve(specsRoot, "vectors/grants", name)))
  };
}

describe("identity, recovery, and policy contracts", () => {
  it("parses shared account, policy, and grant descriptors", () => {
    const account = parseAccountDescriptor(
      loadJson(resolve(specsRoot, "vectors/accounts/raspberry-qr-nip06-account-0.json"))
    );
    const esp32QrAccount = parseAccountDescriptor(
      loadJson(resolve(specsRoot, "vectors/accounts/esp32-qr-nip06-account-0.json"))
    );
    const smartcardAccount = parseAccountDescriptor(
      loadJson(resolve(specsRoot, "vectors/accounts/smartcard-slot-0.json"))
    );
    const customHardwareWalletAccount = parseAccountDescriptor(
      loadJson(resolve(specsRoot, "vectors/accounts/custom-hardware-wallet-slot-0.json"))
    );
    const policy = parsePolicyProfile(loadJson(resolve(specsRoot, "vectors/policies/manual-only-qr-vault.json")));
    const smartcardPolicy = parsePolicyProfile(
      loadJson(resolve(specsRoot, "vectors/policies/manual-only-displayless-smartcard.json"))
    );
    const persistentManualPolicy = parsePolicyProfile(
      loadJson(resolve(specsRoot, "vectors/policies/manual-only-persistent-device.json"))
    );
    const grant = parseGrantDescriptor(loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")));

    expect(account.signer_route.type).toBe("raspberry_qr_vault");
    expect(account.capabilities.persistent_grants).toBe(false);
    expect(account.recovery.source_fingerprint).toBe("cd64b58daca009b9");
    expect(esp32QrAccount.signer_route.type).toBe("esp32_qr_vault");
    expect(esp32QrAccount.capabilities.persistent_grants).toBe(false);
    expect(esp32QrAccount.recovery.source_fingerprint).toBe("cd64b58daca009b9");
    expect(smartcardAccount.recovery.type).toBe("card_slot");
    expect(smartcardAccount.signer_route.trusted_review).toBe("display_less");
    expect(smartcardAccount.capabilities.persistent_grants).toBe(false);
    expect(customHardwareWalletAccount.recovery.type).toBe("hardware_wallet_slot");
    expect(customHardwareWalletAccount.capabilities.persistent_grants).toBe(true);
    expect(policy.mode).toBe("manual_only");
    expect(policy.grants_allowed).toBe(false);
    expect(smartcardPolicy.mode).toBe("manual_only");
    expect(smartcardPolicy.grants_allowed).toBe(false);
    expect(persistentManualPolicy.mode).toBe("manual_only");
    expect(persistentManualPolicy.route_types).toEqual(["esp32_usb_nip46", "custom_hardware_wallet"]);
    expect(customHardwareWalletAccount.policy_profile_id).toBe("policy-manual-only-persistent-device");
    expect(grant.route_type).toBe("esp32_usb_nip46");
    expect(grant.permission).toEqual({ method: "sign_event", parameter: "1", event_kind: 1 });
  });

  it("rejects account descriptors that embed recoverable secret material", () => {
    const account = loadJson(resolve(specsRoot, "vectors/accounts/raspberry-qr-nip06-account-0.json")) as {
      recovery: Record<string, unknown>;
    };
    account.recovery.mnemonic = "leader monkey parrot ring guide accident before fence cannon height naive bean";

    expect(() => parseAccountDescriptor(account)).toThrow(/secret field recovery.mnemonic/u);
  });

  it("rejects unsupported descriptor fields before policy or route use", () => {
    const account = loadJson(resolve(specsRoot, "vectors/accounts/esp32-usb-device-slot-0.json")) as Record<
      string,
      unknown
    >;
    expect(() => parseAccountDescriptor({
      ...account,
      unsigned_metadata: "not allowed"
    })).toThrow(/account descriptor has unsupported field unsigned_metadata/u);

    expect(() => parseAccountDescriptor({
      ...account,
      signer_route: {
        ...(account.signer_route as Record<string, unknown>),
        display_hint: "not allowed"
      }
    })).toThrow(/signer_route has unsupported field display_hint/u);

    expect(() => parseAccountDescriptor({
      ...account,
      capabilities: {
        ...(account.capabilities as Record<string, unknown>),
        autofill_policy: true
      }
    })).toThrow(/capabilities has unsupported field autofill_policy/u);

    expect(() => parseAccountDescriptor({
      ...account,
      policy_profile_id: "manual-only"
    })).toThrow(/policy_profile_id must be a policy-\* stable string id/u);

    const policy = loadJson(resolve(specsRoot, "vectors/policies/scoped-automation-daily-use.json")) as Record<
      string,
      unknown
    >;
    expect(() => parsePolicyProfile({
      ...policy,
      notes: "not allowed"
    })).toThrow(/policy profile has unsupported field notes/u);

    expect(() => parsePolicyProfile({
      ...policy,
      grant_constraints: {
        ...(policy.grant_constraints as Record<string, unknown>),
        companion_override_allowed: false
      }
    })).toThrow(/grant_constraints has unsupported field companion_override_allowed/u);

    const manualPolicy = loadJson(resolve(specsRoot, "vectors/policies/manual-only-persistent-device.json")) as Record<
      string,
      unknown
    >;
    expect(() => parsePolicyProfile({
      ...manualPolicy,
      grant_constraints: {
        expiry_required: true
      }
    })).toThrow(/grant_constraints must be absent/u);

    expect(() => parsePolicyProfile({
      ...policy,
      manual_review_required: [...(policy.manual_review_required as string[]), "auto_like"]
    })).toThrow(/manual_review_required contains unsupported value auto_like/u);

    expect(() => parsePolicyProfile({
      ...policy,
      forbidden_permissions: [...(policy.forbidden_permissions as string[]), "shadow_export"]
    })).toThrow(/forbidden_permissions contains unsupported value shadow_export/u);

    expect(() => parsePolicyProfile({
      ...policy,
      risk_tiers: {
        ...(policy.risk_tiers as Record<string, string>),
        reaction: "low_scoped"
      }
    })).toThrow(/risk_tiers contains unsupported key reaction/u);

    expect(() => parsePolicyProfile({
      ...policy,
      risk_tiers: {
        ...(policy.risk_tiers as Record<string, string>),
        delete: "auto"
      }
    })).toThrow(/risk_tiers.delete uses unsupported tier auto/u);

    const grant = loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")) as Record<string, unknown>;
    expect(() => parseGrantDescriptor({
      ...grant,
      unsigned_metadata: "not allowed"
    })).toThrow(/grant descriptor has unsupported field unsigned_metadata/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      decision: "allow_until_expiry"
    })).toThrow(/grant descriptor has unsupported field decision/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      client: {
        ...(grant.client as Record<string, unknown>),
        origin: "https://example.com"
      }
    })).toThrow(/client has unsupported field origin/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      client: {
        ...(grant.client as Record<string, unknown>),
        label: 123
      }
    })).toThrow(/client.label must be a non-empty string/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      permission: {
        ...(grant.permission as Record<string, unknown>),
        reason: "not allowed"
      }
    })).toThrow(/permission has unsupported field reason/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      rate_limit: {
        ...(grant.rate_limit as Record<string, unknown>),
        burst: 1
      }
    })).toThrow(/rate_limit has unsupported field burst/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      grant_id: "kind-1-session"
    })).toThrow(/grant_id must be a grant-\* stable string id/u);
  });

  it("rejects malformed NIP-06 recovery source fingerprints", () => {
    const account = loadJson(resolve(specsRoot, "vectors/accounts/raspberry-qr-nip06-account-0.json")) as {
      recovery: Record<string, unknown>;
    };
    account.recovery.source_fingerprint = "not-a-fingerprint";

    expect(() => parseAccountDescriptor(account)).toThrow(/source_fingerprint must be 8-byte lowercase hex/u);
  });

  it("rejects QR vault policy automation", () => {
    const policy = loadJson(resolve(specsRoot, "vectors/policies/manual-only-qr-vault.json")) as Record<string, unknown>;
    policy.mode = "scoped_automation";
    policy.grants_allowed = true;

    expect(() => parsePolicyProfile(policy)).toThrow(/QR vault routes must remain manual_only/u);
  });

  it("rejects display-less smartcard policy automation and trusted-review claims", () => {
    const policy = loadJson(resolve(specsRoot, "vectors/policies/manual-only-displayless-smartcard.json")) as Record<
      string,
      unknown
    >;
    policy.mode = "scoped_automation";
    policy.grants_allowed = true;

    expect(() => parsePolicyProfile(policy)).toThrow(/display-less smartcard routes must remain manual_only/u);

    const account = loadJson(resolve(specsRoot, "vectors/accounts/smartcard-slot-0.json")) as {
      signer_route: Record<string, unknown>;
      capabilities: Record<string, unknown>;
    };
    account.signer_route.trusted_review = "device_display";
    account.signer_route.policy_support = "scoped_automation";
    account.capabilities.physical_review = true;
    account.capabilities.persistent_grants = true;

    expect(() => parseAccountDescriptor(account)).toThrow(/smartcard routes must remain display_less/u);
  });

  it("rejects external NIP-46 policy automation", () => {
    const policy = loadJson(resolve(specsRoot, "vectors/policies/external-signer-manual-route.json")) as Record<
      string,
      unknown
    >;
    policy.mode = "scoped_automation";
    policy.grants_allowed = true;
    policy.grant_constraints = {
      expiry_required: true,
      rate_limit_required: true,
      revocation_required: true,
      audit_log_required: true,
      device_confirmation_required: true
    };

    expect(() => parsePolicyProfile(policy)).toThrow(/external NIP-46 routes must remain external-policy manual/u);
  });

  it("rejects external NIP-46 descriptors that claim nSealr persistent grants", () => {
    const account = loadJson(resolve(specsRoot, "vectors/accounts/external-nip46-bunker.json")) as {
      capabilities: Record<string, unknown>;
    };
    account.capabilities.persistent_grants = true;

    expect(() => parseAccountDescriptor(account)).toThrow(/external NIP-46 routes must not claim nSealr persistent grants/u);
  });

  it("rejects wildcard grants and non-persistent policy-route grant targets", () => {
    const grant = loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")) as {
      route_type: string;
      permission: Record<string, unknown>;
    };
    grant.route_type = "esp32_qr_vault";
    grant.permission.method = "*";

    expect(() => parseGrantDescriptor(grant)).toThrow(/nSealr persistent policy route/u);
    expect(() => parseGrantDescriptor({ ...grant, route_type: "esp32_usb_nip46" })).toThrow(/wildcard/u);
    expect(() => parseGrantDescriptor({
      ...grant,
      route_type: "smartcard",
      permission: { method: "sign_event", parameter: "1", event_kind: 1 }
    })).toThrow(/nSealr persistent policy route/u);
    expect(() => parseGrantDescriptor({
      ...grant,
      route_type: "external_nip46",
      permission: { method: "sign_event", parameter: "1", event_kind: 1 }
    })).toThrow(/nSealr persistent policy route/u);
  });

  it("rejects decrypt grants because decrypt operations require manual review", () => {
    const grant = loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")) as {
      permission: Record<string, unknown>;
    };
    grant.permission = { method: "nip44_decrypt" };

    expect(() => parseGrantDescriptor(grant)).toThrow(/decrypt grant permissions require manual review/u);
  });

  it("rejects grant automation outside the v0 kind 1 sign_event menu", () => {
    const grant = loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")) as {
      permission: Record<string, unknown>;
    };

    expect(() => parseGrantDescriptor({
      ...grant,
      permission: { method: "sign_event", parameter: "0", event_kind: 0 }
    })).toThrow(/v0 grants support only sign_event kind 1 automation/u);

    expect(() => parseGrantDescriptor({
      ...grant,
      permission: { method: "get_public_key" }
    })).toThrow(/v0 grants support only sign_event kind 1 automation/u);
  });

  it("matches shared policy decision vectors without a persistent grant store", () => {
    const grant = parseGrantDescriptor(loadJson(resolve(specsRoot, "vectors/grants/esp32-usb-kind-1-session.json")));
    const vectorNames = readdirSync(resolve(specsRoot, "vectors/policy-decisions"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(/\.json$/u, ""))
      .sort();

    expect(vectorNames.length).toBeGreaterThan(0);
    for (const name of vectorNames) {
      const vector = loadJson(resolve(specsRoot, `vectors/policy-decisions/${name}.json`)) as {
        policy_profile_id: string;
        request: Parameters<typeof decidePolicyRequest>[0]["request"];
        decision: ReturnType<typeof decidePolicyRequest>;
      };
      const policyName = vector.policy_profile_id.replace(/^policy-/u, "");
      const policy = parsePolicyProfile(loadJson(resolve(specsRoot, `vectors/policies/${policyName}.json`)));

      expect(decidePolicyRequest({
        policy,
        grants: [grant],
        request: vector.request
      })).toEqual(vector.decision);
    }
  });

  it("parses policy decision requests before evaluation", () => {
    const vector = loadJson(resolve(specsRoot, "vectors/policy-decisions/grant-sign-event-kind-1-rate-limited.json")) as {
      request: unknown;
    };

    expect(parsePolicyDecisionRequest(vector.request)).toMatchObject({
      account_id: "acct-esp32-usb-slot-0",
      route_type: "esp32_usb_nip46",
      grant_usage: {
        "grant-esp32-usb-kind-1-session": {
          window_started_at: 1710000300,
          uses: 5
        }
      }
    });

    expect(() => parsePolicyDecisionRequest({
      ...(vector.request as Record<string, unknown>),
      grant_usage: undefined
    })).toThrow(/grant_usage must be an object/u);

    expect(() => parsePolicyDecisionRequest({
      ...(vector.request as Record<string, unknown>),
      route_type: "raspberry_qr_vault"
    })).toThrow(/persistent or external route/u);

    expect(() => parsePolicyDecisionRequest({
      ...(vector.request as Record<string, unknown>),
      grant_usage: {
        "grant-esp32-usb-kind-1-session": {
          window_started_at: 1710000300,
          uses: -1
        }
      }
    })).toThrow(/uses must be a non-negative integer/u);
  });

  it("matches shared policy change review vectors", () => {
    const context = loadPolicyChangeContext();
    const vectorNames = readdirSync(resolve(specsRoot, "vectors/policy-changes"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => name.replace(/\.json$/u, ""))
      .sort();

    expect(vectorNames.length).toBeGreaterThan(0);
    for (const name of vectorNames) {
      const vector = parsePolicyChangeReviewVector(loadJson(resolve(specsRoot, `vectors/policy-changes/${name}.json`)), context);

      expect(reviewPolicyChangeProposal(vector.proposal, context)).toEqual(vector.review);
    }
  });

  it("rejects policy change proposals that do not match account, policy, and grant context", () => {
    const context = loadPolicyChangeContext();
    const vector = loadJson(resolve(specsRoot, "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json")) as {
      proposal: Record<string, unknown>;
    };

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      account_id: "acct-missing"
    }, context)).toThrow(/account_id target is missing/u);

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      route_type: "custom_hardware_wallet"
    }, context)).toThrow(/account route_type mismatch/u);

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      current_policy_id: "policy-scoped-automation-daily-use"
    }, context)).toThrow(/current_policy_id must match/u);

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      proposed_policy_id: "policy-manual-only-qr-vault"
    }, context)).toThrow(/proposed_policy_id does not include route type/u);

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      proposed_grant_ids: ["grant-custom-hardware-wallet-kind-1-session"]
    }, context)).toThrow(/account mismatch/u);

    expect(() => reviewPolicyChangeProposal({
      ...vector.proposal,
      requested_by: {
        ...(vector.proposal.requested_by as Record<string, unknown>),
        client_pubkey: "5".repeat(64)
      }
    }, context)).toThrow(/client mismatch/u);
  });

  it("rejects policy change proposals that make the companion authoritative", () => {
    const vector = loadJson(resolve(specsRoot, "vectors/policy-changes/esp32-usb-enable-kind-1-automation.json")) as {
      proposal: Record<string, unknown>;
    };

    expect(parsePolicyChangeProposal(vector.proposal)).toMatchObject({
      proposal_id: "proposal-esp32-usb-enable-kind-1-automation",
      companion_authoritative: false
    });

    expect(() => parsePolicyChangeProposal({
      ...vector.proposal,
      companion_authoritative: true
    })).toThrow(/companion_authoritative must be false/u);

    expect(() => parsePolicyChangeProposal({
      ...vector.proposal,
      route_type: "esp32_qr_vault"
    })).toThrow(/device-display persistent route/u);

    expect(() => parsePolicyChangeProposal({
      ...vector.proposal,
      proposal_id: `proposal-${"x".repeat(120)}`
    })).toThrow(/proposal_id must be a proposal-\* stable string id/u);

    expect(() => parsePolicyChangeProposal({
      ...vector.proposal,
      requested_by: {
        ...(vector.proposal.requested_by as Record<string, unknown>),
        label: 123
      }
    })).toThrow(/requested_by.label must be a non-empty string/u);

    expect(() => parsePolicyChangeProposal({
      ...vector.proposal,
      proposed_grant_ids: [
        "grant-esp32-usb-kind-1-session",
        "grant-esp32-usb-kind-1-session"
      ]
    })).toThrow(/proposed_grant_ids must be unique/u);
  });

  it("matches shared route-selection vectors without signer dispatch", () => {
    const accounts = readdirSync(resolve(specsRoot, "vectors/accounts"))
      .filter((name) => name.endsWith(".json"))
      .map((name) => parseAccountDescriptor(loadJson(resolve(specsRoot, "vectors/accounts", name))));
    const vectorNames = readdirSync(resolve(specsRoot, "vectors/route-selections"))
      .filter((name) => name.endsWith(".json"))
      .sort();

    expect(vectorNames.length).toBeGreaterThan(0);
    for (const name of vectorNames) {
      const vector = loadJson(resolve(specsRoot, "vectors/route-selections", name)) as {
        request: Parameters<typeof selectAccountRoute>[1];
        selection: ReturnType<typeof selectAccountRoute>;
      };

      expect(selectAccountRoute(accounts, vector.request)).toEqual(vector.selection);
      expect(parseRouteSelection(vector.selection)).toEqual(vector.selection);
    }
  });

  it("rejects ambiguous or unsupported route selections before signer IO", () => {
    const account = parseAccountDescriptor(loadJson(resolve(specsRoot, "vectors/accounts/raspberry-qr-nip06-account-0.json")));
    const routeSelection = selectAccountRoute([account], {
      account_id: account.account_id,
      method: "sign_event"
    });

    expect(parseRouteSelectionRequest({
      account_id: account.account_id,
      method: "sign_event",
      route_type: "raspberry_qr_vault"
    })).toEqual({
      account_id: account.account_id,
      method: "sign_event",
      route_type: "raspberry_qr_vault"
    });
    expect(() => parseRouteSelectionRequest({
      account_id: account.account_id,
      method: "sign_event",
      route_type: "esp32_usb_nip46",
      secret_key: "1".repeat(64)
    })).toThrow(/unsupported field/u);

    expect(() => selectAccountRoute([account], undefined as never)).toThrow(/request must be an object/u);
    expect(() => selectAccountRoute([], {
      account_id: account.account_id,
      method: "sign_event"
    })).toThrow(/account_id is unknown/u);
    expect(() => selectAccountRoute([account, account], {
      account_id: account.account_id,
      method: "sign_event"
    })).toThrow(/account_id is ambiguous/u);
    expect(() => selectAccountRoute([account], {
      account_id: account.account_id,
      method: "get_public_key"
    })).toThrow(/method is unsupported/u);
    expect(() => selectAccountRoute([account], {
      account_id: account.account_id,
      method: "sign_event",
      route_type: "esp32_usb_nip46"
    })).toThrow(/route_type does not match/u);

    expect(() => parseRouteSelection({
      ...routeSelection,
      repository: "firmware"
    })).toThrow(/repository does not match/u);
    expect(() => parseRouteSelection({
      ...routeSelection,
      contains_secret_material: true
    })).toThrow(/contains_secret_material/u);
    expect(() => parseRouteSelection({
      ...routeSelection,
      mnemonic: "leader monkey parrot ring guide accident before fence cannon height naive bean"
    })).toThrow(/secret field mnemonic/u);
  });
});
