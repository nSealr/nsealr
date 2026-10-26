export type PublicBudgetClock = {
    nowNs(): bigint;
    cpuUs(): number;
};
export declare class PublicS3Budget {
    private readonly clock;
    private readonly start;
    private last;
    private activeStart;
    private charged;
    private externalCpu;
    private lastCpu;
    private external;
    private entered;
    private failed;
    constructor(clock?: PublicBudgetClock);
    private sample;
    private cpu;
    check(): void;
    phase(phase: "active" | "external"): void;
    remainingMs(): number;
}
