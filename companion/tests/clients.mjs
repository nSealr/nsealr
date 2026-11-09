import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import { finalizeEvent, getPublicKey, verifyEvent } from 'nostr-tools/pure';
import { fixtureCamera, opticalFromPixels, scanFrames } from './optical.mjs';

const name = process.env.CLIENT;
const mode = process.env.CLIENT_MODE ?? 'nip07';
if (!['nip07', 'nip46'].includes(mode)) throw Error('CLIENT_MODE must be nip07 or nip46.');
if (!['coracle', 'nostrudel'].includes(name) || !process.env.CLIENT_ROOT || !process.env.CORE_RUNNER) throw Error('Set CLIENT, CLIENT_ROOT and CORE_RUNNER.');
const root = resolve(import.meta.dirname, '..'), clientRoot = resolve(process.env.CLIENT_ROOT);
const port = name === 'coracle' ? 5174 : 5175, origin = `http://127.0.0.1:${port}`;
const cache = resolve(root, `.cache/${name}${mode === 'nip46' ? '-nip46' : ''}`); await mkdir(cache, { recursive: true });
const profile = await mkdtemp(resolve(cache, 'profile-'));
const env = { ...process.env };
if (name === 'coracle') {
  const require = createRequire(resolve(clientRoot, 'package.json'));
  Object.assign(env, require('dotenv').parse(await readFile(resolve(clientRoot, '.env.template'))));
  Object.assign(env, { VITE_DEFAULT_RELAYS: 'wss://relay.nsealr.test', VITE_INDEXER_RELAYS: 'wss://relay.nsealr.test', VITE_SEARCH_RELAYS: 'wss://relay.nsealr.test', VITE_DEFAULT_FOLLOWS: '', VITE_ONBOARDING_LISTS: '', VITE_APP_URL: origin, VITE_ENABLE_ZAPS: 'false', VITE_ENABLE_MARKET: 'false' });
}
const server = spawn(process.execPath, [resolve(clientRoot, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', String(port), '--strictPort'], { cwd: clientRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
let logs = ''; server.stdout.on('data', value => { logs += value; }); server.stderr.on('data', value => { logs += value; });
const key = new Uint8Array(32); key[31] = 3; const pubkey = getPublicKey(key);
const timestamp = Math.floor(Date.now() / 1000) - 60;
const events = [
  finalizeEvent({ kind: 0, created_at: timestamp, tags: [], content: JSON.stringify({ name: 'nSealr local test' }) }, key),
  finalizeEvent({ kind: 3, created_at: timestamp, tags: [], content: '' }, key),
  finalizeEvent({ kind: 10002, created_at: timestamp, tags: [['r', 'wss://relay.nsealr.test']], content: '' }, key),
  finalizeEvent({ kind: 10050, created_at: timestamp, tags: [['relay', 'wss://relay.nsealr.test']], content: '' }, key),
];
const published = [], requests = [], errors = [], sockets = [];
const match = (event, filter) => (!filter.ids || filter.ids.includes(event.id)) && (!filter.authors || filter.authors.includes(event.pubkey)) && (!filter.kinds || filter.kinds.includes(event.kind)) && (!filter.since || event.created_at >= filter.since) && (!filter.until || event.created_at <= filter.until) && Object.entries(filter).every(([key, value]) => !key.startsWith('#') || event.tags.some(tag => tag[0] === key.slice(1) && value.includes(tag[1])));
let context, page, servicing = false, stop = false;
try {
  for (let attempt = 0; attempt < 120; attempt++) { if (logs.includes(origin)) break; if (server.exitCode !== null) throw Error(logs); await new Promise(resolve => setTimeout(resolve, 500)); }
  context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true, args: [`--disable-extensions-except=${resolve(root, 'dist')}`, `--load-extension=${resolve(root, 'dist')}`], viewport: { width: 1280, height: 1000 }, serviceWorkers: 'block' });
  await fixtureCamera(context);
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.hostname === '127.0.0.1' || url.protocol === 'chrome-extension:' || url.protocol === 'data:' || url.protocol === 'blob:') return route.continue();
    return route.abort();
  });
  await context.routeWebSocket('**', socket => {
    if (socket.url().startsWith(`ws://127.0.0.1:${port}`)) { socket.connectToServer(); return; }
    const subscriptions = new Map(); sockets.push({ socket, subscriptions });
    socket.onMessage(message => {
      const row = JSON.parse(String(message));
      if (row[0] === 'REQ') {
        subscriptions.set(row[1], row.slice(2));
        const matches = events.filter(event => row.slice(2).some(filter => match(event, filter)));
        for (const event of matches.slice(0, 30)) socket.send(JSON.stringify(['EVENT', row[1], event]));
        socket.send(JSON.stringify(['EOSE', row[1]]));
      } else if (row[0] === 'CLOSE') subscriptions.delete(row[1]);
      else if (row[0] === 'EVENT') {
        assert.equal(verifyEvent(row[1]), true); const event = row[1];
        if (!events.some(saved => saved.id === event.id)) { events.push(event); published.push(event); }
        socket.send(JSON.stringify(['OK', event.id, true, 'local test relay accepted']));
        for (const entry of sockets) for (const [id, filters] of entry.subscriptions) if (filters.some(filter => match(event, filter))) entry.socket.send(JSON.stringify(['EVENT', id, event]));
      }
    });
  });
  page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
  await page.goto(origin + (name === 'coracle' ? '/login' : '/signin'), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(10000);
  await writeFile(resolve(cache, 'initial.txt'), await page.locator('body').innerText());
  await page.screenshot({ path: resolve(cache, 'initial.png'), fullPage: true });
  if (process.env.STEP === 'initial') { console.log(`Initial ${name} page captured.`); }
  else {
    let bunker;
    if (mode === 'nip46') {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
      const companion = await context.newPage();
      await companion.goto(new URL('index.html', worker.url()).href);
      await companion.locator('#identity').fill(pubkey); await companion.locator('#select').click();
      await companion.locator('#relay').fill('wss://relay.nsealr.test'); await companion.locator('#remote-start').click();
      await companion.locator('#remote-info').waitFor({ state: 'visible' }); bunker = await companion.locator('#bunker').inputValue();
    }
    const pump = (async () => {
      while (!stop) {
        const companion = context.pages().find(item => item.url().startsWith('chrome-extension:'));
        if (!companion || servicing) { await new Promise(resolve => setTimeout(resolve, 100)); continue; }
        if (await companion.locator('#permission[open]').count()) {
          const permission = await companion.locator('#permission-origin').textContent();
          if (mode === 'nip46') assert.match(permission, /^NIP-46 [a-f0-9]{64}$/);
          else assert.equal(permission, origin);
          await companion.getByRole('button', { name: 'Allow this session' }).click();
        }
        if (await companion.locator('#operation[open]').count()) {
          servicing = true;
          try {
            const optical = await opticalFromPixels(companion); requests.push(optical.request);
            const output = spawnSync(process.env.CORE_RUNNER, [], { input: optical.frames.join('\n') + '\n', encoding: 'utf8', timeout: 15000 });
            if (output.status !== 0) { errors.push(`Rust rejected ${optical.request.method}: ${output.stderr.trim()}`); await companion.getByRole('button', { name: 'Cancel', exact: true }).click(); }
            else await scanFrames(companion, output.stdout.trim().split('\n').filter(line => line.startsWith('ns:')));
          } finally { servicing = false; }
        }
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    })();
    void pump.catch(error => { errors.push(error.message); });
    if (mode === 'nip46') {
      await page.getByText(name === 'coracle' ? 'Use Remote Signer' : 'Nostr Connect', { exact: true }).click();
      await page.locator('input[placeholder^="bunker://"]').fill(bunker);
      await page.getByRole('button', { name: name === 'coracle' ? 'Continue' : 'Connect', exact: true }).click();
    } else await page.getByText(name === 'coracle' ? 'Use Browser Extension' : 'Browser Extension', { exact: true }).click();
    for (let attempt = 0; attempt < 600 && !requests.some(request => request.method === 'get_public_key'); attempt++) await page.waitForTimeout(100);
    await page.waitForTimeout(10000);
    await writeFile(resolve(cache, 'logged-in.txt'), await page.locator('body').innerText());
    await page.screenshot({ path: resolve(cache, 'logged-in.png'), fullPage: true });
    assert.ok(requests.some(request => request.method === 'get_public_key'), 'The real client must request its device identity.');
    const note = `nSealr ${name} local qualification — no public publication`;
    if (name === 'coracle') {
      await page.getByText('Post +', { exact: true }).click();
      await page.locator('[contenteditable=true]').fill(note);
    } else {
      await page.goto(origin + '/new/note', { waitUntil: 'domcontentloaded' });
      await page.locator('textarea').first().fill(note);
    }
    await page.getByRole('button', { name: name === 'coracle' ? 'Send' : 'Post', exact: true }).click();
    for (let attempt = 0; attempt < 1200 && !published.some(event => event.kind === 1 && event.content === note); attempt++) await page.waitForTimeout(100);
    const posted = published.find(event => event.kind === 1 && event.content === note);
    assert.ok(posted, 'The real client must publish the exact signed note to the local relay.');
    assert.equal(posted.pubkey, pubkey); assert.equal(verifyEvent(posted), true);
    await writeFile(resolve(cache, 'published.txt'), await page.locator('body').innerText());
    await page.screenshot({ path: resolve(cache, 'published.png'), fullPage: true });
    console.log(`PASS ${name} ${mode}: real client login and public-note UI, companion, QR pixels, Rust host owner, independently verified exact note accepted by local relay.`);
    stop = true; await pump;
  }
} catch (error) {
  errors.push(error.message);
  if (page && !page.isClosed()) {
    await writeFile(resolve(cache, 'failure.txt'), await page.locator('body').innerText());
    await page.screenshot({ path: resolve(cache, 'failure.png'), fullPage: true });
  }
  throw error;
} finally {
  stop = true;
  await writeFile(resolve(cache, 'observations.json'), JSON.stringify({ name, mode, clientRoot, requests, published, errors }, null, 2));
  await writeFile(resolve(cache, 'server.log'), logs);
  await context?.close(); server.kill('SIGTERM');
}
