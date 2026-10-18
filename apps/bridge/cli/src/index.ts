#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { Command } from "commander";
import { isDeepStrictEqual } from "node:util";
import { SerialPort } from "serialport";
import {
  appendLocalGrant,
  appendLocalGrantRevocation,
  approveLocalStorageReview,
  approveNativeHostInstallPlan,
  approvePairingIntent,
  buildNativeHostInstallPlan,
  buildNativeHostManifest,
  createLocalGrantStore,
  createLocalStorageReview,
  executeNativeHostInstallApproval,
  LOCAL_CLIENT_SURFACES,
  parseNativeHostInstallApproval,
  parseNativeHostInstallPlan,
  parseLocalGrantStore,
  parseLocalPairingApproval,
  parseLocalStorageApproval,
  parseLocalStorageReview,
  reviewPairingIntent,
  requireLocalStorageApprovalEntry,
  serializeLocalGrantStore,
  type LocalStorageAccessMode,
  type LocalStoragePurpose,
  type LocalClientSurface,
  type NativeHostBrowser
} from "@nsealr/client";
import { verifySignedEventResponse, type SignEventRequest } from "@nsealr/core";
import { devSignRequest, SmartcardSimulator } from "@nsealr/dev-signer";
import {
  loadSpecsFixtures,
  validateAccessSurfaceFixture,
  validateFeatureMatrixFixture,
  validatePersistentSecretCustodyFixture,
  validateRouteRefusalContractFixture,
  validateReviewTranscriptFixture
} from "@nsealr/fixtures";
import { decodeSerialFrame, encodeSerialFrame } from "@nsealr/framing";
import {
  approveNip46AuthChallengeReview,
  approveNip46ConnectReview,
  createNip46SessionLifecycleCheckpoint,
  decideNip46BridgeAction,
  evaluateNip46RelayRequestStep,
  evaluateNip46RelayResponseStep,
  evaluateNip46SessionRequestGate,
  isNip46RequestPermitted,
  nip46PermissionRequirementFromRequest,
  nip46ResponseFromNSealr,
  nsealrRequestFromNip46,
  parseNip46ApprovedPermissions,
  parseNip46ConnectionUri,
  parseNip46ConnectIntent,
  parseNip46PolicyFile,
  parseNip46Permissions,
  parseNip46RelayEventEnvelope,
  parseNip46SessionActive,
  parseNip46SessionLifecycle,
  reviewNip46AuthChallengeStep,
  reviewNip46ConnectMessage,
  verifyNip46ConnectionTokenResponse,
  type Nip46Permission,
  respondToLocalNip46Request
} from "@nsealr/nip46";
import {
  decidePolicyRequest,
  reviewPolicyChangeProposal,
  selectAccountRoute
} from "@nsealr/policy";
import { validateRequest, validateResponse } from "@nsealr/protocol";
import {
  decodeAnimatedQrEnvelopeFrames,
  decodeQrEnvelope,
  encodeAnimatedQrEnvelopeFrames,
  encodeQrEnvelope
} from "@nsealr/qr";
import {
  REVIEW_DETAIL_BODY_LINE_STYLES as REVIEW_DETAIL_BODY_LINE_STYLE_VALUES,
  renderReviewDetailPages,
  reviewEventTemplate,
  screenReviewForRequest,
  type ReviewDetailPageLimits
} from "@nsealr/review";
import { SmartcardSigner } from "@nsealr/smartcard";
import {
  SerialLineStreamPort,
  exchangeSerialLineRequest,
  type SerialLinePort,
  type SerialLinePortOpener
} from "@nsealr/transport";

type DataFormat = "json" | "qr" | "qr-animated";

type BuildCliOptions = {
  openSerialLinePort?: SerialLinePortOpener;
};

type ErrorOutput = {
  write(message: string): unknown;
};

const DEFAULT_REVIEW_DETAIL_PAGE_LIMITS: ReviewDetailPageLimits = {
  max_title_chars: 18,
  max_body_lines: 5,
  max_line_chars: 26,
  max_compact_body_lines: 9,
  max_compact_line_chars: 48
};
const REVIEW_DETAIL_BODY_LINE_STYLES = new Set<string>(REVIEW_DETAIL_BODY_LINE_STYLE_VALUES);

const PARAMETERLESS_REQUEST_METHODS: Record<string, { protocolMethod: string; defaultRequestId: string }> = {
  capabilities: { protocolMethod: "get_capabilities", defaultRequestId: "req-capabilities-1" },
  "get-capabilities": { protocolMethod: "get_capabilities", defaultRequestId: "req-capabilities-1" },
  pubkey: { protocolMethod: "get_public_key", defaultRequestId: "req-pubkey-1" },
  "get-public-key": { protocolMethod: "get_public_key", defaultRequestId: "req-public-key-1" },
  "signing-status": { protocolMethod: "get_signing_status", defaultRequestId: "req-signing-status-1" },
  "get-signing-status": { protocolMethod: "get_signing_status", defaultRequestId: "req-signing-status-1" }
};

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf8"));
}

function writeJson(path: string, value: unknown): void {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function writeNewJson(path: string, value: unknown): void {
  writeNewText(path, `${JSON.stringify(value, null, 2)}\n`);
}

function writeNewText(path: string, contents: string): void {
  if (existsSync(path)) throw new Error("output path already exists");
  writeFileSync(path, contents, { encoding: "utf8", flag: "wx" });
}

function assertFormat(format: string): asserts format is DataFormat {
  if (format !== "json" && format !== "qr" && format !== "qr-animated") {
    throw new Error(`unsupported format: ${format}`);
  }
}

function optionalAuthorPubkey(value: string | undefined): string | undefined {
  if (value === undefined) return undefined;
  if (!/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error("author pubkey must be 32-byte lowercase hex");
  }
  return value;
}

function positiveIntegerOption(value: string | undefined, fallback: number, optionName: string): number {
  if (value === undefined) return fallback;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    throw new Error(`${optionName} must be a positive integer`);
  }
  return parsed;
}

function nonNegativeIntegerOption(value: string, optionName: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`${optionName} must be a non-negative integer`);
  }
  return parsed;
}

function lowerHex64Option(value: string, optionName: string): string {
  if (!/^[0-9a-f]{64}$/u.test(value)) {
    throw new Error(`${optionName} must be 32-byte lowercase hex`);
  }
  return value;
}

function localClientSurfaceOption(value: string, optionName: string): LocalClientSurface {
  if (!LOCAL_CLIENT_SURFACES.includes(value as LocalClientSurface)) {
    throw new Error(`${optionName} is unsupported`);
  }
  return value as LocalClientSurface;
}

function nativeHostBrowserOption(value: string, optionName: string): NativeHostBrowser {
  if (value !== "chromium" && value !== "firefox") {
    throw new Error(`${optionName} must be chromium or firefox`);
  }
  return value;
}

function addLocalStorageEntry(
  entries: unknown[],
  purpose: LocalStoragePurpose,
  access: LocalStorageAccessMode,
  path: string | undefined
): void {
  if (path === undefined) return;
  entries.push({
    purpose,
    path,
    access,
    contains_secret_material: false
  });
}

function singleValueOption(optionName: string): (value: string, previous: string | undefined) => string {
  return (value: string, previous: string | undefined): string => {
    if (previous !== undefined) {
      throw new Error(`${optionName} is duplicated`);
    }
    return value;
  };
}

function appendPathOption(value: string, previous: string[]): string[] {
  return [...previous, value];
}

function requireGrantStoreStorageApproval(options: {
  storageApproval: string;
  out: string;
  grantStore?: string;
}): void {
  const approval = parseLocalStorageApproval(readJson(options.storageApproval));
  requireLocalStorageApprovalEntry(approval, {
    purpose: "grant_store",
    path: options.out,
    access: "write_new"
  });
  if (options.grantStore !== undefined) {
    requireLocalStorageApprovalEntry(approval, {
      purpose: "grant_store",
      path: options.grantStore,
      access: "read_only"
    });
  }
}

