import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import {
  parseAccountDescriptor,
  parseGrantDescriptor,
  parsePolicyChangeReviewVector,
  parsePolicyProfile,
  type AccountDescriptor,
  type GrantDescriptor,
  type PolicyChangeReviewVector,
  type PolicyDecision,
  type PolicyDecisionRequest,
  type PolicyProfile,
  type RouteSelection,
  type RouteSelectionRequest
} from "@nsealr/policy";
import { REVIEW_DETAIL_BODY_LINE_STYLES } from "@nsealr/review";

export type SpecsFixtureSet = {
  key: {
    name: string;
    secret_key: string;
    public_key: string;
  };
  events: Array<{
    name: string;
    request: unknown;
    response: unknown;
    event_id: string;
    signature: string;
  }>;
  reviews: Array<{
    name: string;
    request: unknown;
    review: {
      kind: number;
      created_at: number;
      author_pubkey: string;
      content: string;
      content_utf8_bytes: number;
      tag_count: number;
      tags: string[][];
    };
  }>;
  reviewScreens: Array<{
    name: string;
    request: unknown;
    review: SpecsFixtureSet["reviews"][number]["review"];
    screen_review: {
      format: "screen-pages";
      request_id: string;
      approval_digest: string;
      pages: Array<{
        title: string;
        lines: string[];
        action: "next" | "approve_or_reject";
      }>;
    };
  }>;
  reviewDisplayFrames: Array<{
    name: string;
    format: string;
    source_review_vector: string;
    page_index: number;
    limits: {
      max_title_chars: number;
      max_body_lines: number;
      max_line_chars: number;
    };
    frame: {
      title: string;
      page_indicator: string;
      body_lines: string[];
      action_hint: string;
    };
  }>;
  reviewDetailPages: Array<{
    name: string;
    format: string;
    display_profile: string;
    source_review_vector: string;
    source_screen_review_vector?: string;
    approval_digest: string;
    limits: {
      max_title_chars: number;
      max_body_lines: number;
      max_line_chars: number;
      max_compact_body_lines: number;
      max_compact_line_chars: number;
    };
    pages: Array<{
      title: string;
      lines: string[];
      action: "next" | "approve_or_reject";
      page_indicator: string;
      body_line_styles: string[];
      logical_page_id: string;
    }>;
  }>;
  reviewTranscripts: Array<{
    name: string;
    format: string;
    source_vector: string;
    screen_review_vector: string;
    qr_envelope: string;
    request: unknown;
    approval_digest: string;
    buttons: string[];
    transcript: Array<{
      frame: {
        title: string;
        page_indicator: string;
        body_lines: string[];
        action_hint: string;
        body_line_styles?: string[];
      };
      button: string;
      decision: boolean | null;
      approved_for_signing: boolean;
    }>;
  }>;
  nip46Payloads: Array<{
    name: string;
    format: string;
    request_message: {
      id: string;
      method: string;
      params: string[];
    };
    permission_requirement?: {
      method: string;
      parameter?: string;
      event_kind?: number;
    };
    permission_checks?: Array<{
      granted_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
      permitted: boolean;
    }>;
    bridge_decisions?: Array<{
      granted_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
      decision: unknown;
    }>;
    nsealr_request?: unknown;
    nsealr_response?: unknown;
    response_message?: {
      id: string;
      result?: string;
      error?: string;
    };
    local_response_message?: {
      id: string;
      result?: string;
      error?: string;
    };
    connect_intent?: {
      id: string;
      remote_signer_pubkey: string;
      secret?: string;
      requested_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
    };
    connect_review?: {
      format: "nsealr-nip46-connect-review-v0";
      id: string;
      remote_signer_pubkey: string;
      secret_present: boolean;
      requested_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
      pages: Array<{
        title: string;
        page_indicator: string;
        body_lines: string[];
      }>;
      connect_digest: string;
    };
    connect_approval?: {
      format: "nsealr-nip46-connect-approval-v0";
      id: string;
      connect_digest: string;
      approved_at: number;
      acknowledges_connect: false;
      creates_grants: false;
      opens_relay: false;
      persists_session_state: false;
      stores_production_secrets: false;
      exposes_secret: false;
    };
  }>;
  nip46PolicyFiles: Array<{
    name: string;
    format: string;
    approved_permissions: Array<{
      method: string;
      parameter?: string;
      event_kind?: number;
    }>;
  }>;
  nip46ConnectionUris: Array<{
    name: string;
    format: "nsealr-nip46-connection-uri-v0";
    uri: string;
    secret_probe: string;
    expected_descriptor: unknown;
    scope: string;
  }>;
  nip46ConnectionTokenResponses: Array<{
    name: string;
    format: "nsealr-nip46-connection-token-response-vector-v0";
    source_connection_uri_vector: string;
    response_step: unknown;
    expected_response: unknown;
    scope: string;
  }>;
  nip46RelayEvents: Array<{
    name: string;
    format: "nsealr-nip46-relay-event-envelope-v0";
    direction: "client_to_remote_signer" | "remote_signer_to_client";
    event: unknown;
    expected_envelope: unknown;
    scope: string;
  }>;
  nip46RelaySteps: Array<{
    name: string;
    format: "nsealr-nip46-relay-request-step-v0" | "nsealr-nip46-relay-response-step-v1";
    direction: "client_to_remote_signer" | "remote_signer_to_client";
    event: unknown;
    decrypted_message: unknown;
    granted_permissions?: unknown[];
    expected_step: unknown;
    scope: string;
  }>;
  nip46AuthChallenges: Array<{
    name: string;
    format: "nsealr-nip46-auth-challenge-review-vector-v0";
    source_relay_step_vector: string;
    review: unknown;
    approval: unknown;
    scope: string;
  }>;
  nip46Sessions: Array<{
    name: string;
    format: "nsealr-nip46-session-lifecycle-vector-v0";
    source_connect_review_vector: string;
    session: {
      name: string;
      format: "nsealr-nip46-session-lifecycle-v0";
      phase: "approved_pending_ack";
      client_pubkey: string;
      remote_signer_pubkey: string;
      relays: string[];
      connect_digest: string;
      approved_at: number;
      expires_at: number;
      requested_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
      approved_permissions: Array<{
        method: string;
        parameter?: string;
        event_kind?: number;
      }>;
      secret_present: boolean;
      secret_value_stored: false;
      contains_secret_material: false;
      derives_nip44_key: false;
      acknowledges_connect: false;
      opens_relay: false;
      creates_grants: false;
      dispatches_signer: false;
      stores_production_secrets: false;
      persists_session_state: false;
      scope: string;
    };
  }>;
  nip46SessionGates: Array<{
    name: string;
    format: "nsealr-nip46-session-request-gate-v0";
    source_session_vector: string;
    evaluated_at: number;
    direction: "client_to_remote_signer";
    event: unknown;
    decrypted_message: unknown;
    expected_gate: unknown;
    scope: string;
  }>;
  accounts: AccountDescriptor[];
  policyProfiles: PolicyProfile[];
  grants: GrantDescriptor[];
  policyDecisions: Array<{
    name: string;
    format: "nsealr-policy-decision-vector-v0";
    policy_profile_id: string;
    request: PolicyDecisionRequest;
    decision: PolicyDecision;
  }>;
  policyChanges: PolicyChangeReviewVector[];
  routeSelections: Array<{
    name: string;
    format: "nsealr-route-selection-vector-v0";
    request: RouteSelectionRequest;
    selection: RouteSelection;
  }>;
  routeRefusals: Array<{
    name: string;
    format: "nsealr-route-refusal-contract-v0";
    request_vector: string;
    cases: Array<{
      route_selection_vector: string;
      route_type: RouteSelection["route_type"];
      trusted_review: RouteSelection["trusted_review"];
      without_dispatcher?: RouteRefusalErrorExpectation;
      without_dispatcher_after_ack?: RouteRefusalErrorExpectation;
      external_review_acknowledgement:
        | {
            mode: "unsupported";
            unsupported_error: RouteRefusalErrorExpectation;
          }
        | {
            mode: "required";
            missing_error: RouteRefusalErrorExpectation;
            mismatch_error: RouteRefusalErrorExpectation;
          };
    }>;
    safety: Record<string, boolean>;
    scope: string;
  }>;
  sourcePublicKeyProofs: Array<{
    format: "nsealr-source-public-key-proof-v0";
    name: string;
    proof_type: "nip06" | "nip19_nsec";
    source_type: "bip39_seed" | "nsec";
    source_vector: string;
    source_fingerprint: string;
    account?: number;
    path?: string;
    passphrase?: string;
    expected_public_key: string;
    security_scope: string;
  }>;
  accessSurfaces: Array<{
    name: string;
    format: "nsealr-access-surface-vector-v0";
    surface: "browser_provider_nip07";
    transport: "local_service";
    client: {
      surface: "browser_extension" | "desktop_app" | "cli" | "sdk" | "native_host_test";
      origin: string;
      app_name?: string;
      instance_id?: string;
    };
    client_grant: {
      client_id: string;
      origin: string;
      surface: "browser_extension" | "desktop_app" | "cli" | "sdk" | "native_host_test";
      allowed_operations: string[];
      approved_at?: number;
      expires_at?: number;
    };
    route_selection_vector: string;
    sign_event_request_vector: string;
    expected: {
      get_public_key: {
        public_key: string;
      };
      sign_event_without_dispatcher: {
        response: unknown;
      };
    };
    safety: Record<string, boolean>;
    scope: string;
  }>;
  featureMatrices: Array<{
    name: string;
    format: "nsealr-signer-feature-matrix-v0";
    features: Array<{
      id: string;
      contract_id: string;
      behavior: string;
    }>;
    solutions: Record<
      string,
      {
        label: string;
        repository: string;
        product_goal: string;
        features: Record<
          string,
          {
            target: string;
            current: string;
            contract_id?: string;
            notes: string;
          }
        >;
      }
    >;
  }>;
  custodyContracts: Array<{
    name: "persistent-secret-custody-v0";
    format: "nsealr-persistent-secret-custody-contract-v0";
    contract_id: "persistent-secret-custody-v0";
    solution: "custom_hardware_wallet";
    repository: "hardware";
    current_status: "research";
    scope: string;
    requirements: {
      secret_at_rest: {
        plaintext_allowed: false;
        allowed_storage: string[];
        production_storage_enabled: false;
      };
      unlock: {
        plaintext_locations: string[];
        required_unlock_assist: string[];
        requires_local_unlock: true;
        requires_device_review_state: true;
      };
      plaintext_persistence: {
        scope: "unlocked_session_ram_only";
        forbidden_outputs: string[];
      };
      wipe_events: string[];
      pin_attempt_policy: {
        requires_tropic01_mac_and_destroy_or_vendor_equivalent: true;
        production_required: true;
      };
      backup_export_policy: {
        enabled_by_default: false;
        requires_local_device_review: true;
        requires_physical_approval: true;
        requires_danger_zone_copy: true;
      };
    };
    non_claims: string[];
  }>;
  limits: {
    format: string;
    name: string;
    limits: Record<string, number>;
    integer_policy: Record<string, unknown>;
  };
  invalidVectors: Array<{
    name: string;
    format: string;
    category:
      | "signing-request"
      | "response"
      | "qr-envelope"
      | "serial-frame"
      | "nip46"
      | "nip46-connection-uri"
      | "nip46-connection-token-response"
      | "nip46-relay-event"
      | "nip46-relay-step"
      | "nip46-session"
      | "nip46-session-gate"
      | "nip46-policy-file";
    expected_error: string;
    request?: unknown;
    response?: unknown;
    envelope?: string;
    frame?: string;
    request_message?: unknown;
    uri?: string;
    connection_token_response?: unknown;
    relay_event?: unknown;
    relay_step?: unknown;
    session?: unknown;
    session_gate?: unknown;
    policy_file?: unknown;
  }>;
};

