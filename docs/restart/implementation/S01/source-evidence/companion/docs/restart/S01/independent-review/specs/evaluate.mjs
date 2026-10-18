// Read-only companion side of the independently generated oracle comparison.
import { readFileSync } from 'node:fs';
import { evaluateNip46RelayResponseStep } from '../../../../../packages/nip46/dist/nip46.js';
import { parseStrictJson } from '../../../../../packages/protocol/dist/encoding.js';
const input = JSON.parse(readFileSync(0, 'utf8'));
const evaluate = (value, parser) => {
  try { return {ok: true, value: parser(value)}; }
  catch (error) { return {ok: false, error: error.message}; }
};
console.log(JSON.stringify({
  cases: input.cases.map(c => evaluate(c.step, evaluateNip46RelayResponseStep)),
  json: input.json.map(c => evaluate(c.raw, value => parseStrictJson(value, 1024)))
}));
