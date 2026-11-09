import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import { fixtureCamera, requestFromPixels, scanResponse } from './optical.mjs';
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
  await fixtureCamera(context);
  const page = await context.newPage(); const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8787');
  await page.getByRole('button', { name: 'Read from device', exact: true }).click();
  let request = await requestFromPixels(page); assert.equal(request.method, 'get_public_key');
  await scanResponse(page, request, key); await page.waitForFunction(() => !document.querySelector('#result-panel').hidden);
  const note = 'Actual QR pixels, exact note. '.repeat(24);
  await page.locator('#note').fill(note);
  await page.getByRole('button', { name: 'Review on device', exact: true }).click();
  request = await requestFromPixels(page); assert.equal(request.method, 'sign_event');
  const unsigned = JSON.parse(request.params[0]); assert.equal(unsigned.pubkey, key); assert.equal(unsigned.content, note);
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
