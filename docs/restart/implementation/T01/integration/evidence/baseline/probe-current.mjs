import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";

const root = process.cwd();
const protocol = await import(pathToFileURL(`${root}/packages/protocol/src/protocol.ts`));
const policy = await import(pathToFileURL(`${root}/packages/policy/src/policy.ts`));
const fixture = (path) => JSON.parse(readFileSync(`${root}/protocols/contracts/v1/${path}`, "utf8"));
const response = fixture("examples/response-get-capabilities-esp32-s3-scaffold.json");
response.result.capabilities.verified = true;
const unknownAuthorityField = protocol.validateResponse(response);
assert.equal(unknownAuthorityField.ok, true);
const account = fixture("vectors/accounts/esp32-usb-device-slot-0.json");
account.capabilities.persistent_grants = false;
account.signer_route.policy_support = "manual_only";
let manualError;
try { policy.parseAccountDescriptor(account); } catch (error) { manualError = error.message; }
assert.equal(manualError, "ESP32 USB/NIP-46 routes must use scoped_automation policy support");
account.signer_route.policy_support = "scoped_automation";
let noGrantError;
try { policy.parseAccountDescriptor(account); } catch (error) { noGrantError = error.message; }
assert.equal(noGrantError, "ESP32 USB/NIP-46 routes require persistent grant support");
const v2Discovery = protocol.validateRequest({ version: 2, request_id: "t01-baseline", method: "get_capabilities" });
assert.equal(v2Discovery.ok, false);
console.log(JSON.stringify({
  source: "dbad656997ad8cf9024ca1489291f5f1d4d3094a",
  capability_unknown_verified_field_accepted: unknownAuthorityField,
  initial_manual_connected_account_rejected: manualError,
  connected_account_without_grants_rejected: noGrantError,
  numeric2_discovery_rejected: v2Discovery,
  meaning: "Actual pre-cutover observations; these reproduce requirement mismatches, not future acceptance or physical signing."
}, null, 2));
