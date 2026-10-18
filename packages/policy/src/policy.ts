import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, utf8ToBytes } from "@noble/hashes/utils.js";

export type RouteType =
  | "raspberry_qr_vault"
  | "esp32_qr_vault"
  | "esp32_usb_nip46"
  | "smartcard"
  | "custom_hardware_wallet"
  | "external_nip46";

export type RouteCustody =
  | "stateless_session"
  | "device_persistent"
  | "card_persistent"
  | "custom_hardware_persistent"
  | "external_signer";

export type SignerRoute = {
  type: RouteType;
  repository?: "raspberry" | "firmware" | "smartcard" | "hardware";
  transport: "qr" | "usb" | "smartcard" | "nfc" | "nip46_relay" | "embedded";
  custody: RouteCustody;
  trusted_review: "device_display" | "external_review" | "external_policy" | "display_less";
  policy_support: "manual_only" | "scoped_automation" | "external";
};

export type AccountDescriptor = {
  format: "nsealr-account-descriptor-v0";
  account_id: string;
  label: string;
  public_key: string;
  signer_route: SignerRoute;
  recovery: Record<string, unknown>;
  capabilities: {
    methods: string[];
    physical_review: boolean;
    physical_approval: boolean;
    persistent_grants: boolean;
  };
  policy_profile_id: string;
};

export type PolicyProfile = {
  format: "nsealr-policy-profile-v0";
  policy_id: string;
  label: string;
  route_types: RouteType[];
  mode: "manual_only" | "scoped_automation";
  grants_allowed: boolean;
  manual_review_required: string[];
  forbidden_permissions: string[];
  grant_constraints?: Record<string, unknown>;
  risk_tiers: Record<string, string>;
};

export type GrantPermission = {
  method: string;
  parameter?: string;
  event_kind?: number;
};

export type GrantDescriptor = {
  format: "nsealr-grant-descriptor-v0";
  grant_id: string;
  account_id: string;
  route_type: RouteType;
  client: {
    pubkey: string;
    label?: string;
  };
  permission: GrantPermission;
  expires_at: number;
  rate_limit: {
    max_uses: number;
    window_seconds: number;
  };
  requires_device_policy_confirmation: true;
  revocable: true;
  audit_event_format: "nsealr-grant-audit-event-v0";
};

export type GrantUsageSnapshot = {
  window_started_at: number;
  uses: number;
};

export type PolicyDecisionRequest = {
  account_id: string;
  route_type: RouteType;
  client_pubkey: string;
  permission: GrantPermission;
  now: number;
  grant_ids: string[];
  grant_usage: Record<string, GrantUsageSnapshot>;
  revoked_grant_ids: string[];
};

export type PolicyDecision = {
  format: "nsealr-policy-decision-v0";
  decision: "allow" | "deny" | "manual_review";
  reason:
    | "decrypt_requires_manual_review"
    | "forbidden_permission"
    | "grant_expired"
    | "grant_rate_limited"
    | "grant_revoked"
    | "grant_valid"
    | "no_matching_grant"
    | "policy_manual_only"
    | "policy_route_mismatch"
    | "unknown_method_requires_manual_review";
  grant_id?: string;
  audit_event: {
    format: "nsealr-grant-audit-event-v0";
    occurred_at: number;
    account_id: string;
    route_type: RouteType;
    client_pubkey: string;
    permission: GrantPermission;
    decision: PolicyDecision["decision"];
    reason: PolicyDecision["reason"];
    grant_id?: string;
  };
};

export type PolicyChangeProposal = {
  format: "nsealr-policy-change-proposal-v0";
  proposal_id: string;
  account_id: string;
  route_type: "esp32_usb_nip46" | "custom_hardware_wallet";
  action: "set_policy";
  current_policy_id: string;
  proposed_policy_id: string;
  proposed_grant_ids: string[];
  requested_by: {
    surface: "browser_extension" | "desktop_app" | "cli" | "sdk" | "native_host_test";
    client_pubkey: string;
    label?: string;
  };
  created_at: number;
  device_review_required: true;
  physical_approval_required: true;
  companion_authoritative: false;
  contains_secret_material: false;
};

export type PolicyChangeReviewPage = {
  title: string;
  lines: string[];
  action: "next" | "approve_or_reject";
};

export type PolicyChangeReview = {
  format: "nsealr-policy-change-review-pages-v0";
  proposal_id: string;
  approval_digest: string;
  pages: PolicyChangeReviewPage[];
};

export type PolicyChangeReviewVector = {
  name: string;
  format: "nsealr-policy-change-review-v0";
  proposal: PolicyChangeProposal;
  review: PolicyChangeReview;
};

export type PolicyChangeReviewContext = {
  accounts: AccountDescriptor[];
  policyProfiles: PolicyProfile[];
  grants: GrantDescriptor[];
};

export type RouteSelectionRequest = {
  account_id: string;
  method: string;
  route_type?: RouteType;
};

export type RouteSelection = {
  format: "nsealr-route-selection-v0";
  account_id: string;
  public_key: string;
  route_type: RouteType;
  repository?: SignerRoute["repository"];
  transport: SignerRoute["transport"];
  custody: SignerRoute["custody"];
  trusted_review: SignerRoute["trusted_review"];
  policy_support: SignerRoute["policy_support"];
  policy_profile_id: string;
  physical_review: boolean;
  physical_approval: boolean;
  persistent_grants: boolean;
  contains_secret_material: false;
};