type RouteRefusalErrorExpectation = {
  error_code: string;
  message: string;
  retryable: false;
};

const REVIEW_TRANSCRIPT_BUTTONS = new Set(["next", "scroll", "approve", "reject"]);
const REVIEW_TRANSCRIPT_BODY_LINE_STYLES = new Set<string>(REVIEW_DETAIL_BODY_LINE_STYLES);
const FEATURE_TARGETS = new Set(["required", "optional", "not_applicable", "forbidden", "research"]);
const FEATURE_CURRENT_STATUSES = new Set([
  "implemented",
  "partial",
  "planned",
  "hardware_blocked",
  "research",
  "not_applicable",
  "forbidden",
  "disabled_until_gates_pass"
]);
const FEATURE_SOLUTION_IDS = new Set([
  "raspberry_qr_vault",
  "esp32_qr_vault",
  "esp32_usb_nip46",
  "smartcard",
  "custom_hardware_wallet"
]);
const ACCESS_SURFACE_SAFETY = {
  stores_production_secrets: false,
  contains_secret_material: false,
  creates_grants: false,
  dispatches_without_signer: false,
  requires_shared_request_validation: true,
  requires_signed_response_verification: true
};
const ROUTE_REFUSAL_SAFETY = {
  stores_production_secrets: false,
  contains_secret_material: false,
  creates_grants: false,
  dispatches_without_signer: false,
  requires_shared_request_validation: true,
  requires_signed_response_verification: true
};
const STATELESS_QR_PARITY_FEATURES = [
  "request_validation_v0",
  "nostr_event_review_universal",
  "review_detail_pages",
  "approval_digest_binding",
  "physical_approval",
  "sign_event_bip340",
  "qr_static_request",
  "qr_animated_request",
  "qr_response",
  "stateless_session_custody",
  "manual_only_policy",
  "device_display_review",
  "response_verification"
];
const PERSISTENT_CUSTODY_ALLOWED_STORAGE = [
  "esp32_flash_encrypted_blob",
  "tropic01_wrapped_secret_blob"
];
const PERSISTENT_CUSTODY_FORBIDDEN_OUTPUTS = [
  "companion_descriptors",
  "crash_dumps",
  "debug_output",
  "flash",
  "logs",
  "usb_reports"
];
const PERSISTENT_CUSTODY_WIPE_EVENTS = [
  "debug_policy_violation",
  "firmware_error",
  "manual_lock",
  "pin_attempt_exhausted",
  "power_loss",
  "session_timeout"
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function expectStringArraySet(name: string, label: string, value: unknown, expected: string[]): void {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
    throw new Error(`invalid persistent-secret custody contract ${name}: ${label} must be a string array`);
  }
  if (JSON.stringify([...value].sort()) !== JSON.stringify([...expected].sort())) {
    throw new Error(`invalid persistent-secret custody contract ${name}: ${label} drift`);
  }
}

export function validatePersistentSecretCustodyFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) {
    throw new Error(`invalid persistent-secret custody contract ${name}: fixture must be an object`);
  }
  if (fixture.format !== "nsealr-persistent-secret-custody-contract-v0") {
    throw new Error(`invalid persistent-secret custody contract ${name}: unsupported format`);
  }
  if (fixture.name !== name) throw new Error(`invalid persistent-secret custody contract ${name}: name mismatch`);
  if (fixture.contract_id !== "persistent-secret-custody-v0") {
    throw new Error(`invalid persistent-secret custody contract ${name}: contract_id drift`);
  }
  if (fixture.solution !== "custom_hardware_wallet" || fixture.repository !== "hardware") {
    throw new Error(`invalid persistent-secret custody contract ${name}: solution boundary drift`);
  }
  if (fixture.current_status !== "research") {
    throw new Error(`invalid persistent-secret custody contract ${name}: current status must remain research`);
  }
  if (typeof fixture.scope !== "string" || !fixture.scope.includes("before production")) {
    throw new Error(`invalid persistent-secret custody contract ${name}: scope must preserve pre-production boundary`);
  }
  if (!isRecord(fixture.requirements)) {
    throw new Error(`invalid persistent-secret custody contract ${name}: requirements must be an object`);
  }

  const secretAtRest = fixture.requirements.secret_at_rest;
  if (!isRecord(secretAtRest)) {
    throw new Error(`invalid persistent-secret custody contract ${name}: secret_at_rest must be an object`);
  }
  if (secretAtRest.plaintext_allowed !== false || secretAtRest.production_storage_enabled !== false) {
    throw new Error(`invalid persistent-secret custody contract ${name}: plaintext-at-rest boundary drift`);
  }
  expectStringArraySet(
    name,
    "secret_at_rest.allowed_storage",
    secretAtRest.allowed_storage,
    PERSISTENT_CUSTODY_ALLOWED_STORAGE
  );

  const unlock = fixture.requirements.unlock;
  if (!isRecord(unlock)) {
    throw new Error(`invalid persistent-secret custody contract ${name}: unlock must be an object`);
  }
  expectStringArraySet(name, "unlock.plaintext_locations", unlock.plaintext_locations, ["esp32_s3_ram"]);
  expectStringArraySet(name, "unlock.required_unlock_assist", unlock.required_unlock_assist, ["tropic01"]);
  if (unlock.requires_local_unlock !== true || unlock.requires_device_review_state !== true) {
    throw new Error(`invalid persistent-secret custody contract ${name}: unlock review boundary drift`);
  }

  const plaintextPersistence = fixture.requirements.plaintext_persistence;
  if (!isRecord(plaintextPersistence) || plaintextPersistence.scope !== "unlocked_session_ram_only") {
    throw new Error(`invalid persistent-secret custody contract ${name}: plaintext persistence boundary drift`);
  }
  expectStringArraySet(
    name,
    "plaintext_persistence.forbidden_outputs",
    plaintextPersistence.forbidden_outputs,
    PERSISTENT_CUSTODY_FORBIDDEN_OUTPUTS
  );
  expectStringArraySet(name, "wipe_events", fixture.requirements.wipe_events, PERSISTENT_CUSTODY_WIPE_EVENTS);

  const pinAttemptPolicy = fixture.requirements.pin_attempt_policy;
  if (
    !isRecord(pinAttemptPolicy) ||
    pinAttemptPolicy.requires_tropic01_mac_and_destroy_or_vendor_equivalent !== true ||
    pinAttemptPolicy.production_required !== true
  ) {
    throw new Error(`invalid persistent-secret custody contract ${name}: PIN attempt policy drift`);
  }

  const backupExportPolicy = fixture.requirements.backup_export_policy;
  if (
    !isRecord(backupExportPolicy) ||
    backupExportPolicy.enabled_by_default !== false ||
    backupExportPolicy.requires_local_device_review !== true ||
    backupExportPolicy.requires_physical_approval !== true ||
    backupExportPolicy.requires_danger_zone_copy !== true
  ) {
    throw new Error(`invalid persistent-secret custody contract ${name}: backup/export policy drift`);
  }

  if (
    !Array.isArray(fixture.non_claims) ||
    !fixture.non_claims.every((claim) => typeof claim === "string") ||
    !fixture.non_claims.some((claim) => claim.includes("does not claim direct TROPIC01")) ||
    !fixture.non_claims.some((claim) => claim.includes("does not enable production signing")) ||
    !fixture.non_claims.some((claim) => claim.includes("does not apply to stateless QR vault"))
  ) {
    throw new Error(`invalid persistent-secret custody contract ${name}: non-claims drift`);
  }
}

