export const NSEALR_V0_LIMITS = {
  max_request_id_length: 128,
  max_decoded_request_json_bytes: 704,
  max_static_qr_decoded_json_bytes: 704,
  max_animated_qr_decoded_json_bytes: 4096,
  max_animated_qr_frame_payload_chars: 256,
  max_animated_qr_frame_count: 64,
  max_serial_frame_bytes: 1024,
  max_nip46_decrypted_message_json_bytes: 1024,
  max_content_utf8_bytes: 512,
  max_tag_count: 16,
  max_tag_fields_per_tag: 8,
  max_tag_field_utf8_bytes: 64,
  max_total_tag_utf8_bytes: 4096,
  max_safe_integer: 9007199254740991
} as const;

export type nSealrV0Limits = typeof NSEALR_V0_LIMITS;

const textEncoder = new TextEncoder();

export function utf8ByteLength(value: string): number {
  return textEncoder.encode(value).byteLength;
}

export function compactJsonUtf8ByteLength(value: unknown): number {
  return utf8ByteLength(JSON.stringify(value));
}

export function isSafeNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && Number.isSafeInteger(value) && value >= 0;
}
