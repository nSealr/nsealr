// Named public experiment only; this meters the service process, never S3 CPU.
export type PublicBudgetClock = { nowNs(): bigint; cpuUs(): number };
export class PublicS3Budget {
  private readonly start: bigint;
  private last: bigint;
  private activeStart: bigint;
  private charged = 0n;
  private externalCpu = 0;
  private external = false;
  private entered = false;
  private failed = false;
  constructor(private readonly clock: PublicBudgetClock = {
    nowNs: () => process.hrtime.bigint(),
    cpuUs: () => { const c = process.cpuUsage(); return c.user + c.system; }
  }) {
    this.start = this.last = this.activeStart = this.sample();
    this.cpu();
  }
  private sample(): bigint {
    const now = this.clock.nowNs();
    if (typeof now !== "bigint" || now < 0n || now > ((1n << 64n) - 1n) - 100_000_000_000n) throw new Error("public S3 clock unavailable");
    return now;
  }
  private cpu(): number {
    const n = this.clock.cpuUs();
    if (!Number.isSafeInteger(n) || n < 0) throw new Error("public S3 CPU observation unavailable");
    return n;
  }
  check(): void {
    if (this.failed) throw new Error("public S3 budget revoked");
    try {
      const now = this.sample();
      if (now < this.last || now - this.start >= 100_000_000_000n) throw new Error("public S3 absolute deadline/clock");
      this.last = now;
      let charge = this.charged;
      if (this.external) {
        const cpu = this.cpu();
        if (cpu < this.externalCpu) throw new Error("public S3 CPU counter rollback");
        // One microsecond upper rounding per sampled interval, conservatively.
        charge += BigInt(cpu - this.externalCpu + 1) * 1000n;
      } else charge += now - this.activeStart;
      if (charge >= 5_000_000_000n) throw new Error("public S3 host ACTIVE/CPU budget exceeded");
    } catch (error) { this.failed = true; throw error; }
  }
  phase(phase: "active" | "external"): void {
    this.check();
    try {
      if (phase === "external") {
        if (this.external || this.entered) throw new Error("public S3 permits one external phase");
        this.charged += this.last - this.activeStart;
        this.externalCpu = this.cpu();
        this.external = this.entered = true;
      } else if (this.external) {
        const cpu = this.cpu();
        if (cpu < this.externalCpu) throw new Error("public S3 CPU counter rollback");
        this.charged += BigInt(cpu - this.externalCpu + 1) * 1000n;
        this.external = false;
        this.activeStart = this.last;
      }
      this.check();
    } catch (error) { this.failed = true; throw error; }
  }
  remainingMs(): number {
    this.check();
    return Number((100_000_000_000n - (this.last - this.start) + 999_999n) / 1_000_000n);
  }
}
