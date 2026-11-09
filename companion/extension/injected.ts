(() => {
  const host = window as Window & { nostr?: unknown };
  if (host.nostr || window.top !== window) return;
  const pending = new Map<string, { resolve: (result: any) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> }>();
  window.addEventListener('message', event => {
    const message = event.data;
    if (event.source !== window || event.origin !== location.origin || message?.channel !== 'nsealr:nip07' || message.type !== 'response') return;
    const request = pending.get(message.id); if (!request) return;
    pending.delete(message.id); clearTimeout(request.timer);
    message.error ? request.reject(Error(message.error)) : request.resolve(message.result);
  });
  const call = (method: string, params: unknown[]) => new Promise((resolve, reject) => {
    if (pending.size >= 8) { reject(Error('Too many pending signer requests.')); return; }
    const id = crypto.randomUUID();
    const timer = setTimeout(() => { pending.delete(id); reject(Error('Signer request expired.')); window.postMessage({ channel: 'nsealr:nip07', type: 'cancel', id }, location.origin); }, 10 * 60_000);
    pending.set(id, { resolve, reject, timer }); window.postMessage({ channel: 'nsealr:nip07', type: 'request', id, method, params }, location.origin);
  });
  host.nostr = Object.freeze({
    getPublicKey: () => call('get_public_key', []),
    signEvent: (event: unknown) => call('sign_event', [event]),
    nip44: Object.freeze({ encrypt: (key: string, plaintext: string) => call('nip44_encrypt', [key, plaintext]), decrypt: (key: string, ciphertext: string) => call('nip44_decrypt', [key, ciphertext]) }),
  });
})();
