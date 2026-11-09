import { schnorr } from '@noble/curves/secp256k1.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { bech32 } from '@scure/base';

export const MAX_MESSAGE = 32768;
export const MAX_CONTENT = 8192;
export const utf8 = new TextEncoder();
export const hex = (bytes: Uint8Array) => bytesToHex(bytes);
export const digest = (bytes: Uint8Array) => hex(sha256(bytes));
export type Method = 'get_public_key' | 'sign_event' | 'nip44_encrypt' | 'nip44_decrypt';
export type Request = { id: string; method: Method; params: string[] };
export type EventTemplate = { pubkey: string; created_at: number; kind: number; tags: string[][]; content: string };
export type SignedEvent = EventTemplate & { id: string; sig: string };
export const methods: Method[] = ['get_public_key', 'sign_event', 'nip44_encrypt', 'nip44_decrypt'];

export function text(value: unknown, max = MAX_MESSAGE): string {
  if (typeof value !== 'string' || utf8.encode(value).length > max) throw Error('Text exceeds the supported limit.');
  for (const character of value) {
    const n = character.codePointAt(0)!;
    if (n >= 0xd800 && n <= 0xdfff) throw Error('Invalid Unicode text.');
  }
  return value;
}

// Reject duplicate fields before JSON.parse can silently replace signed data.
export function parseJSON(input: string, max = MAX_MESSAGE): unknown {
  text(input, max); let at = 0; let nodes = 0;
  const space = () => { while (/^[\t\n\r ]$/.test(input[at] ?? '')) at++; };
  function string(): string {
    const start = at++;
    while (at < input.length) {
      const char = input[at++];
      if (char === '"') return text(JSON.parse(input.slice(start, at)));
      if (char === '\\') at++;
    }
    throw Error('Unclosed JSON string.');
  }
  function value(depth: number): unknown {
    if (depth > 16 || ++nodes > 8192) throw Error('JSON structure exceeds the supported limit.');
    space(); const char = input[at];
    if (char === '"') return string();
    if (char === '{' || char === '[') {
      const object = char === '{'; const end = object ? '}' : ']'; at++; space();
      const result: Record<string, unknown> | unknown[] = object ? Object.create(null) : [];
      if (input[at] === end) { at++; return result; }
      while (true) {
        space();
        if (object) {
          if (input[at] !== '"') throw Error('Invalid JSON field.');
          const key = string(); space();
          if (Object.hasOwn(result, key) || input[at++] !== ':') throw Error('Duplicate or invalid JSON field.');
          (result as Record<string, unknown>)[key] = value(depth + 1);
        } else (result as unknown[]).push(value(depth + 1));
        space(); const next = input[at++];
        if (next === end) return result;
        if (next !== ',') throw Error('Invalid JSON separator.');
      }
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(input.slice(at));
    if (!token) throw Error('Invalid JSON value.');
    at += token[0].length; const parsed = JSON.parse(token[0]);
    if (typeof parsed === 'number' && !Number.isFinite(parsed)) throw Error('Invalid JSON number.');
    return parsed;
  }
  const result = value(0); space();
  if (at !== input.length) throw Error('Trailing JSON data.');
  return result;
}

export function object(input: unknown): Record<string, unknown> {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('Expected a JSON object.');
  return input as Record<string, unknown>;
}

export function publicKey(input: unknown): string {
  if (typeof input !== 'string' || !/^[a-f0-9]{64}$/.test(input)) throw Error('A 32-byte public key is required.');
  schnorr.Point.fromHex(`02${input}`);
  return input;
}

export function identity(input: string): string {
  input = input.trim().replace(/^nostr:/, '');
  if (input.startsWith('npub1')) {
    const decoded = bech32.decode(input as `${string}1${string}`, 90);
    if (decoded.prefix !== 'npub') throw Error('Use an npub public identity.');
    return publicKey(hex(bech32.fromWords(decoded.words)));
  }
  return publicKey(input);
}

export const npub = (key: string) => bech32.encode('npub', bech32.toWords(hexToBytes(publicKey(key))));
export const canonical = (event: EventTemplate) => JSON.stringify([0, event.pubkey, event.created_at, event.kind, event.tags, event.content]);
export const eventId = (event: EventTemplate) => digest(utf8.encode(canonical(event)));

function cipher(input: string): Uint8Array {
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(input)) throw Error('Invalid NIP-44 ciphertext.');
  const decoded = atob(input);
  if (btoa(decoded) !== input || decoded.length < 99 || decoded.charCodeAt(0) !== 2) throw Error('Invalid NIP-44 ciphertext.');
  return Uint8Array.from(decoded, char => char.charCodeAt(0));
}

