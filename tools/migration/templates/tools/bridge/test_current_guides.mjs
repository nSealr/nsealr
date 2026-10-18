import assert from "node:assert/strict";
import {checkGuide,checkCliExcerpt,allCurrentCommandExamples} from "./check_current_guides.mjs";
const stale=[
 "nsealr route --request req.json --signer raspberry-qr",
 "nsealr verify --request req.json --response resp.json",
 "nsealr request --kind 1 --content hello",
 "nsealr request validate --file req.json",
 "nsealr audit export --request req.json",
 "nsealr fixture verify --route esp32-usb --fixture sign-event-disabled",
 "nsealr nip46 decide --payload-file decrypted.json",
];
for(const id of ["22d92bfa3cba175cb486230c6a38dce63bffc1536d6438b42e18d931dc831335","952ea32a0de834c901ff6caa2b5d5e0c0615664b7e76735cb1601a87113ffcd3","f92de0975ed8c8305a907083f7a06234f4488c9c8867542e4320758d97488d3e"]){
 for(const command of stale){assert.throws(()=>checkGuide("docs/guide.md",`\`${command}\``),/unknown|unsupported/u);checkGuide("apps/bridge/cli/src/rejection.test.ts",`\`${command}\``);}
 const examples=allCurrentCommandExamples();assert(examples.length>100,"cover the actual full CLI tree and every registered option");for(const command of examples)checkCliExcerpt(command);
 console.log(`PASS ${id}: seven historical stale-command classes rejected; ${examples.length} actual current command/option forms accepted`);
}
