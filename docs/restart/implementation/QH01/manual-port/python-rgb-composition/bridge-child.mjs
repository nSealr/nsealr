// Fixed diagnostic child. Python owns its lifetime and the real B3 operation.
import assert from 'node:assert/strict';
import cp from 'node:child_process';
import { createHash } from 'node:crypto';
import { fstatSync, readFileSync, readdirSync, readlinkSync, writeFileSync, writeSync } from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { join, resolve } from 'node:path';
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

// Explicit capabilities captured BEFORE either guards or client timer mocking.
// Only the opt-in's fixed native-leaf wrapper can use these references.
const nativeSpawn = cp.spawn;
const nativeTimers = { setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout };
let engine;
const digest = (raw) => createHash('sha256').update(raw).digest('hex');
function nodeFds() {
  const result = {};
  for (const name of readdirSync('/proc/self/fd').sort((a, b) => Number(a) - Number(b))) {
    try {
      const stat = fstatSync(Number(name));
      result[name] = { dev: String(stat.dev), ino: String(stat.ino), target: readlinkSync(`/proc/self/fd/${name}`) };
    } catch (error) {
      if (!['ENOENT', 'EBADF'].includes(error.code)) throw error; // readdir's own closed descriptor only.
    }
  }
  return result;
}
function engineArtifact(name, value, cap, raw = false) {
  const bytes = raw ? Buffer.from(value, 'ascii') : Buffer.from(JSON.stringify(value) + '\n');
  assert(bytes.length <= cap);
  writeFileSync(join(engine.config.output_dir, name), bytes, { flag: 'wx', mode: 0o600 });
}
async function settleEngine() {
  if (!engine || engine.written) return;
  // The same pending helper owns C even if readiness rejects; no replacement owner.
  if (engine.preparation) {
    try { engine.leaf = await engine.preparation; } catch { /* Helper rejects only after its dispose/ended. */ }
  }
  if (engine.leaf) await engine.leaf.dispose();
  if (engine.spawned) {
    assert.equal(engine.spawned, 1); assert.equal(engine.collected, 1);
    assert.equal(engine.settlements.length, 1);
    assert.equal(engine.settlements[0].pid, engine.child.pid);
    await new Promise(setImmediate);
    engine.children_after = readFileSync(`/proc/self/task/${process.pid}/children`, 'utf8').trim();
    engine.fds_after = nodeFds();
    engineArtifact('engine-settlement.json', { qh01_engine_leaf_settlement: engine.settlements[0] }, 2048);
    if (engine.observations.length) {
      assert.equal(engine.observations.length, 1);
      engineArtifact('engine-observation.json', { qh01_engine_leaf_observation: engine.observations[0] }, 262144);
    }
    if (engine.refusal) engineArtifact('engine-refusal.json', { qh01_engine_leaf_refusal: engine.refusal }, 4096);
  }
  engineArtifact('engine-outcome.json', { qh01_engine_leaf_outcome: {
    scope: 'QH01_RGB_ENGINE_OPT_IN_V1', node_pid: process.pid,
    spawned: engine.spawned, collected: engine.collected, capability_calls: engine.capability_calls,
    spawn: engine.spawn_record ?? null, timer_args: engine.timer_args, timer_clears: engine.timer_clears,
    children_before: engine.children_before ?? null, children_after: engine.children_after ?? null,
    fds_before: engine.fds_before ?? null, fds_after: engine.fds_after ?? null,
    response_bytes: engine.response?.length ?? 0, response_sha256: engine.response ? digest(engine.response) : null,
    observation_count: engine.observations.length, readiness_refusal: engine.config.mode === 'loaded-sha-refusal'
  } }, 16384);
  engine.written = true;
  if (engine.spawned) {
    assert.equal(engine.children_after, '');
    assert.deepEqual(engine.fds_after, engine.fds_before);
  }
}

