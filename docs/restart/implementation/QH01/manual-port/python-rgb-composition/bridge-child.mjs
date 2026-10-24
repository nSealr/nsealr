// Fixed diagnostic child. Python owns its lifetime and the real B3 operation.
import assert from 'node:assert/strict';
import cp from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeSync } from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { mock } from 'node:test';
import { pathToFileURL } from 'node:url';

let outputBytes = 0, records = 0;
function emit(event, fields = {}) {
  const wire = JSON.stringify({ v: 1, event, ...fields }) + '\n';
  assert(Buffer.byteLength(wire) <= 2048);
  outputBytes += Buffer.byteLength(wire);
  assert(outputBytes <= 4096 && ++records <= 5);
  assert.equal(writeSync(1, wire), Buffer.byteLength(wire));
}

// This isolated test has no process provider. A helper would invalidate it.
let helperCalls = 0;
for (const name of ['spawn', 'spawnSync', 'fork', 'exec', 'execSync', 'execFile', 'execFileSync']) {
  cp[name] = () => { helperCalls++; throw Error('runtime process helper forbidden'); };
}
syncBuiltinESMExports();
let restoreTimers;
try {
  const [root, bridge, reuse, selectedCase = 'positive'] = process.argv.slice(2);
  assert(root && bridge && reuse && (process.argv.length === 5 || process.argv.length === 6));
  assert(['positive', 'scan_null_after_settlement', 'scan_pending_timeout_after_settlement', 'fixture_cancel_B3_verified_preG'].includes(selectedCase));
  const timeoutCase = selectedCase === 'scan_pending_timeout_after_settlement';
  const cancelCase = selectedCase === 'fixture_cancel_B3_verified_preG';
  const load = (relative) => JSON.parse(readFileSync(`${root}/protocols/contracts/v1/${relative}`, 'utf8'));
  const expected = (name) => readFileSync(`${root}/docs/restart/implementation/QH01/native-qr-probe/expected/${name}.envelope`, 'ascii');
  const { runServiceOnceAsync } = await import(pathToFileURL(`${bridge}/index.js`));
  const { createManualQrRouteDispatcher } = await import(pathToFileURL(`${bridge}/manual-qr.js`));
  const { clientIdForIdentity, encodeNativeMessage, decodeNativeMessage, SignerTransportError } = await import(pathToFileURL(`${reuse}/packages/client/dist/index.js`));
  const { parseAccountDescriptor } = await import(pathToFileURL(`${reuse}/packages/policy/dist/index.js`));
  const { parseImplementationProfile, parseLimitsManifest } = await import(pathToFileURL(`${reuse}/packages/protocol/dist/index.js`));
  const request = load('examples/request-kind-1-basic.json');
  const response = load('examples/response-kind-1-basic.json');
  const requestFrame = expected('request-kind-1-basic');
  const responseFrame = expected('response-kind-1-basic');
  assert.equal(Buffer.byteLength(requestFrame), 259);
  assert.equal(Buffer.byteLength(responseFrame), 611);

  const reply = new Promise((resolve, reject) => {
    let bytes = Buffer.alloc(0);
    process.stdin.on('data', (chunk) => {
      if (bytes.length + chunk.length > 512) { reject(Error('reply cap')); process.stdin.destroy(); return; }
      bytes = Buffer.concat([bytes, chunk]);
    });
    process.stdin.once('error', reject);
    process.stdin.once('end', () => {
      try {
        assert(bytes.length > 0 && bytes.every((byte) => byte < 128) && bytes.at(-1) === 10);
        const wire = bytes.toString('ascii');
        const row = JSON.parse(wire);
        assert.equal(JSON.stringify(row) + '\n', wire);
        if (cancelCase) {
          assert.deepEqual(row, { v: 1, event: 'cancelled' });
          assert.deepEqual(Object.keys(row), ['v', 'event']);
        } else {
          assert.deepEqual(Object.keys(row), ['v', 'event', 'frame']);
          assert.equal(row.v, 1); assert.equal(row.event, 'decoded');
          assert.equal(row.frame, requestFrame);
        }
        resolve(row);
      } catch (error) { reject(error); }
    });
  });
  reply.catch(() => {}); // Observe a refusal even before present awaits it.

  mock.timers.enable({ apis: ['setTimeout'] });
  const set = globalThis.setTimeout, clear = globalThis.clearTimeout;
  const timerArgs = [], clockSteps = [0];
  let now = 0, clearCalls = 0, deadlineFires = 0;
  globalThis.setTimeout = (callback, milliseconds, ...args) => {
    timerArgs.push(milliseconds);
    return set(() => { deadlineFires++; callback(...args); }, milliseconds);
  };
  globalThis.clearTimeout = (timer) => { clearCalls++; return clear(timer); };
  restoreTimers = () => { globalThis.setTimeout = set; globalThis.clearTimeout = clear; mock.timers.reset(); };
  const cases = load('vectors/profile-capabilities/cases-v1.json');
  const implementation = parseImplementationProfile(load(cases.implementation_examples.pi_qr));
  const adapter = structuredClone(implementation);
  const { conformance_only, ...data } = structuredClone(implementation);
  const reported = { ...data, format: 'nsealr.capabilities.v1', form: 'full' };
  for (const source of [adapter, reported]) for (const entry of source.methods) {
    Object.assign(entry, { configuration: 'configured', availability: 'available', reason: null });
  }
  const limits = parseLimitsManifest(structuredClone(cases.limits_manifest));
  const account = parseAccountDescriptor(load('vectors/accounts/raspberry-qr-nip06-account-0.json'));
  account.public_key = load('examples/response-get-public-key.json').result.public_key;
  const connection_id = 'qh01.synthetic.connection', generation = 1;
  const snapshot = { implementation, adapter, reported, limits, adapter_limits: structuredClone(limits), connection_id, generation,
    review_plan: { request_sha256: createHash('sha256').update(JSON.stringify(request)).digest('hex'),
      implementation_id: implementation.implementation_id, connection_id, generation,
      context_id: 'qh01.synthetic.no-consent', geometry_id: 'qh01.unqualified.fixture', pages: 7 } };
  let opens = 0, scans = 0, closes = 0;
  let controls, enteredScan, releaseScan, settledUnderlying;
  let underlyingSettled = false, pendingRetryError = null;
  const scanEntered = new Promise((resolve) => { enteredScan = resolve; });
  const lateScan = new Promise((resolve) => { releaseScan = resolve; });
  const underlyingDone = new Promise((resolve) => { settledUnderlying = resolve; });
  const dispatcher = createManualQrRouteDispatcher({ account_id: account.account_id, route_type: 'raspberry_qr_vault',
    openPort(control) {
      controls = control;
      opens++;
      assert.equal(control.expected_public_key, account.public_key);
      return {
        async present(frame) {
          assert.equal(frame, requestFrame);
          await new Promise((resolve) => queueMicrotask(resolve));
          assert.deepEqual(timerArgs, [100]);
          now = 99; clockSteps.push(now); mock.timers.tick(99);
          assert.equal(deadlineFires, 0); control.before_present();
          emit('present', { frame, timer_args: [...timerArgs], clock: now });
          await reply;
          if (cancelCase) throw new SignerTransportError('signer_transport_failed', 'fixture B3 cancellation collected before G');
          assert.equal(control.abort_signal.aborted, false);
        },
        async scan() {
          scans++;
          if (timeoutCase) {
            emit('scan_pending', { clock: now }); enteredScan();
            return await lateScan;
          }
          const frame = selectedCase === 'scan_null_after_settlement' ? null : responseFrame;
          emit('scan', { frame }); return frame;
        },
        close() { closes++; emit('close'); }
      };
    }
  });
  const client = { surface: 'cli', origin: 'app:qh01-composition', app_name: 'QH01 synthetic composition' };
  const context = { accounts: [account], now: 1, monotonicNow: () => now,
    grants: [{ client_id: clientIdForIdentity(client), origin: client.origin, surface: client.surface, allowed_operations: ['dispatch_signer_request'] }],
    signerCompatibility: () => snapshot, signerDispatcher: (dispatch) => {
      const pending = dispatcher(dispatch);
      Promise.resolve(pending).then(() => { underlyingSettled = true; settledUnderlying(); },
        () => { underlyingSettled = true; settledUnderlying(); });
      return pending;
    } };
  const envelope = { version: 1, request_id: 'qh01.composition', operation: 'dispatch_signer_request',
    params: { client, route_request: { account_id: account.account_id, method: 'sign_event' }, request } };
  const operation = runServiceOnceAsync(encodeNativeMessage(envelope), context);
  let native;
  if (timeoutCase) {
    await scanEntered;
    assert.deepEqual([opens, scans, closes], [1, 1, 0]);
    assert.equal(underlyingSettled, false); assert.equal(now, 99);
    now = 100; clockSteps.push(now); mock.timers.tick(1);
    native = await operation;
    const timedOut = decodeNativeMessage(native);
    assert.equal(timedOut.ok, false); assert.equal(timedOut.error.code, 'signer_transport_timeout');
    assert.equal(controls.abort_signal.aborted, true);
    assert.equal(closes, 0); assert.equal(underlyingSettled, false);
    const blocked = decodeNativeMessage(await runServiceOnceAsync(encodeNativeMessage(envelope), context));
    assert.equal(blocked.ok, false); assert.equal(blocked.error.code, 'runtime_unavailable');
    pendingRetryError = blocked.error.code;
    assert.deepEqual(timerArgs, [100]); assert.equal(clearCalls, 1); assert.equal(deadlineFires, 1);
    emit('timeout', { native_response_base64: Buffer.from(native).toString('base64'), timer_args: [...timerArgs],
      clear_calls: clearCalls, deadline_fires: deadlineFires, clock: now, opens, scans, closes,
      abort_observed: controls.abort_signal.aborted, underlying_settled: underlyingSettled,
      pending_retry_error: pendingRetryError });
    releaseScan(responseFrame);
    await underlyingDone;
  } else {
    native = await operation;
  }
  const result = decodeNativeMessage(native);
  if (selectedCase === 'positive') {
    assert.equal(result.ok, true);
    assert.deepEqual(result.result.signer_response, response);
  } else {
    assert.equal(result.ok, false);
    assert.equal(result.error.code, timeoutCase ? 'signer_transport_timeout' : 'signer_transport_failed');
    assert.equal('result' in result, false);
    assert.equal(controls.abort_signal.aborted, true); assert.equal(underlyingSettled, true);
  }
  assert.equal(result.request_id, envelope.request_id);
  assert.deepEqual([opens, scans, closes], [1, cancelCase ? 0 : 1, 1]);
  assert.deepEqual(timerArgs, [100]); assert.equal(clearCalls, 1);
  if (!timeoutCase) { now = 100; clockSteps.push(now); mock.timers.tick(1); }
  assert.equal(deadlineFires, timeoutCase ? 1 : 0);
  assert.equal(helperCalls, 0);
  assert.equal(readFileSync(`/proc/self/task/${process.pid}/children`, 'utf8').trim(), '');
  emit('result', { native_response_base64: Buffer.from(native).toString('base64'), timer_args: timerArgs,
    clear_calls: clearCalls, deadline_fires: deadlineFires, clock_steps: clockSteps,
    ...(selectedCase === 'positive' ? {} : { lifecycle: { case: selectedCase, opens, scans, closes,
      abort_observed: controls.abort_signal.aborted, underlying_settled: underlyingSettled,
      late_scan_bytes: timeoutCase ? Buffer.byteLength(responseFrame) : 0,
      late_scan_sha256: timeoutCase ? createHash('sha256').update(responseFrame).digest('hex') : null,
      pending_retry_error: pendingRetryError } }) });
} catch (error) {
  const text = (value) => String(value).replace(/[^\x20-\x7e]/g, '?').slice(0, 256);
  emit('error', { name: text(error.name), message: text(error.message) });
  process.exitCode = 1;
} finally {
  if (restoreTimers) restoreTimers();
  process.stdin.destroy();
}
