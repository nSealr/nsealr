import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { verifySignedEventResponse } from "@nsealr/core";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { DevSignerTransport, devSignRequest } from "./dev-signer.js";

const specsRoot = resolveSpecsRoot();
const key = JSON.parse(readFileSync(resolve(specsRoot, "vectors/keys/test-key-1.json"), "utf8"));
const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));

describe("dev signer", () => {
  it("signs a shared fixture request and produces a verifiable response", () => {
    const response = devSignRequest(request, key.secret_key);
    expect(response.request_id).toBe(request.request_id);
    expect(response.ok).toBe(true);
    expect(verifySignedEventResponse(request, response).ok).toBe(true);
  });

  it("keeps the in-memory signer behind the private transport boundary", async () => {
    const transport = new DevSignerTransport(key.secret_key);
    const response = await transport.exchange(request);

    expect(verifySignedEventResponse(request, response).ok).toBe(true);
    await expect(transport.exchange({ ...request, request_id: "bad request id" })).rejects.toThrow(
      "transport request invalid: request_id is invalid"
    );
  });
});
