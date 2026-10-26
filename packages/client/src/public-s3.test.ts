import { describe, it, expect } from "vitest";
import { parseAccountDescriptor } from "@nsealr/policy";
import { clientIdForIdentity, handleLocalServiceRequestAsync, type LocalServiceContext, type PublicS3Fixture } from "./service.js";
const KEY="f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
const client={surface:"cli" as const,origin:"cli:public-s3-unit",instance_id:"unit"};
function setup(method="get_public_key"){
  let generation=0, begin=0, calls=0;
  const fixture:PublicS3Fixture={
    source:"e7f04215fc97808acdafdbf9420f6ef6d0102c5b",image_sha256:"7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da",
    connection:()=>({connection_id:"unit.public.stream",generation,config_digest:"0".repeat(64),state:"open"}),
    begin:()=>{++begin;},check:()=>undefined,phase:()=>undefined,remainingMs:()=>100000
  };
  const account=parseAccountDescriptor({format:"nsealr.account.v1",account_id:"public-s3",label:"public fixture",public_key:KEY,
    profile:"esp32_no_se",implementation_id:"nsealr.s3.public.scalar3.e7f04215.v1",limits_id:"nsealr.limits.s3.public.e7.v1",
    signer_route:{type:"esp32_usb_nip46",repository:"nsealr",transport:"usb",custody:"volatile_session",trusted_review:"device_display",policy_support:"manual_only"},
    recovery:{type:"device_slot",slot_id:"public-only",backup_required:false},capabilities:{methods:["get_public_key","sign_event","get_capabilities"]},policy_profile_id:"policy-public"});
  const request:any={version:2,request_id:"public-s3-unit",method,...(method==="sign_event"?{params:{event_template:{kind:1,created_at:1710000000,content:"S3 public physical approval",tags:[]}}}:{})};
  const message={version:1,request_id:"local-unit",operation:"dispatch_signer_request",params:{client,route_request:{account_id:account.account_id,method},request}};
  const response={version:2,request_id:request.request_id,ok:true,result:{public_key:KEY}};
  const context:LocalServiceContext={accounts:[account],grants:[{client_id:clientIdForIdentity(client),origin:client.origin,surface:client.surface,
    allowed_operations:["dispatch_signer_request"],expires_at:Math.floor(Date.now()/1000)+60}],publicS3Fixture:fixture,
    signerDispatcher:()=>{++calls;return response;}};
  return {context,message,request,response,fixture,account,counts:()=>({calls,begin}),changeGeneration:()=>{++generation;}};
}
describe("public fixture compatibility never fabricates peer capabilities or consent",()=>{
  it("dispatches the named public key with a private original pin",async()=>{
    const f=setup();expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(true);expect(f.counts()).toEqual({calls:1,begin:1});
  });
  for(const missing of ["admission","source","image","grant","real-time"] as const)it("fails closed for missing/wrong "+missing,async()=>{
    const f=setup();
    if(missing==="admission"){f.context.publicS3Fixture=undefined;f.context.signerCompatibility=()=>{throw new Error("must not use fabricated report");};}
    if(missing==="source")(f.fixture as any).source="other";
    if(missing==="image")(f.fixture as any).image_sha256="0".repeat(64);
    if(missing==="grant")f.context.grants=[];
    if(missing==="real-time")f.context.now=1900000000;
    expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);expect(f.counts().calls).toBe(0);
  });
  it("get_capabilities remains unsupported without an operation write",async()=>{
    const f=setup("get_capabilities");expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);expect(f.counts().calls).toBe(0);
  });
  it("rejects a template outside the finite public slice and oversized input",async()=>{
    for(const content of ["different","x".repeat(321)]){
      const f=setup("sign_event");f.request.params.event_template.content=content;
      expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);expect(f.counts().calls).toBe(0);
    }
  });
  it("a connection generation change during callback cannot return an eligible result",async()=>{
    const f=setup();f.context.signerDispatcher=()=>{f.changeGeneration();return f.response;};
    expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);
  });
  it("a mutated account/key cannot switch the original pin",async()=>{
    const f=setup();f.context.signerDispatcher=()=>{f.account.public_key="1".repeat(64);return {...f.response,result:{public_key:f.account.public_key}};};
    expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);
  });
  it("rechecks live revocation after an async callback",async()=>{
    const f=setup();let revoked=false;
    f.context.currentGrants=()=>f.context.grants!.map(g=>({...g,revoked}));
    f.context.signerDispatcher=async()=>{revoked=true;return f.response;};
    expect((await handleLocalServiceRequestAsync(f.message,f.context)).ok).toBe(false);
  });
  it("keeps the single reservation while an adapter has not settled",async()=>{
    const f=setup();let finish!:(r:unknown)=>void;
    f.context.signerDispatcher=()=>new Promise(resolve=>{finish=resolve;});
    const first=handleLocalServiceRequestAsync(f.message,f.context);
    const second=await handleLocalServiceRequestAsync({...f.message,request_id:"second"},f.context);
    expect(second.ok).toBe(false);finish(f.response);expect((await first).ok).toBe(true);
  });
  it("separates session implementation from the preserved persistent model",()=>{
    const f=setup();
    expect(()=>parseAccountDescriptor({...f.account,signer_route:{...f.account.signer_route,custody:"mcu_wrapped_persistent"}})).toThrow(/custody/);
    expect(()=>parseAccountDescriptor({...f.account,implementation_id:"nsealr.conformance.esp32_no_se.v1"})).toThrow(/custody/);
    expect(parseAccountDescriptor({...f.account,implementation_id:"nsealr.conformance.esp32_no_se.v1",
      signer_route:{...f.account.signer_route,custody:"mcu_wrapped_persistent"}}).signer_route.custody).toBe("mcu_wrapped_persistent");
  });
});