function reviewDetailPageLimitsFromOptions(options: {
  maxTitleChars?: string;
  maxBodyLines?: string;
  maxLineChars?: string;
  maxCompactBodyLines?: string;
  maxCompactLineChars?: string;
}): ReviewDetailPageLimits {
  return {
    max_title_chars: positiveIntegerOption(
      options.maxTitleChars,
      DEFAULT_REVIEW_DETAIL_PAGE_LIMITS.max_title_chars,
      "--max-title-chars"
    ),
    max_body_lines: positiveIntegerOption(
      options.maxBodyLines,
      DEFAULT_REVIEW_DETAIL_PAGE_LIMITS.max_body_lines,
      "--max-body-lines"
    ),
    max_line_chars: positiveIntegerOption(
      options.maxLineChars,
      DEFAULT_REVIEW_DETAIL_PAGE_LIMITS.max_line_chars,
      "--max-line-chars"
    ),
    max_compact_body_lines: positiveIntegerOption(
      options.maxCompactBodyLines,
      DEFAULT_REVIEW_DETAIL_PAGE_LIMITS.max_compact_body_lines,
      "--max-compact-body-lines"
    ),
    max_compact_line_chars: positiveIntegerOption(
      options.maxCompactLineChars,
      DEFAULT_REVIEW_DETAIL_PAGE_LIMITS.max_compact_line_chars,
      "--max-compact-line-chars"
    )
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readNip46PolicyPermissions(path: string): Nip46Permission[] {
  return parseNip46PolicyFile(readJson(path));
}

function requirePositiveIntegerField(record: Record<string, unknown>, fixtureName: string, field: string): number {
  const value = record[field];
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`invalid review display-frame fixture ${fixtureName}: ${field} must be a positive integer`);
  }
  return value;
}

function validateReviewDisplayFrameFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid review display-frame fixture ${name}: fixture must be an object`);
  if (fixture.format !== "review-display-frame-v0") {
    throw new Error(`invalid review display-frame fixture ${name}: unsupported format`);
  }
  if (typeof fixture.source_review_vector !== "string" || fixture.source_review_vector.length === 0) {
    throw new Error(`invalid review display-frame fixture ${name}: source_review_vector must be a string`);
  }
  if (typeof fixture.page_index !== "number" || !Number.isInteger(fixture.page_index) || fixture.page_index < 0) {
    throw new Error(`invalid review display-frame fixture ${name}: page_index must be a non-negative integer`);
  }
  if (!isRecord(fixture.limits)) {
    throw new Error(`invalid review display-frame fixture ${name}: limits must be an object`);
  }
  const limits = fixture.limits;
  const maxTitleChars = requirePositiveIntegerField(limits, name, "max_title_chars");
  const maxBodyLines = requirePositiveIntegerField(limits, name, "max_body_lines");
  const maxLineChars = requirePositiveIntegerField(limits, name, "max_line_chars");
  if (!isRecord(fixture.frame)) {
    throw new Error(`invalid review display-frame fixture ${name}: frame must be an object`);
  }
  const frame = fixture.frame;
  if (typeof frame.title !== "string") {
    throw new Error(`invalid review display-frame fixture ${name}: frame must include title`);
  }
  if (typeof frame.page_indicator !== "string") {
    throw new Error(`invalid review display-frame fixture ${name}: frame must include page_indicator`);
  }
  if (!Array.isArray(frame.body_lines) || !frame.body_lines.every((line) => typeof line === "string")) {
    throw new Error(`invalid review display-frame fixture ${name}: frame body_lines must be strings`);
  }
  const bodyLines = frame.body_lines;
  if (typeof frame.action_hint !== "string") {
    throw new Error(`invalid review display-frame fixture ${name}: frame must include action_hint`);
  }
  if (frame.title.length > maxTitleChars) {
    throw new Error(`invalid review display-frame fixture ${name}: title exceeds max_title_chars`);
  }
  if (bodyLines.length > maxBodyLines) {
    throw new Error(`invalid review display-frame fixture ${name}: body_lines exceeds max_body_lines`);
  }
  if (bodyLines.some((line) => line.length > maxLineChars)) {
    throw new Error(`invalid review display-frame fixture ${name}: body line exceeds max_line_chars`);
  }
}

function validateReviewDetailPageFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid review detail-page fixture ${name}: fixture must be an object`);
  if (fixture.format !== "review-detail-pages-v0") {
    throw new Error(`invalid review detail-page fixture ${name}: unsupported format`);
  }
  if (fixture.display_profile !== "ascii-safe-codepoint-fallback-v0") {
    throw new Error(`invalid review detail-page fixture ${name}: unsupported display_profile`);
  }
  if (typeof fixture.source_review_vector !== "string" || fixture.source_review_vector.length === 0) {
    throw new Error(`invalid review detail-page fixture ${name}: source_review_vector must be a string`);
  }
  if (
    typeof fixture.approval_digest !== "string" ||
    !/^[0-9a-f]{64}$/.test(fixture.approval_digest)
  ) {
    throw new Error(`invalid review detail-page fixture ${name}: approval_digest must be 32-byte lowercase hex`);
  }
  if (!isRecord(fixture.limits)) {
    throw new Error(`invalid review detail-page fixture ${name}: limits must be an object`);
  }
  const limits = fixture.limits;
  const maxTitleChars = requirePositiveIntegerField(limits, name, "max_title_chars");
  const maxBodyLines = requirePositiveIntegerField(limits, name, "max_body_lines");
  requirePositiveIntegerField(limits, name, "max_line_chars");
  const maxCompactBodyLines = requirePositiveIntegerField(limits, name, "max_compact_body_lines");
  const maxCompactLineChars = requirePositiveIntegerField(limits, name, "max_compact_line_chars");
  if (!Array.isArray(fixture.pages) || fixture.pages.length === 0) {
    throw new Error(`invalid review detail-page fixture ${name}: pages must be a non-empty array`);
  }
  for (const [index, page] of fixture.pages.entries()) {
    if (!isRecord(page)) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} must be an object`);
    }
    if (typeof page.title !== "string" || page.title.length > maxTitleChars) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} title is invalid`);
    }
    if (typeof page.page_indicator !== "string" || page.page_indicator.length === 0) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} page_indicator is invalid`);
    }
    if (page.action !== "next" && page.action !== "approve_or_reject") {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} action is invalid`);
    }
    if (!Array.isArray(page.lines) || !page.lines.every((line) => typeof line === "string")) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} lines must be strings`);
    }
    if (
      !Array.isArray(page.body_line_styles) ||
      (page.body_line_styles.length !== 0 && page.body_line_styles.length !== page.lines.length)
    ) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} body_line_styles mismatch`);
    }
    for (const [styleIndex, style] of page.body_line_styles.entries()) {
      if (!REVIEW_DETAIL_BODY_LINE_STYLES.has(String(style))) {
        throw new Error(`invalid review detail-page fixture ${name}: page ${index} body_line_styles contains invalid style`);
      }
      if (String(page.lines[styleIndex]).startsWith("  ") && style !== "value") {
        throw new Error(`invalid review detail-page fixture ${name}: page ${index} continuation lines must use value style`);
      }
    }
    const usesCompactBody = page.body_line_styles.length > 0;
    const maxLines = usesCompactBody ? maxCompactBodyLines : maxBodyLines;
    if (page.lines.length > maxLines) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} lines exceed display limit`);
    }
    if (usesCompactBody && page.lines.some((line) => line.length > maxCompactLineChars)) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} line exceeds display limit`);
    }
    if (typeof page.logical_page_id !== "string" || page.logical_page_id.length === 0) {
      throw new Error(`invalid review detail-page fixture ${name}: page ${index} logical_page_id is invalid`);
    }
  }
}

function assertJsonEqual(actual: unknown, expected: unknown, error: string): void {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(error);
  }
}

function validateNip46PermissionPolicyFixture(name: string, fixture: Record<string, unknown>): void {
  assertJsonEqual(
    nip46PermissionRequirementFromRequest(fixture.request_message),
    fixture.permission_requirement,
    `invalid NIP-46 fixture ${name}: permission requirement mismatch`
  );
  if (!Array.isArray(fixture.permission_checks) || fixture.permission_checks.length === 0) {
    throw new Error(`invalid NIP-46 fixture ${name}: permission checks must be a non-empty array`);
  }
  for (const [index, check] of fixture.permission_checks.entries()) {
    if (!isRecord(check) || !Array.isArray(check.granted_permissions)) {
      throw new Error(`invalid NIP-46 fixture ${name}: permission check ${index} must include granted permissions`);
    }
    const grantedPermissions = check.granted_permissions as Nip46Permission[];
    if (check.permitted !== isNip46RequestPermitted(fixture.request_message, grantedPermissions)) {
      throw new Error(`invalid NIP-46 fixture ${name}: permission check mismatch at ${index}`);
    }
  }
}

function validateNip46BridgeDecisionFixtures(name: string, fixture: Record<string, unknown>): void {
  if (!Array.isArray(fixture.bridge_decisions) || fixture.bridge_decisions.length === 0) {
    throw new Error(`invalid NIP-46 fixture ${name}: bridge decisions must be a non-empty array`);
  }
  for (const [index, check] of fixture.bridge_decisions.entries()) {
    if (!isRecord(check) || !Array.isArray(check.granted_permissions)) {
      throw new Error(`invalid NIP-46 fixture ${name}: bridge decision ${index} must include granted permissions`);
    }
    assertJsonEqual(
      decideNip46BridgeAction(fixture.request_message, check.granted_permissions as Nip46Permission[]),
      check.decision,
      `invalid NIP-46 fixture ${name}: bridge decision mismatch at ${index}`
    );
  }
}

