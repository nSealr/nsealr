import { Owner } from './owner.ts';
import { createRumor, messageRelays, publishCopies, readMessage, readWrap, relayCommand, sealCopies } from './messaging.ts';
import type { Copy } from './messaging.ts';
import type { SignedEvent } from './protocol.ts';
import { identity, npub } from './protocol.ts';
import { relayURL } from './relay.ts';

export function messagesUI(owner: Owner) {
  const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const input = (id: string) => get<HTMLInputElement>(id);
  let active: AbortController | null = null, copies: Copy[] = [], envelopes: SignedEvent[] = [], copyAuthor: string | null = null;
  const status = (message: string) => { get('message-status').textContent = message; };
  const urls = (id: string) => {
    const values = input(id).value.trim().split(/\s+/).filter(Boolean);
    if (!values.length || values.length > 3) throw Error('Enter one to three secure relay URLs.');
    return [...new Set(values.map(relayURL))];
  };
  const lockedButtons = ['select', 'connect', 'scan-identity', 'sign', 'publish', 'remote-start', 'accept-client', 'send-message', 'load-messages', 'save-inbox', 'retry-message'];
  const renderCopies = () => {
    const list = get('message-copies'); list.replaceChildren();
    for (const copy of copies) {
      const item = document.createElement('li');
      item.textContent = `${copy.recipient === owner.key ? 'Your copy' : 'Recipient copy'}: ${copy.accepted.length ? `accepted by ${copy.accepted.length} of ${copy.relays.length} inbox relays` : Object.keys(copy.errors).length ? 'not accepted; retry available' : 'ready to publish'}.`;
      list.append(item);
    }
    get('retry-message').hidden = !copies.some(copy => copy.accepted.length < copy.relays.length);
  };
  const run = async (work: (signal: AbortSignal) => Promise<void>) => {
    if (active || owner.operation) throw Error('Finish or cancel the current device request first.');
    if (!owner.key) throw Error('Select your public identity first.');
    const controller = new AbortController(); active = controller; owner.reserved = true;
    for (const id of lockedButtons) get<HTMLButtonElement>(id).disabled = true;
    get('cancel-message').hidden = false;
    try { await work(controller.signal); }
    catch (error) { status(error instanceof Error ? error.message : 'Message operation failed.'); }
    finally {
      active = null; owner.reserved = false; get('cancel-message').hidden = true;
      for (const id of lockedButtons) get<HTMLButtonElement>(id).disabled = false;
    }
  };
  const click = (id: string, action: () => unknown) => get(id).addEventListener('click', () => { Promise.resolve().then(action).catch(error => status(error.message)); });
  click('send-message', () => run(async signal => {
    copies = []; copyAuthor = owner.key; renderCopies();
    const recipient = identity(input('message-recipient').value), rumor = createRumor(owner.key!, recipient, input('message-text').value);
    status('Finding signed inbox preferences for you and the recipient…');
    const boxes = await messageRelays(owner, [...new Set([owner.key!, recipient])], urls('discovery-relays'), signal);
    status('Review the message and each encrypted copy on your device.');
    copies = await sealCopies(owner, rumor, boxes, signal); renderCopies();
    status('Publishing the encrypted recipient and sender copies…');
    await publishCopies(owner, copies, signal, renderCopies);
    status(copies.every(copy => copy.accepted.length) ? 'Each copy was accepted by an inbox relay. This does not prove the recipient has read it.' : 'Some copies were not accepted. Check the per-copy status before retrying.');
  }));
  click('retry-message', () => run(async signal => {
    if (!owner.key || owner.key !== copyAuthor) throw Error('The selected identity changed. Compose a new message.');
    await publishCopies(owner, copies, signal, renderCopies);
    status(copies.every(copy => copy.accepted.length) ? 'Each copy was accepted by an inbox relay.' : 'Some copies remain unaccepted.');
  }));
  click('save-inbox', () => run(async signal => {
    const inboxes = urls('inbox-relays'), discovery = urls('discovery-relays');
    const event = await owner.start('Message inbox preferences', 'sign_event', [{ kind: 10050, created_at: Math.floor(Date.now() / 1000), tags: inboxes.map(url => ['relay', url]), content: '' }], true);
    if (typeof event === 'string') throw Error('Invalid inbox preference event.');
    let accepted = 0;
    for (const url of discovery) { await relayCommand(owner, url, event, true, signal); accepted++; status(`Inbox preferences accepted by ${accepted} of ${discovery.length} discovery relays.`); }
  }));
  click('load-messages', () => run(async signal => {
    const boxes = await messageRelays(owner, [owner.key!], urls('discovery-relays'), signal);
    const found = new Map<string, SignedEvent>();
    for (const url of boxes.get(owner.key!)!) {
      const rows = await relayCommand(owner, url, { kinds: [1059], '#p': [owner.key], limit: 30, since: Math.floor(Date.now() / 1000) - 30 * 86400 }, false, signal);
      for (const row of rows) { const event = readWrap(row, owner.key!); found.set(event.id, event); }
    }
    envelopes = [...found.values()].sort((a, b) => b.created_at - a.created_at).slice(0, 60);
    const list = get('message-list'); list.replaceChildren();
    for (const [index, event] of envelopes.entries()) {
      const item = document.createElement('li'), button = document.createElement('button'); button.className = 'quiet';
      button.textContent = `Open encrypted message ${index + 1} · ${event.id.slice(0, 12)}`;
      button.onclick = () => { void run(async readSignal => {
        const message = await readMessage(owner, event, readSignal);
        get('message-author').textContent = `${npub(message.pubkey)} · ${new Date(message.created_at * 1000).toLocaleString()}`;
        get('message-content').textContent = message.content; get('opened-message').hidden = false;
        status('Selected plaintext released by the device. Clear local messages when finished.');
      }).catch(error => status(error.message)); };
      item.append(button); list.append(item);
    }
    status(`${envelopes.length} encrypted envelopes loaded from the last 30 days (up to 30 per inbox, 60 total). Envelope dates are intentionally randomized.`);
  }));
  const cancel = () => { active?.abort(); if (owner.reserved) owner.cancel('Message operation cancelled.'); };
  const clear = () => { cancel(); copies = []; envelopes = []; copyAuthor = null; input('message-text').value = ''; get('message-content').textContent = ''; get('message-author').textContent = ''; get('opened-message').hidden = true; get('message-list').replaceChildren(); renderCopies(); status('Local messages cleared.'); };
  click('cancel-message', cancel); click('clear-messages', clear);
  return { clear, cancel };
}
