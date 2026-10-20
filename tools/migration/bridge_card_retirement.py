#!/usr/bin/env python3
"""Retire active card routing and explicitly replace affected cases with rejection."""
import argparse,re
from pathlib import Path
from rehearse import canonical,digest
from transforms import Changes


def test_replace(text,old,new):
    start=text.index('  it("'+old+'"');end=text.index('\n  });',start)+len('\n  });')
    return text[:start]+new+text[end:]


def apply(target,output):
    c=Changes(target);dispositions=[]
    path='packages/policy/src/policy.ts';text=(target/path).read_text()
    text=text.replace('  | "smartcard"\n','').replace('  | "card_persistent"\n','').replace(' | "smartcard"','').replace(' | "nfc"','').replace(' | "display_less"','')
    text=text.replace('  "smartcard",\n','').replace('  "card_persistent",\n','').replace('  ["smartcard", "nsealr"],\n','').replace('"qr", "usb", "smartcard", "nfc", "nip46_relay", "embedded"','"qr", "usb", "nip46_relay", "embedded"').replace(', "display_less"','')
    text=re.sub(r'  if \(route.type === "smartcard"\) \{.*?\n  \}\n\n','',text,flags=re.S)
    text=re.sub(r'  if \(recovery.type === "card_slot"\) \{.*?\n  \}\n','',text,flags=re.S)
    text=re.sub(r'  if \(routeTypes.includes\("smartcard"\).*?\n  \}\n','',text,flags=re.S)
    c.put(path,text.encode())
    path='packages/client/src/service.ts';text=(target/path).read_text();start=text.index('  const displayLessSignEvent =');end=text.index(' else if (acknowledgement !== undefined) {',start)
    text=text[:start]+'  if (acknowledgement !== undefined) {'+text[end+len(' else if (acknowledgement !== undefined) {'):]
    text=text.replace('import { approvalDigestForRequest } from "@nsealr/review";\n','')
    text=text.replace('      request: request.params.request,\n      ...(acknowledgement !== undefined ? { external_review_acknowledgement: acknowledgement } : {})','      request: request.params.request')
    c.put(path,text.encode())
    path='packages/policy/src/policy.test.ts';text=(target/path).read_text()
    text=re.sub(r'    const smartcardAccount = parseAccountDescriptor\(.*?\n    \);\n','',text,flags=re.S)
    text=re.sub(r'    const smartcardPolicy = parsePolicyProfile\(.*?\n    \);\n','',text,flags=re.S)
    text=re.sub(r'    expect\(smartcard(?:Account|Policy)\..*?\n','',text)
    old='rejects display-less smartcard policy automation and trusted-review claims';new='rejects retired card policies and account routes before trusting capability claims'
    text=test_replace(text,old,'''  it("'''+new+'''", () => {
    const policy = loadJson(resolve(specsRoot, "vectors/policies/manual-only-qr-vault.json")) as Record<string, unknown>;
    expect(() => parsePolicyProfile(policy)).not.toThrow();
    policy.route_types = ["smartcard"];
    policy.mode = "scoped_automation";
    policy.grants_allowed = true;
    expect(() => parsePolicyProfile(policy)).toThrow(/route_type/u);
    const account = loadJson(resolve(specsRoot, "vectors/accounts/esp32-usb-device-slot-0.json")) as { signer_route: Record<string, unknown> };
    expect(() => parseAccountDescriptor(account)).not.toThrow();
    account.signer_route.type = "smartcard";
    expect(() => parseAccountDescriptor(account)).toThrow(/route type/u);
  });''')
    text=text.replace('route_type: "smartcard",\n      permission: { method: "sign_event", parameter: "1", event_kind: 1 }\n    })).toThrow(/nSealr persistent policy route/u);','route_type: "smartcard",\n      permission: { method: "sign_event", parameter: "1", event_kind: 1 }\n    })).toThrow(/route_type/u);')
    dispositions.append({'path':path,'before':old,'after':new,'disposition':'Retire card automation/trust support; keep explicit unsupported-route and positive active-route controls.'});c.put(path,text.encode())
    path='packages/client/src/service.test.ts';text=(target/path).read_text()
    text=re.sub(r'const smartcardRouteVector = .*?\nif \(!smartcardRouteVector\).*?\n','',text)
    old='requires explicit external review acknowledgement for display-less smartcard dispatch';new='rejects retired routes before invoking any signer dispatcher'
    text=test_replace(text,old,'''  it("'''+new+'''", () => {
    let called = false;
    for (const acknowledgement of [undefined, externalReviewAcknowledgement()]) {
      const result = handleLocalServiceRequest({
        version: 1, request_id: "retired-card-route", operation: "dispatch_signer_request",
        params: { client, route_request: { ...routeVector.request, route_type: "smartcard" }, request,
          ...(acknowledgement === undefined ? {} : { external_review_acknowledgement: acknowledgement }) }
      }, { accounts: fixtures.accounts, grants: [grant], now: 1_900_000_000,
        signerDispatcher: () => { called = true; return response; } });
      expect(result).toMatchObject({ ok: false, error: { code: "invalid_service_request" } });
      expect(called).toBe(false);
    }
  });''')
    dispositions.append({'path':path,'before':old,'after':new,'disposition':'Retired card acknowledgement prerequisite becomes explicit route rejection with/without acknowledgement.'})
    old='passes acknowledged display-less smartcard requests through the injected dispatcher';new='refuses host acknowledgement bypass while preserving active dispatch'
    text=test_replace(text,old,'''  it("'''+new+'''", () => {
    let calls = 0;
    const context = { accounts: fixtures.accounts, grants: [grant], now: 1_900_000_000,
      signerDispatcher: () => { calls += 1; return response; } };
    const base = { version: 1, request_id: "active-route-control", operation: "dispatch_signer_request",
      params: { client, route_request: routeVector.request, request } };
    expect(handleLocalServiceRequest({ ...base, params: { ...base.params,
      external_review_acknowledgement: externalReviewAcknowledgement() } }, context))
      .toMatchObject({ ok: false, error: { code: "external_review_acknowledgement_unsupported" } });
    expect(calls).toBe(0);
    expect(handleLocalServiceRequest(base, context)).toMatchObject({ ok: true, result: { signer_response: response } });
    expect(calls).toBe(1);
  });''')
    dispositions.append({'path':path,'before':old,'after':new,'disposition':'Card successful-dispatch support retired; negative host acknowledgement bypass plus accepted active dispatch retained.'})
    text=text.replace('smartcardRouteVector.request','routeVector.request');c.put(path,text.encode())
    path='packages/client/src/local-service-client.test.ts';text=(target/path).read_text();text=re.sub(r'const smartcardRouteVector = .*?\nif \(!smartcardRouteVector\).*?\n','',text)
    old='passes external review acknowledgement through dispatch options for display-less routes';new='rejects host acknowledgement options before active signer dispatch'
    text=test_replace(text,old,'''  it("'''+new+'''", async () => {
    let calls = 0;
    const service = new LocalServiceClient({ exchange: (message) => handleLocalServiceRequest(message, {
      accounts: fixtures.accounts, grants: [grant], now: 1_900_000_000,
      signerDispatcher: () => { calls += 1; return response; }
    }) });
    await expect(service.dispatchSignerRequest(client, routeVector.request, request, {
      requestId: "client-host-acknowledgement", externalReviewAcknowledgement: externalReviewAcknowledgement()
    })).resolves.toMatchObject({ ok: false, error: { code: "external_review_acknowledgement_unsupported" } });
    expect(calls).toBe(0);
    await expect(service.dispatchSignerRequest(client, routeVector.request, request))
      .resolves.toMatchObject({ ok: true, result: { signer_response: response } });
    expect(calls).toBe(1);
  });''')
    dispositions.append({'path':path,'before':old,'after':new,'disposition':'Retire successful card option forwarding; retain denial and positive active client behavior.'});c.put(path,text.encode())
    path='packages/fixtures/src/fixtures.test.ts';text=(target/path).read_text()
    for value in ['acct-smartcard-slot-0','policy-manual-only-displayless-smartcard','smartcard-sign-event-slot-0','smartcard']:
        text=text.replace('      "'+value+'",\n','').replace(',\n      "'+value+'"','')
    text=text.replace('expect(contract.cases.find((routeCase) => routeCase.route_type === "smartcard")?.external_review_acknowledgement.mode)\n      .toBe("required");','expect(contract.cases.find((routeCase) => String(routeCase.route_type) === "smartcard")).toBeUndefined();')
    text=text.replace('.repository).toBe("hardware")','.repository).toBe("nsealr")');c.put(path,text.encode())
    path='apps/bridge/cli/src/index.ts';text=(target/path).read_text()
    text=text.replace('JSON.stringify(decision) !== JSON.stringify(policyDecision.expected_decision)','!isDeepStrictEqual(decision, policyDecision.expected_decision)')
    c.put(path,text.encode())
    path='apps/bridge/cli/src/index.test.ts';text=(target/path).read_text();old='runs request -> smartcard-sim-sign -> verify-response after explicit review acknowledgement';new='rejects the retired smartcard command without creating signer output'
    text=test_replace(text,old,'''  it("'''+new+'''", async () => {
    const tempRoot = mkdtempSync(join(tmpdir(), "nsealr-cli-retired-command-"));
    const responsePath = join(tempRoot, "response.json");
    await expect(runCli(["smartcard-sim-sign", "--out", responsePath]))
      .rejects.toThrow(/unknown command/u);
    expect(existsSync(responsePath)).toBe(false);
  });''');dispositions.append({'path':path,'before':old,'after':new,'disposition':'Retire the card simulator signing ceremony; prove removed command cannot create output.'});c.put(path,text.encode())
    result=c.apply(output,'Retire card routing and replace obsolete behavior assertions with active-boundary controls')
    (output/'case-dispositions.json').write_bytes(canonical(dispositions));return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
