import QRCode from 'qrcode';
import { Camera } from './camera.ts';
import { Owner } from './owner.ts';
import type { Result } from './owner.ts';
import { npub, methods } from './protocol.ts';
import type { Method, SignedEvent } from './protocol.ts';
import { RemoteSigner, publishNote, relayURL } from './relay.ts';
import { messagesUI } from './messages-ui.ts';

declare const chrome: any;
const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const input = (id: string) => get<HTMLInputElement>(id);
const button = (id: string, action: () => unknown) => get(id).addEventListener('click', () => { Promise.resolve().then(action).catch(fail); });
const dialog = (id: string) => get<HTMLDialogElement>(id);
const status = (message: string, error = false) => { get('status').textContent = message; get('status').classList.toggle('error', error); };
const fail = (error: unknown) => status(error instanceof Error ? error.message : String(error), true);
const owner = new Owner(render);
const messages = messagesUI(owner);
let frame = 0, paused = false, activeId = '', signed: SignedEvent | null = null, remote: RemoteSigner | null = null;
let cameraMode: 'identity' | 'response' = 'response';
let permission: { resolve: (allowed: boolean) => void; origin: string } | null = null;
let extensionPort: any;
const camera = new Camera(get<HTMLVideoElement>('video'), code => {
  try {
    if (cameraMode === 'identity') { messages.clear(); closeRemote(); owner.select(code); stopCamera(); status('Public identity selected. Read it from the device to confirm.'); }
    else if (owner.scan(code)) { stopCamera(); status('Device response received.'); }
    else { const { received, total } = owner.collector.progress; get('camera-status').textContent = `Collected ${received} of ${total} response frames.`; }
  } catch (error) { get('camera-status').textContent = error instanceof Error ? error.message : 'Could not read this QR.'; }
}, message => { get('camera-status').textContent = message; });

