import { finalizeEvent, generateSecretKey } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { Owner } from './owner.ts';
import { eventId, object, parseJSON, publicKey, signedEvent, template, text, MAX_MESSAGE } from './protocol.ts';
import type { EventTemplate, SignedEvent } from './protocol.ts';
import { relayURL } from './relay.ts';

export type Rumor = EventTemplate & { id: string };
export type Copy = { recipient: string; event: SignedEvent; relays: string[]; accepted: string[]; errors: Record<string, string> };
export const MAX_RUMOR = 4096;
const now = () => Math.floor(Date.now() / 1000);
const randomPast = () => now() - crypto.getRandomValues(new Uint32Array(1))[0] % (2 * 24 * 60 * 60);
const checkSignal = (signal: AbortSignal) => { if (signal.aborted) throw Error('Message operation cancelled.'); };

export function createRumor(author: string, recipient: string, content: string): Rumor {
  const event = template({ created_at: now(), kind: 14, tags: [['p', publicKey(recipient)]], content: text(content) }, author);
  if (!event.content) throw Error('Write a message first.');
  const rumor = { ...event, id: eventId(event) };
  text(JSON.stringify(rumor), MAX_RUMOR);
  return rumor;
}
export function readRumor(input: string, author: string, recipient: string): Rumor {
  const row = object(parseJSON(text(input, MAX_RUMOR)));
  if (!Object.hasOwn(row, 'id')) throw Error('The message has no rumor ID.');
  const event = template(row, author);
  if (event.kind !== 14) throw Error('This is not a supported text message.');
  const peers = event.tags.filter(tag => tag[0] === 'p').map(tag => publicKey(tag[1]));
  if (!peers.length || peers.length > 2 || new Set(peers).size !== peers.length ||
      (peers.length === 2 && !peers.includes(author)) ||
      (author !== recipient && (!peers.includes(recipient) || peers.some(peer => peer !== author && peer !== recipient)))) throw Error('The message recipients do not match this identity.');
  return { ...event, id: eventId(event) };
}
export function readWrap(input: unknown, recipient: string): SignedEvent {
  const event = signedEvent(input, undefined, MAX_MESSAGE);
  const peers = event.tags.filter(tag => tag[0] === 'p');
  if (event.kind !== 1059 || peers.length !== 1 || peers[0][1] !== recipient || peers[0].length < 2 || peers[0].length > 3) throw Error('Gift wrap is not addressed to the selected identity.');
  for (const tag of event.tags) {
    if (tag[0] === 'p') { if (tag[2]) relayURL(tag[2]); }
    else if (tag[0] === 'alt' && tag.length === 2) text(tag[1], 256);
    else throw Error('Unsupported gift-wrap metadata.');
  }
  return event;
}

// One relay command; AUTH always follows that socket's actual challenge through the device.
export function relayCommand(owner: Owner, url: string, filterOrEvent: Record<string, unknown> | SignedEvent, publish: boolean, signal: AbortSignal): Promise<SignedEvent[]> {
  url = relayURL(url); checkSignal(signal);
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url), items: SignedEvent[] = [];
    const subscription = crypto.randomUUID(); let finished = false, authentication = '', authId = '', authenticated = false;
    let timer: ReturnType<typeof setTimeout>;
    const finish = (error?: Error) => {
      if (finished) return; finished = true; clearTimeout(timer); signal.removeEventListener('abort', aborted); socket.close();
      if (owner.operation?.origin === `Relay ${url}`) owner.cancel(error?.message ?? 'Relay request ended before authorization.');
      error ? reject(error) : resolve(items);
    };
    const deadline = (milliseconds: number) => { clearTimeout(timer); timer = setTimeout(() => finish(Error('Relay request timed out.')), milliseconds); };
    const aborted = () => finish(Error('Message operation cancelled.'));
    signal.addEventListener('abort', aborted, { once: true }); deadline(20000);
    const send = () => socket.send(JSON.stringify(publish ? ['EVENT', filterOrEvent] : ['REQ', subscription, filterOrEvent]));
    socket.onopen = send;
    socket.onerror = () => finish(Error('Relay connection failed.'));
    socket.onclose = () => finish(Error('Relay disconnected before completing the request.'));
    socket.onmessage = packet => { void (async () => {
      if (finished || typeof packet.data !== 'string') return;
      const row = parseJSON(packet.data, 50000); if (!Array.isArray(row)) return;
      if (row[0] === 'AUTH') {
        const challenge = text(row[1], 1024);
        if (!challenge || authentication || authenticated) throw Error('Relay changed or repeated its authentication challenge.');
        authentication = challenge; deadline(10 * 60_000);
        const auth = await owner.start(`Relay ${url}`, 'sign_event', [{ kind: 22242, created_at: now(), tags: [['relay', url], ['challenge', challenge]], content: '' }], true);
        checkSignal(signal); if (finished) return;
        if (typeof auth === 'string') throw Error('Invalid relay authorization result.');
        authId = auth.id; socket.send(JSON.stringify(['AUTH', auth])); return;
      }
      if (row[0] === 'OK' && row[1] === authId && authId) {
        if (row[2] !== true) throw Error('Relay rejected authorization.');
        authenticated = true; deadline(20000); send(); return;
      }
      if (row[0] === 'OK' && publish && row[1] === (filterOrEvent as SignedEvent).id) {
        if (row[2] === true) finish();
        else if (!String(row[3]).startsWith('auth-required:')) throw Error('Relay rejected the message.');
      }
      if (row[0] === 'CLOSED' && row[1] === subscription && !String(row[2]).startsWith('auth-required:')) throw Error('Relay refused the message query.');
      if (row[0] === 'EVENT' && row[1] === subscription) {
        if (items.length >= 100) throw Error('Too many relay results. Narrow the history window.');
        items.push(signedEvent(row[2], undefined, MAX_MESSAGE));
      }
      if (row[0] === 'EOSE' && row[1] === subscription) finish();
    })().catch(error => finish(error instanceof Error ? error : Error('Relay request failed.'))); };
  });
}

