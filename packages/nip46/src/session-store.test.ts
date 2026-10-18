import { describe, expect, it } from "vitest";
import { NIP46_SESSION_SECRET_FIELDS, parseNip46SessionActive } from "./nip46.js";
import {
  InMemorySessionStore,
  toActiveSessionRecord,
  type ActiveSessionRecordInput
} from "./session-store.js";

const baseInput: ActiveSessionRecordInput = {
  name: "session-1",
  phase: "session_active",
  clientPubkey: "b".repeat(64),
  remoteSignerPubkey: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
  relays: ["wss://relay1.example.com/"],
  connectDigest: "4591a3b711e32fdbadbfce542b15127490f8215351e621b0a0e0ed1e4f093225",
  approvedPermissions: [{ method: "sign_event", parameter: "1", event_kind: 1 }],
  secretPresent: true
};

describe("toActiveSessionRecord", () => {
  it("produces a contract-conformant record for each persistable phase", () => {
    for (const phase of ["connect_ack", "session_active", "session_closed"] as const) {
      const record = toActiveSessionRecord({ ...baseInput, name: `session-${phase}`, phase });
      // The record must round-trip through the contract parser unchanged.
      expect(() => parseNip46SessionActive(record)).not.toThrow();
      expect(record.phase).toBe(phase);
      expect(record.persists_session_state).toBe(true);
      expect(record.contains_secret_material).toBe(false);
    }
  });

  it("never persists secret material in the field list", () => {
    const record = toActiveSessionRecord(baseInput);
    for (const field of record.persisted_state.fields) {
      expect(NIP46_SESSION_SECRET_FIELDS.has(field.toLowerCase())).toBe(false);
    }
  });
});

describe("InMemorySessionStore", () => {
  it("saves, loads, lists and deletes records", async () => {
    const store = new InMemorySessionStore();
    const record = toActiveSessionRecord(baseInput);
    await store.save(record);
    expect(await store.load("session-1")).toEqual(record);
    expect(await store.list()).toEqual(["session-1"]);
    await store.delete("session-1");
    expect(await store.load("session-1")).toBeUndefined();
    expect(await store.list()).toEqual([]);
  });

  it("rejects a record that is not contract-conformant", async () => {
    const store = new InMemorySessionStore();
    const bad = { ...toActiveSessionRecord(baseInput), stores_production_secrets: true } as never;
    await expect(store.save(bad)).rejects.toThrow();
  });
});
