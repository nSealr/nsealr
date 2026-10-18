import { schnorr } from "@noble/curves/secp256k1.js";
import {
  bytesToHex,
  computeEventId,
  hexToBytes,
  verifySignedEventResponse,
  type EventTemplate,
  type SignEventRequest,
  type SignEventResponse,
  type SignedEvent
} from "@nsealr/core";
import { validateRequest, validateResponse } from "@nsealr/protocol";

export function publicKeyFromSecret(secretKeyHex: string): string {
  return bytesToHex(schnorr.getPublicKey(hexToBytes(secretKeyHex)));
}

export function signTemplate(template: EventTemplate, secretKeyHex: string): SignedEvent {
  const pubkey = publicKeyFromSecret(secretKeyHex);
  const eventWithoutId = {
    pubkey,
    created_at: template.created_at,
    kind: template.kind,
    tags: template.tags,
    content: template.content
  };
  const id = computeEventId(eventWithoutId);
  const aux = new Uint8Array(32);
  const sig = bytesToHex(schnorr.sign(hexToBytes(id), hexToBytes(secretKeyHex), aux));
  return { id, ...eventWithoutId, sig };
}

export function devSignRequest(request: SignEventRequest, secretKeyHex: string): SignEventResponse {
  if (request.version !== 1 || request.method !== "sign_event") {
    throw new Error("devSignRequest only supports v0 sign_event requests");
  }
  return {
    version: 1,
    request_id: request.request_id,
    ok: true,
    result: {
      event: signTemplate(request.params.event_template, secretKeyHex)
    }
  };
}

function assertValidRequest(value: unknown): void {
  const validation = validateRequest(value);
  if (!validation.ok) {
    throw new Error(`transport request invalid: ${validation.error}`);
  }
}

function assertValidResponse(value: unknown): void {
  const validation = validateResponse(value);
  if (!validation.ok) {
    throw new Error(`transport response invalid: ${validation.error}`);
  }
}

export class DevSignerTransport {
  readonly name = "dev-signer";

  constructor(private readonly secretKeyHex: string) {}

  async exchange(request: unknown): Promise<unknown> {
    assertValidRequest(request);
    const response = devSignRequest(request as SignEventRequest, this.secretKeyHex);
    assertValidResponse(response);
    const verification = verifySignedEventResponse(request, response);
    if (!verification.ok) {
      throw new Error(`transport response invalid: ${verification.error}`);
    }
    return response;
  }
}