function validateNip46PayloadFixture(name: string, fixture: unknown): void {
  if (!isRecord(fixture)) throw new Error(`invalid NIP-46 fixture ${name}: fixture must be an object`);
  if (fixture.format !== "nip46-decrypted-payload-v0") {
    throw new Error(`invalid NIP-46 fixture ${name}: unsupported format`);
  }
  if (!isRecord(fixture.request_message)) {
    throw new Error(`invalid NIP-46 fixture ${name}: request_message must be an object`);
  }
  validateNip46BridgeDecisionFixtures(name, fixture);
  if (fixture.request_message.method === "ping" || fixture.request_message.method === "switch_relays") {
    validateNip46PermissionPolicyFixture(name, fixture);
    assertJsonEqual(
      respondToLocalNip46Request(fixture.request_message),
      fixture.local_response_message,
      `invalid NIP-46 fixture ${name}: local response mismatch`
    );
    return;
  }
  if (fixture.request_message.method === "connect") {
    if ("permission_requirement" in fixture || "permission_checks" in fixture) {
      throw new Error(`invalid NIP-46 fixture ${name}: connect must not include permission policy`);
    }
    assertJsonEqual(
      parseNip46ConnectIntent(fixture.request_message),
      fixture.connect_intent,
      `invalid NIP-46 fixture ${name}: connect intent mismatch`
    );
    assertJsonEqual(
      reviewNip46ConnectMessage(fixture.request_message),
      fixture.connect_review,
      `invalid NIP-46 fixture ${name}: connect review mismatch`
    );
    if (!isRecord(fixture.connect_review) || !isRecord(fixture.connect_approval)) {
      throw new Error(`invalid NIP-46 fixture ${name}: connect must include review and approval artifacts`);
    }
    assertJsonEqual(
      approveNip46ConnectReview(fixture.connect_review, {
        reviewedConnectDigest: String(fixture.connect_review.connect_digest),
        approvedAt: Number(fixture.connect_approval.approved_at)
      }),
      fixture.connect_approval,
      `invalid NIP-46 fixture ${name}: connect approval mismatch`
    );
    return;
  }
  validateNip46PermissionPolicyFixture(name, fixture);
  assertJsonEqual(
    nsealrRequestFromNip46(fixture.request_message),
    fixture.nsealr_request,
    `invalid NIP-46 fixture ${name}: nSealr request mismatch`
  );
  assertJsonEqual(
    nip46ResponseFromNSealr(String(fixture.request_message.id), fixture.nsealr_response),
    fixture.response_message,
    `invalid NIP-46 fixture ${name}: response message mismatch`
  );
}

function validateNip46PolicyFileFixture(name: string, fixture: unknown): void {
  parseNip46PolicyFile(fixture, `invalid NIP-46 policy-file fixture ${name}`);
}

function expectFixtureRejection(name: string, expectedError: string, action: () => void): void {
  try {
    action();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!message.includes(expectedError)) {
      throw new Error(`invalid hardening fixture ${name}: expected ${expectedError}, got ${message}`);
    }
    return;
  }
  throw new Error(`invalid hardening fixture ${name}: unexpectedly accepted`);
}

function validateInvalidHardeningFixture(fixture: {
  name: string;
  category: string;
  expected_error: string;
  request?: unknown;
  response?: unknown;
  envelope?: string;
  frame?: string;
  request_message?: unknown;
  uri?: string;
  relay_event?: unknown;
  relay_step?: unknown;
  connection_token_response?: unknown;
  session?: unknown;
  session_gate?: unknown;
  policy_file?: unknown;
}): void {
  if (fixture.category === "signing-request") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      const result = validateRequest(fixture.request);
      if (!result.ok) throw new Error(result.error);
    });
    return;
  }
  if (fixture.category === "response") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      const result = validateResponse(fixture.response);
      if (!result.ok) throw new Error(result.error);
    });
    return;
  }
  if (fixture.category === "qr-envelope") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      decodeQrEnvelope(String(fixture.envelope));
    });
    return;
  }
  if (fixture.category === "serial-frame") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      const frame = decodeSerialFrame(String(fixture.frame));
      if (frame.type === "request") {
        const result = validateRequest(frame.payload);
        if (!result.ok) throw new Error(result.error);
      }
      if (frame.type === "response") {
        const result = validateResponse(frame.payload);
        if (!result.ok) throw new Error(result.error);
      }
    });
    return;
  }
  if (fixture.category === "nip46") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      decideNip46BridgeAction(fixture.request_message, []);
    });
    return;
  }
  if (fixture.category === "nip46-connection-uri") {
    if (typeof fixture.uri !== "string") {
      throw new Error(`invalid hardening fixture ${fixture.name}: uri must be a string`);
    }
    const uri = fixture.uri;
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      parseNip46ConnectionUri(uri);
    });
    return;
  }
  if (fixture.category === "nip46-connection-token-response") {
    const tokenResponse = fixture.connection_token_response;
    if (!isRecord(tokenResponse) || typeof tokenResponse.connection_uri !== "string") {
      throw new Error(`invalid hardening fixture ${fixture.name}: connection_token_response must include connection_uri`);
    }
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      verifyNip46ConnectionTokenResponse({
        connectionUri: tokenResponse.connection_uri,
        responseStep: tokenResponse.response_step
      });
    });
    return;
  }
  if (fixture.category === "nip46-relay-event") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      parseNip46RelayEventEnvelope(fixture.relay_event, "client_to_remote_signer");
    });
    return;
  }
  if (fixture.category === "nip46-relay-step") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      const relayStep = fixture.relay_step;
      if (isRecord(relayStep) && relayStep.format === "nsealr-nip46-relay-response-step-v1") {
        evaluateNip46RelayResponseStep(relayStep);
        return;
      }
      evaluateNip46RelayRequestStep(relayStep);
    });
    return;
  }
  if (fixture.category === "nip46-session") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      parseNip46SessionLifecycle(fixture.session);
    });
    return;
  }
  if (fixture.category === "nip46-session-active") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      parseNip46SessionActive(fixture.session);
    });
    return;
  }
  if (fixture.category === "nip46-session-gate") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      evaluateNip46SessionRequestGate(fixture.session_gate);
    });
    return;
  }
  if (fixture.category === "nip46-policy-file") {
    expectFixtureRejection(fixture.name, fixture.expected_error, () => {
      parseNip46PolicyFile(fixture.policy_file);
    });
    return;
  }
  throw new Error(`invalid hardening fixture ${fixture.name}: unsupported category ${fixture.category}`);
}

function readValue(path: string, format: DataFormat): unknown {
  if (format === "qr") return decodeQrEnvelope(readFileSync(path, "utf8").trim());
  if (format === "qr-animated") {
    const frames = readFileSync(path, "utf8")
      .trim()
      .split(/\n/u)
      .filter((line) => line.length > 0);
    return decodeAnimatedQrEnvelopeFrames(frames);
  }
  return readJson(path);
}

function writeValue(path: string, value: unknown, format: DataFormat): void {
  if (format === "qr") {
    writeFileSync(path, `${encodeQrEnvelope(value)}\n`, "utf8");
    return;
  }
  if (format === "qr-animated") {
    writeFileSync(path, `${encodeAnimatedQrEnvelopeFrames(value).join("\n")}\n`, "utf8");
    return;
  }
  writeJson(path, value);
}

function assertResponseForRequest(request: unknown, response: unknown, label: string): void {
  const requestShape = validateRequest(request);
  if (!requestShape.ok) throw new Error(requestShape.error);
  const responseShape = validateResponse(response);
  if (!responseShape.ok) throw new Error(responseShape.error);
  if ((response as { request_id?: unknown }).request_id !== (request as { request_id?: unknown }).request_id) {
    throw new Error(`${label} request_id does not match request`);
  }
  if ((response as { ok?: boolean }).ok === true && (request as { method?: string }).method === "sign_event") {
    const result = verifySignedEventResponse(request, response);
    if (!result.ok) {
      throw new Error(label === "response" ? result.error : `${label} ${result.error}`);
    }
  }
}

