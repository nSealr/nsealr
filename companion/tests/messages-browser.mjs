import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from 'playwright';
import { finalizeEvent, getPublicKey, verifyEvent, getEventHash } from 'nostr-tools/pure';
import { v2 as nip44 } from 'nostr-tools/nip44';
import { fixtureCamera, opticalFromPixels, scanFrames } from './optical.mjs';

// Real companion UI and Rust owner; synthetic camera and local relay, automatic host approval.
if (!process.env.CORE_RUNNER) throw Error('Set CORE_RUNNER to the persistent Rust optical host runner.');
const root = resolve(import.meta.dirname, '..'), cache = resolve(root, '.cache/messages-browser');
await mkdir(cache, { recursive: true });
const author = new Uint8Array(32), recipient = new Uint8Array(32); author[31] = 3; recipient[31] = 4;
const pubkey = getPublicKey(author), peer = getPublicKey(recipient), relay = 'wss://inbox.nsealr.test/';
const content = 'Private text through actual QR pixels and the Rust owner.';
const events = [author, recipient].map(key => finalizeEvent({ kind: 10050, created_at: Math.floor(Date.now() / 1000) - 60, tags: [['relay', relay]], content: '' }, key));
const requests = [], published = [], errors = [];
const server = spawn(process.execPath, ['serve.mjs'], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
const device = spawn(process.env.CORE_RUNNER, ['--session'], { stdio: ['pipe', 'pipe', 'pipe'] });
let output = '', diagnostic = '', waiting, context, page, stop = false, pump;
device.stderr.on('data', data => { diagnostic += data; });
device.stdout.on('data', data => {
  output += data;
  while (output.includes('\n')) {
    const end = output.indexOf('\n'), line = output.slice(0, end).trim(); output = output.slice(end + 1);
    if (!waiting || !line.startsWith('ns:')) continue;
    waiting.frames.push(line);
    if (waiting.frames.length === Number(line.split(':')[3])) { clearTimeout(waiting.timer); const current = waiting; waiting = null; current.resolve(current.frames); }
  }
});
device.on('exit', code => { if (waiting) { clearTimeout(waiting.timer); waiting.reject(Error(`Rust host runner exited ${code}: ${diagnostic}`)); waiting = null; } });
const exchange = frames => new Promise((resolve, reject) => {
  if (waiting) return reject(Error('A host request is already pending.'));
  waiting = { frames: [], resolve, reject, timer: setTimeout(() => { waiting = null; reject(Error(`Rust host response timeout: ${diagnostic}`)); }, 15000) };
  device.stdin.write(frames.join('\n') + '\n');
});
try {
  await new Promise((resolve, reject) => {
    server.stdout.on('data', data => { if (String(data).includes('http://127.0.0.1:8787')) resolve(); });
    server.once('error', reject); server.once('exit', code => reject(Error(`Companion server exited ${code}`)));
  });
  context = await chromium.launch({ channel: 'chromium', headless: true });
  const browser = await context.newContext({ viewport: { width: 1280, height: 1000 } });
  await fixtureCamera(browser);
  await browser.routeWebSocket('**', socket => {
    assert.equal(socket.url(), relay);
    socket.onMessage(packet => {
      const row = JSON.parse(String(packet));
      if (row[0] === 'REQ') {
        const filter = row[2];
        for (const event of events.filter(event => (!filter.kinds || filter.kinds.includes(event.kind)) && (!filter.authors || filter.authors.includes(event.pubkey)) && (!filter['#p'] || event.tags.some(tag => tag[0] === 'p' && filter['#p'].includes(tag[1]))))) socket.send(JSON.stringify(['EVENT', row[1], event]));
        socket.send(JSON.stringify(['EOSE', row[1]]));
      } else if (row[0] === 'EVENT') {
        assert.equal(verifyEvent(row[1]), true); events.push(row[1]); published.push(row[1]);
        socket.send(JSON.stringify(['OK', row[1].id, true, 'accepted by local test relay']));
      }
    });
  });
  page = await browser.newPage(); page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8787');
  pump = (async () => {
    while (!stop) {
      if (await page.locator('#operation[open]').count()) {
        const optical = await opticalFromPixels(page); requests.push(optical.request);
        await scanFrames(page, await exchange(optical.frames));
      }
      await page.waitForTimeout(100);
    }
  })();
  void pump.catch(error => { errors.push(error.message); });
  await page.locator('#connect').click();
  await page.waitForFunction(() => !document.querySelector('#selected').textContent.includes('No identity'));
  await page.locator('#discovery-relays').fill(relay);
  await page.locator('#message-recipient').fill(peer);
  await page.locator('#message-text').fill(content);
  await page.locator('#send-message').click();
  await Promise.race([pump, page.getByText('Each copy was accepted by an inbox relay. This does not prove the recipient has read it.', { exact: true }).waitFor({ timeout: 180000 })]);
  assert.equal(published.length, 2);
  const rumors = [];
  for (const key of [recipient, author]) {
    const wrap = published.find(event => event.tags.some(tag => tag[0] === 'p' && tag[1] === getPublicKey(key)));
    assert.ok(wrap); assert.equal(verifyEvent(wrap), true);
    const seal = JSON.parse(nip44.decrypt(wrap.content, nip44.utils.getConversationKey(key, wrap.pubkey)));
    assert.equal(verifyEvent(seal), true); assert.equal(seal.pubkey, pubkey); assert.equal(seal.kind, 13);
    const rumor = JSON.parse(nip44.decrypt(seal.content, nip44.utils.getConversationKey(key, seal.pubkey)));
    assert.equal(rumor.id, getEventHash(rumor)); assert.equal(rumor.content, content); rumors.push(rumor);
  }
  assert.deepEqual(rumors[0], rumors[1]);
  await page.locator('#load-messages').click();
  await page.getByRole('button', { name: /^Open encrypted message 1/ }).click();
  await Promise.race([pump, page.locator('#opened-message').waitFor({ state: 'visible', timeout: 180000 })]);
  assert.equal(await page.locator('#message-content').textContent(), content);
  assert.deepEqual(requests.map(request => request.method), ['get_public_key', 'nip44_encrypt', 'sign_event', 'nip44_encrypt', 'sign_event', 'nip44_decrypt', 'nip44_decrypt']);
  await page.screenshot({ path: resolve(cache, 'selected-message.png'), fullPage: true });
  await page.locator('#clear-messages').click(); assert.equal(await page.locator('#message-content').textContent(), '');
  assert.deepEqual(errors, []); stop = true; await pump;
  console.log('PASS private-message UI: actual QR/Rust host encrypt+seal recipient/self, independently verified layers, selected two-step receive, local plaintext clear. No physical-device or public-relay claim.');
} catch (error) {
  errors.push(error.message);
  if (page && !page.isClosed()) { await page.screenshot({ path: resolve(cache, 'failure.png'), fullPage: true }); await writeFile(resolve(cache, 'failure.txt'), await page.locator('body').innerText()); }
  throw error;
} finally {
  stop = true;
  if (waiting) clearTimeout(waiting.timer);
  await writeFile(resolve(cache, 'observations.json'), JSON.stringify({ requests, published, errors, diagnostic }, null, 2));
  await context?.close(); device.kill('SIGTERM'); server.kill('SIGTERM');
}
