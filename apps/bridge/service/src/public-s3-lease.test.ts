import { describe, expect, it, vi } from "vitest";
import type { Duplex } from "node:stream";
import { once } from "node:events";
import { mkdtempSync, writeFileSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { encodeSerialFrame, decodeSerialFrame } from "@nsealr/framing";
import { devSignRequest } from "../../../../packages/dev-signer/src/index.js";
import { LocalServiceClient, createLocalGrantStore, createLocalStorageReview,
  approveLocalStorageReview, clientIdForIdentity, handleLocalServiceRequestAsync } from "@nsealr/client";
import { loadPublicS3Context } from "./public-s3.js";

const wire = vi.hoisted(() => ({
  stream: undefined as unknown as Duplex, writes: [] as string[],
  events: [] as string[], response: "", endedBeforeClose: false
}));
// Controlled local byte transport, with actual Node data/end/destroy events.
// No parser or production API is replaced; this is not a USB/device claim.
vi.mock("node:net", async importOriginal => {
  const original = await importOriginal<typeof import("node:net")>();
  const { Duplex } = await import("node:stream");
  return { ...original, createConnection: () => {
    const stream = new Duplex({
      allowHalfOpen: true, autoDestroy: false,
      read() {},
      write(chunk, _encoding, callback) {
        wire.writes.push(chunk.toString());
        stream.once("end", () => {
          wire.events.push("write-complete");
          callback();
        });
        stream.push(Buffer.from(wire.response));
        stream.push(null);
        // Let the real readable end be observed with a complete line retained
        // by SerialLineStreamPort, before the write callback or any close.
        stream.resume();
      }
    });
    stream.on("end", () => {
      wire.events.push("end");
      wire.endedBeforeClose = stream.readableEnded && !stream.destroyed;
    });
    stream.on("close", () => wire.events.push("close"));
    wire.stream = stream;
    queueMicrotask(() => stream.push(Buffer.from("nsealr-public-usb-open-v1\n")));
    return stream;
  } };
});

const CLIENT = { surface: "cli" as const, origin: "cli:nsealr-public-s3", app_name: "nSealr public S3 lab", instance_id: "v01" };
const ROOT = new URL("../../../../docs/restart/implementation/V01/public-s3-live-flow/", import.meta.url);
async function context() {
  wire.writes = []; wire.events = []; wire.endedBeforeClose = false;
  const dir = mkdtempSync(join(tmpdir(), "nsealr-v01-eof-"));
  const grantStorePath = join(dir, "grants.json"), accountStorePath = join(dir, "accounts.json"),
    routeDriverStorePath = join(dir, "drivers.json"), storageApprovalPath = join(dir, "storage.json");
  const now = Math.floor(Date.now()/1000);
  writeFileSync(accountStorePath, readFileSync(new URL("accounts.example.json", ROOT)));
  writeFileSync(routeDriverStorePath, readFileSync(new URL("drivers.example.json", ROOT)));
  writeFileSync(grantStorePath, JSON.stringify(createLocalGrantStore([{
    client_id: clientIdForIdentity(CLIENT), origin: CLIENT.origin, surface: CLIENT.surface,
    approved_at: now-1, expires_at: now+600,
    allowed_operations: ["select_account_route","validate_signer_request","dispatch_signer_request","verify_signer_response"]
  }], { updatedAt: now })));
  const review = createLocalStorageReview([
    {purpose:"grant_store",path:grantStorePath}, {purpose:"account_store",path:accountStorePath},
    {purpose:"route_driver_store",path:routeDriverStorePath}
  ].map(x=>({...x,access:"read_only",contains_secret_material:false})));
  writeFileSync(storageApprovalPath, JSON.stringify(approveLocalStorageReview(review,{approvedAt:now})));
  const session = await loadPublicS3Context({ grantStorePath, accountStorePath, routeDriverStorePath, storageApprovalPath });
  return { session, async close() { try { await session.close(); } finally { rmSync(dir,{recursive:true,force:true}); } } };
}
describe("public lease EOF boundary; real Node stream events, no USB", () => {
  it("F2 refuses a valid buffered response after observed EOF before close", async () => {
    const request = {version:2,request_id:"public-s3-observed-eof",method:"sign_event",
      params:{event_template:{kind:1,created_at:1710000000,content:"S3 public physical approval",tags:[]}}};
    wire.response = encodeSerialFrame({type:"response",payload:devSignRequest(request,"0".repeat(63)+"3")});
    expect(decodeSerialFrame(wire.response).type).toBe("response");
    const f = await context();
    try {
      f.session.arm();
      const client = new LocalServiceClient({exchange: r=>handleLocalServiceRequestAsync(r,f.session.context)});
      const reply = await client.dispatchSignerRequest(CLIENT,{
        account_id:"public-s3",method:"sign_event",implementation_id:"nsealr.s3.public.scalar3.e7f04215.v1",
        custody:"volatile_session",transport:"usb",limits_id:"nsealr.limits.s3.public.e7.v1"
      },request);
      expect(wire.writes).toHaveLength(1); // The one in-flight write is not recalled.
      expect(wire.endedBeforeClose).toBe(true);
      expect(wire.events.indexOf("end")).toBeLessThan(wire.events.indexOf("write-complete"));
      expect(wire.events.indexOf("end")).toBeLessThan(wire.events.indexOf("close"));
      expect(reply.ok).toBe(false);
      expect(f.session.context.publicS3Fixture!.connection()).toMatchObject({state:"failed",generation:1});
      expect(()=>f.session.check()).toThrow(/lease/);
    } finally { await f.close(); }
  });
  it("F2 rejects an already observed EOF at admission and keeps failure after close", async () => {
    const f = await context();
    try {
      const ended = once(wire.stream,"end");
      wire.stream.push(null); wire.stream.resume(); await ended;
      expect(wire.stream.readableEnded).toBe(true);expect(wire.stream.destroyed).toBe(false);
      f.session.arm();
      expect(f.session.context.publicS3Fixture!.connection()).toMatchObject({state:"failed",generation:1});
      expect(()=>f.session.context.publicS3Fixture!.begin()).toThrow(/fresh connection/);
      await f.session.close();
      expect(f.session.context.publicS3Fixture!.connection()).toMatchObject({state:"failed",generation:1});
      expect(wire.writes).toHaveLength(0);
    } finally { await f.close(); }
  });
});