// The four existing cases still have no process provider. Other helpers always refuse.
let helperCalls = 0;
for (const name of ['spawn', 'spawnSync', 'fork', 'exec', 'execSync', 'execFile', 'execFileSync']) {
  cp[name] = () => { helperCalls++; throw Error('runtime process helper forbidden'); };
}
syncBuiltinESMExports();
let restoreTimers;
try {
  const [root, bridge, reuse, selectedCase = 'positive', engineConfig] = process.argv.slice(2);
  const engineCase = selectedCase === 'fixture_request_engine';
  assert(root && bridge && reuse && (engineCase ? process.argv.length === 7 : process.argv.length === 5 || process.argv.length === 6));
  assert(['positive', 'scan_null_after_settlement', 'scan_pending_timeout_after_settlement', 'fixture_cancel_B3_verified_preG', 'fixture_request_engine'].includes(selectedCase));
  let engineRefusal = false, inspectionFailed = false;
  if (engineCase) {
    const raw = readFileSync(engineConfig); assert(raw.length <= 8192);
    const config = JSON.parse(raw);
    assert.deepEqual(Object.keys(config), ['v', 'scope', 'mode', 'source_root', 'output_dir', 'python', 'library', 'library_sha256',
      'child_expected_sha256', 'module', 'module_sha256', 'module_source_sha256',
      ...(config.mode === 'synthetic-inspection' ? ['synthetic_inspection'] : [])]);
    assert.equal(config.v, 1); assert.equal(config.scope, 'QH01_RGB_ENGINE_OPT_IN_V1');
    assert(['positive', 'loaded-sha-refusal', 'synthetic-inspection'].includes(config.mode));
    engineRefusal = config.mode === 'loaded-sha-refusal';
    if (config.mode === 'synthetic-inspection') {
      const fixture = config.synthetic_inspection;
      assert.deepEqual(Object.keys(fixture), ['config', 'sha256', 'scenario', 'callback_source_sha256', 'expected_status']);
      assert.equal(resolve(fixture.config), join(config.output_dir, 'synthetic-inspection-config.json'));
      const bytes = readFileSync(fixture.config); assert(bytes.length <= 4096);
      assert.equal(digest(bytes), fixture.sha256);
      const selection = JSON.parse(bytes);
      assert.deepEqual(Object.keys(selection), ['v', 'scope', 'scenario', 'callback_source_sha256', 'trace_path']);
      assert.equal(selection.v, 1); assert.equal(selection.scope, 'QP01_SYNTHETIC_INSPECTION_V1');
      assert.equal(selection.scenario, fixture.scenario);
      assert.equal(selection.trace_path, join(config.output_dir, 'inspection-trace.json'));
      assert.equal(selection.callback_source_sha256, fixture.callback_source_sha256);
      assert.equal(digest(readFileSync(`${root}/apps/pi/app/nsealr_vault/synthetic_inspection.py`)), fixture.callback_source_sha256);
      assert(Number.isInteger(fixture.expected_status) && [0, -5, -6, -7, -9, -11].includes(fixture.expected_status));
      inspectionFailed = fixture.expected_status !== 0;
    }
    assert.equal(config.source_root, root); assert.equal(resolve(engineConfig), join(config.output_dir, 'engine-initialization.json'));
    assert.equal(digest(readFileSync(config.library)), config.library_sha256);
    assert.equal(config.child_expected_sha256, engineRefusal ? (config.library_sha256[0] === '0' ? '1' : '0') + config.library_sha256.slice(1) : config.library_sha256);
    assert.equal(digest(readFileSync(config.module)), config.module_sha256);
    assert.equal(digest(readFileSync(`${root}/docs/restart/implementation/QP01/request-engine/native-leaf.ts`)), config.module_source_sha256);
    const imported = await import(pathToFileURL(config.module));
    assert.deepEqual(Object.keys(imported), ['createPrepareNative']);
    assert.equal(digest(readFileSync(config.module)), config.module_sha256);
    engine = { config, spawned: 0, collected: 0, capability_calls: 0, timer_args: [], timer_clears: 0,
      settlements: [], observations: [], preparation: null, leaf: null, child: null, response: null, refusal: null, written: false };
    engine.env = Object.freeze({ ...process.env, NSEALR_QP01_PYTHON: config.python,
      NSEALR_QP01_LIBRARY: config.library, NSEALR_QP01_LIBRARY_SHA256: config.child_expected_sha256,
      ...(config.mode === 'synthetic-inspection' ? {
        NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG: config.synthetic_inspection.config,
        NSEALR_QP01_SYNTHETIC_INSPECTION_CONFIG_SHA256: config.synthetic_inspection.sha256
      } : {}) });
    engine.prepare = imported.createPrepareNative({ root, timers: {
      setTimeout(callback, milliseconds, ...args) {
        assert.equal(milliseconds, 5000); assert.deepEqual(engine.timer_args, []);
        engine.timer_args.push(milliseconds); return nativeTimers.setTimeout(callback, milliseconds, ...args);
      },
      clearTimeout(handle) { engine.timer_clears++; return nativeTimers.clearTimeout(handle); }
    },
    spawn(python, argv, options) {
      assert(engine.reply_received && !engine.child && engine.capability_calls === 0);
      assert.equal(python, config.python);
      assert.deepEqual(argv, ['-B', `${root}/docs/restart/implementation/QP01/request-engine/exchange.py`, '--ready-fd', '4']);
      assert.deepEqual(Object.keys(options), ['cwd', 'env', 'stdio']);
      assert.equal(options.cwd, root); assert.equal(options.env, engine.env);
      assert.deepEqual(options.stdio, ['pipe', 'pipe', 'pipe', 'pipe', 'pipe']);
      engine.capability_calls++;
      engine.child = nativeSpawn(python, argv, options);
      engine.spawn_record = { python, argv, cwd: root, pid: engine.child.pid,
        initialization: { library: config.library, sha256: config.child_expected_sha256 } };
      return engine.child;
    },
    onSpawn: () => { engine.spawned++; }, onCollected: () => { engine.collected++; },
    reportSettlement: (value) => engine.settlements.push(value),
    reportObservation: (value) => engine.observations.push(value)
    });
  }
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
  const engineExpected = engineCase ? JSON.parse(readFileSync(`${root}/docs/restart/implementation/QP01/request-engine/expectations.json`, 'utf8'))
    .independent_positive_expectations.find((row) => row.id === 'basic') : null;
  const expectedResponse = engineCase ? { ...response, result: { event: engineExpected.expected_complete_event } } : response;
  const requestFrame = expected('request-kind-1-basic');
  const responseFrame = engineCase ? null : expected('response-kind-1-basic');
  assert.equal(Buffer.byteLength(requestFrame), 259);
  if (!engineCase) assert.equal(Buffer.byteLength(responseFrame), 611);

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
          const decoded = await reply;
          if (cancelCase) throw new SignerTransportError('signer_transport_failed', 'fixture B3 cancellation collected before G');
          assert.equal(control.abort_signal.aborted, false);
          if (engineCase) {
            engine.reply_received = true;
            engine.children_before = readFileSync(`/proc/self/task/${process.pid}/children`, 'utf8').trim();
            assert.equal(engine.children_before, ''); engine.fds_before = nodeFds();
            engine.preparation = engine.prepare(false, engine.env);
            try {
              engine.leaf = await engine.preparation;
              assert(!engineRefusal, 'wrong loaded SHA must refuse before readiness');
              engine.response = await engine.leaf.send(decoded.frame); // Actual B3 bytes, never reconstructed JSON.
              assert.equal(Buffer.byteLength(engine.response), 611);
              assert.equal(digest(engine.response), '250167d1137f6da25676b00b62913a3d8f29391a1ff5331d64f7079d953f5ded');
              engineArtifact('engine-response.envelope', engine.response, 947, true);
            } catch (error) {
              if (inspectionFailed) {
                assert.equal(engine.collected, 1); assert.equal(engine.observations.length, 0);
                const status = engine.settlements[0];
                assert.equal(status.code, 1); assert.equal(status.signal, null); assert.equal(status.sent, true);
                assert.equal(status.readiness_hex, '52'); assert.equal(status.stdout_bytes, 0); assert.equal(status.overflow, false);
                const raw = readFileSync(join(engine.config.output_dir, 'inspection-trace.json'));
                assert(raw.length <= 131072);
                const trace = JSON.parse(raw);
                assert.equal(trace.native_status, engine.config.synthetic_inspection.expected_status);
                assert.equal(trace.config_sha256, engine.config.synthetic_inspection.sha256);
                assert.equal(trace.output_bytes, 0); assert.equal(trace.output_sha256, null);
                engineArtifact('inspection-refusal-error.txt', String(error), 262144, true);
                engine.refusal = { name: error.name, message: String(error.message).slice(0, 2048) };
                throw new SignerTransportError('signer_transport_failed', 'synthetic inspection native refusal collected');
              }
              if (!engineRefusal) throw error;
              assert.equal(engine.collected, 1); assert.equal(engine.observations.length, 0);
              const status = engine.settlements[0];
              assert.equal(status.code, 1); assert.equal(status.signal, null); assert.equal(status.sent, false);
              assert.equal(status.readiness_hex, ''); assert.equal(status.stdout_bytes, 0); assert.equal(status.overflow, false);
              assert(String(error.message).includes('native library SHA256 mismatch'));
              engine.refusal = { name: error.name, message: String(error.message) };
              throw new SignerTransportError('signer_transport_failed', 'fixture native loaded-SHA readiness refusal');
            }
          }
        },
        async scan() {
          scans++;
          if (timeoutCase) {
            emit('scan_pending', { clock: now }); enteredScan();
            return await lateScan;
          }
          const frame = engineCase ? engine.response : selectedCase === 'scan_null_after_settlement' ? null : responseFrame;
          emit('scan', { frame }); return frame;
        },
        close() {
          if (engineCase) assert.equal(engine.collected, 1);
          closes++; emit('close');
        }
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
  if (selectedCase === 'positive' || engineCase && !engineRefusal && !inspectionFailed) {
    assert.equal(result.ok, true);
    assert.deepEqual(result.result.signer_response, expectedResponse);
  } else {
    assert.equal(result.ok, false);
    assert.equal(result.error.code, timeoutCase ? 'signer_transport_timeout' : 'signer_transport_failed');
    assert.equal('result' in result, false);
    assert.equal(controls.abort_signal.aborted, true); assert.equal(underlyingSettled, true);
  }
  assert.equal(result.request_id, envelope.request_id);
  assert.deepEqual([opens, scans, closes], [1, cancelCase || engineRefusal || inspectionFailed ? 0 : 1, 1]);
  assert.deepEqual(timerArgs, [100]); assert.equal(clearCalls, 1);
  if (!timeoutCase) { now = 100; clockSteps.push(now); mock.timers.tick(1); }
  assert.equal(deadlineFires, timeoutCase ? 1 : 0);
  assert.equal(helperCalls, 0);
  if (engineCase) await settleEngine();
  assert.equal(readFileSync(`/proc/self/task/${process.pid}/children`, 'utf8').trim(), '');
  emit('result', { native_response_base64: Buffer.from(native).toString('base64'), timer_args: timerArgs,
    clear_calls: clearCalls, deadline_fires: deadlineFires, clock_steps: clockSteps,
    ...(engineCase ? { engine: { mode: engine.config.mode, spawned: engine.spawned, collected: engine.collected,
      capability_calls: engine.capability_calls, pid: engine.child.pid, code: engine.settlements[0].code,
      signal: engine.settlements[0].signal, timer_args: engine.timer_args, timer_clears: engine.timer_clears,
      children_after: engine.children_after, fd_restored: JSON.stringify(engine.fds_before) === JSON.stringify(engine.fds_after) } }
      : selectedCase === 'positive' ? {} : { lifecycle: { case: selectedCase, opens, scans, closes,
      abort_observed: controls.abort_signal.aborted, underlying_settled: underlyingSettled,
      late_scan_bytes: timeoutCase ? Buffer.byteLength(responseFrame) : 0,
      late_scan_sha256: timeoutCase ? createHash('sha256').update(responseFrame).digest('hex') : null,
      pending_retry_error: pendingRetryError } }) });
} catch (error) {
  const text = (value) => String(value).replace(/[^\x20-\x7e]/g, '?').slice(0, 256);
  emit('error', { name: text(error.name), message: text(error.message) });
  process.exitCode = 1;
} finally {
  if (engine) await settleEngine(); // Same actual C owner; never exit early on a client/refusal/error path.
  if (restoreTimers) restoreTimers();
  process.stdin.destroy();
}
