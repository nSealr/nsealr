import { compactJsonUtf8ByteLength, validateRequest } from "@nsealr/protocol";
import type { RouteSelection } from "@nsealr/policy";
import type { EffectiveSignerLimits } from "./service.js";

export const PUBLIC_S3_IMPLEMENTATION = "nsealr.s3.public.scalar3.e7f04215.v1";
export const PUBLIC_S3_LIMITS = "nsealr.limits.s3.public.e7.v1";
export const PUBLIC_S3_KEY = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
export type PublicS3Fixture = {
  readonly source: "e7f04215fc97808acdafdbf9420f6ef6d0102c5b";
  readonly image_sha256: "7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da";
  /** Application observations of one real local stream; never a wire report. */
  connection(): { connection_id: string; generation: number; config_digest: string; state: "open" | "settled" | "failed" };
  begin(): void;
  check(): void;
  phase(phase: "active" | "external"): void;
  remainingMs(): number;
};

export function assessPublicS3(route: RouteSelection, request: unknown, fixture: PublicS3Fixture): EffectiveSignerLimits {
  if (fixture.source !== "e7f04215fc97808acdafdbf9420f6ef6d0102c5b" ||
      fixture.image_sha256 !== "7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da" ||
      route.implementation_id !== PUBLIC_S3_IMPLEMENTATION || route.limits_id !== PUBLIC_S3_LIMITS ||
      route.public_key !== PUBLIC_S3_KEY || route.profile !== "esp32_no_se" || route.custody !== "volatile_session" ||
      route.transport !== "usb" || route.route_type !== "esp32_usb_nip46" ||
      !["get_public_key", "sign_event"].includes(route.method)) throw new Error("unavailable public S3 fixture admission");
  const validation = validateRequest(request);
  if (!validation.ok || typeof request !== "object" || request === null) throw new Error("invalid public S3 request");
  const r = request as { method: string; params?: { event_template?: unknown } };
  if (r.method !== route.method || compactJsonUtf8ByteLength(request) > 320) throw new Error("public S3 request exceeds actual adapter");
  if (r.method === "sign_event") {
    const event = r.params?.event_template;
    // This first public wiring is intentionally the observed template only.
    const e = event as { kind?: unknown; created_at?: unknown; content?: unknown; tags?: unknown };
    if (!e || e.kind !== 1 || e.created_at !== 1710000000 || e.content !== "S3 public physical approval" || !Array.isArray(e.tags) || e.tags.length !== 0)
      throw new Error("public S3 template not admitted");
  }
  const c = fixture.connection();
  if (!/^[A-Za-z0-9._:-]{1,128}$/u.test(c.connection_id) || !Number.isSafeInteger(c.generation) ||
      c.generation < 0 || !/^[0-9a-f]{64}$/u.test(c.config_digest) || c.state === "failed")
    throw new Error("public S3 connection is unavailable");
  return {
    method: { method_id: route.method as "sign_event" | "get_public_key", scope: r.method === "sign_event" ? "sign_event" : "discovery",
      request_json_bytes: 320, response_json_bytes: 704, parse_work: 8192, retained_bytes: 8192,
      pending_requests: 1, deadline_ms: 100000, queued_operations: 0, cached_responses: 0,
      ...(r.method === "sign_event" ? { content_utf8_bytes: 128, tag_count: 4, tag_fields: 4,
        tag_field_utf8_bytes: 64, aggregate_tag_utf8_bytes: 160, canonical_bytes: 1024, review_pages: 128 } : {}) },
    transport: { transport_id: "usb", scope: "transport", frame_bytes: 1024, frame_count: 1,
      reassembly_bytes: 704, parse_work: 8192, retained_bytes: 8192, pending_requests: 1,
      deadline_ms: 100000, queued_frames: 0 }
  };
}
