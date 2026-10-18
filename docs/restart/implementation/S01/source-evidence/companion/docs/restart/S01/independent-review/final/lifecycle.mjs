import assert from 'node:assert/strict';
import { PassThrough } from 'node:stream';
import { createReadStream, createWriteStream, mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { SerialLineStreamPort } from '../../../../../packages/transport/dist/transport.js';
const tick = () => new Promise(resolve => setImmediate(resolve));
const listeners = stream => stream.eventNames().map(event => [event, stream.listeners(event)]);
const rejected = promise => promise.then(() => assert.fail('operation should reject'), error => error);
const schedulers = {sync: callback => callback(), microtask: queueMicrotask, nextTick: process.nextTick, immediate: setImmediate, timer: callback => setTimeout(callback, 0)};
let count = 0;
for (const [timing, schedule] of Object.entries(schedulers)) for (const emitClose of [true, false]) for (const shared of [true, false]) for (const descriptorKind of ['inherited', 'data', 'accessor']) {
  const hookFault = new Error('hook fault'); let calls = 0, finished = 0;
  let complete; const completion = new Promise(resolve => { complete = resolve; });
  class Stream extends PassThrough {
    _destroy(error, callback) {
      assert.equal(this instanceof Stream, true); assert.equal(error, null); ++calls;
      schedule(() => { callback(hookFault); callback(new Error('duplicate must be ignored')); if (++finished === (shared ? 1 : 2)) complete(); });
    }
  }
  const input = new Stream({emitClose}), output = shared ? input : new Stream({emitClose});
  const streams = [...new Set([input, output])];
  for (const stream of streams) {
    const original = stream._destroy;
    if (descriptorKind === 'data') Object.defineProperty(stream, '_destroy', {value: original, enumerable: true, writable: false, configurable: true});
    if (descriptorKind === 'accessor') Object.defineProperty(stream, '_destroy', {get() { return original; }, enumerable: false, configurable: true});
  }
  const descriptors = streams.map(stream => Object.getOwnPropertyDescriptor(stream, '_destroy'));
  const received = []; const observer = error => received.push(error);
  streams.forEach(stream => stream.on('error', observer));
  const inherited = streams.map(listeners);
  const port = new SerialLineStreamPort({input, output});
  const reading = rejected(port.readLine()); port.close(); port.close();
  assert.match((await reading).message, /closed/);
  await completion; await tick(); await tick();
  assert.equal(calls, streams.length, timing);
  assert.deepEqual(received, streams.map(() => hookFault));
  for (const [index, stream] of streams.entries()) {
    assert.equal(stream.closed, true);
    assert.deepEqual(Object.getOwnPropertyDescriptor(stream, '_destroy'), descriptors[index]);
    assert.deepEqual(listeners(stream), inherited[index]);
  }
  assert.match((await rejected(port.readLine())).message, /closed/);
  ++count;
}
console.log(`PASS ${count} destruction timing/descriptor/shared-stream combinations with duplicate callbacks and inherited error observers`);

// A constructor error after both wrappers are installed must restore both hooks.
{
  const input = new PassThrough(), output = new PassThrough();
  const before = [input, output].map(stream => ({descriptor: Object.getOwnPropertyDescriptor(stream, '_destroy'), listeners: listeners(stream)}));
  assert.throws(() => new SerialLineStreamPort({input, output, encoding: 'not-an-encoding'}));
  for (const [index, stream] of [input, output].entries()) {
    assert.deepEqual(Object.getOwnPropertyDescriptor(stream, '_destroy'), before[index].descriptor);
    assert.deepEqual(listeners(stream), before[index].listeners); stream.destroy();
  }
  await tick(); console.log('PASS constructor failure after installing both hooks restores original descriptors/listeners');
}

// Node may defer destruction until _construct completes. Pending port I/O still
// cancels immediately; hook cleanup follows actual completion without polling.
{
  const constructions = [];
  const opts = {emitClose: false, construct(callback) { constructions.push(callback); }, destroy(error, callback) { queueMicrotask(() => callback(error)); }};
  const input = new PassThrough(opts), output = new PassThrough(opts);
  const before = [input, output].map(listeners);
  const port = new SerialLineStreamPort({input, output}); await tick();
  const reading = rejected(port.readLine()), writing = rejected(port.writeLine('x'));
  port.close(); assert.match((await reading).message, /closed/); assert.match((await writing).message, /closed/);
  assert.equal(input.closed, false); assert.equal(output.closed, false); assert.equal(constructions.length, 2);
  constructions.forEach(callback => callback()); await tick(); await tick();
  assert.equal(input.closed, true); assert.equal(output.closed, true);
  // Node's own construction listeners disappear; only compare the owned types.
  for (const stream of [input, output]) for (const event of ['data', 'error', 'close']) assert.equal(stream.listenerCount(event), 0);
  console.log('PASS destruction deferred by construction cancels I/O before completion and cleans after completion');
}

// Exercise real filesystem stream destruction, beyond custom PassThrough hooks.
{
  const directory = mkdtempSync(join(tmpdir(), 's01-review-native-'));
  writeFileSync(join(directory, 'input'), 'line\ntail');
  const input = createReadStream(join(directory, 'input')), output = createWriteStream(join(directory, 'output'));
  const inputHook = input._destroy, outputHook = output._destroy;
  const port = new SerialLineStreamPort({input, output});
  try {
    await port.writeLine('written'); assert.equal(await port.readLine(), 'line\n'); assert.equal(await port.readLine(), 'tail'); assert.equal(await port.readLine(), null);
    const close = new Promise(resolve => output.once('close', resolve)); port.close(); await close; await tick();
    assert.equal(input._destroy, inputHook); assert.equal(output._destroy, outputHook);
    for (const stream of [input, output]) for (const event of ['data', 'error', 'close']) assert.equal(stream.listenerCount(event), 0);
    console.log('PASS real filesystem streams read/write/EOF/async-close cleanup');
  } finally { port.close(); rmSync(directory, {recursive: true, force: true}); }
}
