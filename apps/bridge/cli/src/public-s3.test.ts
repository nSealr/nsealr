import { createServer, type Socket } from "node:net";
import { mkdtempSync, writeFileSync, readFileSync, existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { randomUUID } from "node:crypto";
import { describe, it, expect } from "vitest";
import { encodeSerialFrame, decodeSerialFrame } from "@nsealr/framing";
import { devSignRequest } from "@nsealr/dev-signer";
import { createLocalStorageReview, approveLocalStorageReview, createLocalGrantStore, clientIdForIdentity } from "@nsealr/client";
import { dispatchPublicS3, PUBLIC_S3_CLI_CLIENT } from "./public-s3.js";
import { buildCli } from "./index.js";
import { loadServiceContextFromFiles } from "../../service/src/context.js";

const KEY = "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9";
async function lab(run: (f: { dir: string; files: { grantStore: string; accountStore: string; routeDriverStore: string; storageApproval: string }; writes: unknown[]; out: string; endDeviceOutput():void }) => Promise<void>,
  answer: (request: any, socket: Socket) => void, header = "nsealr-public-usb-open-v1\n") {
  const dir = mkdtempSync(join(tmpdir(), "nsealr-v01-"));
  const path = "/tmp/nsealr-s3-public-" + randomUUID() + ".sock";
  const sockets = new Set<Socket>(), writes: unknown[] = [];
  const server = createServer(socket => {
    sockets.add(socket); socket.on("close", () => sockets.delete(socket));
    socket.write(header);
    socket.on("error", () => undefined);
    let buffer = "";
    socket.on("data", bytes => {
      buffer += bytes.toString("utf8");
      if (buffer.length > 1024) { socket.destroy(); return; }
      if (buffer.includes("\n")) {
        const frame = decodeSerialFrame(buffer); writes.push(frame.payload); answer(frame.payload, socket);
      }
    });
  });
  await new Promise<void>((resolve, reject) => { server.once("error", reject); server.listen(path, resolve); });
  const now = Math.floor(Date.now()/1000);
  const files = { grantStore: join(dir, "grants.json"), accountStore: join(dir, "accounts.json"),
    routeDriverStore: join(dir, "drivers.json"), storageApproval: join(dir, "storage.json") };
  const grant = { client_id: clientIdForIdentity(PUBLIC_S3_CLI_CLIENT), origin: PUBLIC_S3_CLI_CLIENT.origin,
    surface: PUBLIC_S3_CLI_CLIENT.surface, approved_at: now-1, expires_at: now+600,
    allowed_operations: ["select_account_route","validate_signer_request","dispatch_signer_request","verify_signer_response"] as const };
  writeFileSync(files.grantStore, JSON.stringify(createLocalGrantStore([{ ...grant, allowed_operations: [...grant.allowed_operations] }], { updatedAt: now })));
  writeFileSync(files.accountStore, JSON.stringify({ format: "nsealr-service-account-store-v0", updated_at: now, contains_secret_material: false,
    accounts: [{ format: "nsealr.account.v1", account_id: "public-s3", label: "PUBLIC scalar3 ONLY", public_key: KEY,
      profile: "esp32_no_se", implementation_id: "nsealr.s3.public.scalar3.e7f04215.v1", limits_id: "nsealr.limits.s3.public.e7.v1",
      signer_route: { type: "esp32_usb_nip46", repository: "nsealr", transport: "usb", custody: "volatile_session",
        trusted_review: "device_display", policy_support: "manual_only" },
      recovery: { type: "device_slot", slot_id: "PUBLIC-scalar3-not-backup", backup_required: false },
      capabilities: { methods: ["get_public_key","sign_event"] }, policy_profile_id: "policy-public-s3-manual-only" }] }));
  writeFileSync(files.routeDriverStore, JSON.stringify({ format: "nsealr-service-route-driver-store-v0", updated_at: now, contains_secret_material: false,
    routes: [{ account_id: "public-s3", route_type: "esp32_usb_nip46", transport: "usb", driver: "public_s3_stream", stream_path: path }] }));
  const review = createLocalStorageReview([
    { purpose: "grant_store", path: files.grantStore }, { purpose: "account_store", path: files.accountStore }, { purpose: "route_driver_store", path: files.routeDriverStore }
  ].map(x => ({...x,access:"read_only",contains_secret_material:false})));
  writeFileSync(files.storageApproval, JSON.stringify(approveLocalStorageReview(review,{approvedAt:now})));
  try { await run({ dir, files, writes, out: join(dir,"result.json"), endDeviceOutput(){ for(const socket of sockets)socket.end(); } }); }
  finally {
    for (const socket of sockets) socket.destroy();
    await new Promise<void>(resolve => server.close(() => resolve()));
    rmSync(dir,{recursive:true,force:true});
  }
}
function signed(r: any, key = "0".repeat(63)+"3") { return devSignRequest(r,key); }
describe("real Node client→service child→Unix stream; host fixture, no USB/S3", () => {
  it("sends nothing during setup, then one fresh request and collects the service before output", async () => {
    await lab(async f => {
      const cli=buildCli({publicS3Ready:async()=>{expect(f.writes).toEqual([]);}});
      await cli.parseAsync(["node","nsealr","local","dispatch-public-s3",
        "--grant-store",f.files.grantStore,"--account-store",f.files.accountStore,
        "--route-driver-store",f.files.routeDriverStore,"--storage-approval",f.files.storageApproval,
        "--expected-public-key",KEY,"--out",f.out]);
      const result=JSON.parse(readFileSync(f.out,"utf8"));expect(f.writes).toHaveLength(1);
      expect(result.request.request_id).toMatch(/^public-s3-/);expect(result.response.result.event.pubkey).toBe(KEY);
      expect(result.settlement).toEqual({exit_code:0,stdout_EOF:true,stderr_EOF:true,stdin_finished:true});
    },(r,s)=>s.write(encodeSerialFrame({type:"response",payload:signed(r)})));
  });
  it("keeps a >5s real external wait distinct from service ACTIVE; no human/targetCPU claim", async () => {
    const start=performance.now();
    await lab(async f => {
      await dispatchPublicS3({ ...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>undefined });
      expect(existsSync(f.out)).toBe(true);
    },(r,s)=>setTimeout(()=>s.write(encodeSerialFrame({type:"response",payload:signed(r)})),5100));
    expect(performance.now()-start).toBeGreaterThan(5000);
  },15000);
  it("creates the actual fixed client's pairing intent without a USB route",async()=>{
    const dir=mkdtempSync(join(tmpdir(),"nsealr-public-pair-"));
    try {
      const out=join(dir,"intent.json");
      await buildCli().parseAsync(["node","nsealr","local","public-s3-pairing","--out",out]);
      const intent=JSON.parse(readFileSync(out,"utf8"));
      expect(intent.client_id).toBe(clientIdForIdentity(PUBLIC_S3_CLI_CLIENT));
      expect(intent.requested_operations).toContain("dispatch_signer_request");
    } finally {rmSync(dir,{recursive:true,force:true});}
  });
  it("the ordinary service loader never promotes a public stream store to readiness",async()=>{
    await lab(async f=>{
      expect(()=>loadServiceContextFromFiles({
        grantStorePath:f.files.grantStore,accountStorePath:f.files.accountStore,
        routeDriverStorePath:f.files.routeDriverStore,storageApprovalPath:f.files.storageApproval,
        openSerialLinePort:()=>{throw new Error("must not open");}
      })).toThrow(/explicit application admission/);
      expect(f.writes).toHaveLength(0);
    },()=>{throw new Error("must not write");});
  });
  it("gets the pinned public key through the same service path without signing", async () => {
    await lab(async f=>{
      await dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"get_public_key",out:f.out,ready:async()=>undefined});
      expect(f.writes).toHaveLength(1);expect((f.writes[0] as any).method).toBe("get_public_key");
    },(r,s)=>s.write(encodeSerialFrame({type:"response",payload:{version:2,request_id:r.request_id,ok:true,result:{public_key:KEY}}})));
  });
  it("requires the USB-open plumbing acknowledgement before setup/operation", async () => {
    await lab(async f => {
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,
        ready:async()=>undefined,operationTimeoutMs:80})).rejects.toThrow();
      expect(f.writes).toHaveLength(0);expect(existsSync(f.out)).toBe(false);
    }, () => undefined, "not-a-USB-open-ack\n");
  });
  it("refuses existing output before a signing attempt or connection",async()=>{
    await lab(async f=>{
      writeFileSync(f.out,"original");
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>undefined})).rejects.toThrow(/already exists/);
      expect(f.writes).toHaveLength(0);expect(readFileSync(f.out,"utf8")).toBe("original");
    },()=>{throw new Error("no write");});
  });
  it("setup timeout aborts its callback and sends no request",async()=>{
    await lab(async f=>{
      let aborted=false;
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,setupTimeoutMs:100,
        ready:async signal=>new Promise<void>((_,reject)=>signal.addEventListener("abort",()=>{aborted=true;reject(new Error("stopped"));},{once:true}))
      })).rejects.toThrow(/setup expired/);
      expect(aborted).toBe(true);expect(f.writes).toHaveLength(0);expect(existsSync(f.out)).toBe(false);
    },()=>{throw new Error("no write");});
  });
  it("rejects a different independent pin before opening/writing", async ()=>{
    await lab(async f=>{
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:"1".repeat(64),method:"sign_event",out:f.out,ready:async()=>undefined})).rejects.toThrow(/pinned/);
      expect(f.writes).toHaveLength(0);expect(existsSync(f.out)).toBe(false);
    },()=>{throw new Error("no write");});
  });
  it("observes setup EOF before Enter instead of writing through a stale lease",async()=>{
    await lab(async f=>{
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>{
        f.endDeviceOutput();await new Promise(resolve=>setTimeout(resolve,50));
      }})).rejects.toThrow();expect(f.writes).toHaveLength(0);expect(existsSync(f.out)).toBe(false);
    },()=>undefined);
  });
  it("reloads a revoked grant after Enter and sends nothing", async ()=>{
    await lab(async f=>{
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>{
        const store=JSON.parse(readFileSync(f.files.grantStore,"utf8"));store.grants[0].revoked=true;writeFileSync(f.files.grantStore,JSON.stringify(store));
      }})).rejects.toThrow(/changed/);expect(f.writes).toHaveLength(0);expect(existsSync(f.out)).toBe(false);
    },()=>{throw new Error("no write");});
  });
  for(const corruption of ["key","request","event","checksum"] as const) it("refuses "+corruption+" substitution without publishing or retry",async()=>{
    await lab(async f=>{
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>undefined})).rejects.toThrow();
      expect(f.writes).toHaveLength(1);expect(existsSync(f.out)).toBe(false);
    },(r,s)=>{
      const response:any=signed(r,corruption==="key"?"0".repeat(63)+"4":undefined);
      if(corruption==="request")response.request_id="stale";
      if(corruption==="event")response.result.event.content="substituted";
      let line=encodeSerialFrame({type:"response",payload:response});
      if(corruption==="checksum")line=line.slice(0,-3)+"00\n";
      s.write(line);
    });
  });
  it("revocation during external work suppresses an otherwise valid result",async()=>{
    let change:()=>void=()=>undefined;
    await lab(async f=>{
      change=()=>{const g=JSON.parse(readFileSync(f.files.grantStore,"utf8"));g.grants[0].revoked=true;writeFileSync(f.files.grantStore,JSON.stringify(g));};
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>undefined})).rejects.toThrow();
      expect(f.writes).toHaveLength(1);expect(existsSync(f.out)).toBe(false);
    },(r,s)=>{change();s.write(encodeSerialFrame({type:"response",payload:signed(r)}));});
  });
  it("times out the operation and closes the only child/stream without retry",async()=>{
    await lab(async f=>{
      await expect(dispatchPublicS3({...f.files,expectedPublicKey:KEY,method:"sign_event",out:f.out,ready:async()=>undefined,operationTimeoutMs:80})).rejects.toThrow(/expired/);
      expect(f.writes).toHaveLength(1);expect(existsSync(f.out)).toBe(false);
    },()=>undefined);
  });
});