export async function messageRelays(owner: Owner, keys: string[], discovery: string[], signal: AbortSignal): Promise<Map<string, string[]>> {
  if (!discovery.length || discovery.length > 3) throw Error('Choose one to three discovery relays.');
  const found = new Map<string, SignedEvent>(); let successful = 0;
  for (const url of discovery) {
    checkSignal(signal);
    const generation = owner.generation;
    let events: SignedEvent[];
    try { events = await relayCommand(owner, url, { kinds: [10050], authors: keys, limit: 6 }, false, signal); }
    catch (error) { if (signal.aborted || generation !== owner.generation) throw error; continue; }
    successful++;
    for (const event of events) if (event.kind === 10050 && keys.includes(event.pubkey) && (!found.has(event.pubkey) || found.get(event.pubkey)!.created_at < event.created_at)) found.set(event.pubkey, event);
  }
  const result = new Map<string, string[]>();
  for (const key of keys) {
    const event = found.get(key);
    if (!successful || !event || event.content || !event.tags.length || event.tags.length > 8 || event.tags.some(tag => tag[0] !== 'relay' || tag.length !== 2)) throw Error(`No supported signed message-relay list found for ${key}.`);
    result.set(key, [...new Set(event.tags.map(tag => relayURL(tag[1])))]);
  }
  return result;
}

export async function sealCopies(owner: Owner, rumor: Rumor, mailboxes: Map<string, string[]>, signal: AbortSignal): Promise<Copy[]> {
  if (owner.key !== rumor.pubkey) throw Error('The selected identity changed.');
  const recipient = rumor.tags.find(tag => tag[0] === 'p')![1];
  const copies: Copy[] = [];
  for (const peer of [...new Set([recipient, rumor.pubkey])]) {
    checkSignal(signal);
    const relays = mailboxes.get(peer); if (!relays?.length) throw Error('The recipient has no signed message-relay list.');
    const cipher = await owner.start('Private message', 'nip44_encrypt', [peer, JSON.stringify(rumor)], true);
    checkSignal(signal); if (typeof cipher !== 'string') throw Error('Invalid encryption result.');
    const seal = await owner.start('Private message', 'sign_event', [{ pubkey: rumor.pubkey, created_at: randomPast(), kind: 13, tags: [], content: cipher }], true);
    checkSignal(signal); if (typeof seal === 'string') throw Error('Invalid seal result.');
    const ephemeral = generateSecretKey(), conversation = nip44.utils.getConversationKey(ephemeral, peer);
    try {
      const content = nip44.encrypt(JSON.stringify(seal), conversation);
      const event = finalizeEvent({ kind: 1059, created_at: randomPast(), tags: [['p', peer]], content }, ephemeral);
      text(JSON.stringify(event)); copies.push({ recipient: peer, event, relays, accepted: [], errors: {} });
    } finally { ephemeral.fill(0); conversation.fill(0); }
  }
  return copies;
}
export async function publishCopies(owner: Owner, copies: Copy[], signal: AbortSignal, changed: () => void): Promise<void> {
  for (const copy of copies) for (const url of copy.relays) {
    checkSignal(signal); if (copy.accepted.includes(url)) continue;
    const generation = owner.generation;
    try { await relayCommand(owner, url, copy.event, true, signal); copy.accepted.push(url); delete copy.errors[url]; }
    catch (error) { copy.errors[url] = error instanceof Error ? error.message : 'Publication failed.'; if (signal.aborted || generation !== owner.generation) { changed(); throw error; } }
    changed();
  }
}
export async function readMessage(owner: Owner, input: unknown, signal: AbortSignal): Promise<Rumor> {
  const recipient = owner.key; if (!recipient) throw Error('Select your public identity first.');
  const wrap = readWrap(input, recipient); checkSignal(signal);
  const clearSeal = await owner.start('Open selected message', 'nip44_decrypt', [wrap.pubkey, wrap.content], true);
  checkSignal(signal); if (typeof clearSeal !== 'string') throw Error('Invalid gift-wrap result.');
  const seal = signedEvent(parseJSON(clearSeal));
  if (seal.kind !== 13 || seal.tags.length) throw Error('Invalid private-message seal.');
  const plaintext = await owner.start('Read selected message', 'nip44_decrypt', [seal.pubkey, seal.content], true);
  checkSignal(signal); if (typeof plaintext !== 'string') throw Error('Invalid private-message result.');
  return readRumor(plaintext, seal.pubkey, recipient);
}
