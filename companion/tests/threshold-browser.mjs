import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import { verifyEvent } from 'nostr-tools/pure';
import { frames } from '../src/frames.ts';
import { fixtureCamera, opticalFromPixels, scanFrames } from './optical.mjs';

// Real native threshold custody, three isolated host devices, automatic review.
// The actual browser/extension and QR decoder run; camera/relay hardware does not.
if (!process.env.THRESHOLD_RUNNER) throw Error('Set THRESHOLD_RUNNER to the three-device native host driver.');
const root = resolve(import.meta.dirname, '..'), cache = resolve(root, '.cache/threshold-browser');
await mkdir(cache, { recursive: true });
const profile = await mkdtemp(resolve(cache, 'profile-'));
const server = spawn(process.execPath, ['serve.mjs'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
const device = spawn(process.env.THRESHOLD_RUNNER, [], { stdio: ['pipe', 'pipe', 'pipe'] });
let context, page, waiting, buffer = '', diagnostic = '';
const errors = [], exchanges = [], outputs = [], indexByKey = new Map();
device.stderr.on('data', data => { diagnostic += data; });
device.stdout.on('data', data => {
  buffer += data;
  while (buffer.includes('\n')) {
    const at = buffer.indexOf('\n'), line = buffer.slice(0, at).trim(); buffer = buffer.slice(at + 1);
    if (!waiting || !line) continue;
    const prefix = `${waiting.index} `;
    if (!line.startsWith(prefix)) { waiting.reject(Error(`Unexpected device output: ${line}`)); continue; }
    const raw = line.slice(prefix.length);
    if (raw === 'END') { clearTimeout(waiting.timer); const current = waiting; waiting = null; current.resolve(current.outputs); }
    else { JSON.parse(raw); waiting.outputs.push(raw); outputs.push({ index: waiting.index, raw }); }
  }
});
device.on('exit', code => { if (waiting) { clearTimeout(waiting.timer); waiting.reject(Error(`Native driver exited ${code}: ${diagnostic}`)); waiting = null; } });
const command = (index, input) => new Promise((resolve, reject) => {
  if (waiting) return reject(Error('A device command is already pending.'));
  waiting = { index, outputs: [], resolve, reject, timer: setTimeout(() => { waiting = null; reject(Error(`Native driver timed out: ${diagnostic}`)); }, 20000) };
  const lines = Array.isArray(input) ? input : [input]; exchanges.push({ index, frames: lines });
  device.stdin.write(lines.map(line => `${index} ${line}\n`).join(''));
});
const scan = async raws => {
  assert.ok(raws.length);
  // Each device keeps animating its current packet while the camera collects it.
  await scanFrames(page, raws.flatMap(raw => { const packet = frames(raw); return [...packet, ...packet]; }), 'Scan device outputs');
};
const optical = previousDigest => opticalFromPixels(page, { dialog: '#threshold-operation', canvas: '#threshold-qr', previousDigest });
async function routePhase(count) {
  const next = []; let previous;
  for (let i = 0; i < count; i++) {
    const packet = await optical(previous); previous = packet.frames[0].split(':')[1];
    const index = indexByKey.get(packet.request.recipient); assert.notEqual(index, undefined);
    next.push(...await command(index, packet.frames));
    await page.locator('#threshold-delivered').click();
  }
  return next;
}
try {
  await new Promise((resolve, reject) => {
    server.stdout.on('data', data => { if (String(data).includes('http://127.0.0.1:8787')) resolve(); });
    server.once('error', reject); server.once('exit', code => reject(Error(`Companion server exited ${code}`)));
  });
  context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
    args: [`--disable-extensions-except=${resolve(root, 'dist')}`, `--load-extension=${resolve(root, 'dist')}`], viewport: { width: 1280, height: 1100 } });
  await fixtureCamera(context);
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
  page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
  await page.goto(new URL('index.html', worker.url()).href);
  const joins = [];
  for (let i = 0; i < 3; i++) {
    const [raw] = await command(i, 'JOIN'); const join = JSON.parse(raw);
    assert.equal(join.type, 'nsealr_join'); indexByKey.set(join.key, i); joins.push(raw);
  }
  await page.locator('#group-create').click(); await scan(joins);
  const setup = await optical(); assert.equal(setup.request.type, 'nsealr_setup');
  const first = []; for (let i = 0; i < 3; i++) first.push(...await command(i, setup.frames));
  assert.equal(first.length, 6); await scan(first);
  const second = await routePhase(6); assert.equal(second.length, 6); await scan(second);
  const groups = await routePhase(6); assert.equal(groups.length, 3); await scan(groups);
  await page.locator('#threshold-operation').waitFor({ state: 'hidden' });
  const descriptor = JSON.parse(await page.locator('#group-record').inputValue());
  assert.equal(descriptor.type, 'nsealr_group');
  for (const raw of groups) { const value = JSON.parse(raw); assert.equal(value.group, descriptor.group); assert.equal(value.pubkey, descriptor.pubkey); }
  await page.screenshot({ path: resolve(cache, 'group-ready.png'), fullPage: true });

  // The real extension's original origin/request remains the owner of this signature.
  await context.route('http://127.0.0.1:8787/threshold-client', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Threshold client</title><h1>Local NIP07 client</h1>' }));
  const client = await context.newPage(); await client.goto('http://127.0.0.1:8787/threshold-client');
  await client.waitForFunction(() => !!window.nostr);
  await client.evaluate(() => { window.__result = null; window.nostr.getPublicKey().then(result => window.__result = { result }).catch(error => window.__result = { error: error.message }); });
  await page.locator('#permission[open]').waitFor();
  assert.equal(await page.locator('#permission-origin').textContent(), 'http://127.0.0.1:8787');
  await page.getByRole('button', { name: 'Allow this session' }).click();
  const publicRequest = await opticalFromPixels(page);
  assert.equal(publicRequest.request.method, 'get_public_key');
  const publicResponse = await command(indexByKey.get(descriptor.members[0]), publicRequest.frames);
  assert.equal(publicResponse.length, 1); await scanFrames(page, frames(publicResponse[0]));
  await client.waitForFunction(() => window.__result !== null);
  assert.equal((await client.evaluate(() => window.__result)).result, descriptor.pubkey);
  const note = 'Exact threshold note through three native host participants and actual QR pixels.';
  await client.evaluate(content => { window.__result = null; window.nostr.signEvent({ kind: 1, created_at: 1710000000, tags: [], content }).then(result => window.__result = { result }).catch(error => window.__result = { error: error.message }); }, note);
  await page.locator('#permission[open]').waitFor();
  assert.equal(await page.locator('#permission-origin').textContent(), 'http://127.0.0.1:8787');
  await page.getByRole('button', { name: 'Allow this session' }).click();
  const start = await optical(); assert.equal(start.request.type, 'nsealr_sign'); assert.equal(JSON.parse(start.request.event).content, note);
  assert.equal(await page.locator('#threshold-origin').textContent(), 'http://127.0.0.1:8787');
  const commitments = [];
  for (const key of start.request.members) commitments.push(...await command(indexByKey.get(key), start.frames));
  assert.equal(commitments.length, 2); await scan(commitments);
  const shares = await routePhase(2); assert.equal(shares.length, 2); await scan(shares);
  const final = await routePhase(2); assert.equal(final.length, 2);
  await scan([final[0]]);
  await client.waitForFunction(() => window.__result !== null);
  const result = await client.evaluate(() => window.__result); assert.equal(result.error, undefined);
  assert.equal(result.result.pubkey, descriptor.pubkey); assert.equal(result.result.content, note); assert.equal(verifyEvent(result.result), true);
  assert.equal(result.result.id, JSON.parse(JSON.parse(final[1]).result).id);
  assert.equal(await page.locator('#threshold-operation').isVisible(), false);
  assert.deepEqual(errors, []);
  await page.screenshot({ path: resolve(cache, 'signature-returned.png'), fullPage: true });
  console.log('PASS threshold UI: real native 2-of-3 setup, signed encrypted phase routing, exact event review on two host participants, actual extension origin, independently verified aggregate signature. Synthetic camera and automatic host review; no physical-device claim.');
} catch (error) {
  errors.push(error.message);
  if (page && !page.isClosed()) { await page.screenshot({ path: resolve(cache, 'failure.png'), fullPage: true }); await writeFile(resolve(cache, 'failure.txt'), await page.locator('body').innerText()); }
  throw error;
} finally {
  if (waiting) clearTimeout(waiting.timer);
  await writeFile(resolve(cache, 'observations.json'), JSON.stringify({ exchanges, outputs, errors, diagnostic }, null, 2));
  await context?.close(); device.kill('SIGTERM'); server.kill('SIGTERM');
}
