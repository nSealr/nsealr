import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import {
  checkedProduct, compactReportedCapabilities, intersectMethodLimits,
  parseImplementationProfile, parseLimitsManifest, parseReportedCapabilities,
  readBoundedJson, requireMessageFeature, resolveReportedCapabilities,
  type FullCapabilities, type ImplementationProfile
} from "./capabilities.js";

const root = resolveSpecsRoot();
const load = (path: string) => JSON.parse(readFileSync(resolve(root, path), "utf8"));
const cases = load("vectors/profile-capabilities/cases-v1.json");
const profiles = Object.keys(cases.implementation_examples);
const manifest = (profile = "pi_qr"): ImplementationProfile => parseImplementationProfile(load(cases.implementation_examples[profile]));
function full(profile = "pi_qr"): FullCapabilities {
  const { conformance_only: _, ...value } = manifest(profile);
  return { ...value, format: "nsealr.capabilities.v1", form: "full" };
}

describe("strict bounded reported capabilities", () => {
  it("S-01/P-01: resolves full/reference examples without creating local evidence", () => {
    for (const profile of profiles) {
      const value = full(profile), local = manifest(profile);
      const compact = compactReportedCapabilities(value, local, 704);
      expect(resolveReportedCapabilities(parseReportedCapabilities(JSON.stringify(compact)), local)).toEqual(value);
      expect(resolveReportedCapabilities(parseReportedCapabilities(JSON.stringify(value)), local)).toEqual(value);
      expect(value).not.toHaveProperty("verified");
      expect(value).not.toHaveProperty("signing_enabled");
      expect(local.conformance_only).toBe(true);
    }
  });

  it("A-01/A-02: distinguishes all report axes and rejects contradictory available state", () => {
    const input = cases.cases.find((item: {id: string}) => item.id === "A-01").input;
    for (const [support, configuration, availability] of input.states) {
      const value = full();
      Object.assign(value.methods[0], { support, configuration, availability, reason: availability === "available" ? null : "unknown" });
      expect(parseReportedCapabilities(JSON.stringify(value))).toEqual(value);
    }
    for (const state of [
      { support: "unavailable", configuration: "configured", availability: "available", reason: null },
      { support: "supported", configuration: "unconfigured", availability: "available", reason: null },
      { support: "supported", configuration: "configured", availability: "available", reason: "locked" }
    ]) {
      const value = full(); Object.assign(value.methods[0], state);
      expect(() => parseReportedCapabilities(JSON.stringify(value))).toThrow();
    }
  });

  it("A-03: rejects authority/evidence assertions at each nested descriptor position", () => {
    const input = cases.cases.find((item: {id: string}) => item.id === "A-03").input;
    for (const forbidden of input.forbidden_fields) {
      for (const position of input.positions) {
        const value = full();
        const target = position === "root" ? value : position === "method" ? value.methods[0] : position === "transport" ? value.transports[0] : position === "messages" ? value.messages : value.device;
        Object.assign(target, { [forbidden]: true });
        expect(() => parseReportedCapabilities(JSON.stringify(value))).toThrow();
      }
    }
  });

  it("S-02: rejects duplicate IDs, immutable changes, unknown local manifests and illegal deltas", () => {
    const value = full(), local = manifest();
    const compact = compactReportedCapabilities(value, local, 704);
    expect(() => resolveReportedCapabilities({ ...compact, implementation_id: "unknown" }, local)).toThrow(/manifest/);
    expect(() => resolveReportedCapabilities({ ...compact, profile: "p4_qr" }, local)).toThrow(/profile/);
    expect(() => resolveReportedCapabilities({ ...compact, runtime: [...compact.runtime, ...compact.runtime] }, local)).toThrow(/duplicate/);
    expect(() => resolveReportedCapabilities({ ...compact, runtime: [{ method_id: "nip44_encrypt", configuration: "configured", availability: "available", reason: null }] }, local)).toThrow(/implemented/);
    const altered = full(); altered.custody.configuration_id = "unrecognized";
    expect(() => resolveReportedCapabilities(altered, local)).toThrow(/Immutable/);
    const duplicate = full(); duplicate.methods.push(duplicate.methods[0]);
    expect(() => parseReportedCapabilities(JSON.stringify(duplicate))).toThrow(/duplicate/);
    const unknown = full(); Object.assign(unknown.methods[0], { revision: 2 });
    expect(() => parseReportedCapabilities(JSON.stringify(unknown))).toThrow(/revision/);
    const missingRuntime = { ...compact, runtime: [] };
    expect(() => resolveReportedCapabilities(missingRuntime, local)).toThrow(/omitted/);
  });

  it("S-03: checks original bytes, decoded duplicate names, Unicode, tokens, depth and work bounds", () => {
    for (const input of [
      '{"a":1,"a":2}', '{"a":1,"\\u0061":2}', '{}{}', '\ufeff{}',
      '{"a":"\\ud800"}', '{"a":"\\udc00"}', '{"a":-0}', '{"a":1.0}',
      '{"a":1e0}', '{"a":9007199254740992}', '{"a":01}',
      '['.repeat(9) + ']'.repeat(9), ' '.repeat(8193),
      JSON.stringify({ ["k".repeat(129)]: 1 }),
      JSON.stringify(Object.fromEntries(Array.from({length: 33}, (_, i) => [`k${i}`, i])))
    ]) expect(() => readBoundedJson(input)).toThrow();
    expect(() => readBoundedJson(Uint8Array.of(0x7b, 0xff, 0x7d))).toThrow(/UTF8/);
    expect(() => readBoundedJson('"\ud800"')).toThrow();
    expect(readBoundedJson('{"a":"\\ud83d\\ude00","n":9007199254740991}')).toEqual({ a: "😀", n: Number.MAX_SAFE_INTEGER });
    expect(readBoundedJson(' '.repeat(8190) + '{}')).toEqual({});
    const tooLong = full(); tooLong.device.name = "é".repeat(65);
    expect(() => parseReportedCapabilities(JSON.stringify(tooLong))).toThrow(/label/);
  });

  it("S-07/L-05: complete compact state must fit and cannot omit transport or message changes", () => {
    const value = full(), local = manifest();
    const reference = compactReportedCapabilities(value, local, 704);
    const exact = new TextEncoder().encode(JSON.stringify(reference)).byteLength;
    expect(compactReportedCapabilities(value, local, exact)).toEqual(reference);
    expect(() => compactReportedCapabilities(value, local, exact - 1)).toThrow(/budget/);
    const changed = full(); Object.assign(changed.transports[0], { availability: "unavailable", reason: "busy" });
    expect(() => compactReportedCapabilities(changed, local, 704)).toThrow(/representable/);
    const message = full(); message.messages.nip44_v2_primitive.reason = "unknown";
    expect(() => compactReportedCapabilities(message, local, 704)).toThrow(/representable/);
  });
});