function fixtureCountLabel(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

async function openNodeSerialLinePort(path: string): Promise<SerialLinePort> {
  const serialPort = new SerialPort({ path, baudRate: 115_200, autoOpen: false });
  await new Promise<void>((resolve, reject) => {
    serialPort.open((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
  return new SerialLineStreamPort({ input: serialPort, output: serialPort });
}

export function buildCli(options: BuildCliOptions = {}): Command {
  const openSerialLinePort = options.openSerialLinePort ?? openNodeSerialLinePort;
  const program = new Command();
  program.name("nsealr").description("nSealr companion CLI").version("0.1.0");

  program
    .command("fixture")
    .argument("<action>")
    .requiredOption("--specs <path>")
    .description("Verify shared specs fixtures")
    .action((action: string, options: { specs: string }) => {
      if (action !== "verify") throw new Error(`unsupported fixture action: ${action}`);
      const fixtures = loadSpecsFixtures(options.specs);
      for (const event of fixtures.events) {
        const response = event.response as unknown;
        const request = event.request as unknown;
        const shape = validateResponse(response);
        if (!shape.ok) throw new Error(`invalid response fixture ${event.name}: ${shape.error}`);
        const verification = verifySignedEventResponse(request, response);
        if (!verification.ok) throw new Error(`invalid event fixture ${event.name}: ${verification.error}`);
      }
      for (const review of fixtures.reviews) {
        const request = review.request as { params?: { event_template?: unknown } };
        const requestShape = validateRequest(request);
        if (!requestShape.ok) throw new Error(`invalid review request fixture ${review.name}: ${requestShape.error}`);
        const actual = reviewEventTemplate(request.params?.event_template);
        if (JSON.stringify(actual) !== JSON.stringify(review.review)) {
          throw new Error(`invalid review fixture ${review.name}: review output mismatch`);
        }
      }
      for (const reviewScreen of fixtures.reviewScreens) {
        const requestShape = validateRequest(reviewScreen.request);
        if (!requestShape.ok) throw new Error(`invalid review-screen request fixture ${reviewScreen.name}: ${requestShape.error}`);
        const actual = screenReviewForRequest(reviewScreen.request);
        if (JSON.stringify(actual) !== JSON.stringify(reviewScreen.screen_review)) {
          throw new Error(`invalid review-screen fixture ${reviewScreen.name}: screen_review output mismatch`);
        }
      }
      for (const transcript of fixtures.reviewTranscripts) {
        validateReviewTranscriptFixture(transcript.name, transcript);
      }
      for (const displayFrame of fixtures.reviewDisplayFrames) {
        validateReviewDisplayFrameFixture(displayFrame.name, displayFrame);
      }
      for (const detailPages of fixtures.reviewDetailPages) {
        validateReviewDetailPageFixture(detailPages.name, detailPages);
      }
      for (const nip46Payload of fixtures.nip46Payloads) {
        validateNip46PayloadFixture(nip46Payload.name, nip46Payload);
      }
      for (const nip46PolicyFile of fixtures.nip46PolicyFiles) {
        validateNip46PolicyFileFixture(nip46PolicyFile.name, nip46PolicyFile);
      }
      for (const account of fixtures.accounts) {
        if (account.signer_route.type.endsWith("_qr_vault") && account.capabilities.persistent_grants !== false) {
          throw new Error(`invalid account descriptor ${account.account_id}: QR vaults must not support persistent grants`);
        }
      }
      for (const policy of fixtures.policyProfiles) {
        if (policy.route_types.some((route) => route.endsWith("_qr_vault")) && policy.grants_allowed) {
          throw new Error(`invalid policy profile ${policy.policy_id}: QR vault policies must not allow grants`);
        }
        if (policy.route_types.includes("external_nip46") && policy.grants_allowed) {
          throw new Error(`invalid policy profile ${policy.policy_id}: external NIP-46 policies must not allow nSealr grants`);
        }
      }
      for (const grant of fixtures.grants) {
        if (!["esp32_usb_nip46", "custom_hardware_wallet"].includes(grant.route_type)) {
          throw new Error(`invalid grant descriptor ${grant.grant_id}: grants require nSealr persistent policy routes`);
        }
      }
      for (const policyDecision of fixtures.policyDecisions) {
        const policy = fixtures.policyProfiles.find((candidate) => candidate.policy_id === policyDecision.policy_profile_id);
        if (policy === undefined) {
          throw new Error(`invalid policy decision fixture ${policyDecision.name}: policy profile not found`);
        }
        const actual = decidePolicyRequest({
          policy,
          grants: fixtures.grants,
          request: policyDecision.request
        });
        if (JSON.stringify(actual) !== JSON.stringify(policyDecision.decision)) {
          throw new Error(`invalid policy decision fixture ${policyDecision.name}: policy decision mismatch`);
        }
      }
      for (const policyChange of fixtures.policyChanges) {
        const actual = reviewPolicyChangeProposal(policyChange.proposal, {
          accounts: fixtures.accounts,
          policyProfiles: fixtures.policyProfiles,
          grants: fixtures.grants
        });
        if (JSON.stringify(actual) !== JSON.stringify(policyChange.review)) {
          throw new Error(`invalid policy change fixture ${policyChange.name}: policy change review mismatch`);
        }
      }
      for (const routeSelection of fixtures.routeSelections) {
        const actual = selectAccountRoute(fixtures.accounts, routeSelection.request);
        if (JSON.stringify(actual) !== JSON.stringify(routeSelection.selection)) {
          throw new Error(`invalid route selection fixture ${routeSelection.name}: route selection mismatch`);
        }
      }
      for (const accessSurface of fixtures.accessSurfaces) {
        validateAccessSurfaceFixture(accessSurface.name, accessSurface);
      }
      for (const routeRefusal of fixtures.routeRefusals) {
        validateRouteRefusalContractFixture(routeRefusal.name, routeRefusal);
      }
      for (const connectionUri of fixtures.nip46ConnectionUris) {
        const actual = parseNip46ConnectionUri(connectionUri.uri);
        if (JSON.stringify(actual) !== JSON.stringify(connectionUri.expected_descriptor)) {
          throw new Error(`invalid NIP-46 connection URI fixture ${connectionUri.name}: descriptor mismatch`);
        }
        if (JSON.stringify(actual).includes(connectionUri.secret_probe)) {
          throw new Error(`invalid NIP-46 connection URI fixture ${connectionUri.name}: secret echo`);
        }
      }
      for (const tokenResponse of fixtures.nip46ConnectionTokenResponses) {
        const sourceToken = fixtures.nip46ConnectionUris.find(
          (connectionUri) => `vectors/nip46-connection-uris/${connectionUri.name}.json` === tokenResponse.source_connection_uri_vector
        );
        if (sourceToken === undefined) {
          throw new Error(`invalid NIP-46 connection token response fixture ${tokenResponse.name}: source token missing`);
        }
        const actual = verifyNip46ConnectionTokenResponse({
          connectionUri: sourceToken.uri,
          responseStep: tokenResponse.response_step
        });
        if (JSON.stringify(actual) !== JSON.stringify(tokenResponse.expected_response)) {
          throw new Error(`invalid NIP-46 connection token response fixture ${tokenResponse.name}: response mismatch`);
        }
        if (JSON.stringify(actual).includes(sourceToken.secret_probe)) {
          throw new Error(`invalid NIP-46 connection token response fixture ${tokenResponse.name}: secret echo`);
        }
      }
      for (const relayEvent of fixtures.nip46RelayEvents) {
        const actual = parseNip46RelayEventEnvelope(relayEvent.event, relayEvent.direction);
        if (JSON.stringify(actual) !== JSON.stringify(relayEvent.expected_envelope)) {
          throw new Error(`invalid NIP-46 relay event fixture ${relayEvent.name}: envelope mismatch`);
        }
      }
      for (const relayStep of fixtures.nip46RelaySteps) {
        const actual = relayStep.format === "nsealr-nip46-relay-response-step-v1"
          ? evaluateNip46RelayResponseStep(relayStep)
          : evaluateNip46RelayRequestStep(relayStep);
        if (!isDeepStrictEqual(actual, relayStep.expected_step)) {
          throw new Error(`invalid NIP-46 relay step fixture ${relayStep.name}: step mismatch`);
        }
      }
      for (const authChallenge of fixtures.nip46AuthChallenges) {
        const sourceStep = fixtures.nip46RelaySteps.find(
          (relayStep) => `vectors/nip46-relay-steps/${relayStep.name}.json` === authChallenge.source_relay_step_vector
        );
        if (sourceStep === undefined) {
          throw new Error(`invalid NIP-46 auth challenge fixture ${authChallenge.name}: source relay step missing`);
        }
        const review = reviewNip46AuthChallengeStep(sourceStep);
        if (JSON.stringify(review) !== JSON.stringify(authChallenge.review)) {
          throw new Error(`invalid NIP-46 auth challenge fixture ${authChallenge.name}: review mismatch`);
        }
        const expectedReview = authChallenge.review as { auth_challenge_digest?: unknown };
        const expectedApproval = authChallenge.approval as { approved_at?: unknown };
        const approval = approveNip46AuthChallengeReview(authChallenge.review, {
          reviewedAuthChallengeDigest: String(expectedReview.auth_challenge_digest),
          approvedAt: Number(expectedApproval.approved_at)
        });
        if (JSON.stringify(approval) !== JSON.stringify(authChallenge.approval)) {
          throw new Error(`invalid NIP-46 auth challenge fixture ${authChallenge.name}: approval mismatch`);
        }
      }
      for (const session of fixtures.nip46Sessions) {
        const actual = parseNip46SessionLifecycle(session.session);
        if (JSON.stringify(actual) !== JSON.stringify(session.session)) {
          throw new Error(`invalid NIP-46 session fixture ${session.name}: session mismatch`);
        }
      }
      for (const gate of fixtures.nip46SessionGates) {
        const sourceSession = fixtures.nip46Sessions.find(
          (session) => `vectors/nip46-sessions/${session.name}.json` === gate.source_session_vector
        );
        if (sourceSession === undefined) {
          throw new Error(`invalid NIP-46 session gate fixture ${gate.name}: source session missing`);
        }
        const actual = evaluateNip46SessionRequestGate({
          format: gate.format,
          session: sourceSession.session,
          evaluated_at: gate.evaluated_at,
          direction: gate.direction,
          event: gate.event,
          decrypted_message: gate.decrypted_message
        });
        if (JSON.stringify(actual) !== JSON.stringify(gate.expected_gate)) {
          throw new Error(`invalid NIP-46 session gate fixture ${gate.name}: gate mismatch`);
        }
      }
      for (const featureMatrix of fixtures.featureMatrices) {
        validateFeatureMatrixFixture(featureMatrix.name, featureMatrix);
      }
      for (const custodyContract of fixtures.custodyContracts) {
        validatePersistentSecretCustodyFixture(custodyContract.name, custodyContract);
      }
      for (const invalidVector of fixtures.invalidVectors) {
        validateInvalidHardeningFixture(invalidVector);
      }
      const policyFileFixtureLabel =
        fixtureCountLabel(fixtures.nip46PolicyFiles.length, "NIP-46 policy-file fixture");
      const connectionUriFixtureLabel =
        fixtureCountLabel(fixtures.nip46ConnectionUris.length, "NIP-46 connection URI fixture");
      const connectionTokenResponseFixtureLabel =
        fixtureCountLabel(fixtures.nip46ConnectionTokenResponses.length, "NIP-46 connection token response fixture");
      const relayEventFixtureLabel =
        fixtureCountLabel(fixtures.nip46RelayEvents.length, "NIP-46 relay event fixture");
      const relayStepFixtureLabel =
        fixtureCountLabel(fixtures.nip46RelaySteps.length, "NIP-46 relay step fixture");
      const authChallengeFixtureLabel =
        fixtureCountLabel(fixtures.nip46AuthChallenges.length, "NIP-46 auth challenge fixture");
      const sessionFixtureLabel =
        fixtureCountLabel(fixtures.nip46Sessions.length, "NIP-46 session fixture");
      const sessionGateFixtureLabel =
        fixtureCountLabel(fixtures.nip46SessionGates.length, "NIP-46 session gate fixture");
      const routeRefusalFixtureLabel =
        fixtureCountLabel(fixtures.routeRefusals.length, "route-refusal contract");
      const custodyContractFixtureLabel =
        fixtureCountLabel(fixtures.custodyContracts.length, "persistent-secret custody contract");
      console.log(
        `verified ${fixtureCountLabel(fixtures.events.length, "event fixture")}, ${fixtureCountLabel(fixtures.reviews.length, "review fixture")}, ${fixtureCountLabel(fixtures.reviewScreens.length, "review-screen fixture")}, ${fixtureCountLabel(fixtures.reviewDisplayFrames.length, "review display-frame fixture")}, ${fixtureCountLabel(fixtures.reviewDetailPages.length, "review detail-page fixture")}, ${fixtureCountLabel(fixtures.reviewTranscripts.length, "review transcript fixture")}, ${fixtureCountLabel(fixtures.nip46Payloads.length, "NIP-46 payload fixture")}, ${policyFileFixtureLabel}, ${connectionUriFixtureLabel}, ${connectionTokenResponseFixtureLabel}, ${relayEventFixtureLabel}, ${relayStepFixtureLabel}, ${authChallengeFixtureLabel}, ${sessionFixtureLabel}, ${sessionGateFixtureLabel}, ${fixtureCountLabel(fixtures.accounts.length, "account descriptor")}, ${fixtureCountLabel(fixtures.policyProfiles.length, "policy profile")}, ${fixtureCountLabel(fixtures.grants.length, "grant descriptor")}, ${fixtureCountLabel(fixtures.policyChanges.length, "policy change vector")}, ${fixtureCountLabel(fixtures.policyDecisions.length, "policy decision vector")}, ${fixtureCountLabel(fixtures.routeSelections.length, "route selection vector")}, ${routeRefusalFixtureLabel}, ${fixtureCountLabel(fixtures.accessSurfaces.length, "access-surface vector")}, ${fixtureCountLabel(fixtures.featureMatrices.length, "feature matrix")}, ${custodyContractFixtureLabel}, and ${fixtureCountLabel(fixtures.invalidVectors.length, "invalid hardening fixture")}`
      );
    });

  program
    .command("policy")
    .argument("<action>")
    .requiredOption("--proposal <path>")
    .requiredOption("--account <path>")
    .requiredOption("--current-policy <path>")
    .requiredOption("--proposed-policy <path>")
    .option("--grant <path>", "Proposed grant descriptor JSON; repeat for multiple grants", appendPathOption, [])
    .requiredOption("--out <path>")
    .description("Review secretless policy-change proposals")
    .action((action: string, options: {
      proposal: string;
      account: string;
      currentPolicy: string;
      proposedPolicy: string;
      grant: string[];
      out: string;
    }) => {
      if (action !== "review-change") throw new Error(`unsupported policy action: ${action}`);
      const context = {
        accounts: [readJson(options.account)],
        policyProfiles: [readJson(options.currentPolicy), readJson(options.proposedPolicy)],
        grants: options.grant.map((path) => readJson(path))
      };
      const review = reviewPolicyChangeProposal(readJson(options.proposal), context);
      writeNewJson(options.out, review);
    });

  program
    .command("request")
    .argument("<method>")
    .requiredOption("--out <path>")
    .option("--event-template <path>")
    .option("--request-id <id>")
    .option("--output-format <format>", "Output format: json, qr, or qr-animated", "json")
    .description("Create a nSealr request")
    .action((method: string, options: { out: string; eventTemplate?: string; requestId?: string; outputFormat: string }) => {
      assertFormat(options.outputFormat);
      const parameterlessMethod = PARAMETERLESS_REQUEST_METHODS[method];
      if (parameterlessMethod) {
        const request = {
          version: 1,
          request_id: options.requestId ?? parameterlessMethod.defaultRequestId,
          method: parameterlessMethod.protocolMethod
        };
        const validation = validateRequest(request);
        if (!validation.ok) throw new Error(validation.error);
        writeValue(options.out, request, options.outputFormat);
        return;
      }
      if (method === "sign-event") {
        if (!options.eventTemplate) throw new Error("--event-template is required for sign-event");
        const request = {
          version: 1,
          request_id: options.requestId ?? "req-sign-event-1",
          method: "sign_event",
          params: {
            event_template: readJson(options.eventTemplate)
          }
        };
        const validation = validateRequest(request);
        if (!validation.ok) throw new Error(validation.error);
        writeValue(options.out, request, options.outputFormat);
        return;
      }
      throw new Error(`unsupported request method: ${method}`);
    });

  program
    .command("dev-sign")
    .requiredOption("--secret-key <hex>")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .requiredOption("--out <path>")
    .option("--output-format <format>", "Output format: json, qr, or qr-animated", "json")
    .description("Sign a request with a test-only software signer")
    .action((options: { secretKey: string; request: string; requestFormat: string; out: string; outputFormat: string }) => {
      assertFormat(options.requestFormat);
      assertFormat(options.outputFormat);
      const request = readValue(options.request, options.requestFormat);
      const validation = validateRequest(request);
      if (!validation.ok) throw new Error(validation.error);
      if ((request as { method?: string }).method !== "sign_event") {
        throw new Error("dev-sign supports sign_event requests only");
      }
      writeValue(options.out, devSignRequest(request as Parameters<typeof devSignRequest>[0], options.secretKey), options.outputFormat);
    });

  program
    .command("review-request")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .option("--screen-review", "Render deterministic screen-review pages with approval digest")
    .option("--detail-pages", "Render complete constrained-display review detail pages")
    .option("--max-title-chars <n>", "Detail-page title width for --detail-pages")
    .option("--max-body-lines <n>", "Detail-page body lines for --detail-pages")
    .option("--max-line-chars <n>", "Detail-page body width for --detail-pages")
    .option("--max-compact-body-lines <n>", "Compact detail-page body lines for --detail-pages")
    .option("--max-compact-line-chars <n>", "Compact detail-page body width for --detail-pages")
    .option("--author-pubkey <hex>", "Signer author pubkey to bind into review output")
    .requiredOption("--out <path>")
    .description("Render an untrusted local review preview for a signing request")
    .action((options: {
      request: string;
      requestFormat: string;
      screenReview?: boolean;
      detailPages?: boolean;
      maxTitleChars?: string;
      maxBodyLines?: string;
      maxLineChars?: string;
      maxCompactBodyLines?: string;
      maxCompactLineChars?: string;
      authorPubkey?: string;
      out: string;
    }) => {
      assertFormat(options.requestFormat);
      if (options.screenReview === true && options.detailPages === true) {
        throw new Error("review-request accepts only one review output mode");
      }
      const authorPubkey = optionalAuthorPubkey(options.authorPubkey);
      const request = readValue(options.request, options.requestFormat);
      const validation = validateRequest(request);
      if (!validation.ok) throw new Error(validation.error);
      if ((request as { method?: string }).method !== "sign_event") {
        throw new Error("review-request supports sign_event requests only");
      }
      if (options.screenReview === true) {
        writeJson(options.out, screenReviewForRequest(request, authorPubkey));
        return;
      }
      const eventTemplate = (request as { params?: { event_template?: unknown } }).params?.event_template;
      if (options.detailPages === true) {
        writeJson(
          options.out,
          renderReviewDetailPages(reviewEventTemplate(eventTemplate, authorPubkey), reviewDetailPageLimitsFromOptions(options))
        );
        return;
      }
      writeJson(options.out, reviewEventTemplate(eventTemplate, authorPubkey));
    });

  const local = program.command("local").description("Inspect local companion service objects");

  local
    .command("review-pairing")
    .requiredOption("--intent <path>", "Read a local-service pairing intent JSON file")
    .requiredOption("--out <path>", "Write deterministic pairing-review metadata JSON")
    .description("Render local-service pairing review metadata without approving a client")
    .action((options: { intent: string; out: string }) => {
      writeJson(options.out, reviewPairingIntent(readJson(options.intent)));
    });

  local
    .command("approve-pairing")
    .requiredOption("--intent <path>", "Read a local-service pairing intent JSON file")
    .requiredOption("--reviewed-pairing-digest <hex>", "Pairing digest the user reviewed and approved")
    .requiredOption("--approved-at <timestamp>", "Approval timestamp as a non-negative integer")
    .option("--expires-at <timestamp>", "Optional expiry timestamp as a non-negative integer")
    .requiredOption("--out <path>", "Write the pairing approval artifact JSON")
    .description("Create a pairing approval artifact after explicit digest confirmation")
    .action((options: {
      intent: string;
      reviewedPairingDigest: string;
      approvedAt: string;
      expiresAt?: string;
      out: string;
    }) => {
      const intent = readJson(options.intent);
      const review = reviewPairingIntent(intent);
      const reviewedPairingDigest = lowerHex64Option(
        options.reviewedPairingDigest,
        "--reviewed-pairing-digest"
      );
      if (reviewedPairingDigest !== review.pairing_digest) {
        throw new Error("reviewed pairing digest does not match intent");
      }
      const approvedAt = nonNegativeIntegerOption(options.approvedAt, "--approved-at");
      const expiresAt = options.expiresAt === undefined
        ? undefined
        : nonNegativeIntegerOption(options.expiresAt, "--expires-at");
      writeJson(options.out, approvePairingIntent(intent, {
        approvedAt,
        ...(expiresAt !== undefined ? { expiresAt } : {})
      }));
    });

  local
    .command("review-storage")
    .option(
      "--grant-store <path>",
      "Review an existing local grant-store path for read-only service loading",
      singleValueOption("--grant-store")
    )
    .option(
      "--grant-store-output <path>",
      "Review a new local grant-store output path",
      singleValueOption("--grant-store-output")
    )
    .option(
      "--account-store <path>",
      "Review an existing service account-store path for read-only service loading",
      singleValueOption("--account-store")
    )
    .option(
      "--route-driver-store <path>",
      "Review an existing service route-driver-store path for read-only service loading",
      singleValueOption("--route-driver-store")
    )
    .requiredOption("--out <path>", "Write deterministic storage-review metadata JSON")
    .description("Render local-service storage-location review metadata without choosing or writing storage")
    .action((options: {
      grantStore?: string;
      grantStoreOutput?: string;
      accountStore?: string;
      routeDriverStore?: string;
      out: string;
    }) => {
      const entries: unknown[] = [];
      addLocalStorageEntry(entries, "grant_store", "read_only", options.grantStore);
      addLocalStorageEntry(entries, "grant_store", "write_new", options.grantStoreOutput);
      addLocalStorageEntry(entries, "account_store", "read_only", options.accountStore);
      addLocalStorageEntry(entries, "route_driver_store", "read_only", options.routeDriverStore);
      writeJson(options.out, createLocalStorageReview(entries));
    });

  local
    .command("approve-storage")
    .requiredOption("--review <path>", "Read a local-service storage review JSON file")
    .requiredOption("--reviewed-storage-digest <hex>", "Storage digest the user reviewed and approved")
    .requiredOption("--approved-at <timestamp>", "Approval timestamp as a non-negative integer")
    .requiredOption("--out <path>", "Write the storage approval artifact JSON")
    .description("Create a storage-location approval artifact after explicit digest confirmation")
    .action((options: {
      review: string;
      reviewedStorageDigest: string;
      approvedAt: string;
      out: string;
    }) => {
      const review = parseLocalStorageReview(readJson(options.review));
      const reviewedStorageDigest = lowerHex64Option(
        options.reviewedStorageDigest,
        "--reviewed-storage-digest"
      );
      if (reviewedStorageDigest !== review.storage_digest) {
        throw new Error("reviewed storage digest does not match review");
      }
      writeJson(options.out, approveLocalStorageReview(review, {
        approvedAt: nonNegativeIntegerOption(options.approvedAt, "--approved-at")
      }));
    });

  const localNativeHost = local
    .command("native-host")
    .description("Build explicit browser native-host onboarding artifacts");

  localNativeHost
    .command("manifest")
    .requiredOption("--browser <browser>", "Browser target: chromium or firefox", singleValueOption("--browser"))
    .requiredOption("--host-path <path>", "Absolute path to the nSealr native host executable", singleValueOption("--host-path"))
    .option("--extension-id <id>", "Allowed browser extension id; repeat for multiple ids", appendPathOption, [])
    .requiredOption("--out <path>", "Write the native-host manifest JSON")
    .description("Render a browser native-host manifest without installing it")
    .action((options: {
      browser: string;
      hostPath: string;
      extensionId: string[];
      out: string;
    }) => {
      writeNewJson(options.out, buildNativeHostManifest({
        browser: nativeHostBrowserOption(options.browser, "--browser"),
        hostPath: options.hostPath,
        extensionIds: options.extensionId
      }));
    });

  localNativeHost
    .command("plan-install")
    .requiredOption("--browser <browser>", "Browser target: chromium or firefox", singleValueOption("--browser"))
    .requiredOption("--host-path <path>", "Absolute path to the nSealr native host executable", singleValueOption("--host-path"))
    .requiredOption("--manifest-path <path>", "Absolute browser native-host manifest path", singleValueOption("--manifest-path"))
    .option("--extension-id <id>", "Allowed browser extension id; repeat for multiple ids", appendPathOption, [])
    .requiredOption("--out <path>", "Write the digest-bound install plan JSON")
    .description("Create a dry-run native-host install plan without writing browser files")
    .action((options: {
      browser: string;
      hostPath: string;
      manifestPath: string;
      extensionId: string[];
      out: string;
    }) => {
      writeNewJson(options.out, buildNativeHostInstallPlan({
        browser: nativeHostBrowserOption(options.browser, "--browser"),
        hostPath: options.hostPath,
        manifestPath: options.manifestPath,
        extensionIds: options.extensionId
      }));
    });

  localNativeHost
    .command("approve-install")
    .requiredOption("--plan <path>", "Read a native-host install plan JSON file")
    .requiredOption("--reviewed-install-digest <hex>", "Install digest the user reviewed and approved")
    .requiredOption("--approved-at <timestamp>", "Approval timestamp as a non-negative integer")
    .requiredOption("--out <path>", "Write the install approval artifact JSON")
    .description("Create a native-host install approval artifact after digest confirmation")
    .action((options: {
      plan: string;
      reviewedInstallDigest: string;
      approvedAt: string;
      out: string;
    }) => {
      writeNewJson(options.out, approveNativeHostInstallPlan(
        parseNativeHostInstallPlan(readJson(options.plan)),
        {
          reviewedInstallDigest: lowerHex64Option(
            options.reviewedInstallDigest,
            "--reviewed-install-digest"
          ),
          approvedAt: nonNegativeIntegerOption(options.approvedAt, "--approved-at")
        }
      ));
    });

  localNativeHost
    .command("execute-install")
    .requiredOption("--approval <path>", "Read a native-host install approval JSON file")
    .requiredOption("--reviewed-install-digest <hex>", "Install digest the user reviewed before execution")
    .requiredOption("--out <path>", "Write the install execution report JSON")
    .description("Write only the approved native-host manifest path with write-new semantics")
    .action(async (options: {
      approval: string;
      reviewedInstallDigest: string;
      out: string;
    }) => {
      if (existsSync(options.out)) throw new Error("output path already exists");
      const execution = await executeNativeHostInstallApproval(
        parseNativeHostInstallApproval(readJson(options.approval)),
        {
          reviewedInstallDigest: lowerHex64Option(
            options.reviewedInstallDigest,
            "--reviewed-install-digest"
          ),
          writer: {
            ensureDirectory(path) {
              mkdirSync(path, { recursive: true });
            },
            writeFileNew(path, contents) {
              writeFileSync(path, contents, { encoding: "utf8", flag: "wx" });
            }
          }
        }
      );
      writeNewJson(options.out, execution);
    });

  const localGrantStore = local
    .command("grant-store")
    .description("Build explicit local-service grant-store artifacts");

  localGrantStore
    .command("append-approval")
    .requiredOption("--approval <path>", "Read a local-service pairing approval artifact JSON file")
    .option("--grant-store <path>", "Optional existing local grant-store JSON file to extend")
    .requiredOption("--storage-approval <path>", "Read a storage approval covering the input/output grant-store paths")
    .requiredOption("--updated-at <timestamp>", "Grant-store update timestamp as a non-negative integer")
    .requiredOption("--out <path>", "Write a new local grant-store JSON file")
    .description("Append a pairing approval artifact to a storage-approved new output grant store")
    .action((options: {
      approval: string;
      grantStore?: string;
      storageApproval: string;
      updatedAt: string;
      out: string;
    }) => {
      requireGrantStoreStorageApproval(options);
      const updatedAt = nonNegativeIntegerOption(options.updatedAt, "--updated-at");
      const approval = parseLocalPairingApproval(readJson(options.approval));
      const currentStore = options.grantStore === undefined
        ? createLocalGrantStore([], { updatedAt })
        : parseLocalGrantStore(readJson(options.grantStore));
      const nextStore = appendLocalGrant(currentStore, approval.grant, { updatedAt });
      writeNewText(options.out, serializeLocalGrantStore(nextStore));
    });

  localGrantStore
    .command("revoke-client")
    .requiredOption("--grant-store <path>", "Read an existing local grant-store JSON file")
    .requiredOption("--storage-approval <path>", "Read a storage approval covering the input/output grant-store paths")
    .requiredOption("--client-id <hex>", "Client id to revoke")
    .requiredOption("--origin <origin>", "Client origin recorded in the grant")
    .requiredOption("--surface <surface>", "Client surface recorded in the grant")
    .requiredOption("--revoked-at <timestamp>", "Revocation timestamp as a non-negative integer")
    .requiredOption("--out <path>", "Write a new local grant-store JSON file")
    .description("Append a client revocation to a storage-approved new output grant store")
    .action((options: {
      grantStore: string;
      storageApproval: string;
      clientId: string;
      origin: string;
      surface: string;
      revokedAt: string;
      out: string;
    }) => {
      requireGrantStoreStorageApproval(options);
      const revokedAt = nonNegativeIntegerOption(options.revokedAt, "--revoked-at");
      const currentStore = parseLocalGrantStore(readJson(options.grantStore));
      const nextStore = appendLocalGrantRevocation(currentStore, {
        clientId: lowerHex64Option(options.clientId, "--client-id"),
        origin: options.origin,
        surface: localClientSurfaceOption(options.surface, "--surface")
      }, { revokedAt });
      writeNewText(options.out, serializeLocalGrantStore(nextStore));
    });

  program
    .command("smartcard-sim-sign")
    .requiredOption("--secret-key <hex>")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .option("--review-acknowledged", "Confirm external review before sending an event id to a display-less smartcard")
    .option("--approval-digest <hex>", "Required with --review-acknowledged; binds acknowledgement to a reviewed request digest")
    .requiredOption("--out <path>")
    .option("--output-format <format>", "Output format: json, qr, or qr-animated", "json")
    .description("Sign a request through the test-only smartcard APDU simulator")
    .action(
      async (options: {
        secretKey: string;
        request: string;
        requestFormat: string;
        reviewAcknowledged?: boolean;
        approvalDigest?: string;
        out: string;
        outputFormat: string;
      }) => {
        assertFormat(options.requestFormat);
        assertFormat(options.outputFormat);
        const request = readValue(options.request, options.requestFormat);
        const validation = validateRequest(request);
        if (!validation.ok) throw new Error(validation.error);
        if ((request as { method?: string }).method !== "sign_event") {
          throw new Error("smartcard-sim-sign supports sign_event requests only");
        }
        if (options.approvalDigest !== undefined && options.reviewAcknowledged !== true) {
          throw new Error("approval digest requires --review-acknowledged");
        }
        let acknowledgement: Parameters<SmartcardSigner["signEventRequest"]>[1];
        if (options.reviewAcknowledged === true) {
          const approvalDigest = options.approvalDigest;
          if (approvalDigest === undefined) {
            throw new Error("approval_digest is required for display-less smartcard signing");
          }
          acknowledgement = { acknowledged: true, source: "external-review", approvalDigest };
        }
        const signer = new SmartcardSigner(new SmartcardSimulator(options.secretKey));
        const response = await signer.signEventRequest(request as SignEventRequest, acknowledgement);
        writeValue(options.out, response, options.outputFormat);
      }
    );

  const serialFrame = program.command("serial-frame").description("Encode and decode newline serial frames");

  serialFrame
    .command("wrap-request")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .requiredOption("--out <path>")
    .description("Wrap a validated request as a serial request frame")
    .action((options: { request: string; requestFormat: string; out: string }) => {
      assertFormat(options.requestFormat);
      const request = readValue(options.request, options.requestFormat);
      const validation = validateRequest(request);
      if (!validation.ok) throw new Error(validation.error);
      writeFileSync(options.out, encodeSerialFrame({ type: "request", payload: request }), "utf8");
    });

  serialFrame
    .command("unwrap-response")
    .option("--request <path>", "Original request to verify the serial response against")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .requiredOption("--response-frame <path>")
    .requiredOption("--out <path>")
    .option("--output-format <format>", "Output format: json, qr, or qr-animated", "json")
    .description("Decode and validate a serial response frame")
    .action((options: { request?: string; requestFormat: string; responseFrame: string; out: string; outputFormat: string }) => {
      assertFormat(options.requestFormat);
      assertFormat(options.outputFormat);
      const frame = decodeSerialFrame(readFileSync(options.responseFrame, "utf8").trim());
      if (frame.type !== "response") {
        throw new Error(`serial-frame unwrap-response expected response frame, got ${frame.type}`);
      }
      if (options.request !== undefined) {
        const request = readValue(options.request, options.requestFormat);
        assertResponseForRequest(request, frame.payload, "serial frame response");
      } else {
        const validation = validateResponse(frame.payload);
        if (!validation.ok) throw new Error(validation.error);
      }
      writeValue(options.out, frame.payload, options.outputFormat);
    });

  const serialLine = program.command("serial-line").description("Exchange validated requests over a newline serial port");

  serialLine
    .command("exchange")
    .requiredOption("--port <path>", "Serial device path, for example /dev/cu.usbmodem1101")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .requiredOption("--out <path>")
    .option("--output-format <format>", "Output format: json, qr, or qr-animated", "json")
    .option("--timeout-ms <value>", "Read/write timeout in milliseconds", "30000")
    .option("--max-ignored-lines <value>", "Maximum non-protocol lines to skip before failing", "32")
    .description("Send one validated request frame and write the verified response")
    .action(
      async (actionOptions: {
        port: string;
        request: string;
        requestFormat: string;
        out: string;
        outputFormat: string;
        timeoutMs: string;
        maxIgnoredLines: string;
      }) => {
        assertFormat(actionOptions.requestFormat);
        assertFormat(actionOptions.outputFormat);
        const request = readValue(actionOptions.request, actionOptions.requestFormat);
        const validation = validateRequest(request);
        if (!validation.ok) throw new Error(validation.error);
        const responseTimeoutMs = positiveIntegerOption(actionOptions.timeoutMs, 30_000, "--timeout-ms");
        const maxIgnoredLines = positiveIntegerOption(actionOptions.maxIgnoredLines, 32, "--max-ignored-lines");
        const response = await exchangeSerialLineRequest({
          path: actionOptions.port,
          request,
          openPort: openSerialLinePort,
          responseTimeoutMs,
          maxIgnoredLines
        });
        writeValue(actionOptions.out, response, actionOptions.outputFormat);
      }
    );

  const nip46 = program.command("nip46").description("Inspect already-decrypted NIP-46 payloads");

  nip46
    .command("review-connect")
    .description("Write deterministic review pages for an already-decrypted NIP-46 connect request")
    .requiredOption("--message <path>", "Read a decrypted NIP-46 connect message JSON file")
    .requiredOption("--out <path>", "Write the connect review JSON")
    .action((options: { message: string; out: string }) => {
      writeJson(options.out, reviewNip46ConnectMessage(readJson(options.message)));
    });

  nip46
    .command("approve-connect")
    .description("Write a digest-bound local approval artifact for a reviewed NIP-46 connect request")
    .requiredOption("--review <path>", "Read a NIP-46 connect review JSON file")
    .requiredOption("--reviewed-connect-digest <hex>", "Digest read and confirmed by the user")
    .requiredOption("--approved-at <unix>", "Unix timestamp recorded in the local approval artifact")
    .requiredOption("--out <path>", "Write the connect approval JSON")
    .action((options: { review: string; reviewedConnectDigest: string; approvedAt: string; out: string }) => {
      const approval = approveNip46ConnectReview(readJson(options.review), {
        reviewedConnectDigest: options.reviewedConnectDigest,
        approvedAt: nonNegativeIntegerOption(options.approvedAt, "--approved-at")
      });
      writeNewJson(options.out, approval);
    });

  nip46
    .command("review-auth-challenge")
    .description("Write deterministic review pages for an already-decrypted NIP-46 auth_url response step")
    .requiredOption("--step <path>", "Read a NIP-46 relay response-step input JSON file")
    .requiredOption("--out <path>", "Write the auth challenge review JSON")
    .action((options: { step: string; out: string }) => {
      writeNewJson(options.out, reviewNip46AuthChallengeStep(readJson(options.step)));
    });

  nip46
    .command("approve-auth-challenge")
    .description("Write a digest-bound local approval artifact for a reviewed NIP-46 auth_url response step")
    .requiredOption("--review <path>", "Read a NIP-46 auth challenge review JSON file")
    .requiredOption("--reviewed-auth-challenge-digest <hex>", "Digest read and confirmed by the user")
    .requiredOption("--approved-at <unix>", "Unix timestamp recorded in the local approval artifact")
    .requiredOption("--out <path>", "Write the auth challenge approval JSON")
    .action((options: { review: string; reviewedAuthChallengeDigest: string; approvedAt: string; out: string }) => {
      const approval = approveNip46AuthChallengeReview(readJson(options.review), {
        reviewedAuthChallengeDigest: options.reviewedAuthChallengeDigest,
        approvedAt: nonNegativeIntegerOption(options.approvedAt, "--approved-at")
      });
      writeNewJson(options.out, approval);
    });

  nip46
    .command("create-session-checkpoint")
    .description("Write a reviewed-but-not-active NIP-46 session lifecycle checkpoint")
    .requiredOption("--review <path>", "Read a NIP-46 connect review JSON file")
    .requiredOption("--approval <path>", "Read a NIP-46 connect approval JSON file")
    .requiredOption("--name <value>", "Stable checkpoint name")
    .requiredOption("--client-pubkey <hex>", "Client public key bound to the future session")
    .requiredOption("--relays <csv>", "Comma-separated normalized wss relay URLs")
    .requiredOption("--expires-at <unix>", "Unix timestamp when the checkpoint expires")
    .option("--permissions <value>", "Comma-separated approved NIP-46 permissions", "")
    .option("--policy-file <path>", "Read approved NIP-46 permissions from a policy file")
    .requiredOption("--out <path>", "Write the session lifecycle checkpoint JSON")
    .action((options: {
      review: string;
      approval: string;
      name: string;
      clientPubkey: string;
      relays: string;
      expiresAt: string;
      permissions: string;
      policyFile?: string;
      out: string;
    }) => {
      if (options.policyFile && options.permissions.trim() !== "") {
        throw new Error("--policy-file cannot be combined with --permissions");
      }
      const approvedPermissions = options.policyFile
        ? readNip46PolicyPermissions(options.policyFile)
        : parseNip46ApprovedPermissions(options.permissions);
      const checkpoint = createNip46SessionLifecycleCheckpoint(
        readJson(options.review),
        readJson(options.approval),
        {
          name: options.name,
          clientPubkey: options.clientPubkey,
          relays: options.relays.split(",").map((relay) => relay.trim()),
          approvedPermissions,
          expiresAt: nonNegativeIntegerOption(options.expiresAt, "--expires-at")
        }
      );
      writeNewJson(options.out, checkpoint);
    });

  nip46
    .command("gate-session-request")
    .description("Write the deterministic gate result for a pending NIP-46 session request")
    .requiredOption("--session <path>", "Read a NIP-46 session lifecycle checkpoint JSON file")
    .requiredOption("--event <path>", "Read the kind:24133 relay event JSON file")
    .requiredOption("--message <path>", "Read the already-decrypted NIP-46 request message JSON file")
    .requiredOption("--evaluated-at <unix>", "Unix timestamp used for session expiry checks")
    .option("--direction <value>", "Relay direction", "client_to_remote_signer")
    .requiredOption("--out <path>", "Write the session request gate JSON")
    .action((options: {
      session: string;
      event: string;
      message: string;
      evaluatedAt: string;
      direction: string;
      out: string;
    }) => {
      const gate = evaluateNip46SessionRequestGate({
        format: "nsealr-nip46-session-request-gate-v0",
        session: readJson(options.session),
        evaluated_at: nonNegativeIntegerOption(options.evaluatedAt, "--evaluated-at"),
        direction: options.direction,
        event: readJson(options.event),
        decrypted_message: readJson(options.message)
      });
      writeNewJson(options.out, gate);
    });

  nip46
    .command("parse-connection-uri")
    .description("Write descriptor-only metadata for a bunker:// or nostrconnect:// token")
    .requiredOption("--uri-file <path>", "Read a local text file containing the connection URI")
    .requiredOption("--out <path>", "Write the non-secret connection URI descriptor JSON")
    .action((options: { uriFile: string; out: string }) => {
      const uri = readFileSync(options.uriFile, "utf8").trim();
      writeJson(options.out, parseNip46ConnectionUri(uri));
    });

  nip46
    .command("verify-connection-token-response")
    .description("Verify a nostrconnect:// token response secret without writing the secret")
    .requiredOption("--uri-file <path>", "Read the original local nostrconnect:// token file")
    .requiredOption("--step <path>", "Read a NIP-46 relay response-step input JSON file")
    .requiredOption("--out <path>", "Write the secretless token response verification JSON")
    .action((options: { uriFile: string; step: string; out: string }) => {
      const uri = readFileSync(options.uriFile, "utf8").trim();
      writeNewJson(options.out, verifyNip46ConnectionTokenResponse({
        connectionUri: uri,
        responseStep: readJson(options.step)
      }));
    });

  nip46
    .command("decide")
    .requiredOption("--message <path>")
    .option("--permissions <value>", "Comma-separated approved NIP-46 permissions", "")
    .option("--policy-file <path>", "Read approved NIP-46 permissions from a policy file")
    .requiredOption("--out <path>")
    .description("Write the bridge decision for an already-decrypted NIP-46 request")
    .action((options: { message: string; permissions: string; policyFile?: string; out: string }) => {
      const message = readJson(options.message);
      if (options.policyFile && options.permissions.trim() !== "") {
        throw new Error("--policy-file cannot be combined with --permissions");
      }
      const permissions = options.policyFile
        ? readNip46PolicyPermissions(options.policyFile)
        : parseNip46ApprovedPermissions(options.permissions);
      writeJson(options.out, decideNip46BridgeAction(message, permissions));
    });

  program
    .command("verify-response")
    .requiredOption("--request <path>")
    .option("--request-format <format>", "Request format: json, qr, or qr-animated", "json")
    .requiredOption("--response <path>")
    .option("--response-format <format>", "Response format: json, qr, or qr-animated", "json")
    .description("Verify a signer response against the original request")
    .action((options: { request: string; requestFormat: string; response: string; responseFormat: string }) => {
      assertFormat(options.requestFormat);
      assertFormat(options.responseFormat);
      const request = readValue(options.request, options.requestFormat);
      const response = readValue(options.response, options.responseFormat);
      assertResponseForRequest(request, response, "response");
      console.log("response verified");
    });

  return program;
}

export async function runCliMain(
  argv: string[] = process.argv,
  options: BuildCliOptions & { errorOutput?: ErrorOutput } = {}
): Promise<number> {
  try {
    await buildCli(options).parseAsync(argv, { from: "node" });
    return 0;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    (options.errorOutput ?? process.stderr).write(`${message}\n`);
    return 1;
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  process.exitCode = await runCliMain(process.argv);
}