export function validateReviewTranscriptFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid review transcript fixture ${name}: fixture must be an object`);
  if (fixture.format !== "qr-review-transcript-v0") {
    throw new Error(`invalid review transcript fixture ${name}: unsupported format`);
  }
  if (typeof fixture.qr_envelope !== "string" || !fixture.qr_envelope.startsWith("nsealr1:")) {
    throw new Error(`invalid review transcript fixture ${name}: qr_envelope must be a nsealr1 envelope`);
  }
  if (typeof fixture.approval_digest !== "string" || !/^[0-9a-f]{64}$/u.test(fixture.approval_digest)) {
    throw new Error(`invalid review transcript fixture ${name}: approval_digest must be 32-byte lowercase hex`);
  }
  if (!Array.isArray(fixture.buttons) || fixture.buttons.length === 0) {
    throw new Error(`invalid review transcript fixture ${name}: buttons must be a non-empty array`);
  }
  if (!Array.isArray(fixture.transcript) || fixture.transcript.length !== fixture.buttons.length) {
    throw new Error(`invalid review transcript fixture ${name}: transcript length must match buttons`);
  }
  for (const [index, step] of fixture.transcript.entries()) {
    if (!isRecord(step)) throw new Error(`invalid review transcript fixture ${name}: step ${index} must be an object`);
    const button = fixture.buttons[index];
    if (!REVIEW_TRANSCRIPT_BUTTONS.has(String(button))) {
      throw new Error(`invalid review transcript fixture ${name}: unsupported button at step ${index}`);
    }
    if (step.button !== button) {
      throw new Error(`invalid review transcript fixture ${name}: button mismatch at step ${index}`);
    }
    if (step.decision !== null && typeof step.decision !== "boolean") {
      throw new Error(`invalid review transcript fixture ${name}: decision must be boolean or null at step ${index}`);
    }
    if (typeof step.approved_for_signing !== "boolean") {
      throw new Error(`invalid review transcript fixture ${name}: approval state must be boolean at step ${index}`);
    }
    if (!isRecord(step.frame) || typeof step.frame.title !== "string") {
      throw new Error(`invalid review transcript fixture ${name}: frame must include title at step ${index}`);
    }
    if (!Array.isArray(step.frame.body_lines) || !step.frame.body_lines.every((line) => typeof line === "string")) {
      throw new Error(`invalid review transcript fixture ${name}: frame body_lines must be strings at step ${index}`);
    }
    const bodyLineStyles = step.frame.body_line_styles;
    if (bodyLineStyles !== undefined) {
      if (
        !Array.isArray(bodyLineStyles) ||
        bodyLineStyles.length !== step.frame.body_lines.length ||
        !bodyLineStyles.every((style) => REVIEW_TRANSCRIPT_BODY_LINE_STYLES.has(String(style)))
      ) {
        throw new Error(`invalid review transcript fixture ${name}: frame body_line_styles mismatch at step ${index}`);
      }
    }
  }
}

export function validateFeatureMatrixFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid feature matrix ${name}: fixture must be an object`);
  if (fixture.format !== "nsealr-signer-feature-matrix-v0") {
    throw new Error(`invalid feature matrix ${name}: unsupported format`);
  }
  if (fixture.name !== name) throw new Error(`invalid feature matrix ${name}: name mismatch`);
  if (!Array.isArray(fixture.features)) throw new Error(`invalid feature matrix ${name}: features must be an array`);

  const canonicalContracts = new Map<string, string>();
  for (const [index, feature] of fixture.features.entries()) {
    if (!isRecord(feature)) throw new Error(`invalid feature matrix ${name}: feature ${index} must be an object`);
    if (typeof feature.id !== "string" || feature.id.length === 0) {
      throw new Error(`invalid feature matrix ${name}: feature ${index} id must be a string`);
    }
    if (typeof feature.contract_id !== "string" || feature.contract_id.length === 0) {
      throw new Error(`invalid feature matrix ${name}: feature ${feature.id} contract_id must be a string`);
    }
    if (typeof feature.behavior !== "string" || feature.behavior.length === 0) {
      throw new Error(`invalid feature matrix ${name}: feature ${feature.id} behavior must be a string`);
    }
    canonicalContracts.set(feature.id, feature.contract_id);
  }

  if (!isRecord(fixture.solutions)) throw new Error(`invalid feature matrix ${name}: solutions must be an object`);
  const solutionIds = Object.keys(fixture.solutions).sort();
  const expectedSolutionIds = [...FEATURE_SOLUTION_IDS].sort();
  if (JSON.stringify(solutionIds) !== JSON.stringify(expectedSolutionIds)) {
    throw new Error(`invalid feature matrix ${name}: signer family drift`);
  }

  const activeContracts = new Map<string, string>();
  const statelessQrTargetsBySolution = new Map<string, Record<string, string | undefined>>();
  for (const solutionId of solutionIds) {
    const solution = fixture.solutions[solutionId];
    if (!isRecord(solution)) throw new Error(`invalid feature matrix ${name}: solution ${solutionId} must be an object`);
    if (typeof solution.label !== "string" || solution.label.length === 0) {
      throw new Error(`invalid feature matrix ${name}: solution ${solutionId} label must be a string`);
    }
    if (typeof solution.repository !== "string" || solution.repository.length === 0) {
      throw new Error(`invalid feature matrix ${name}: solution ${solutionId} repository must be a string`);
    }
    if (typeof solution.product_goal !== "string" || solution.product_goal.length === 0) {
      throw new Error(`invalid feature matrix ${name}: solution ${solutionId} product_goal must be a string`);
    }
    if (!isRecord(solution.features)) {
      throw new Error(`invalid feature matrix ${name}: solution ${solutionId} features must be an object`);
    }
    const featureIds = Object.keys(solution.features).sort();
    const expectedFeatureIds = [...canonicalContracts.keys()].sort();
    if (JSON.stringify(featureIds) !== JSON.stringify(expectedFeatureIds)) {
      throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature set drift`);
    }
    const currentQrTargets: Record<string, string | undefined> = {};
    for (const featureId of featureIds) {
      const feature = solution.features[featureId];
      if (!isRecord(feature)) {
        throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature ${featureId} must be an object`);
      }
      if (!FEATURE_TARGETS.has(String(feature.target))) {
        throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature ${featureId} target is unknown`);
      }
      if (!FEATURE_CURRENT_STATUSES.has(String(feature.current))) {
        throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature ${featureId} current status is unknown`);
      }
      if (typeof feature.notes !== "string" || feature.notes.length === 0) {
        throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature ${featureId} notes must be a string`);
      }

      const activeTarget = feature.target === "required" || feature.target === "optional" || feature.target === "research";
      if (activeTarget) {
        if (typeof feature.contract_id !== "string" || feature.contract_id.length === 0) {
          throw new Error(`invalid feature matrix ${name}: solution ${solutionId} feature ${featureId} missing contract_id`);
        }
        if (feature.contract_id !== canonicalContracts.get(featureId)) {
          throw new Error(`invalid feature matrix ${name}: shared feature contract drift for ${featureId}`);
        }
        const previous = activeContracts.get(featureId);
        if (previous !== undefined && previous !== feature.contract_id) {
          throw new Error(`invalid feature matrix ${name}: shared feature contract drift for ${featureId}`);
        }
        activeContracts.set(featureId, feature.contract_id);
      } else if ("contract_id" in feature) {
        throw new Error(`invalid feature matrix ${name}: inactive feature ${featureId} must not set contract_id`);
      }

      if (STATELESS_QR_PARITY_FEATURES.includes(featureId)) {
        currentQrTargets[featureId] = String(feature.target);
      }
    }
    if (solutionId === "raspberry_qr_vault" || solutionId === "esp32_qr_vault") {
      statelessQrTargetsBySolution.set(solutionId, currentQrTargets);
    }
  }
  const raspberryQrTargets = statelessQrTargetsBySolution.get("raspberry_qr_vault");
  const esp32QrTargets = statelessQrTargetsBySolution.get("esp32_qr_vault");
  if (JSON.stringify(raspberryQrTargets) !== JSON.stringify(esp32QrTargets)) {
    throw new Error(`invalid feature matrix ${name}: stateless QR vault target drift`);
  }
}

export function validateAccessSurfaceFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid access-surface fixture ${name}: fixture must be an object`);
  if (fixture.format !== "nsealr-access-surface-vector-v0") {
    throw new Error(`invalid access-surface fixture ${name}: unsupported format`);
  }
  if (fixture.name !== name) throw new Error(`invalid access-surface fixture ${name}: name mismatch`);
  if (fixture.surface !== "browser_provider_nip07") {
    throw new Error(`invalid access-surface fixture ${name}: unsupported surface`);
  }
  if (fixture.transport !== "local_service") {
    throw new Error(`invalid access-surface fixture ${name}: unsupported transport`);
  }
  if (!isRecord(fixture.client) || fixture.client.surface !== "browser_extension" || typeof fixture.client.origin !== "string") {
    throw new Error(`invalid access-surface fixture ${name}: client boundary is invalid`);
  }
  if (!isRecord(fixture.client_grant) || fixture.client_grant.origin !== fixture.client.origin) {
    throw new Error(`invalid access-surface fixture ${name}: client grant boundary is invalid`);
  }
  if (typeof fixture.route_selection_vector !== "string" || fixture.route_selection_vector.length === 0) {
    throw new Error(`invalid access-surface fixture ${name}: route_selection_vector is invalid`);
  }
  if (typeof fixture.sign_event_request_vector !== "string" || !fixture.sign_event_request_vector.startsWith("examples/")) {
    throw new Error(`invalid access-surface fixture ${name}: sign_event_request_vector is invalid`);
  }
  if (!isRecord(fixture.safety)) throw new Error(`invalid access-surface fixture ${name}: safety must be an object`);
  const safetyKeys = Object.keys(fixture.safety).sort();
  const expectedSafetyKeys = Object.keys(ACCESS_SURFACE_SAFETY).sort();
  if (JSON.stringify(safetyKeys) !== JSON.stringify(expectedSafetyKeys)) {
    throw new Error(`invalid access-surface fixture ${name}: safety boundary drift`);
  }
  for (const [key, expected] of Object.entries(ACCESS_SURFACE_SAFETY)) {
    if (fixture.safety[key] !== expected) {
      throw new Error(`invalid access-surface fixture ${name}: safety boundary drift`);
    }
  }
  const expected = fixture.expected;
  if (!isRecord(expected)) throw new Error(`invalid access-surface fixture ${name}: expected must be an object`);
  if (!isRecord(expected.get_public_key) || typeof expected.get_public_key.public_key !== "string") {
    throw new Error(`invalid access-surface fixture ${name}: expected get_public_key is invalid`);
  }
  if (
    !isRecord(expected.sign_event_without_dispatcher) ||
    !isRecord(expected.sign_event_without_dispatcher.response)
  ) {
    throw new Error(`invalid access-surface fixture ${name}: expected signer-unavailable response is invalid`);
  }
  const unavailableResponse = expected.sign_event_without_dispatcher.response;
  if (
    unavailableResponse.ok !== false ||
    !isRecord(unavailableResponse.error) ||
    unavailableResponse.error.code !== "signer_route_unavailable" ||
    unavailableResponse.error.retryable !== false
  ) {
    throw new Error(`invalid access-surface fixture ${name}: signer-unavailable response drift`);
  }
}