const ROUTE_TYPES = new Set<RouteType>([
  "raspberry_qr_vault",
  "esp32_qr_vault",
  "esp32_usb_nip46",
  "smartcard",
  "custom_hardware_wallet",
  "external_nip46"
]);
const QR_ROUTE_TYPES = new Set<RouteType>(["raspberry_qr_vault", "esp32_qr_vault"]);
const ROUTE_REPOSITORIES = new Map<RouteType, string>([
  ["raspberry_qr_vault", "raspberry"],
  ["esp32_qr_vault", "firmware"],
  ["esp32_usb_nip46", "firmware"],
  ["smartcard", "smartcard"],
  ["custom_hardware_wallet", "hardware"]
]);
const ROUTE_TRANSPORTS = new Set(["qr", "usb", "smartcard", "nfc", "nip46_relay", "embedded"]);
const CUSTODY_MODES = new Set([
  "stateless_session",
  "device_persistent",
  "card_persistent",
  "custom_hardware_persistent",
  "external_signer"
]);
const REVIEW_MODES = new Set(["device_display", "external_review", "external_policy", "display_less"]);
const POLICY_SUPPORT_MODES = new Set(["manual_only", "scoped_automation", "external"]);
const POLICY_REVIEW_REQUIREMENTS = new Set([
  "connect",
  "delete_event",
  "nip04_decrypt",
  "nip44_decrypt",
  "policy_change",
  "sign_event",
  "switch_relays",
  "unknown_method"
]);
const POLICY_FORBIDDEN_PERMISSIONS = new Set([
  "companion_authoritative_policy_change",
  "decrypt_without_review",
  "export_secret",
  "local_private_key_storage",
  "trusted_review_claim",
  "wildcard"
]);
const POLICY_RISK_NAMES = new Set(["decrypt", "delete", "kind:1", "policy_change", "profile", "sign_event", "unknown"]);
const POLICY_RISK_TIERS = new Set(["device_review", "external_policy", "external_review", "low_scoped", "manual"]);
const DEVICE_METHODS = new Set(["get_capabilities", "get_signing_status", "get_public_key", "sign_event"]);
const DECRYPT_METHODS = new Set(["nip04_decrypt", "nip44_decrypt"]);
const POLICY_DECISION_ROUTE_TYPES = new Set<RouteType>([
  "esp32_usb_nip46",
  "smartcard",
  "custom_hardware_wallet",
  "external_nip46"
]);
const POLICY_CHANGE_ROUTE_TYPES = new Set<RouteType>(["esp32_usb_nip46", "custom_hardware_wallet"]);
const GRANT_ROUTE_TYPES = new Set<RouteType>(["esp32_usb_nip46", "custom_hardware_wallet"]);
const GRANT_AUTOMATION_EVENT_KINDS = new Set([1]);
const POLICY_CHANGE_SURFACES = new Set(["browser_extension", "desktop_app", "cli", "sdk", "native_host_test"]);
const SECRET_FIELD_NAMES = new Set([
  "secret_key",
  "private_key",
  "nsec",
  "mnemonic",
  "seed",
  "passphrase",
  "nip49_ciphertext"
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertRecord(value: unknown, label: string): asserts value is Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${label} must be an object`);
}

function assertOnlyKeys(value: Record<string, unknown>, allowedKeys: string[], label: string): void {
  for (const key of Object.keys(value)) {
    if (!allowedKeys.includes(key)) throw new Error(`${label} has unsupported field ${key}`);
  }
}

function secretFieldPaths(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => secretFieldPaths(item, prefix ? `${prefix}[${index}]` : `[${index}]`));
  }
  if (!isRecord(value)) return [];
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    const nested = secretFieldPaths(child, path);
    return SECRET_FIELD_NAMES.has(key.toLowerCase()) ? [path, ...nested] : nested;
  });
}

function rejectSecretFields(value: unknown): void {
  const secretPath = secretFieldPaths(value)[0];
  if (secretPath !== undefined) throw new Error(`descriptor must not contain secret field ${secretPath}`);
}

function requireStringId(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/u.test(value)) {
    throw new Error(`${field} must be a stable string id`);
  }
  return value;
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${field} must be a non-empty string`);
  return value;
}

function requireXOnlyPubkey(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${field} must be 32-byte lowercase hex`);
  }
  return value;
}

function requireSourceFingerprint(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^[0-9a-f]{16}$/u.test(value)) {
    throw new Error(`${field} must be 8-byte lowercase hex`);
  }
  return value;
}

function requireGrantId(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^grant-[A-Za-z0-9._:-]{1,122}$/u.test(value)) {
    throw new Error(`${field} must be a grant-* stable string id`);
  }
  return value;
}

function requireBoolean(value: unknown, field: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${field} must be boolean`);
  return value;
}

function requirePositiveInteger(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`${field} must be a positive integer`);
  }
  return value;
}

