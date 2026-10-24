// Pure prerequisite: injected MockChild only; no C/O/W/signature or helper process.
import assert from 'node:assert/strict';
import cp from 'node:child_process';
import { EventEmitter } from 'node:events';
import { readFileSync } from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { PassThrough } from 'node:stream';
import { mock } from 'node:test';
import { pathToFileURL } from 'node:url';

const [modulePath, root] = process.argv.slice(2);
assert(modulePath && root && process.argv.length === 4);
// Capture explicitly BEFORE any mock or module import; inject only these references.
const realSetTimeout = globalThis.setTimeout;
const realClearTimeout = globalThis.clearTimeout;
const originalHelpers = {};
let realHelperCalls = 0;
for (const name of ['spawn', 'spawnSync', 'fork', 'exec', 'execSync', 'execFile', 'execFileSync']) {
  originalHelpers[name] = cp[name];
  cp[name] = () => { realHelperCalls++; throw Error('pure preflight forbids actual process helpers'); };
}
syncBuiltinESMExports();
const children = () => readFileSync(`/proc/self/task/${process.pid}/children`, 'utf8').trim();
const childrenBefore = children();
assert.equal(childrenBefore, '');
const imported = await import(pathToFileURL(modulePath));
assert.deepEqual(Object.keys(imported), ['createPrepareNative']);
assert.equal(realHelperCalls, 0);
assert.equal(children(), childrenBefore);

let spawns = 0, collected = 0, clientFires = 0, mockSpawnCalls = 0;
const settlements = [], observations = [], timerArgs = [], clearArgs = [], kills = [];
let scheduledNs;
class MockChild extends EventEmitter {
  constructor() {
    super();
    this.stdin = new PassThrough(); this.stdin.resume();
    this.stdout = new PassThrough(); this.stderr = new PassThrough();
    this.stdio = [this.stdin, this.stdout, this.stderr, new PassThrough(), new PassThrough()];
    this.exitCode = null; this.signalCode = null;
    // No PID: this is solely a mock object, never a kernel-process observation.
  }
  kill(signal) {
    const elapsedNs = process.hrtime.bigint() - scheduledNs;
    kills.push({ signal, elapsed_ns: String(elapsedNs) });
    assert.equal(signal, 'SIGKILL');
    assert(elapsedNs >= 5_000_000_000n, 'real5000 must not fire before5000ms; no lower tolerance');
    this.signalCode = signal;
    for (const stream of this.stdio) stream.end();
    this.emit('close', null, signal); // SIMULATED close; not actual child collection/EOF.
    return true;
  }
}
try {
  mock.timers.enable({ apis: ['setTimeout'] });
  assert.notEqual(globalThis.setTimeout, realSetTimeout);
  globalThis.setTimeout(() => { clientFires++; }, 100);
  const env = { NSEALR_QP01_PYTHON: '/PURE_MOCK_NO_EXEC/python',
    NSEALR_QP01_LIBRARY: '/PURE_MOCK_NO_LOAD/library.so', NSEALR_QP01_LIBRARY_SHA256: '0'.repeat(64) };
  const prepareNative = imported.createPrepareNative({
    root,
    spawn(python, argv, options) {
      mockSpawnCalls++;
      assert.equal(python, env.NSEALR_QP01_PYTHON);
      assert.deepEqual(argv, ['-B', `${root}/docs/restart/implementation/QP01/request-engine/exchange.py`, '--ready-fd', '4']);
      assert.equal(options.env, env); assert.equal(options.cwd, root);
      assert.deepEqual(options.stdio, ['pipe', 'pipe', 'pipe', 'pipe', 'pipe']);
      const child = new MockChild();
      queueMicrotask(() => child.stdio[4].end('R'));
      return child;
    },
    timers: {
      setTimeout(callback, milliseconds, ...args) {
        timerArgs.push(milliseconds);
        scheduledNs = process.hrtime.bigint();
        return realSetTimeout(callback, milliseconds, ...args);
      },
      clearTimeout(handle) { clearArgs.push(handle); return realClearTimeout(handle); }
    },
    onSpawn: () => { spawns++; }, onCollected: () => { collected++; },
    reportSettlement: (value) => settlements.push(value),
    reportObservation: (value) => observations.push(value)
  });
  const leaf = await prepareNative(false, env);
  assert.deepEqual(timerArgs, [5000]);
  assert.equal(spawns, 1); assert.equal(mockSpawnCalls, 1);
  assert.equal(leaf.isCollected(), false);
  mock.timers.tick(5000);
  assert.equal(clientFires, 1);
  assert.equal(kills.length, 0); assert.equal(collected, 0);
  const afterVirtualTick = { client_fires: clientFires, mock_leaf_kills: kills.length,
    mock_collected: collected, virtual_tick_ms: 5000 };
  await leaf.dispose(); // Wait for REAL captured5000 callback, with SIMULATED child close.
  await new Promise(setImmediate);
  assert.equal(kills.length, 1); assert.equal(collected, 1);
  assert.equal(leaf.isCollected(), true);
  assert.equal(clearArgs.length, 1); assert.equal(settlements.length, 1);
  assert.equal(settlements[0].code, null); assert.equal(settlements[0].signal, 'SIGKILL');
  assert.equal(settlements[0].sent, false); assert.equal(settlements[0].stdout_bytes, 0);
  assert.equal(settlements[0].stderr_bytes, 0); assert.equal(observations.length, 0);
  assert.equal(realHelperCalls, 0); assert.equal(children(), childrenBefore);
  console.log(JSON.stringify({ role: 'PURE_REAL_TIMER_WITH_MOCK_CHILD_NO_C_O_W_SIGNING',
    node_version: process.version, import_helpers: 0, actual_helper_calls: realHelperCalls,
    actual_direct_children_before: childrenBefore, actual_direct_children_after: children(),
    client_timer_arg_ms: 100, native_timer_args_ms: timerArgs, after_virtual_tick: afterVirtualTick,
    real_timer_callbacks: kills.length, mock_kills: kills, mock_spawn_calls: mockSpawnCalls,
    mock_collected: collected, mock_settlement: settlements[0], clear_calls: clearArgs.length,
    limits: ['MockChild has no PID; simulated close is not process/EOF evidence',
      'real elapsed>=5000 only; no hard upper timer/collection guarantee or actual C run'] }));
} finally {
  mock.timers.reset();
  for (const [name, fn] of Object.entries(originalHelpers)) cp[name] = fn;
  syncBuiltinESMExports();
}