export function template(input: unknown, key: string, contentLimit = MAX_CONTENT): EventTemplate {
  const row = object(input);
  if (Object.keys(row).some(k => !['pubkey', 'created_at', 'kind', 'tags', 'content', 'id'].includes(k))) throw Error('Unsupported event field.');
  if (row.pubkey !== undefined && row.pubkey !== key) throw Error('The request uses a different identity.');
  if (!Number.isSafeInteger(row.created_at) || (row.created_at as number) < 0 ||
      !Number.isInteger(row.kind) || (row.kind as number) < 0 || (row.kind as number) > 65535) throw Error('Invalid event kind or timestamp.');
  if (!Array.isArray(row.tags) || row.tags.length > 256) throw Error('Too many event tags.');
  const tags = row.tags.map(tag => {
    if (!Array.isArray(tag) || tag.length < 1 || tag.length > 8) throw Error('Invalid event tag.');
    return tag.map(field => text(field, MAX_CONTENT));
  });
  const event = { pubkey: publicKey(key), created_at: row.created_at as number, kind: row.kind as number, tags, content: text(row.content, contentLimit) };
  text(JSON.stringify(event));
  if (row.id !== undefined && row.id !== eventId(event)) throw Error('The supplied event ID does not match the event.');
  return event;
}

export function signedEvent(input: unknown, expected?: EventTemplate, contentLimit = MAX_CONTENT): SignedEvent {
  const row = object(input);
  if (Object.keys(row).length !== 7 || !Object.hasOwn(row, 'id') || !Object.hasOwn(row, 'sig')) throw Error('Invalid signed event fields.');
  const { sig, ...unsigned } = row;
  const event = template(unsigned, publicKey(row.pubkey), contentLimit);
  if (typeof sig !== 'string' || !/^[a-f0-9]{128}$/.test(sig)) throw Error('Invalid signature encoding.');
  const id = eventId(event);
  if (row.id !== id || !schnorr.verify(hexToBytes(sig), hexToBytes(id), hexToBytes(event.pubkey))) throw Error('Event ID or signature verification failed.');
  if (expected && canonical(event) !== canonical(expected)) throw Error('The device returned a changed event.');
  return { ...event, id, sig };
}

export function request(method: Method, params: unknown[], key: string | null): Request {
  if (!methods.includes(method)) throw Error('Unsupported signer method.');
  let values: string[];
  if (method === 'get_public_key') {
    if (params.length) throw Error('This method takes no parameters.');
    values = [];
  } else {
    if (!key) throw Error('Connect your device identity first.');
    if (method === 'sign_event') {
      if (params.length !== 1) throw Error('One event is required.');
      values = [JSON.stringify(template(typeof params[0] === 'string' ? parseJSON(params[0]) : params[0], key))];
    } else {
      if (params.length !== 2) throw Error('A public key and message are required.');
      values = [publicKey(params[0]), text(params[1], method === 'nip44_encrypt' ? MAX_CONTENT : MAX_MESSAGE - 512)];
      if (!values[1]) throw Error('The message is empty.');
      if (method === 'nip44_decrypt') cipher(values[1]);
    }
  }
  const result = { id: crypto.randomUUID(), method, params: values };
  text(JSON.stringify(result));
  return result;
}

export function response(input: string, pending: Request, key: string | null): string | SignedEvent {
  const row = object(parseJSON(input));
  if (row.id !== pending.id) throw Error('This response belongs to a different request.');
  if (Object.keys(row).length !== 2 || ('result' in row) === ('error' in row)) throw Error('Invalid device response.');
  if ('error' in row) throw Error(`Device: ${text(row.error, 512)}`);
  const result = text(row.result);
  if (pending.method === 'get_public_key') {
    const actual = publicKey(result);
    if (key && actual !== key) throw Error('The device identity does not match the selected npub.');
    return actual;
  }
  if (pending.method === 'sign_event') return signedEvent(parseJSON(result), template(parseJSON(pending.params[0]), key!));
  if (pending.method === 'nip44_encrypt') {
    const length = utf8.encode(pending.params[1]).length;
    const nextPower = 2 ** Math.ceil(Math.log2(length));
    const chunk = nextPower <= 256 ? 32 : nextPower / 8;
    const padded = length <= 32 ? 32 : chunk * Math.ceil(length / chunk);
    if (cipher(result).length !== 67 + padded) throw Error('NIP-44 result length does not match the request.');
  }
  if (pending.method === 'nip44_decrypt') text(result, MAX_CONTENT);
  return result;
}