function closePermission(allowed: boolean) {
  const current = permission; permission = null; dialog('permission').close(); current?.resolve(allowed);
}
function ask(origin: string, method: Method | 'connect', detail: string): Promise<boolean> {
  if (permission || owner.operation || owner.reserved) return Promise.resolve(false);
  get('permission-title').textContent = method === 'connect' ? 'Pair this client?' : `Allow ${method.replaceAll('_', ' ')}?`;
  get('permission-origin').textContent = origin; get('permission-detail').textContent = detail;
  dialog('permission').showModal(); return new Promise(resolve => { permission = { resolve, origin }; });
}
function stopCamera() { camera.stop(); dialog('camera').close(); }
async function startCamera(mode: 'identity' | 'response') {
  cameraMode = mode; dialog('camera').showModal(); get('camera-status').textContent = 'Starting camera…';
  try {
    await camera.start();
    const choices = get<HTMLSelectElement>('camera-choice'); choices.replaceChildren();
    for (const device of (await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === 'videoinput')) {
      const option = document.createElement('option'); option.value = device.deviceId; option.textContent = device.label || `Camera ${choices.length + 1}`; choices.append(option);
    }
  } catch (error) { stopCamera(); throw error; }
}
function clearResult() { signed = null; input('result').value = ''; get('result-panel').hidden = true; get('publish-controls').hidden = true; }
function showResult(result: Result) {
  signed = typeof result === 'string' ? null : result;
  input('result').value = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
  get('result-title').textContent = signed ? 'Verified signed event' : 'Device result';
  get('result-panel').hidden = false; get('publish-controls').hidden = !signed;
  status(signed ? 'Signature verified. Publish when you are ready.' : 'Device response received.');
}
async function local(method: Method, params: unknown[]) {
  clearResult(); const result = await owner.start('This companion', method, params, true); showResult(result);
}
function drawQR() {
  const operation = owner.operation; if (!operation) return;
  frame %= operation.frames.length;
  get('frame-count').textContent = `${frame + 1} / ${operation.frames.length}`;
  void QRCode.toCanvas(get<HTMLCanvasElement>('request-qr'), operation.frames[frame], { scale: 5, margin: 4, errorCorrectionLevel: 'M', color: { dark: '#000000', light: '#ffffff' } }).catch(fail);
}
function render() {
  get('selected').textContent = owner.key ? npub(owner.key) : 'No identity selected.';
  const operation = owner.operation;
  if (operation) {
    if (activeId !== operation.request.id) {
      clearResult(); activeId = operation.request.id; frame = 0; paused = false; get('pause').textContent = 'Pause';
      get('operation-title').textContent = operation.request.method.replaceAll('_', ' ');
      get('operation-origin').textContent = operation.origin;
      if (!dialog('operation').open) dialog('operation').showModal(); drawQR();
    }
    const progress = owner.collector.progress;
    get('progress').textContent = progress.total ? `Collected ${progress.received} of ${progress.total} response frames.` : 'Waiting for the device response.';
  } else {
    activeId = ''; dialog('operation').close();
    if (cameraMode === 'response') stopCamera();
    const canvas = get<HTMLCanvasElement>('request-qr'); canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
  }
  const grants = get('grants'); grants.replaceChildren();
  for (const [origin, permissions] of owner.grants) {
    const row = document.createElement('li'), label = document.createElement('span'), revoke = document.createElement('button');
    label.textContent = `${origin} — ${[...permissions].join(', ')}`; revoke.textContent = 'Revoke'; revoke.className = 'quiet';
    revoke.onclick = () => owner.revoke(origin); row.append(label, revoke); grants.append(row);
  }
  get('grants-panel').hidden = !owner.grants.size;
}
setInterval(() => { if (owner.operation && !paused) { frame++; drawQR(); } }, 500);
button('select', () => { messages.clear(); closeRemote(); owner.select(input('identity').value); status('Public identity selected. Read it from the device to confirm.'); });
button('connect', () => local('get_public_key', []));
button('scan-identity', () => startCamera('identity'));
button('sign', () => local('sign_event', [{ kind: 1, created_at: Math.floor(Date.now() / 1000), tags: [], content: input('note').value }]));
button('cancel', () => owner.cancel());
dialog('operation').addEventListener('cancel', event => { event.preventDefault(); owner.cancel(); });
button('pause', () => { paused = !paused; get('pause').textContent = paused ? 'Play' : 'Pause'; });
button('next', () => { frame++; drawQR(); });
button('previous', () => { frame = Math.max(0, frame - 1); drawQR(); });
button('scan-response', () => startCamera('response'));
button('camera-stop', stopCamera);
dialog('camera').addEventListener('cancel', event => { event.preventDefault(); stopCamera(); });
get('camera-choice').addEventListener('change', () => { void camera.start(input('camera-choice').value).catch(fail); });
button('deny', () => closePermission(false)); button('allow', () => closePermission(true));
dialog('permission').addEventListener('cancel', event => { event.preventDefault(); closePermission(false); });
button('clear-result', clearResult);
button('copy-result', () => navigator.clipboard.writeText(input('result').value));
button('copy-bunker', () => navigator.clipboard.writeText(input('bunker').value));
button('publish', async () => { if (!signed) throw Error('There is no verified event to publish.'); await publishNote(signed, input('publish-relay').value); status('Relay accepted the signed event.'); });
button('remote-start', async () => {
  if (!owner.key) throw Error('Connect your device identity first.');
  remote?.close(); remote = new RemoteSigner(relayURL(input('relay').value), owner, ask, message => { if (remote?.client) input('bunker').value = ''; status(message); });
  await remote.open(); input('bunker').value = remote.bunker; get('remote-info').hidden = false; get('remote-stop').hidden = false;
});
button('accept-client', async () => { if (!remote) throw Error('Open a relay session first.'); await remote.acceptClient(input('client-link').value); input('bunker').value = ''; input('client-link').value = ''; });
function closeRemote() { if (permission?.origin.startsWith('NIP-46 ')) closePermission(false); remote?.close(); remote = null; input('bunker').value = ''; input('client-link').value = ''; get('remote-info').hidden = true; get('remote-stop').hidden = true; }
button('remote-stop', closeRemote);
button('disconnect', () => { messages.clear(); closePermission(false); closeRemote(); owner.disconnect(); clearResult(); stopCamera(); input('identity').value = ''; input('note').value = ''; status('Disconnected.'); });
window.addEventListener('pagehide', () => { messages.cancel(); closePermission(false); remote?.close(); owner.disconnect(); camera.stop(); });

if (typeof chrome !== 'undefined' && chrome.runtime?.id) {
  extensionPort = chrome.runtime.connect({ name: 'companion' });
  const heartbeat = setInterval(() => { try { extensionPort.postMessage({ type: 'ping' }); } catch { clearInterval(heartbeat); } }, 20000);
  extensionPort.onMessage.addListener(async (message: any) => {
    if (message.type === 'cancel') {
      if (permission?.origin === message.origin) closePermission(false);
      if (owner.operation?.origin === message.origin) owner.cancel('The client disconnected.');
      return;
    }
    if (message.type !== 'request' || typeof message.id !== 'string' || typeof message.origin !== 'string' || !methods.includes(message.method)) return;
    try {
      if (!owner.grants.get(message.origin)?.has(message.method)) {
        if (!await ask(message.origin, message.method, 'Allow this method for this browser session. You still review every request on your device.')) throw Error('Permission rejected.');
        owner.grant(message.origin, message.method);
      }
      const result = await owner.start(message.origin, message.method, message.params);
      extensionPort.postMessage({ type: 'response', id: message.id, result });
      status(`${message.method === 'sign_event' ? 'Verified signed event' : 'Device result'} returned to ${message.origin}.`);
    } catch (error) { extensionPort.postMessage({ type: 'response', id: message.id, error: error instanceof Error ? error.message : 'Request failed.' }); }
  });
  extensionPort.onDisconnect.addListener(() => { clearInterval(heartbeat); messages.clear(); owner.disconnect(); closePermission(false); status('Browser connection closed. Reload the companion to reconnect.', true); });
}
render();
