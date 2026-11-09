import { digest, MAX_MESSAGE, text, utf8 } from './protocol.ts';
export const CHUNK = 384;
export const MAX_FRAMES = 86;
const encode = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
function decode(value: string): Uint8Array {
  if (!/^[A-Za-z0-9_-]+$/.test(value) || value.length > 512) throw Error('Invalid QR chunk.');
  const bytes = Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/')), c => c.charCodeAt(0));
  if (encode(bytes) !== value) throw Error('Noncanonical QR chunk.');
  return bytes;
}
export function frames(message: string): string[] {
  const bytes = utf8.encode(text(message));
  if (!bytes.length) throw Error('Empty QR message.');
  const id = digest(bytes); const count = Math.ceil(bytes.length / CHUNK);
  return Array.from({ length: count }, (_, index) => `ns:${id}:${index}:${count}:${encode(bytes.subarray(index * CHUNK, (index + 1) * CHUNK))}`);
}

export class Collector {
  private id = '';
  private count = 0;
  private chunks = new Map<number, Uint8Array>();
  get progress() { return { received: this.chunks.size, total: this.count }; }
  clear() { for (const bytes of this.chunks.values()) bytes.fill(0); this.chunks.clear(); this.id = ''; this.count = 0; }
  add(frame: string): string | null {
    if (frame.length > 590) throw Error('QR frame is too large.');
    const match = /^ns:([a-f0-9]{64}):(0|[1-9]\d?):([1-9]\d?):([A-Za-z0-9_-]+)$/.exec(frame);
    if (!match) throw Error('This is not an nSealr response QR.');
    const [, id, indexText, countText, payload] = match;
    const index = Number(indexText), count = Number(countText);
    if (count > MAX_FRAMES || index >= count) throw Error('Invalid QR frame position.');
    const bytes = decode(payload);
    if (bytes.length > CHUNK || !bytes.length || (index < count - 1 && bytes.length !== CHUNK) ||
        (count - 1) * CHUNK + (index === count - 1 ? bytes.length : 1) > MAX_MESSAGE) throw Error('Invalid QR chunk length.');
    if (this.id && (this.id !== id || this.count !== count)) throw Error('Mixed QR messages. Cancel and scan one response.');
    const previous = this.chunks.get(index);
    if (previous && encode(previous) !== payload) throw Error('Conflicting QR frames.');
    this.id = id; this.count = count; this.chunks.set(index, bytes);
    if (this.chunks.size !== count) return null;
    const joined = new Uint8Array((count - 1) * CHUNK + this.chunks.get(count - 1)!.length);
    for (let i = 0; i < count; i++) joined.set(this.chunks.get(i)!, i * CHUNK);
    try {
      if (joined.length > MAX_MESSAGE || digest(joined) !== id) throw Error('QR message checksum failed.');
      return new TextDecoder('utf-8', { fatal: true }).decode(joined);
    } finally { joined.fill(0); this.clear(); }
  }
}
