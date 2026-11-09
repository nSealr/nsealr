declare const chrome: any;
export {};
let companion: any = null;
let companionTab: number | null = null;
let opening = false;
type Pending = { client: any; clientId: string; origin: string; method: string; params: unknown[]; timer: ReturnType<typeof setTimeout> };
const pending = new Map<string, Pending>();

function reject(id: string, reason: string) {
  const request = pending.get(id); if (!request) return;
  clearTimeout(request.timer); pending.delete(id);
  try { request.client.postMessage({ id: request.clientId, error: reason }); } catch { /* The requesting tab already closed. */ }
}
function forward(id: string, request: Pending) {
  companion?.postMessage({ type: 'request', id, origin: request.origin, method: request.method, params: request.params });
}
function openCompanion() {
  if (companionTab !== null) { void chrome.tabs.update(companionTab, { active: true }); return; }
  if (opening) return;
  opening = true;
  chrome.tabs.create({ url: chrome.runtime.getURL('index.html') }, (tab: { id: number }) => { companionTab = tab.id; opening = false; });
}
chrome.action.onClicked.addListener(openCompanion);
chrome.runtime.onConnect.addListener((port: any) => {
  if (port.name === 'companion') {
    if (port.sender?.url !== chrome.runtime.getURL('index.html') || companion) { port.disconnect(); return; }
    companion = port; companionTab = port.sender.tab?.id ?? null;
    port.onMessage.addListener((message: any) => {
      if (message.type !== 'response') return;
      const request = pending.get(message.id); if (!request) return;
      clearTimeout(request.timer); pending.delete(message.id);
      try { request.client.postMessage({ id: request.clientId, ...(typeof message.error === 'string' ? { error: message.error } : { result: message.result }) }); } catch { /* Client disconnected after completing the request. */ }
    });
    port.onDisconnect.addListener(() => { companion = null; companionTab = null; for (const id of [...pending.keys()]) reject(id, 'Companion closed.'); });
    for (const [id, request] of pending) forward(id, request);
    return;
  }
  if (port.name !== 'nip07' || port.sender?.frameId !== 0 || !port.sender?.tab || !port.sender?.url) { port.disconnect(); return; }
  let origin: string;
  try { const url = new URL(port.sender.url); if (!['https:', 'http:'].includes(url.protocol)) throw Error(); origin = url.origin; }
  catch { port.disconnect(); return; }
  port.onMessage.addListener((message: any) => {
    if (message.type === 'ping') return;
    if (message.type === 'cancel') {
      for (const [id, row] of pending) if (row.client === port && row.clientId === message.id) { reject(id, 'Request cancelled.'); companion?.postMessage({ type: 'cancel', origin, id }); }
      return;
    }
    if (message.type !== 'request' || typeof message.id !== 'string' || message.id.length > 128 || !['get_public_key', 'sign_event', 'nip44_encrypt', 'nip44_decrypt'].includes(message.method) || !Array.isArray(message.params) || message.params.length > 2) return;
    if (pending.size) { port.postMessage({ id: message.id, error: 'Another device request is already open.' }); return; }
    if (JSON.stringify(message).length > 40000) { port.postMessage({ id: message.id, error: 'Signer request is too large.' }); return; }
    const id = crypto.randomUUID();
    const timer = setTimeout(() => { reject(id, 'Request expired.'); companion?.postMessage({ type: 'cancel', origin, id }); }, 10 * 60_000);
    const request = { client: port, clientId: message.id, origin, method: message.method, params: message.params, timer };
    pending.set(id, request);
    if (companion) forward(id, request); openCompanion();
  });
  port.onDisconnect.addListener(() => {
    for (const [id, row] of pending) if (row.client === port) { reject(id, 'The client disconnected.'); companion?.postMessage({ type: 'cancel', origin, id }); }
  });
});