function requireNonNegativeInteger(value: unknown, field: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${field} must be a non-negative integer`);
  }
  return value;
}

function requireRouteType(value: unknown, field = "route_type"): RouteType {
  if (typeof value !== "string" || !ROUTE_TYPES.has(value as RouteType)) {
    throw new Error(`${field} is unknown`);
  }
  return value as RouteType;
}

function requireStringArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string" && item.length > 0)) {
    throw new Error(`${field} must be an array of strings`);
  }
  return value;
}

function requireGrantIdArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value)) throw new Error(`${field} must be an array of grant ids`);
  const grantIds = value.map((item, index) => requireGrantId(item, `${field}[${index}]`));
  if (new Set(grantIds).size !== grantIds.length) throw new Error(`${field} must be unique`);
  return grantIds;
}

function requirePolicyId(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^policy-[A-Za-z0-9._:-]{1,121}$/u.test(value)) {
    throw new Error(`${field} must be a policy-* stable string id`);
  }
  return value;
}

function requireProposalId(value: unknown, field: string): string {
  if (typeof value !== "string" || !/^proposal-[A-Za-z0-9._:-]{1,119}$/u.test(value)) {
    throw new Error(`${field} must be a proposal-* stable string id`);
  }
  return value;
}

function parseSignerRoute(value: unknown): SignerRoute {
  assertRecord(value, "signer_route");
  assertOnlyKeys(value, ["type", "repository", "transport", "custody", "trusted_review", "policy_support"], "signer_route");
  const type = requireRouteType(value.type, "signer_route.type");
  const expectedRepository = ROUTE_REPOSITORIES.get(type);
  if (expectedRepository !== undefined && value.repository !== expectedRepository) {
    throw new Error(`signer_route.repository must be ${expectedRepository}`);
  }
  if (expectedRepository === undefined && "repository" in value) {
    throw new Error("external signer routes must not claim a nSealr repository");
  }
  const transport = requireString(value.transport, "signer_route.transport");
  if (!ROUTE_TRANSPORTS.has(transport)) throw new Error("signer_route.transport is unknown");
  const custody = requireString(value.custody, "signer_route.custody");
  if (!CUSTODY_MODES.has(custody)) throw new Error("signer_route.custody is unknown");
  const trustedReview = requireString(value.trusted_review, "signer_route.trusted_review");
  if (!REVIEW_MODES.has(trustedReview)) throw new Error("signer_route.trusted_review is unknown");
  const policySupport = requireString(value.policy_support, "signer_route.policy_support");
  if (!POLICY_SUPPORT_MODES.has(policySupport)) throw new Error("signer_route.policy_support is unknown");
  return {
    type,
    ...(typeof value.repository === "string" ? { repository: value.repository as SignerRoute["repository"] } : {}),
    transport: transport as SignerRoute["transport"],
    custody: custody as SignerRoute["custody"],
    trusted_review: trustedReview as SignerRoute["trusted_review"],
    policy_support: policySupport as SignerRoute["policy_support"]
  };
}

function validateRecovery(recovery: unknown): Record<string, unknown> {
  assertRecord(recovery, "recovery");
  if (recovery.type === "nip06") {
    assertOnlyKeys(recovery, ["type", "path", "account", "source_vector", "source_fingerprint"], "NIP-06 recovery");
    if (typeof recovery.path !== "string" || !recovery.path.startsWith("m/44'/1237'/")) {
      throw new Error("NIP-06 recovery path must use the Nostr derivation prefix");
    }
    if (typeof recovery.account !== "number" || !Number.isInteger(recovery.account) || recovery.account < 0) {
      throw new Error("NIP-06 recovery account must be a non-negative integer");
    }
    requireString(recovery.source_vector, "NIP-06 recovery source_vector");
    requireSourceFingerprint(recovery.source_fingerprint, "NIP-06 recovery source_fingerprint");
    return recovery;
  }
  if (recovery.type === "device_slot") {
    assertOnlyKeys(recovery, ["type", "slot_id", "backup_required"], "device_slot recovery");
    requireString(recovery.slot_id, "device_slot recovery slot_id");
    requireBoolean(recovery.backup_required, "device_slot recovery backup_required");
    return recovery;
  }
  if (recovery.type === "card_slot") {
    assertOnlyKeys(recovery, ["type", "card_id", "slot_id", "backup_required"], "card_slot recovery");
    requireString(recovery.card_id, "card_slot recovery card_id");
    requireString(recovery.slot_id, "card_slot recovery slot_id");
    requireBoolean(recovery.backup_required, "card_slot recovery backup_required");
    return recovery;
  }
  if (recovery.type === "hardware_wallet_slot") {
    assertOnlyKeys(recovery, ["type", "device_id", "slot_id", "backup_required"], "hardware_wallet_slot recovery");
    requireString(recovery.device_id, "hardware_wallet_slot recovery device_id");
    requireString(recovery.slot_id, "hardware_wallet_slot recovery slot_id");
    requireBoolean(recovery.backup_required, "hardware_wallet_slot recovery backup_required");
    return recovery;
  }
  if (recovery.type === "external_signer") {
    assertOnlyKeys(recovery, ["type", "external_signer_id"], "external_signer recovery");
    requireString(recovery.external_signer_id, "external_signer recovery external_signer_id");
    return recovery;
  }
  throw new Error("recovery.type is unknown");
}

function validateRouteSemantics(
  route: SignerRoute,
  capabilities: AccountDescriptor["capabilities"],
  source: unknown
): void {
  if (QR_ROUTE_TYPES.has(route.type)) {
    const serialized = JSON.stringify(source) ?? "";
    if (serialized.toLowerCase().includes("tropic01")) {
      throw new Error("stateless QR vault descriptors must not reference TROPIC01");
    }
    if (route.transport !== "qr") throw new Error("stateless QR vault routes must use qr transport");
    if (route.custody !== "stateless_session") {
      throw new Error("stateless QR vault routes must use stateless_session custody");
    }
    if (route.policy_support !== "manual_only") {
      throw new Error("stateless QR vault routes must use manual_only policy support");
    }
    if (capabilities.persistent_grants !== false) {
      throw new Error("stateless QR vault routes must not support persistent grants");
    }
    return;
  }

  if (route.type === "esp32_usb_nip46") {
    if (route.transport !== "usb") throw new Error("ESP32 USB/NIP-46 routes must use usb transport");
    if (route.custody !== "device_persistent") {
      throw new Error("ESP32 USB/NIP-46 routes must use device_persistent custody");
    }
    if (route.trusted_review !== "device_display") throw new Error("ESP32 USB/NIP-46 routes must use device_display review");
    if (route.policy_support !== "scoped_automation") {
      throw new Error("ESP32 USB/NIP-46 routes must use scoped_automation policy support");
    }
    if (!capabilities.physical_review || !capabilities.physical_approval) {
      throw new Error("ESP32 USB/NIP-46 routes require physical review and approval");
    }
    if (!capabilities.persistent_grants) throw new Error("ESP32 USB/NIP-46 routes require persistent grant support");
    return;
  }

  if (route.type === "smartcard") {
    if (route.transport !== "smartcard") throw new Error("smartcard routes must use smartcard transport");
    if (route.custody !== "card_persistent") throw new Error("smartcard routes must use card_persistent custody");
    if (route.trusted_review !== "display_less") throw new Error("smartcard routes must remain display_less");
    if (route.policy_support !== "manual_only") {
      throw new Error("display-less smartcard routes must use manual_only policy support");
    }
    if (capabilities.physical_review || capabilities.physical_approval) {
      throw new Error("display-less smartcard routes must not claim physical review or approval");
    }
    if (capabilities.persistent_grants) throw new Error("display-less smartcard routes must not support persistent grants");
    return;
  }

  if (route.type === "custom_hardware_wallet") {
    if (route.transport !== "usb") throw new Error("custom hardware-wallet routes must use usb transport in v0");
    if (route.custody !== "custom_hardware_persistent") {
      throw new Error("custom hardware-wallet routes must use custom_hardware_persistent custody");
    }
    if (route.trusted_review !== "device_display") throw new Error("custom hardware-wallet routes must use device_display review");
    if (route.policy_support !== "scoped_automation") {
      throw new Error("custom hardware-wallet routes must use scoped_automation policy support");
    }
    if (!capabilities.physical_review || !capabilities.physical_approval) {
      throw new Error("custom hardware-wallet routes require physical review and approval");
    }
    if (!capabilities.persistent_grants) throw new Error("custom hardware-wallet routes require persistent grant support");
    return;
  }

  if (route.type === "external_nip46") {
    if (route.transport !== "nip46_relay") throw new Error("external NIP-46 routes must use nip46_relay transport");
    if (route.custody !== "external_signer") throw new Error("external NIP-46 routes must use external_signer custody");
    if (route.trusted_review !== "external_policy") throw new Error("external NIP-46 routes must use external_policy review");
    if (route.policy_support !== "external") throw new Error("external NIP-46 routes must use external policy support");
    if (capabilities.physical_review || capabilities.physical_approval) {
      throw new Error("external NIP-46 routes must not claim nSealr physical review or approval");
    }
    if (capabilities.persistent_grants) {
      throw new Error("external NIP-46 routes must not claim nSealr persistent grants");
    }
  }
}

export function parseAccountDescriptor(value: unknown): AccountDescriptor {
  rejectSecretFields(value);
  assertRecord(value, "account descriptor");
  assertOnlyKeys(value, [
    "format",
    "account_id",
    "label",
    "public_key",
    "signer_route",
    "recovery",
    "capabilities",
    "policy_profile_id"
  ], "account descriptor");
  if (value.format !== "nsealr-account-descriptor-v0") throw new Error("account descriptor format mismatch");
  const route = parseSignerRoute(value.signer_route);
  assertRecord(value.capabilities, "capabilities");
  assertOnlyKeys(
    value.capabilities,
    ["methods", "physical_review", "physical_approval", "persistent_grants"],
    "capabilities"
  );
  const methods = requireStringArray(value.capabilities.methods, "capabilities.methods");
  const unknownMethod = methods.find((method) => !DEVICE_METHODS.has(method));
  if (unknownMethod !== undefined) throw new Error(`capabilities.methods contains unknown method ${unknownMethod}`);
  const descriptor: AccountDescriptor = {
    format: "nsealr-account-descriptor-v0",
    account_id: requireStringId(value.account_id, "account_id"),
    label: requireString(value.label, "label"),
    public_key: requireXOnlyPubkey(value.public_key, "public_key"),
    signer_route: route,
    recovery: validateRecovery(value.recovery),
    capabilities: {
      methods,
      physical_review: requireBoolean(value.capabilities.physical_review, "capabilities.physical_review"),
      physical_approval: requireBoolean(value.capabilities.physical_approval, "capabilities.physical_approval"),
      persistent_grants: requireBoolean(value.capabilities.persistent_grants, "capabilities.persistent_grants")
    },
    policy_profile_id: requirePolicyId(value.policy_profile_id, "policy_profile_id")
  };
  validateRouteSemantics(route, descriptor.capabilities, value);
  return descriptor;
}

export function parsePolicyProfile(value: unknown): PolicyProfile {
  rejectSecretFields(value);
  assertRecord(value, "policy profile");
  assertOnlyKeys(value, [
    "format",
    "policy_id",
    "label",
    "route_types",
    "mode",
    "grants_allowed",
    "manual_review_required",
    "forbidden_permissions",
    "grant_constraints",
    "risk_tiers"
  ], "policy profile");
  if (value.format !== "nsealr-policy-profile-v0") throw new Error("policy profile format mismatch");
  const routeTypes = requireStringArray(value.route_types, "route_types").map((route) => requireRouteType(route));
  const mode = requireString(value.mode, "mode");
  if (mode !== "manual_only" && mode !== "scoped_automation") throw new Error("mode is unknown");
  const grantsAllowed = requireBoolean(value.grants_allowed, "grants_allowed");
  const manualReviewRequired = requireStringArray(value.manual_review_required, "manual_review_required");
  for (const requirement of manualReviewRequired) {
    if (!POLICY_REVIEW_REQUIREMENTS.has(requirement)) {
      throw new Error(`manual_review_required contains unsupported value ${requirement}`);
    }
  }
  const forbiddenPermissions = requireStringArray(value.forbidden_permissions, "forbidden_permissions");
  for (const permission of forbiddenPermissions) {
    if (!POLICY_FORBIDDEN_PERMISSIONS.has(permission)) {
      throw new Error(`forbidden_permissions contains unsupported value ${permission}`);
    }
  }
  if (!forbiddenPermissions.includes("wildcard")) throw new Error("forbidden_permissions must include wildcard");
  if (!forbiddenPermissions.includes("export_secret")) throw new Error("forbidden_permissions must include export_secret");
  if (routeTypes.some((route) => QR_ROUTE_TYPES.has(route)) && (mode !== "manual_only" || grantsAllowed !== false)) {
    throw new Error("QR vault routes must remain manual_only with grants_allowed false");
  }
  if (routeTypes.includes("smartcard") && (mode !== "manual_only" || grantsAllowed !== false)) {
    throw new Error("display-less smartcard routes must remain manual_only with grants_allowed false");
  }
  if (routeTypes.includes("external_nip46") && (mode !== "manual_only" || grantsAllowed !== false)) {
    throw new Error("external NIP-46 routes must remain external-policy manual without nSealr grants");
  }
  if (mode === "manual_only" && grantsAllowed) throw new Error("manual_only profiles must not allow grants");
  if (grantsAllowed) {
    assertRecord(value.grant_constraints, "grant_constraints");
    assertOnlyKeys(value.grant_constraints, [
      "expiry_required",
      "rate_limit_required",
      "revocation_required",
      "audit_log_required",
      "device_confirmation_required"
    ], "grant_constraints");
    for (const field of [
      "expiry_required",
      "rate_limit_required",
      "revocation_required",
      "audit_log_required",
      "device_confirmation_required"
    ]) {
      if (value.grant_constraints[field] !== true) throw new Error(`grant_constraints.${field} must be true`);
    }
  } else if (value.grant_constraints !== undefined) {
    throw new Error("grant_constraints must be absent when grants are not allowed");
  }
  assertRecord(value.risk_tiers, "risk_tiers");
  for (const [riskName, riskTier] of Object.entries(value.risk_tiers)) {
    if (!POLICY_RISK_NAMES.has(riskName)) throw new Error(`risk_tiers contains unsupported key ${riskName}`);
    if (typeof riskTier !== "string" || !POLICY_RISK_TIERS.has(riskTier)) {
      throw new Error(`risk_tiers.${riskName} uses unsupported tier ${String(riskTier)}`);
    }
  }
  const policyId = requirePolicyId(value.policy_id, "policy_id");
  return {
    format: "nsealr-policy-profile-v0",
    policy_id: policyId,
    label: requireString(value.label, "label"),
    route_types: routeTypes,
    mode,
    grants_allowed: grantsAllowed,
    manual_review_required: manualReviewRequired,
    forbidden_permissions: forbiddenPermissions,
    ...(value.grant_constraints !== undefined ? { grant_constraints: value.grant_constraints as Record<string, unknown> } : {}),
    risk_tiers: value.risk_tiers as Record<string, string>
  };
}

function parseGrantPermission(value: unknown): GrantPermission {
  assertRecord(value, "permission");
  assertOnlyKeys(value, ["method", "parameter", "event_kind"], "permission");
  if (value.method === "*" || value.parameter === "*") throw new Error("grant permission must not use wildcard values");
  const method = requireString(value.method, "permission.method");
  if (method === "export_secret") throw new Error("grant permission must not request secret export");
  if (DECRYPT_METHODS.has(method)) throw new Error("decrypt grant permissions require manual review");
  if (method !== "sign_event") throw new Error("v0 grants support only sign_event kind 1 automation");
  if (method === "sign_event") {
    if (typeof value.parameter !== "string" || !/^[0-9]+$/u.test(value.parameter)) {
      throw new Error("sign_event permission.parameter must be a decimal event kind");
    }
    if (typeof value.event_kind !== "number" || !Number.isInteger(value.event_kind) || value.event_kind < 0) {
      throw new Error("sign_event permission.event_kind must be a non-negative integer");
    }
    if (Number(value.parameter) !== value.event_kind) {
      throw new Error("sign_event permission parameter/event_kind mismatch");
    }
    if (value.parameter !== "1" || !GRANT_AUTOMATION_EVENT_KINDS.has(value.event_kind)) {
      throw new Error("v0 grants support only sign_event kind 1 automation");
    }
    return { method, parameter: value.parameter, event_kind: value.event_kind };
  }
  throw new Error("v0 grants support only sign_event kind 1 automation");
}

function parsePolicyDecisionPermission(value: unknown): GrantPermission {
  assertRecord(value, "permission");
  assertOnlyKeys(value, ["method", "parameter", "event_kind"], "permission");
  if (value.method === "*" || value.parameter === "*") throw new Error("permission must not use wildcard values");
  const method = requireString(value.method, "permission.method");
  if (method === "sign_event") {
    if (typeof value.parameter !== "string" || !/^[0-9]+$/u.test(value.parameter)) {
      throw new Error("sign_event permission.parameter must be a decimal event kind");
    }
    if (typeof value.event_kind !== "number" || !Number.isInteger(value.event_kind) || value.event_kind < 0) {
      throw new Error("sign_event permission.event_kind must be a non-negative integer");
    }
    if (Number(value.parameter) !== value.event_kind) {
      throw new Error("sign_event permission parameter/event_kind mismatch");
    }
    return { method, parameter: value.parameter, event_kind: value.event_kind };
  }
  if ("parameter" in value || "event_kind" in value) {
    throw new Error("non-sign_event permissions must not include parameters");
  }
  return { method };
}

export function parseGrantDescriptor(value: unknown): GrantDescriptor {
  rejectSecretFields(value);
  assertRecord(value, "grant descriptor");
  assertOnlyKeys(value, [
    "format",
    "grant_id",
    "account_id",
    "route_type",
    "client",
    "permission",
    "expires_at",
    "rate_limit",
    "requires_device_policy_confirmation",
    "revocable",
    "audit_event_format"
  ], "grant descriptor");
  if (value.format !== "nsealr-grant-descriptor-v0") throw new Error("grant descriptor format mismatch");
  const routeType = requireRouteType(value.route_type);
  if (!GRANT_ROUTE_TYPES.has(routeType)) throw new Error("grant route_type must be a nSealr persistent policy route");
  assertRecord(value.client, "client");
  assertOnlyKeys(value.client, ["pubkey", "label"], "client");
  assertRecord(value.rate_limit, "rate_limit");
  assertOnlyKeys(value.rate_limit, ["max_uses", "window_seconds"], "rate_limit");
  if (value.requires_device_policy_confirmation !== true) {
    throw new Error("requires_device_policy_confirmation must be true");
  }
  if (value.revocable !== true) throw new Error("revocable must be true");
  if (value.audit_event_format !== "nsealr-grant-audit-event-v0") throw new Error("audit_event_format mismatch");
  return {
    format: "nsealr-grant-descriptor-v0",
    grant_id: requireGrantId(value.grant_id, "grant_id"),
    account_id: requireStringId(value.account_id, "account_id"),
    route_type: routeType,
    client: {
      pubkey: requireXOnlyPubkey(value.client.pubkey, "client.pubkey"),
      ...("label" in value.client ? { label: requireString(value.client.label, "client.label") } : {})
    },
    permission: parseGrantPermission(value.permission),
    expires_at: requirePositiveInteger(value.expires_at, "expires_at"),
    rate_limit: {
      max_uses: requirePositiveInteger(value.rate_limit.max_uses, "rate_limit.max_uses"),
      window_seconds: requirePositiveInteger(value.rate_limit.window_seconds, "rate_limit.window_seconds")
    },
    requires_device_policy_confirmation: true,
    revocable: true,
    audit_event_format: "nsealr-grant-audit-event-v0"
  };
}

function parseGrantUsageSnapshots(value: unknown): Record<string, GrantUsageSnapshot> {
  assertRecord(value, "grant_usage");
  const snapshots: Record<string, GrantUsageSnapshot> = {};
  for (const [grantId, usage] of Object.entries(value)) {
    requireGrantId(grantId, "grant_usage key");
    assertRecord(usage, `grant_usage.${grantId}`);
    assertOnlyKeys(usage, ["window_started_at", "uses"], `grant_usage.${grantId}`);
    snapshots[grantId] = {
      window_started_at: requirePositiveInteger(usage.window_started_at, `grant_usage.${grantId}.window_started_at`),
      uses: requireNonNegativeInteger(usage.uses, `grant_usage.${grantId}.uses`)
    };
  }
  return snapshots;
}

export function parsePolicyDecisionRequest(value: unknown): PolicyDecisionRequest {
  rejectSecretFields(value);
  assertRecord(value, "policy decision request");
  assertOnlyKeys(value, [
    "account_id",
    "route_type",
    "client_pubkey",
    "permission",
    "now",
    "grant_ids",
    "grant_usage",
    "revoked_grant_ids"
  ], "policy decision request");
  const routeType = requireRouteType(value.route_type);
  if (!POLICY_DECISION_ROUTE_TYPES.has(routeType)) {
    throw new Error("policy decision route_type must be a persistent or external route");
  }
  return {
    account_id: requireStringId(value.account_id, "account_id"),
    route_type: routeType,
    client_pubkey: requireXOnlyPubkey(value.client_pubkey, "client_pubkey"),
    permission: parsePolicyDecisionPermission(value.permission),
    now: requirePositiveInteger(value.now, "now"),
    grant_ids: requireGrantIdArray(value.grant_ids, "grant_ids"),
    grant_usage: parseGrantUsageSnapshots(value.grant_usage),
    revoked_grant_ids: requireGrantIdArray(value.revoked_grant_ids, "revoked_grant_ids")
  };
}

function permissionsMatch(grantPermission: GrantPermission, requestPermission: GrantPermission): boolean {
  if (grantPermission.method !== requestPermission.method) return false;
  if (grantPermission.method === "sign_event") {
    return grantPermission.parameter === requestPermission.parameter && grantPermission.event_kind === requestPermission.event_kind;
  }
  return grantPermission.parameter === undefined && grantPermission.event_kind === undefined;
}

function isGrantRateLimited(grant: GrantDescriptor, request: PolicyDecisionRequest): boolean {
  const usage = request.grant_usage[grant.grant_id];
  if (usage === undefined) return false;
  const windowEndsAt = usage.window_started_at + grant.rate_limit.window_seconds;
  return request.now < windowEndsAt && usage.uses >= grant.rate_limit.max_uses;
}

function buildPolicyDecision(
  request: PolicyDecisionRequest,
  decision: PolicyDecision["decision"],
  reason: PolicyDecision["reason"],
  grantId?: string
): PolicyDecision {
  return {
    format: "nsealr-policy-decision-v0",
    decision,
    reason,
    ...(grantId !== undefined ? { grant_id: grantId } : {}),
    audit_event: {
      format: "nsealr-grant-audit-event-v0",
      occurred_at: request.now,
      account_id: request.account_id,
      route_type: request.route_type,
      client_pubkey: request.client_pubkey,
      permission: request.permission,
      decision,
      reason,
      ...(grantId !== undefined ? { grant_id: grantId } : {})
    }
  };
}

export function decidePolicyRequest(input: {
  policy: PolicyProfile;
  grants: GrantDescriptor[];
  request: PolicyDecisionRequest;
}): PolicyDecision {
  const { policy, grants } = input;
  const request = parsePolicyDecisionRequest(input.request);
  const method = request.permission.method;
  if (!policy.route_types.includes(request.route_type)) {
    return buildPolicyDecision(request, "manual_review", "policy_route_mismatch");
  }
  if (policy.forbidden_permissions.includes(method) || method === "export_secret") {
    return buildPolicyDecision(request, "deny", "forbidden_permission");
  }
  if (DECRYPT_METHODS.has(method)) {
    return buildPolicyDecision(request, "manual_review", "decrypt_requires_manual_review");
  }
  if (method === "unknown_method") {
    return buildPolicyDecision(request, "manual_review", "unknown_method_requires_manual_review");
  }
  if (!policy.grants_allowed) {
    return buildPolicyDecision(request, "manual_review", "policy_manual_only");
  }

  const revokedGrantIds = new Set(request.revoked_grant_ids);
  for (const grantId of request.grant_ids) {
    const grant = grants.find((candidate) => candidate.grant_id === grantId);
    if (grant === undefined) continue;
    if (grant.account_id !== request.account_id) continue;
    if (grant.route_type !== request.route_type) continue;
    if (grant.client.pubkey !== request.client_pubkey) continue;
    if (!permissionsMatch(grant.permission, request.permission)) continue;
    if (revokedGrantIds.has(grant.grant_id)) {
      return buildPolicyDecision(request, "deny", "grant_revoked", grant.grant_id);
    }
    if (request.now >= grant.expires_at) {
      return buildPolicyDecision(request, "deny", "grant_expired", grant.grant_id);
    }
    if (isGrantRateLimited(grant, request)) {
      return buildPolicyDecision(request, "deny", "grant_rate_limited", grant.grant_id);
    }
    return buildPolicyDecision(request, "allow", "grant_valid", grant.grant_id);
  }

  return buildPolicyDecision(request, "manual_review", "no_matching_grant");
}

function sortForCanonicalJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map((item) => sortForCanonicalJson(item));
  if (!isRecord(value)) return value;
  return Object.fromEntries(
    Object.keys(value)
      .sort()
      .map((key) => [key, sortForCanonicalJson(value[key])])
  );
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(sortForCanonicalJson(value));
}

function sha256Utf8Hex(value: string): string {
  return bytesToHex(sha256(utf8ToBytes(value)));
}

function parseContextArray<T>(
  context: Record<string, unknown>,
  field: "accounts" | "policyProfiles" | "grants",
  parser: (value: unknown) => T
): T[] {
  const value = context[field];
  if (!Array.isArray(value)) throw new Error(`policy change context ${field} must be an array`);
  return value.map((item, index) => {
    try {
      return parser(item);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`policy change context ${field}[${index}]: ${message}`);
    }
  });
}

export function parsePolicyChangeReviewContext(value: unknown): PolicyChangeReviewContext {
  assertRecord(value, "policy change context");
  assertOnlyKeys(value, ["accounts", "policyProfiles", "grants"], "policy change context");
  return {
    accounts: parseContextArray(value, "accounts", parseAccountDescriptor),
    policyProfiles: parseContextArray(value, "policyProfiles", parsePolicyProfile),
    grants: parseContextArray(value, "grants", parseGrantDescriptor)
  };
}

export function parsePolicyChangeProposal(value: unknown): PolicyChangeProposal {
  rejectSecretFields(value);
  assertRecord(value, "policy change proposal");
  assertOnlyKeys(value, [
    "format",
    "proposal_id",
    "account_id",
    "route_type",
    "action",
    "current_policy_id",
    "proposed_policy_id",
    "proposed_grant_ids",
    "requested_by",
    "created_at",
    "device_review_required",
    "physical_approval_required",
    "companion_authoritative",
    "contains_secret_material"
  ], "policy change proposal");
  if (value.format !== "nsealr-policy-change-proposal-v0") throw new Error("policy change proposal format mismatch");
  const routeType = requireRouteType(value.route_type);
  if (!POLICY_CHANGE_ROUTE_TYPES.has(routeType)) {
    throw new Error("policy change route_type must be a device-display persistent route");
  }
  if (value.action !== "set_policy") throw new Error("policy change action must be set_policy");
  assertRecord(value.requested_by, "policy change requested_by");
  assertOnlyKeys(value.requested_by, ["surface", "client_pubkey", "label"], "policy change requested_by");
  const surface = requireString(value.requested_by.surface, "policy change requested_by.surface");
  if (!POLICY_CHANGE_SURFACES.has(surface)) throw new Error("policy change requested_by.surface is unsupported");
  if (value.device_review_required !== true) throw new Error("policy change device_review_required must be true");
  if (value.physical_approval_required !== true) throw new Error("policy change physical_approval_required must be true");
  if (value.companion_authoritative !== false) throw new Error("policy change companion_authoritative must be false");
  if (value.contains_secret_material !== false) throw new Error("policy change contains_secret_material must be false");
  return {
    format: "nsealr-policy-change-proposal-v0",
    proposal_id: requireProposalId(value.proposal_id, "proposal_id"),
    account_id: requireStringId(value.account_id, "account_id"),
    route_type: routeType as PolicyChangeProposal["route_type"],
    action: "set_policy",
    current_policy_id: requirePolicyId(value.current_policy_id, "current_policy_id"),
    proposed_policy_id: requirePolicyId(value.proposed_policy_id, "proposed_policy_id"),
    proposed_grant_ids: requireGrantIdArray(value.proposed_grant_ids, "proposed_grant_ids"),
    requested_by: {
      surface: surface as PolicyChangeProposal["requested_by"]["surface"],
      client_pubkey: requireXOnlyPubkey(value.requested_by.client_pubkey, "requested_by.client_pubkey"),
      ...("label" in value.requested_by ? { label: requireString(value.requested_by.label, "requested_by.label") } : {})
    },
    created_at: requirePositiveInteger(value.created_at, "created_at"),
    device_review_required: true,
    physical_approval_required: true,
    companion_authoritative: false,
    contains_secret_material: false
  };
}

function findSingleAccount(context: PolicyChangeReviewContext, proposal: PolicyChangeProposal): AccountDescriptor {
  const matches = context.accounts.filter((account) => account.account_id === proposal.account_id);
  if (matches.length === 0) throw new Error("policy change account_id target is missing");
  if (matches.length > 1) throw new Error("policy change account_id target is ambiguous");
  return matches[0];
}

function findSinglePolicy(
  context: PolicyChangeReviewContext,
  policyId: string,
  field: "current_policy_id" | "proposed_policy_id"
): PolicyProfile {
  const matches = context.policyProfiles.filter((policy) => policy.policy_id === policyId);
  if (matches.length === 0) throw new Error(`policy change ${field} target is missing`);
  if (matches.length > 1) throw new Error(`policy change ${field} target is ambiguous`);
  return matches[0];
}

function findSingleGrant(context: PolicyChangeReviewContext, grantId: string): GrantDescriptor {
  const matches = context.grants.filter((grant) => grant.grant_id === grantId);
  if (matches.length === 0) throw new Error(`policy change proposed grant ${grantId} target is missing`);
  if (matches.length > 1) throw new Error(`policy change proposed grant ${grantId} target is ambiguous`);
  return matches[0];
}

function validatePolicyChangeProfileRoute(
  proposal: PolicyChangeProposal,
  policy: PolicyProfile,
  field: "current_policy_id" | "proposed_policy_id"
): void {
  if (!policy.route_types.includes(proposal.route_type)) {
    throw new Error(`policy change ${field} does not include route type ${proposal.route_type}`);
  }
}

function validateParsedPolicyChangeProposalContext(
  proposal: PolicyChangeProposal,
  context: PolicyChangeReviewContext
): void {
  const account = findSingleAccount(context, proposal);
  if (account.signer_route.type !== proposal.route_type) {
    throw new Error("policy change account route_type mismatch");
  }
  if (account.policy_profile_id !== proposal.current_policy_id) {
    throw new Error("policy change current_policy_id must match the account descriptor default policy");
  }

  const currentPolicy = findSinglePolicy(context, proposal.current_policy_id, "current_policy_id");
  const proposedPolicy = findSinglePolicy(context, proposal.proposed_policy_id, "proposed_policy_id");
  validatePolicyChangeProfileRoute(proposal, currentPolicy, "current_policy_id");
  validatePolicyChangeProfileRoute(proposal, proposedPolicy, "proposed_policy_id");

  if (proposal.proposed_grant_ids.length > 0 && !proposedPolicy.grants_allowed) {
    throw new Error("policy change proposed_policy_id must allow grants when proposed_grant_ids is not empty");
  }
  for (const grantId of proposal.proposed_grant_ids) {
    const grant = findSingleGrant(context, grantId);
    if (grant.account_id !== proposal.account_id) {
      throw new Error(`policy change proposed grant ${grantId} account mismatch`);
    }
    if (grant.route_type !== proposal.route_type) {
      throw new Error(`policy change proposed grant ${grantId} route mismatch`);
    }
    if (grant.client.pubkey !== proposal.requested_by.client_pubkey) {
      throw new Error(`policy change proposed grant ${grantId} client mismatch`);
    }
  }
}

export function validatePolicyChangeProposalContext(value: unknown, contextValue: unknown): PolicyChangeProposal {
  const proposal = parsePolicyChangeProposal(value);
  const context = parsePolicyChangeReviewContext(contextValue);
  validateParsedPolicyChangeProposalContext(proposal, context);
  return proposal;
}

function buildPolicyChangeReview(proposal: PolicyChangeProposal): PolicyChangeReview {
  const policyLines = [
    `From: ${proposal.current_policy_id}`,
    `To: ${proposal.proposed_policy_id}`,
    `Grants: ${proposal.proposed_grant_ids.length}`,
    ...proposal.proposed_grant_ids.map((grantId) => `Grant: ${grantId}`)
  ];
  const requesterLines = [
    `Surface: ${proposal.requested_by.surface}`,
    `Client: ${proposal.requested_by.client_pubkey}`,
    ...(proposal.requested_by.label !== undefined ? [`Label: ${proposal.requested_by.label}`] : [])
  ];
  const pages: PolicyChangeReviewPage[] = [
    {
      title: "Policy change",
      lines: [
        `Action: ${proposal.action}`,
        `Account: ${proposal.account_id}`,
        `Route: ${proposal.route_type}`
      ],
      action: "next"
    },
    {
      title: "Requester",
      lines: requesterLines,
      action: "next"
    },
    {
      title: "Policy",
      lines: policyLines,
      action: "next"
    },
    {
      title: "Decision",
      lines: [
        "Review on device",
        "Physical approval required",
        "Companion cannot approve alone"
      ],
      action: "approve_or_reject"
    }
  ];
  return {
    format: "nsealr-policy-change-review-pages-v0",
    proposal_id: proposal.proposal_id,
    approval_digest: sha256Utf8Hex(canonicalJson({ proposal, pages })),
    pages
  };
}

export function reviewPolicyChangeProposal(value: unknown, contextValue: unknown): PolicyChangeReview {
  return buildPolicyChangeReview(validatePolicyChangeProposalContext(value, contextValue));
}

function parsePolicyChangeReview(value: unknown): PolicyChangeReview {
  assertRecord(value, "policy change review");
  assertOnlyKeys(value, ["format", "proposal_id", "approval_digest", "pages"], "policy change review");
  if (value.format !== "nsealr-policy-change-review-pages-v0") throw new Error("policy change review format mismatch");
  if (typeof value.approval_digest !== "string" || !/^[0-9a-f]{64}$/u.test(value.approval_digest)) {
    throw new Error("policy change approval_digest is invalid");
  }
  if (!Array.isArray(value.pages)) throw new Error("policy change review pages must be an array");
  const pages = value.pages.map((page, index) => {
    assertRecord(page, `policy change review pages[${index}]`);
    assertOnlyKeys(page, ["title", "lines", "action"], `policy change review pages[${index}]`);
    const action = requireString(page.action, `policy change review pages[${index}].action`);
    if (action !== "next" && action !== "approve_or_reject") {
      throw new Error(`policy change review pages[${index}].action is invalid`);
    }
    return {
      title: requireString(page.title, `policy change review pages[${index}].title`),
      lines: requireStringArray(page.lines, `policy change review pages[${index}].lines`),
      action: action as PolicyChangeReviewPage["action"]
    };
  });
  return {
    format: "nsealr-policy-change-review-pages-v0",
    proposal_id: requireProposalId(value.proposal_id, "policy change review proposal_id"),
    approval_digest: value.approval_digest,
    pages
  };
}

export function parsePolicyChangeReviewVector(value: unknown, contextValue?: unknown): PolicyChangeReviewVector {
  rejectSecretFields(value);
  assertRecord(value, "policy change review vector");
  assertOnlyKeys(value, ["name", "format", "proposal", "review"], "policy change review vector");
  if (value.format !== "nsealr-policy-change-review-v0") throw new Error("policy change review vector format mismatch");
  const proposal = parsePolicyChangeProposal(value.proposal);
  if (contextValue !== undefined) {
    const context = parsePolicyChangeReviewContext(contextValue);
    validateParsedPolicyChangeProposalContext(proposal, context);
  }
  const review = parsePolicyChangeReview(value.review);
  const expectedReview = buildPolicyChangeReview(proposal);
  if (review.proposal_id !== proposal.proposal_id) throw new Error("policy change review proposal_id mismatch");
  if (review.approval_digest !== expectedReview.approval_digest) throw new Error("policy change approval_digest mismatch");
  if (JSON.stringify(review.pages) !== JSON.stringify(expectedReview.pages)) {
    throw new Error("policy change review pages mismatch");
  }
  return {
    name: requireStringId(value.name, "policy change review vector name"),
    format: "nsealr-policy-change-review-v0",
    proposal,
    review
  };
}

function routeSelectionFromAccount(account: AccountDescriptor): RouteSelection {
  return {
    format: "nsealr-route-selection-v0",
    account_id: account.account_id,
    public_key: account.public_key,
    route_type: account.signer_route.type,
    ...(account.signer_route.repository !== undefined ? { repository: account.signer_route.repository } : {}),
    transport: account.signer_route.transport,
    custody: account.signer_route.custody,
    trusted_review: account.signer_route.trusted_review,
    policy_support: account.signer_route.policy_support,
    policy_profile_id: account.policy_profile_id,
    physical_review: account.capabilities.physical_review,
    physical_approval: account.capabilities.physical_approval,
    persistent_grants: account.capabilities.persistent_grants,
    contains_secret_material: false
  };
}

export function parseRouteSelection(value: unknown): RouteSelection {
  rejectSecretFields(value);
  assertRecord(value, "route selection");
  assertOnlyKeys(value, [
    "format",
    "account_id",
    "public_key",
    "route_type",
    "repository",
    "transport",
    "custody",
    "trusted_review",
    "policy_support",
    "policy_profile_id",
    "physical_review",
    "physical_approval",
    "persistent_grants",
    "contains_secret_material"
  ], "route selection");
  if (value.format !== "nsealr-route-selection-v0") throw new Error("route selection format mismatch");
  const routeType = requireRouteType(value.route_type, "route selection route_type");
  const expectedRepository = ROUTE_REPOSITORIES.get(routeType);
  if (expectedRepository !== undefined && value.repository !== expectedRepository) {
    throw new Error("route selection repository does not match route_type");
  }
  if (expectedRepository === undefined && "repository" in value) {
    throw new Error("external route selections must not claim a nSealr repository");
  }
  const transport = requireString(value.transport, "route selection transport");
  if (!ROUTE_TRANSPORTS.has(transport)) throw new Error("route selection transport is unknown");
  const custody = requireString(value.custody, "route selection custody");
  if (!CUSTODY_MODES.has(custody)) throw new Error("route selection custody is unknown");
  const trustedReview = requireString(value.trusted_review, "route selection trusted_review");
  if (!REVIEW_MODES.has(trustedReview)) throw new Error("route selection trusted_review is unknown");
  const policySupport = requireString(value.policy_support, "route selection policy_support");
  if (!POLICY_SUPPORT_MODES.has(policySupport)) throw new Error("route selection policy_support is unknown");
  const routeSelection: RouteSelection = {
    format: "nsealr-route-selection-v0",
    account_id: requireStringId(value.account_id, "route selection account_id"),
    public_key: requireXOnlyPubkey(value.public_key, "route selection public_key"),
    route_type: routeType,
    ...(typeof value.repository === "string" ? { repository: value.repository as RouteSelection["repository"] } : {}),
    transport: transport as RouteSelection["transport"],
    custody: custody as RouteSelection["custody"],
    trusted_review: trustedReview as RouteSelection["trusted_review"],
    policy_support: policySupport as RouteSelection["policy_support"],
    policy_profile_id: requirePolicyId(value.policy_profile_id, "route selection policy_profile_id"),
    physical_review: requireBoolean(value.physical_review, "route selection physical_review"),
    physical_approval: requireBoolean(value.physical_approval, "route selection physical_approval"),
    persistent_grants: requireBoolean(value.persistent_grants, "route selection persistent_grants"),
    contains_secret_material: false
  };
  if (value.contains_secret_material !== false) {
    throw new Error("route selection contains_secret_material must be false");
  }
  const routeSelectionCapabilities: AccountDescriptor["capabilities"] = {
    // Route-selection responses do not carry method lists; route request parsing
    // checks method support before a response is produced.
    methods: [],
    physical_review: routeSelection.physical_review,
    physical_approval: routeSelection.physical_approval,
    persistent_grants: routeSelection.persistent_grants
  };
  validateRouteSemantics(routeSelectionToSignerRoute(routeSelection), routeSelectionCapabilities, value);
  return routeSelection;
}

function routeSelectionToSignerRoute(routeSelection: RouteSelection): SignerRoute {
  return {
    type: routeSelection.route_type,
    ...(routeSelection.repository !== undefined ? { repository: routeSelection.repository } : {}),
    transport: routeSelection.transport,
    custody: routeSelection.custody,
    trusted_review: routeSelection.trusted_review,
    policy_support: routeSelection.policy_support
  };
}

export function parseRouteSelectionRequest(value: unknown): RouteSelectionRequest {
  assertRecord(value, "route selection request");
  assertOnlyKeys(value, ["account_id", "method", "route_type"], "route selection request");
  const accountId = requireStringId(value.account_id, "route selection account_id");
  const method = requireString(value.method, "route selection method");
  const routeType = value.route_type === undefined
    ? undefined
    : requireRouteType(value.route_type, "route selection route_type");
  return routeType === undefined
    ? { account_id: accountId, method }
    : { account_id: accountId, method, route_type: routeType };
}

export function selectAccountRoute(accounts: AccountDescriptor[], request: RouteSelectionRequest): RouteSelection {
  if (!Array.isArray(accounts)) throw new Error("route selection accounts must be an array");
  const parsedRequest = parseRouteSelectionRequest(request);
  const accountId = parsedRequest.account_id;
  const method = parsedRequest.method;
  const routeType = parsedRequest.route_type;
  const matches = accounts.filter((account) => account.account_id === accountId);
  if (matches.length === 0) throw new Error("route selection account_id is unknown");
  if (matches.length > 1) throw new Error("route selection account_id is ambiguous");
  const account = matches[0];
  if (routeType !== undefined && account.signer_route.type !== routeType) {
    throw new Error("route selection route_type does not match account");
  }
  if (!account.capabilities.methods.includes(method)) {
    throw new Error("route selection method is unsupported by account");
  }
  return parseRouteSelection(routeSelectionFromAccount(account));
}
