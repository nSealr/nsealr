export class PublicS3Budget {
    clock;
    start;
    last;
    activeStart;
    charged = 0n;
    externalCpu = 0;
    external = false;
    entered = false;
    failed = false;
    constructor(clock = {
        nowNs: () => process.hrtime.bigint(),
        cpuUs: () => { const c = process.cpuUsage(); return c.user + c.system; }
    }) {
        this.clock = clock;
        this.start = this.last = this.activeStart = this.sample();
        this.cpu();
    }
    sample() {
        const now = this.clock.nowNs();
        if (typeof now !== "bigint" || now < 0n || now > ((1n << 64n) - 1n) - 100000000000n)
            throw new Error("public S3 clock unavailable");
        return now;
    }
    cpu() {
        const n = this.clock.cpuUs();
        if (!Number.isSafeInteger(n) || n < 0)
            throw new Error("public S3 CPU observation unavailable");
        return n;
    }
    check() {
        if (this.failed)
            throw new Error("public S3 budget revoked");
        try {
            const now = this.sample();
            if (now < this.last || now - this.start >= 100000000000n)
                throw new Error("public S3 absolute deadline/clock");
            this.last = now;
            let charge = this.charged;
            if (this.external) {
                const cpu = this.cpu();
                if (cpu < this.externalCpu)
                    throw new Error("public S3 CPU counter rollback");
                // One microsecond upper rounding per sampled interval, conservatively.
                charge += BigInt(cpu - this.externalCpu + 1) * 1000n;
            }
            else
                charge += now - this.activeStart;
            if (charge >= 5000000000n)
                throw new Error("public S3 host ACTIVE/CPU budget exceeded");
        }
        catch (error) {
            this.failed = true;
            throw error;
        }
    }
    phase(phase) {
        this.check();
        try {
            if (phase === "external") {
                if (this.external || this.entered)
                    throw new Error("public S3 permits one external phase");
                this.charged += this.last - this.activeStart;
                this.externalCpu = this.cpu();
                this.external = this.entered = true;
            }
            else if (this.external) {
                const cpu = this.cpu();
                if (cpu < this.externalCpu)
                    throw new Error("public S3 CPU counter rollback");
                this.charged += BigInt(cpu - this.externalCpu + 1) * 1000n;
                this.external = false;
                this.activeStart = this.last;
            }
            this.check();
        }
        catch (error) {
            this.failed = true;
            throw error;
        }
    }
    remainingMs() {
        this.check();
        return Number((100000000000n - (this.last - this.start) + 999999n) / 1000000n);
    }
}
