// Independent S01-QUEUE-03 regression at candidate d385ddb0.
import assert from 'node:assert/strict';
import { PassThrough } from 'node:stream';
import { SerialLineStreamPort } from '../../../../packages/transport/dist/transport.js';

const tick = () => new Promise(resolve => setImmediate(resolve));
const results = [];
for (const emitClose of [true, false]) {
  for (const asyncDestroy of [false, true]) {
    const options = {emitClose, ...(asyncDestroy ? {destroy(error, callback) { setImmediate(() => callback(error)); }} : {})};
    const input = new PassThrough(options), output = new PassThrough(options);
    const inheritedInput = input.eventNames().map(name => [name, input.listenerCount(name)]);
    const inheritedOutput = output.eventNames().map(name => [name, output.listenerCount(name)]);
    const port = new SerialLineStreamPort({input, output});
    port.close(); await tick(); await tick();
    const actualInput = input.eventNames().map(name => [name, input.listenerCount(name)]);
    const actualOutput = output.eventNames().map(name => [name, output.listenerCount(name)]);
    const record = {emitClose, asyncDestroy, inputClosed: input.closed, outputClosed: output.closed, inheritedInput, inheritedOutput, actualInput, actualOutput};
    results.push(record); console.log(JSON.stringify(record));
    assert.equal(input.closed, true); assert.equal(output.closed, true);
  }
}
const hostile = results.find(x => !x.emitClose && x.asyncDestroy);
// Preserve all four observations before failing on the missing cleanup.
assert.deepEqual(hostile.actualInput, hostile.inheritedInput, 'S01-QUEUE-03: input retains owned listeners after asynchronous close with emitClose:false');
assert.deepEqual(hostile.actualOutput, hostile.inheritedOutput, 'S01-QUEUE-03: output retains owned listeners after asynchronous close with emitClose:false');
