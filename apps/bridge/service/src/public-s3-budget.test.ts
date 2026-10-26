import { describe, expect, it } from "vitest";
import { PublicS3Budget } from "./public-s3-budget.js";
function fixture() {
  let now = 0n, cpu = 0;
  const budget = new PublicS3Budget({ nowNs: () => now, cpuUs: () => cpu });
  return { budget, wall: (ns: bigint) => { now += ns; }, cpu: (us: number) => { cpu += us; }, setWall: (ns: bigint) => { now = ns; } };
}
describe("named public service ledger; no USER or target CPU measurement", () => {
  it("allows real-clock-shaped external wall above5s while charging host CPU and ACTIVE", () => {
    const f = fixture(); f.wall(300_000_000n); f.budget.phase("external");
    f.wall(6_000_000_000n); f.cpu(2000); f.budget.phase("active");
    f.wall(300_000_000n); expect(() => f.budget.check()).not.toThrow();
    expect(f.budget.remainingMs()).toBe(93400);
  });
  it("keeps the continuous100s deadline during external work", () => {
    const f = fixture(); f.budget.phase("external"); f.wall(100_000_000_000n);
    expect(() => f.budget.check()).toThrow(/deadline/);
  });
  it("charges ACTIVE wall even with zero CPU", () => {
    const f = fixture(); f.wall(5_000_000_000n); expect(() => f.budget.check()).toThrow(/ACTIVE/);
  });
  it("charges CPU consumed in the external phase", () => {
    const f = fixture(); f.budget.phase("external"); f.wall(10_000_000_000n); f.cpu(5_000_000);
    expect(() => f.budget.check()).toThrow(/ACTIVE/);
  });
  it("retains a failure after clock rollback instead of rearming", () => {
    const f = fixture(); f.wall(100n); f.budget.check(); f.setWall(99n);
    expect(() => f.budget.check()).toThrow(/clock/); f.setWall(101n);
    expect(() => f.budget.check()).toThrow(/revoked/);
  });
  it("rejects CPU rollback/unavailable and a second external phase", () => {
    const f = fixture(); f.cpu(10); f.budget.phase("external"); f.cpu(-1);
    expect(() => f.budget.check()).toThrow(/CPU/);
    expect(() => new PublicS3Budget({ nowNs: () => 0n, cpuUs: () => NaN })).toThrow(/CPU/);
    const g = fixture(); g.budget.phase("external"); g.budget.phase("active");
    expect(() => g.budget.phase("external")).toThrow(/one external/);
  });
  it("rejects invalid clocks/overflow without changing units", () => {
    expect(() => new PublicS3Budget({ nowNs: () => -1n, cpuUs: () => 0 })).toThrow(/clock/);
    expect(() => new PublicS3Budget({ nowNs: () => 1n << 64n, cpuUs: () => 0 })).toThrow(/clock/);
  });
  for (const boundary of ["check","phase-exit"] as const) it("F1 rejects intermediate CPU10→20→19 at "+boundary+" and keeps revocation sticky", () => {
    const f=fixture();f.cpu(10);f.budget.phase("external");
    f.cpu(10);f.budget.check();f.cpu(-1);
    expect(()=>boundary==="check"?f.budget.check():f.budget.phase("active")).toThrow(/CPU/);
    f.cpu(100);
    expect(()=>f.budget.check()).toThrow(/revoked/);
    expect(()=>f.budget.remainingMs()).toThrow(/revoked/);
  });
  it("F1 preserves cumulative external CPU charge across intermediate samples", () => {
    const f=fixture();f.cpu(10);f.budget.phase("external");
    f.cpu(2_000_000);f.budget.check();f.cpu(2_000_000);f.budget.check();
    f.cpu(1_000_000);expect(()=>f.budget.check()).toThrow(/ACTIVE/);
  });

});
