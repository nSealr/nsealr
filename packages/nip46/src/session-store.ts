// Secretless persistence for NIP-46 active sessions. A persisted record is a
// contract-conformant `nsealr-nip46-session-active-v0` object: metadata, pubkeys,
// relays, connect digest and approved permissions only — never the client
// transport key, the NIP-44 conversation key, or any other secret material.
// Every record is validated through `parseNip46SessionActive` on the way in, so
// a record carrying secret fields (or drifting from the contract) is rejected.

import { NIP46_SESSION_ACTIVE_PHASE_FLAGS, parseNip46SessionActive, type Nip46Permission, type Nip46SessionActive } from "./nip46.js";

export type ActiveSessionRecordInput = {
  name: string;
  phase: "connect_ack" | "session_active" | "session_closed";
  clientPubkey: string;
  remoteSignerPubkey: string;
  relays: string[];
  connectDigest: string;
  approvedPermissions: Nip46Permission[];
  secretPresent: boolean;
};

const PERSISTED_FIELDS = [
  "name",
  "client_pubkey",
  "remote_signer_pubkey",
  "relays",
  "connect_digest",
  "approved_permissions",
  "phase"
];

function scopeForPhase(phase: ActiveSessionRecordInput["phase"]): string {
  if (phase === "session_closed") {
    return "Closed NIP-46 session: relay closed and NIP-44 conversation key wiped; session state persisted (metadata only), no secret material.";
  }
  return `Active NIP-46 session in ${phase} phase: NIP-44 transport over relay, session state persisted (metadata only), no secret material.`;
}

// Assemble a contract-conformant active-session record from runtime state +
// connect-review metadata. Validated through the contract parser before return,
// so the persisted shape can never silently drift from specs.
export function toActiveSessionRecord(input: ActiveSessionRecordInput): Nip46SessionActive {
  const flags = NIP46_SESSION_ACTIVE_PHASE_FLAGS[input.phase];
  return parseNip46SessionActive({
    name: input.name,
    format: "nsealr-nip46-session-active-v0",
    phase: input.phase,
    client_pubkey: input.clientPubkey,
    remote_signer_pubkey: input.remoteSignerPubkey,
    relays: input.relays,
    connect_digest: input.connectDigest,
    approved_permissions: input.approvedPermissions,
    nip44: { event_kind: 24133, payload_encrypted: true, version: 2 },
    acknowledges_connect: flags.acknowledges_connect,
    derives_nip44_key: flags.derives_nip44_key,
    opens_relay: flags.opens_relay,
    dispatches_signer: flags.dispatches_signer,
    creates_grants: false,
    persists_session_state: true,
    persisted_state: { fields: [...PERSISTED_FIELDS], contains_secret_material: false },
    secret_present: input.secretPresent,
    secret_value_stored: false,
    contains_secret_material: false,
    stores_production_secrets: false,
    scope: scopeForPhase(input.phase)
  });
}

export interface SessionStore {
  save(record: Nip46SessionActive): Promise<void>;
  load(name: string): Promise<Nip46SessionActive | undefined>;
  list(): Promise<string[]>;
  delete(name: string): Promise<void>;
}

export class InMemorySessionStore implements SessionStore {
  private readonly records = new Map<string, Nip46SessionActive>();

  async save(record: Nip46SessionActive): Promise<void> {
    const validated = parseNip46SessionActive(record);
    this.records.set(validated.name, validated);
  }

  async load(name: string): Promise<Nip46SessionActive | undefined> {
    const record = this.records.get(name);
    return record === undefined ? undefined : structuredClone(record);
  }

  async list(): Promise<string[]> {
    return [...this.records.keys()].sort();
  }

  async delete(name: string): Promise<void> {
    this.records.delete(name);
  }
}
