import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import QRCode from 'qrcode';
import jsQR from 'jsqr';
import { finalizeEvent, getPublicKey } from 'nostr-tools/pure';

// Optical simulation: real browser pixels/decoder, public test key, no device claim.
const secret = new Uint8Array(32); secret[31] = 1;
const key = getPublicKey(secret);
const root = resolve(import.meta.dirname, '..');
await mkdir(resolve(root, '.cache'), { recursive: true });
const profile = await mkdtemp(resolve(root, '.cache/browser-'));
const server = spawn(process.execPath, ['serve.mjs'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
let context;
try {
  await new Promise((resolve, reject) => {
    server.stdout.on('data', data => { if (String(data).includes('http://127.0.0.1:8787')) resolve(); });
    server.once('error', reject); server.once('exit', code => reject(Error(`Companion server exited: ${code}`)));
    server.stderr.on('data', data => process.stderr.write(data));
  });
  context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
    args: [`--disable-extensions-except=${resolve(root, 'dist')}`, `--load-extension=${resolve(root, 'dist')}`],
    viewport: { width: 1100, height: 900 } });
  await context.addInitScript(() => {
    window.__testQRImages = [];
    window.__testTracks = [];
    if (!navigator.mediaDevices) return;
    Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', { configurable: true, value: async () => [{ kind: 'videoinput', deviceId: 'pixels', label: 'QR pixel stream', groupId: 'test' }] });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { configurable: true, value: async () => {
      if (!window.__testQRImages.length) throw Error('No test QR pixels supplied.');
      const images = await Promise.all(window.__testQRImages.map(source => new Promise(resolve => { const image = new Image(); image.onload = () => resolve(image); image.src = source; })));
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = 512;
      const ctx = canvas.getContext('2d'); let index = 0;
      const draw = () => { ctx.fillStyle = 'white'; ctx.fillRect(0, 0, 512, 512); ctx.drawImage(images[index++ % images.length], 0, 0, 512, 512); };
      draw(); const timer = setInterval(draw, 350); const stream = canvas.captureStream(15);
      for (const track of stream.getTracks()) { const stop = track.stop.bind(track); track.stop = () => { clearInterval(timer); stop(); }; window.__testTracks.push(track); }
      return stream;
    } });
  });
  async function requestFromPixels(page) {
    await page.locator('#operation[open]').waitFor();
    const chunks = new Map(); let id, total;
    for (let attempt = 0; attempt < 30; attempt++) {
      const pixels = await page.locator('#request-qr').evaluate(canvas => ({ data: [...canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data], width: canvas.width, height: canvas.height }));
      const qr = jsQR(Uint8ClampedArray.from(pixels.data), pixels.width, pixels.height);
      if (qr) {
        const parts = qr.data.split(':'); assert.equal(parts[0], 'ns');
        id ??= parts[1]; total ??= Number(parts[3]); assert.equal(parts[1], id); assert.equal(Number(parts[3]), total);
        chunks.set(Number(parts[2]), Buffer.from(parts[4], 'base64url'));
        if (chunks.size === total) {
          const message = Buffer.concat(Array.from({ length: total }, (_, index) => chunks.get(index)));
          assert.equal(createHash('sha256').update(message).digest('hex'), id);
          return JSON.parse(message.toString('utf8'));
        }
      }
      await page.waitForTimeout(150);
    }
    throw Error('Could not decode the displayed request pixels.');
  }
  async function scanResponse(page, request, result) {
    const message = Buffer.from(JSON.stringify({ id: request.id, result: typeof result === 'string' ? result : JSON.stringify(result) }));
    const digest = createHash('sha256').update(message).digest('hex'), count = Math.ceil(message.length / 384);
    const codes = await Promise.all(Array.from({ length: count }, (_, index) => QRCode.toDataURL(`ns:${digest}:${index}:${count}:${message.subarray(index * 384, (index + 1) * 384).toString('base64url')}`, { width: 512, margin: 4, errorCorrectionLevel: 'M' })));
    await page.evaluate(images => { window.__testQRImages = images; }, codes);
    await page.getByRole('button', { name: 'Scan device response', exact: true }).click();
    await page.locator('#operation').waitFor({ state: 'hidden', timeout: 20000 });
    assert.equal(await page.evaluate(() => window.__testTracks.every(track => track.readyState === 'ended')), true);
  }
  const page = await context.newPage(); const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8787');
  await page.getByRole('button', { name: 'Read from device', exact: true }).click();
  let request = await requestFromPixels(page); assert.equal(request.method, 'get_public_key');
  await scanResponse(page, request, key); await page.waitForFunction(() => !document.querySelector('#result-panel').hidden);
  await page.locator('#note').fill('Actual QR pixels, exact note.');
  await page.getByRole('button', { name: 'Review on device', exact: true }).click();
  request = await requestFromPixels(page); assert.equal(request.method, 'sign_event');
  const unsigned = JSON.parse(request.params[0]); assert.equal(unsigned.pubkey, key); assert.equal(unsigned.content, 'Actual QR pixels, exact note.');
  const signed = finalizeEvent(unsigned, secret); await scanResponse(page, request, signed);
  await page.waitForFunction(() => document.querySelector('#result-title').textContent === 'Verified signed event');
  assert.equal(JSON.parse(await page.locator('#result').inputValue()).id, signed.id);
  await page.screenshot({ path: resolve(root, '.cache/browser-result.png'), fullPage: true });
  console.log('PASS browser: displayed QR pixels → decoded request → animated response video → verified exact signed result; camera stopped.');

  await context.route('http://127.0.0.1:8787/client', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>NIP07 client</title><h1>Client</h1>' }));
  const client = await context.newPage(); await client.goto('http://127.0.0.1:8787/client');
  await client.waitForFunction(() => !!window.nostr);
  await client.evaluate(() => { window.__result = null; window.nostr.getPublicKey().then(result => window.__result = { result }).catch(error => window.__result = { error: error.message }); });
  let companion;
  for (let attempt = 0; attempt < 40 && !companion; attempt++) { companion = context.pages().find(item => item.url().startsWith('chrome-extension:')); if (!companion) await page.waitForTimeout(100); }
  assert.ok(companion); companion.on('pageerror', error => errors.push(error.message));
  await companion.locator('#permission[open]').waitFor();
  assert.equal(await companion.locator('#permission-origin').textContent(), 'http://127.0.0.1:8787');
  await companion.getByRole('button', { name: 'Allow this session' }).click();
  request = await requestFromPixels(companion); await scanResponse(companion, request, key);
  await client.waitForFunction(() => window.__result !== null); assert.equal((await client.evaluate(() => window.__result)).result, key);
  // Chrome may stop an idle service worker after 30 seconds; the open companion keeps its port alive.
  await companion.waitForTimeout(35000);
  await client.evaluate(() => { window.__result = null; window.nostr.signEvent({ kind: 1, created_at: 1710000000, tags: [], content: 'Extension note' }).then(result => window.__result = { result }).catch(error => window.__result = { error: error.message }); });
  await companion.locator('#permission[open]').waitFor(); await companion.getByRole('button', { name: 'Allow this session' }).click();
  request = await requestFromPixels(companion); assert.equal(JSON.parse(request.params[0]).pubkey, key);
  await scanResponse(companion, request, finalizeEvent(JSON.parse(request.params[0]), secret));
  await client.waitForFunction(() => window.__result !== null); assert.equal((await client.evaluate(() => window.__result)).result.content, 'Extension note');
  await client.evaluate(() => { window.__result = null; window.nostr.signEvent({ kind: 1, created_at: 1710000001, tags: [], content: 'Cancel me' }).catch(error => window.__result = { error: error.message }); });
  await companion.locator('#operation[open]').waitFor(); await companion.getByRole('button', { name: 'Cancel', exact: true }).click();
  await client.waitForFunction(() => window.__result !== null); assert.match((await client.evaluate(() => window.__result)).error, /cancelled/);
  await client.evaluate(() => { window.nostr.signEvent({ kind: 1, created_at: 1710000002, tags: [], content: 'Navigation cancellation' }).catch(() => {}); });
  await companion.locator('#operation[open]').waitFor(); await client.goto('about:blank');
  await companion.locator('#operation').waitFor({ state: 'hidden' });
  assert.deepEqual(errors, []);
  await companion.screenshot({ path: resolve(root, '.cache/browser-extension.png'), fullPage: true });
  console.log('PASS extension: actual window.nostr provider, trusted origin grant, idle worker lifetime, optical key/sign requests, verified result, cancellation and client navigation cleanup.');
} finally {
  await context?.close(); server.kill('SIGTERM');
}