function validateRouteRefusalError(name: string, label: string, value: unknown, expectedCode: string): void {
  if (!isRecord(value)) {
    throw new Error(`invalid route-refusal contract ${name}: ${label} must be an object`);
  }
  const keys = Object.keys(value).sort();
  if (JSON.stringify(keys) !== JSON.stringify(["error_code", "message", "retryable"])) {
    throw new Error(`invalid route-refusal contract ${name}: ${label} has unsupported fields`);
  }
  if (value.error_code !== expectedCode) {
    throw new Error(`invalid route-refusal contract ${name}: ${label} error_code drift`);
  }
  if (typeof value.message !== "string" || value.message.length === 0) {
    throw new Error(`invalid route-refusal contract ${name}: ${label} message must be non-empty`);
  }
  if (value.retryable !== false) {
    throw new Error(`invalid route-refusal contract ${name}: ${label} must be non-retryable`);
  }
}

export function validateRouteRefusalContractFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) {
    throw new Error(`invalid route-refusal contract ${name}: fixture must be an object`);
  }
  if (fixture.format !== "nsealr-route-refusal-contract-v0") {
    throw new Error(`invalid route-refusal contract ${name}: unsupported format`);
  }
  if (fixture.name !== name) throw new Error(`invalid route-refusal contract ${name}: name mismatch`);
  if (typeof fixture.request_vector !== "string" || !fixture.request_vector.startsWith("examples/")) {
    throw new Error(`invalid route-refusal contract ${name}: request_vector must point under examples`);
  }
  if (!Array.isArray(fixture.cases) || fixture.cases.length === 0) {
    throw new Error(`invalid route-refusal contract ${name}: cases must be non-empty`);
  }
  for (const [index, routeCase] of (fixture.cases as unknown[]).entries()) {
    if (!isRecord(routeCase)) {
      throw new Error(`invalid route-refusal contract ${name}: case ${index} must be an object`);
    }
    if (typeof routeCase.route_selection_vector !== "string" || routeCase.route_selection_vector.length === 0) {
      throw new Error(`invalid route-refusal contract ${name}: case ${index} route_selection_vector is invalid`);
    }
    if (typeof routeCase.route_type !== "string" || typeof routeCase.trusted_review !== "string") {
      throw new Error(`invalid route-refusal contract ${name}: case ${index} route metadata is invalid`);
    }
    if (!isRecord(routeCase.external_review_acknowledgement)) {
      throw new Error(`invalid route-refusal contract ${name}: case ${index} acknowledgement rule is invalid`);
    }
    if (routeCase.external_review_acknowledgement.mode === "required") {
      validateRouteRefusalError(
        name,
        `case ${index} without_dispatcher_after_ack`,
        routeCase.without_dispatcher_after_ack,
        "signer_route_unavailable"
      );
      validateRouteRefusalError(
        name,
        `case ${index} missing_error`,
        routeCase.external_review_acknowledgement.missing_error,
        "external_review_acknowledgement_required"
      );
      validateRouteRefusalError(
        name,
        `case ${index} mismatch_error`,
        routeCase.external_review_acknowledgement.mismatch_error,
        "external_review_acknowledgement_mismatch"
      );
      if ("without_dispatcher" in routeCase) {
        throw new Error(`invalid route-refusal contract ${name}: display-less case ${index} bypasses acknowledgement`);
      }
    } else if (routeCase.external_review_acknowledgement.mode === "unsupported") {
      validateRouteRefusalError(
        name,
        `case ${index} without_dispatcher`,
        routeCase.without_dispatcher,
        "signer_route_unavailable"
      );
      validateRouteRefusalError(
        name,
        `case ${index} unsupported_error`,
        routeCase.external_review_acknowledgement.unsupported_error,
        "external_review_acknowledgement_unsupported"
      );
      if ("without_dispatcher_after_ack" in routeCase) {
        throw new Error(`invalid route-refusal contract ${name}: trusted-review case ${index} uses display-less dispatcher rule`);
      }
    } else {
      throw new Error(`invalid route-refusal contract ${name}: case ${index} acknowledgement mode is unsupported`);
    }
  }
  if (JSON.stringify(fixture.safety) !== JSON.stringify(ROUTE_REFUSAL_SAFETY)) {
    throw new Error(`invalid route-refusal contract ${name}: safety boundary drift`);
  }
  if (
    typeof fixture.scope !== "string" ||
    !fixture.scope.includes("Secretless route-refusal") ||
    !fixture.scope.includes("not a signer family")
  ) {
    throw new Error(`invalid route-refusal contract ${name}: scope drift`);
  }
}

export function validateSourcePublicKeyProofFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid source public-key proof ${name}: fixture must be an object`);
  if (fixture.format !== "nsealr-source-public-key-proof-v0") {
    throw new Error(`invalid source public-key proof ${name}: unsupported format`);
  }
  if (fixture.name !== name) throw new Error(`invalid source public-key proof ${name}: name mismatch`);
  if (fixture.proof_type !== "nip06" && fixture.proof_type !== "nip19_nsec") {
    throw new Error(`invalid source public-key proof ${name}: proof_type is unsupported`);
  }
  if (fixture.source_type !== "bip39_seed" && fixture.source_type !== "nsec") {
    throw new Error(`invalid source public-key proof ${name}: source_type is unsupported`);
  }
  if (fixture.proof_type === "nip06") {
    if (fixture.source_type !== "bip39_seed") {
      throw new Error(`invalid source public-key proof ${name}: NIP-06 proof requires BIP-39 source`);
    }
    if (typeof fixture.account !== "number" || !Number.isInteger(fixture.account) || fixture.account < 0) {
      throw new Error(`invalid source public-key proof ${name}: NIP-06 account must be a non-negative integer`);
    }
    if (typeof fixture.path !== "string" || !fixture.path.startsWith("m/44'/1237'/")) {
      throw new Error(`invalid source public-key proof ${name}: NIP-06 path is invalid`);
    }
    if (typeof fixture.passphrase !== "string") {
      throw new Error(`invalid source public-key proof ${name}: NIP-06 passphrase must be explicit`);
    }
    if (typeof fixture.source_vector !== "string" || !fixture.source_vector.startsWith("vectors/keys/")) {
      throw new Error(`invalid source public-key proof ${name}: NIP-06 source_vector must point to vectors/keys`);
    }
  } else {
    if (fixture.source_type !== "nsec") {
      throw new Error(`invalid source public-key proof ${name}: NIP-19 proof requires nsec source`);
    }
    if ("account" in fixture || "path" in fixture || "passphrase" in fixture) {
      throw new Error(`invalid source public-key proof ${name}: nsec proof must not include NIP-06 fields`);
    }
    if (typeof fixture.source_vector !== "string" || !fixture.source_vector.startsWith("vectors/nip19/")) {
      throw new Error(`invalid source public-key proof ${name}: nsec source_vector must point to vectors/nip19`);
    }
  }
  if (typeof fixture.source_fingerprint !== "string" || !/^[0-9a-f]{16}$/u.test(fixture.source_fingerprint)) {
    throw new Error(`invalid source public-key proof ${name}: source_fingerprint must be 8-byte lowercase hex`);
  }
  if (typeof fixture.expected_public_key !== "string" || !/^[0-9a-f]{64}$/u.test(fixture.expected_public_key)) {
    throw new Error(`invalid source public-key proof ${name}: expected_public_key must be 32-byte lowercase hex`);
  }
  if (typeof fixture.security_scope !== "string" || !fixture.security_scope.includes("RAM-only")) {
    throw new Error(`invalid source public-key proof ${name}: security_scope must describe RAM-only scope`);
  }
  const serialized = JSON.stringify(fixture);
  if (/mnemonic|secret_key|nsec1/u.test(serialized)) {
    throw new Error(`invalid source public-key proof ${name}: proof fixture must not contain source secret material`);
  }
}

function loadJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

function fileStem(file: string): string {
  return file.replace(/\.json$/, "");
}

function validateAccountPolicyReferences(accounts: AccountDescriptor[], policyProfiles: PolicyProfile[]): void {
  const policyById = new Map(policyProfiles.map((policy) => [policy.policy_id, policy]));
  for (const account of accounts) {
    const policy = policyById.get(account.policy_profile_id);
    if (policy === undefined) {
      throw new Error(`invalid account descriptor ${account.account_id}: policy profile not found`);
    }
    if (!policy.route_types.includes(account.signer_route.type)) {
      throw new Error(`invalid account descriptor ${account.account_id}: policy profile does not include signer route type`);
    }
  }
}

export function loadSpecsFixtures(specsRoot: string): SpecsFixtureSet {
  const eventsRoot = resolve(specsRoot, "vectors/events");
  const reviewsRoot = resolve(specsRoot, "vectors/review");
  const reviewScreensRoot = resolve(specsRoot, "vectors/review-screens");
  const reviewDisplayFramesRoot = resolve(specsRoot, "vectors/review-display-frames");
  const reviewDetailPagesRoot = resolve(specsRoot, "vectors/review-detail-pages");
  const reviewTranscriptsRoot = resolve(specsRoot, "vectors/review-transcripts");
  const nip46Root = resolve(specsRoot, "vectors/nip46");
  const nip46PolicyFilesRoot = resolve(specsRoot, "vectors/nip46-policy-files");
  const nip46ConnectionUrisRoot = resolve(specsRoot, "vectors/nip46-connection-uris");
  const nip46ConnectionTokenResponsesRoot = resolve(specsRoot, "vectors/nip46-connection-token-responses");
  const nip46RelayEventsRoot = resolve(specsRoot, "vectors/nip46-relay-events");
  const nip46RelayStepsRoot = resolve(specsRoot, "vectors/nip46-relay-steps");
  const nip46AuthChallengesRoot = resolve(specsRoot, "vectors/nip46-auth-challenges");
  const nip46SessionsRoot = resolve(specsRoot, "vectors/nip46-sessions");
  const nip46SessionGatesRoot = resolve(specsRoot, "vectors/nip46-session-gates");
  const accountsRoot = resolve(specsRoot, "vectors/accounts");
  const policyProfilesRoot = resolve(specsRoot, "vectors/policies");
  const grantsRoot = resolve(specsRoot, "vectors/grants");
  const policyDecisionsRoot = resolve(specsRoot, "vectors/policy-decisions");
  const policyChangesRoot = resolve(specsRoot, "vectors/policy-changes");
  const routeSelectionsRoot = resolve(specsRoot, "vectors/route-selections");
  const routeRefusalsRoot = resolve(specsRoot, "vectors/route-refusals");
  const sourcePublicKeyProofsRoot = resolve(specsRoot, "vectors/source-public-key-proofs");
  const accessSurfacesRoot = resolve(specsRoot, "vectors/access-surfaces");
  const featureMatricesRoot = resolve(specsRoot, "vectors/features");
  const custodyContractsRoot = resolve(specsRoot, "vectors/custody");
  const invalidVectorsRoot = resolve(specsRoot, "vectors/invalid");
  const eventFiles = readdirSync(eventsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const reviewFiles = readdirSync(reviewsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const reviewScreenFiles = readdirSync(reviewScreensRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const reviewDisplayFrameFiles = readdirSync(reviewDisplayFramesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const reviewDetailPageFiles = readdirSync(reviewDetailPagesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const reviewTranscriptFiles = readdirSync(reviewTranscriptsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46Files = readdirSync(nip46Root)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46PolicyFiles = readdirSync(nip46PolicyFilesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46ConnectionUriFiles = readdirSync(nip46ConnectionUrisRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46ConnectionTokenResponseFiles = readdirSync(nip46ConnectionTokenResponsesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46RelayEventFiles = readdirSync(nip46RelayEventsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46RelayStepFiles = readdirSync(nip46RelayStepsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46AuthChallengeFiles = readdirSync(nip46AuthChallengesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46SessionFiles = readdirSync(nip46SessionsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const nip46SessionGateFiles = readdirSync(nip46SessionGatesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const accountFiles = readdirSync(accountsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const policyProfileFiles = readdirSync(policyProfilesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const grantFiles = readdirSync(grantsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const policyDecisionFiles = readdirSync(policyDecisionsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const policyChangeFiles = readdirSync(policyChangesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const routeSelectionFiles = readdirSync(routeSelectionsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const routeRefusalFiles = readdirSync(routeRefusalsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const sourcePublicKeyProofFiles = readdirSync(sourcePublicKeyProofsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const accessSurfaceFiles = readdirSync(accessSurfacesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const featureMatrixFiles = readdirSync(featureMatricesRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const custodyContractFiles = readdirSync(custodyContractsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const invalidVectorFiles = readdirSync(invalidVectorsRoot)
    .filter((file) => file.endsWith(".json"))
    .sort();
  const accounts = accountFiles.map((file) => parseAccountDescriptor(loadJson(resolve(accountsRoot, file))));
  const policyProfiles = policyProfileFiles.map((file) => parsePolicyProfile(loadJson(resolve(policyProfilesRoot, file))));
  const grants = grantFiles.map((file) => parseGrantDescriptor(loadJson(resolve(grantsRoot, file))));
  validateAccountPolicyReferences(accounts, policyProfiles);
  const policyChangeContext = { accounts, policyProfiles, grants };

  return {
    key: loadJson(resolve(specsRoot, "vectors/keys/test-key-1.json")) as SpecsFixtureSet["key"],
    limits: loadJson(resolve(specsRoot, "vectors/limits/nsealr-v0.json")) as SpecsFixtureSet["limits"],
    events: eventFiles.map((file) => loadJson(resolve(eventsRoot, file)) as SpecsFixtureSet["events"][number]),
    reviews: reviewFiles.map((file) => loadJson(resolve(reviewsRoot, file)) as SpecsFixtureSet["reviews"][number]),
    reviewScreens: reviewScreenFiles.map(
      (file) => loadJson(resolve(reviewScreensRoot, file)) as SpecsFixtureSet["reviewScreens"][number]
    ),
    reviewDisplayFrames: reviewDisplayFrameFiles.map(
      (file) => loadJson(resolve(reviewDisplayFramesRoot, file)) as SpecsFixtureSet["reviewDisplayFrames"][number]
    ),
    reviewDetailPages: reviewDetailPageFiles.map(
      (file) => loadJson(resolve(reviewDetailPagesRoot, file)) as SpecsFixtureSet["reviewDetailPages"][number]
    ),
    reviewTranscripts: reviewTranscriptFiles.map(
      (file) => loadJson(resolve(reviewTranscriptsRoot, file)) as SpecsFixtureSet["reviewTranscripts"][number]
    ),
    nip46Payloads: nip46Files.map(
      (file) => loadJson(resolve(nip46Root, file)) as SpecsFixtureSet["nip46Payloads"][number]
    ),
    nip46PolicyFiles: nip46PolicyFiles.map(
      (file) =>
        ({
          ...(loadJson(resolve(nip46PolicyFilesRoot, file)) as Record<string, unknown>),
          name: fileStem(file)
        }) as SpecsFixtureSet["nip46PolicyFiles"][number]
    ),
    nip46ConnectionUris: nip46ConnectionUriFiles.map(
      (file) => loadJson(resolve(nip46ConnectionUrisRoot, file)) as SpecsFixtureSet["nip46ConnectionUris"][number]
    ),
    nip46ConnectionTokenResponses: nip46ConnectionTokenResponseFiles.map(
      (file) =>
        loadJson(resolve(nip46ConnectionTokenResponsesRoot, file)) as SpecsFixtureSet["nip46ConnectionTokenResponses"][number]
    ),
    nip46RelayEvents: nip46RelayEventFiles.map(
      (file) => loadJson(resolve(nip46RelayEventsRoot, file)) as SpecsFixtureSet["nip46RelayEvents"][number]
    ),
    nip46RelaySteps: nip46RelayStepFiles.map(
      (file) => loadJson(resolve(nip46RelayStepsRoot, file)) as SpecsFixtureSet["nip46RelaySteps"][number]
    ),
    nip46AuthChallenges: nip46AuthChallengeFiles.map(
      (file) => loadJson(resolve(nip46AuthChallengesRoot, file)) as SpecsFixtureSet["nip46AuthChallenges"][number]
    ),
    nip46Sessions: nip46SessionFiles.map(
      (file) => loadJson(resolve(nip46SessionsRoot, file)) as SpecsFixtureSet["nip46Sessions"][number]
    ),
    nip46SessionGates: nip46SessionGateFiles.map(
      (file) => loadJson(resolve(nip46SessionGatesRoot, file)) as SpecsFixtureSet["nip46SessionGates"][number]
    ),
    accounts,
    policyProfiles,
    grants,
    policyDecisions: policyDecisionFiles.map(
      (file) => loadJson(resolve(policyDecisionsRoot, file)) as SpecsFixtureSet["policyDecisions"][number]
    ),
    policyChanges: policyChangeFiles.map((file) =>
      parsePolicyChangeReviewVector(loadJson(resolve(policyChangesRoot, file)), policyChangeContext)
    ),
    routeSelections: routeSelectionFiles.map(
      (file) => loadJson(resolve(routeSelectionsRoot, file)) as SpecsFixtureSet["routeSelections"][number]
    ),
    routeRefusals: routeRefusalFiles.map((file) => {
      const fixture = loadJson(resolve(routeRefusalsRoot, file));
      const name = fileStem(file);
      validateRouteRefusalContractFixture(name, fixture);
      return fixture as SpecsFixtureSet["routeRefusals"][number];
    }),
    sourcePublicKeyProofs: sourcePublicKeyProofFiles.map((file) => {
      const fixture = loadJson(resolve(sourcePublicKeyProofsRoot, file));
      const name = fileStem(file);
      validateSourcePublicKeyProofFixture(name, fixture);
      return fixture as SpecsFixtureSet["sourcePublicKeyProofs"][number];
    }),
    accessSurfaces: accessSurfaceFiles.map(
      (file) => loadJson(resolve(accessSurfacesRoot, file)) as SpecsFixtureSet["accessSurfaces"][number]
    ),
    featureMatrices: featureMatrixFiles.map(
      (file) => loadJson(resolve(featureMatricesRoot, file)) as SpecsFixtureSet["featureMatrices"][number]
    ),
    custodyContracts: custodyContractFiles.map((file) => {
      const fixture = loadJson(resolve(custodyContractsRoot, file));
      const name = fileStem(file);
      validatePersistentSecretCustodyFixture(name, fixture);
      return fixture as SpecsFixtureSet["custodyContracts"][number];
    }),
    invalidVectors: invalidVectorFiles.map(
      (file) => loadJson(resolve(invalidVectorsRoot, file)) as SpecsFixtureSet["invalidVectors"][number]
    )
  };
}
