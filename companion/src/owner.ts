import { Collector, frames } from './frames.ts';
import { identity, request, response } from './protocol.ts';
import type { Method, Request, SignedEvent } from './protocol.ts';

export type Operation = { request: Request; origin: string; frames: string[]; expires: number };
export type Result = string | SignedEvent;
type Pending = Operation & { resolve: (value: Result) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> };

// Browser grants only admit requests. Every admitted operation still crosses the device.
export class Owner {
  key: string | null = null;
  private pending: Pending | null = null;
  readonly collector = new Collector();
  readonly grants = new Map<string, Set<Method>>();
  generation = 0;
  reserved = false;
  private changed: () => void;
  private lifetime: number;
  constructor(changed: () => void = () => {}, lifetime = 10 * 60_000) { this.changed = changed; this.lifetime = lifetime; }
  get operation(): Operation | null {
    if (!this.pending) return null;
    const { request, origin, frames, expires } = this.pending;
    return { request, origin, frames, expires };
  }
  select(value: string) {
    const key = identity(value);
    this.cancel('Identity changed.'); this.grants.clear(); this.key = key; this.changed();
  }
  grant(origin: string, method: Method) {
    const set = this.grants.get(origin) ?? new Set<Method>(); set.add(method); this.grants.set(origin, set); this.changed();
  }
  revoke(origin: string) {
    this.grants.delete(origin);
    if (this.pending?.origin === origin) this.cancel('Connection revoked.');
    else this.generation++;
    this.changed();
  }
  start(origin: string, method: Method, params: unknown[], local = false): Promise<Result> {
    if (this.reserved && !local) return Promise.reject(Error('Another coordinated device operation is in progress.'));
    if (this.pending) return Promise.reject(Error('Another device request is already open.'));
    if (!local && !this.grants.get(origin)?.has(method)) return Promise.reject(Error('This application has no permission for that method.'));
    let prepared: Request;
    try { prepared = request(method, params, this.key); Object.freeze(prepared.params); Object.freeze(prepared); } catch (error) { return Promise.reject(error); }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.cancel('The request expired.'), this.lifetime);
      this.collector.clear();
      this.pending = { request: prepared, origin, frames: frames(JSON.stringify(prepared)), expires: Date.now() + this.lifetime, resolve, reject, timer };
      this.changed();
    });
  }
  scan(frame: string): boolean {
    const pending = this.pending;
    if (!pending) throw Error('There is no pending device request.');
    if (Date.now() > pending.expires) { this.cancel('The request expired.'); return false; }
    try {
      const message = this.collector.add(frame); this.changed();
      if (message === null) return false;
      const value = response(message, pending.request, this.key);
      if (pending.request.method === 'get_public_key') this.key = value as string;
      this.pending = null; clearTimeout(pending.timer); this.collector.clear(); pending.resolve(value); this.changed(); return true;
    } catch (error) {
      this.cancel(error instanceof Error ? error.message : 'Device response failed.'); throw error;
    }
  }
  cancel(reason = 'Request cancelled.') {
    this.generation++;
    const pending = this.pending; this.pending = null; this.collector.clear();
    if (pending) { clearTimeout(pending.timer); pending.reject(Error(reason)); }
    this.changed();
  }
  disconnect() { this.cancel('Companion disconnected.'); this.key = null; this.grants.clear(); this.changed(); }
}