describe("finite applicable limit dimensions", () => {
  it("L-01/L-02: validates each declared dimension with no unlimited or zero-positive defaults", () => {
    const base = parseLimitsManifest(cases.limits_manifest);
    for (const group of ["methods", "transports"] as const) {
      for (let i = 0; i < base[group].length; i++) {
        for (const [key, value] of Object.entries(base[group][i])) {
          if (typeof value !== "number") continue;
          const zeroAllowed = ["queued_operations", "cached_responses", "queued_frames"].includes(key);
          for (const invalid of [null, -1, 0.5, Number.MAX_SAFE_INTEGER + 1, "unlimited", ...(zeroAllowed ? [] : [0])]) {
            const changed = structuredClone(base) as any; changed[group][i][key] = invalid;
            expect(() => parseLimitsManifest(changed)).toThrow();
          }
          const absent = structuredClone(base) as any; delete absent[group][i][key];
          expect(() => parseLimitsManifest(absent)).toThrow();
        }
      }
    }
    const extra = structuredClone(base) as any; extra.methods[0].unbounded_bytes = 1;
    expect(() => parseLimitsManifest(extra)).toThrow();
    const aggregate = structuredClone(base); aggregate.methods[0].pending_requests = Number.MAX_SAFE_INTEGER;
    expect(() => parseLimitsManifest(aggregate)).toThrow();
  });

  it("L-01/L-03: intersects dimensions without inflating either endpoint and checks expansion first", () => {
    const local = parseLimitsManifest(cases.limits_manifest).methods.find((method) => method.method_id === "sign_event")!;
    const peer = { ...local, content_utf8_bytes: 256, deadline_ms: 50 };
    const intersection = intersectMethodLimits(local, peer);
    for (const [key, value] of Object.entries(intersection)) {
      if (typeof value === "number") {
        expect(value).toBeLessThanOrEqual((local as any)[key]);
        expect(value).toBeLessThanOrEqual((peer as any)[key]);
      }
    }
    expect(checkedProduct(65535, 4)).toBe(262140);
    expect(checkedProduct(65536, 4)).toBe(262144);
    expect(() => checkedProduct(Number.MAX_SAFE_INTEGER, 4)).toThrow(/overflow/);
    expect(() => intersectMethodLimits(local, { ...peer, method_id: "get_public_key" })).toThrow(/dimensions/);
    expect(() => intersectMethodLimits({ ...local, retained_bytes: 1 }, peer)).toThrow(/retention/);
    expect(() => intersectMethodLimits({ ...local, unknown_unit: 1 } as any, { ...peer, unknown_unit: 1 } as any)).toThrow(/fields/);
  });
});

describe("message primitive/context/workflow separation", () => {
  it("D-01/D-02/D-03/D-04: primitive does not establish context or a named admitted workflow", () => {
    const messages = full().messages;
    expect(() => requireMessageFeature(messages, "nip44_v2_primitive")).toThrow();
    Object.assign(messages.nip44_v2_primitive, { support: "supported", configuration: "configured", availability: "available", reason: null });
    expect(() => requireMessageFeature(messages, "nip44_v2_primitive")).not.toThrow();
    expect(() => requireMessageFeature(messages, "verified_message_context_v1")).toThrow();
    expect(() => requireMessageFeature(messages, "nip17_59_one_to_one_text_v1", "workflow.test")).toThrow();
    Object.assign(messages.verified_message_context_v1, { support: "supported", configuration: "configured", availability: "available", reason: null });
    expect(() => requireMessageFeature(messages, "nip17_59_one_to_one_text_v1", "workflow.test")).toThrow();
    Object.assign(messages.nip17_59_one_to_one_text_v1, { support: "supported", configuration: "configured", availability: "available", reason: null, workflow_id: "workflow.test" });
    expect(() => requireMessageFeature(messages, "nip17_59_one_to_one_text_v1", "workflow.test")).not.toThrow();
    expect(() => requireMessageFeature(messages, "nip17_59_one_to_one_text_v1", "other")).toThrow();
  });
});
