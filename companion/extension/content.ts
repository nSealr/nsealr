declare const chrome: any;
export {};
(() => {
  if (window.top !== window) return;
  let port: any = null, ping: ReturnType<typeof setInterval> | null = null;
  const pending = new Set<string>();
  const reply = (message: unknown) => window.postMessage(message, location.origin);
  function connect() {
    if (port) return;
    port = chrome.runtime.connect({ name: 'nip07' });
    port.onMessage.addListener((message: any) => {
      if (!pending.delete(message.id)) return;
      reply({ channel: 'nsealr:nip07', type: 'response', ...message });
    });
    port.onDisconnect.addListener(() => {
      if (ping) clearInterval(ping); ping = null; port = null;
      for (const id of pending) reply({ channel: 'nsealr:nip07', type: 'response', id, error: 'Companion connection closed.' });
      pending.clear();
    });
    ping = setInterval(() => { if (pending.size) port?.postMessage({ type: 'ping' }); }, 20000);
  }
  window.addEventListener('message', event => {
    const message = event.data;
    if (event.source !== window || event.origin !== location.origin || message?.channel !== 'nsealr:nip07' || typeof message.id !== 'string' || message.id.length > 128) return;
    if (message.type === 'cancel') { if (pending.delete(message.id)) port?.postMessage({ type: 'cancel', id: message.id }); return; }
    if (message.type !== 'request') return;
    if (!['get_public_key', 'sign_event', 'nip44_encrypt', 'nip44_decrypt'].includes(message.method) || !Array.isArray(message.params) || message.params.length > 2) return;
    if (pending.size >= 8 || pending.has(message.id)) return;
    try {
      if (JSON.stringify(message).length > 40000) throw Error('Signer request is too large.');
      connect(); pending.add(message.id); port.postMessage({ type: 'request', id: message.id, method: message.method, params: message.params });
    } catch (error) { pending.delete(message.id); reply({ channel: 'nsealr:nip07', type: 'response', id: message.id, error: error instanceof Error ? error.message : 'Signer connection failed.' }); }
  });
  window.addEventListener('pagehide', () => port?.disconnect());
})();
