import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { getEventHash, verifyEvent } from "nostr-tools/pure";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { computeEventId, verifySchnorrSignature, verifySignedEventResponse } from "./nostr.js";

const specsRoot = resolveSpecsRoot();
const basicVector = JSON.parse(
  readFileSync(resolve(specsRoot, "vectors/events/kind-1-basic.json"), "utf8")
);
const basicRequest = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const basicResponse = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));

describe("Nostr core verification", () => {
  it("computes the NIP-01 event id from canonical serialization", () => {
    expect(computeEventId(basicVector.signed_event)).toBe(basicVector.event_id);
  });

  it("matches nostr-tools event hash and signature verification", () => {
    expect(getEventHash(basicVector.signed_event)).toBe(basicVector.event_id);
    expect(verifyEvent(basicVector.signed_event)).toBe(true);
  });

  it("verifies the BIP-340 signature from the shared fixture", () => {
    const event = basicVector.signed_event;
    expect(verifySchnorrSignature(event.pubkey, event.id, event.sig)).toBe(true);
  });

  it("rejects response request id mismatches", () => {
    const response = structuredClone(basicResponse);
    response.request_id = "different-request";

    expect(verifySignedEventResponse(basicRequest, response)).toEqual({
      ok: false,
      error: "response request_id does not match request"
    });
  });

  it("rejects signed events that do not match the requested template", () => {
    const response = structuredClone(basicResponse);
    response.result.event.content = "tampered";

    expect(verifySignedEventResponse(basicRequest, response)).toEqual({
      ok: false,
      error: "signed event does not match requested template"
    });
  });

  it("rejects event id mismatches", () => {
    const response = structuredClone(basicResponse);
    response.result.event.id = `${"0".repeat(63)}1`;

    expect(verifySignedEventResponse(basicRequest, response)).toEqual({
      ok: false,
      error: "signed event id does not match NIP-01 canonical serialization"
    });
  });

  it("rejects invalid signatures", () => {
    const response = structuredClone(basicResponse);
    response.result.event.sig = `${"0".repeat(127)}1`;

    expect(verifySignedEventResponse(basicRequest, response)).toEqual({
      ok: false,
      error: "signed event signature is invalid"
    });
  });
});
