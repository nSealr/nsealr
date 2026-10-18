// Independent S01-QUEUE-03 probe on da286979; no product or stream-private fields.
import assert from 'node:assert/strict';
import { PassThrough } from 'node:stream';
import { SerialLineStreamPort } from '../../../../../packages/transport/dist/transport.js';
const tick = () => new Promise(resolve => setImmediate(resolve));
const results = [];
for (const emitClose of [true, false]) for (const suppressErrorEvent of [false, true]) {
  const input = new PassThrough({
    autoDestroy: false, emitClose,
    destroy(error, callback) { setImmediate(() => callback(suppressErrorEvent ? null : error)); }
  });
  const output = new PassThrough();
  const port = new SerialLineStreamPort({input, output});
  input.end('stale'); await tick();
  assert.equal(input.readableEnded, true);
  const fault = new Error('independent destruction fault after EOF');
  input.destroy(fault); await tick(); await tick();
  assert.equal(input.closed, true); assert.equal(input.errored, fault);
  let received, thrown;
  try { received = await port.readLine(); } catch (error) { thrown = error; }
  const result = {emitClose, suppressErrorEvent, inputClosed: input.closed, inputErrored: input.errored.message, ...(received === undefined ? {} : {received}), ...(thrown === undefined ? {} : {thrown: thrown.message}), preservedFirstError: thrown === fault, outputDestroyed: output.destroyed};
  results.push(result); console.log(JSON.stringify(result));
  port.close(); await tick();
}
// Keep all positive/negative observations before reporting the contract failure.
for (const result of results) {
  assert.equal(result.preservedFirstError, true, `S01-QUEUE-03 known errored input after EOF must reject, ${JSON.stringify(result)}`);
  assert.equal(result.outputDestroyed, true, 'terminal error must destroy output too');
}
