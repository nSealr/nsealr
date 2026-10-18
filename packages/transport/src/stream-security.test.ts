import { PassThrough, Writable } from "node:stream";
import { describe, expect, it } from "vitest";
import { SerialLineStreamPort } from "./transport.js";

describe("S01 stream retained-state bounds", () => {
  it("rejects 10000 short lines before retaining 20000 bytes under a four-byte cap", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4 });
    input.write("x\n".repeat(10000));
    const diagnostic = port as unknown as { buffer: string };
    const retainedBytes = Buffer.byteLength(diagnostic.buffer);
    try {
      expect(retainedBytes, `baseline retains ${retainedBytes} bytes`).toBeLessThanOrEqual(4);
      await expect(port.readLine()).rejects.toThrow(/buffer|limit|bound/i);
    } finally { port.close(); }
  });

  it("pauses queued complete lines and resumes after consumption", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4 });
    try {
      input.write("a\nb\n");
      expect(input.isPaused()).toBe(true);
      expect(await port.readLine()).toBe("a\n");
      expect(await port.readLine()).toBe("b\n");
      expect(input.isPaused()).toBe(false);
    } finally { port.close(); }
  });

  it("bounds pending readers and rejects them on close", async () => {
    const port = new SerialLineStreamPort({ input: new PassThrough(), output: new PassThrough() });
    const first = port.readLine();
    const firstCheck = expect(first).rejects.toThrow(/clos/i);
    const secondCheck = expect(port.readLine()).rejects.toThrow(/pending|progress/i);
    port.close();
    await Promise.all([firstCheck, secondCheck]);
  });

  it("cancels a stalled pending write and rejects later writes", async () => {
    const output = new Writable({ write() {} });
    const port = new SerialLineStreamPort({ input: new PassThrough(), output });
    const write = port.writeLine("x");
    const check = expect(write).rejects.toThrow(/clos/i);
    port.close();
    await check;
    await expect(port.writeLine("x")).rejects.toThrow(/clos/i);
  });
});

describe("S01 stream limits, errors and cleanup", () => {
  // F01 was independently reproduced in review/s01 at 67804a5d1995504a69d2fe49618da8e263ec3d89.
  // Compare listener identities as well as counts: the port must preserve inherited listeners.
  const listeners = (stream: PassThrough) => stream.eventNames().map(name => [name, stream.listeners(name)]);
  const tick = () => new Promise<void>(resolve => setImmediate(resolve));

  for (const emitClose of [true, false]) {
    // F02 independent probe: review/s01 at 63cff320864552888c0666f972dacf7ea5ec2084.
    for (const suppressErrorEvent of [false, true]) {
      it(`discards EOF data after a recorded destruction error: emitClose=${emitClose}, suppress=${suppressErrorEvent}`, async () => {
        const input = new PassThrough({ autoDestroy: false, emitClose, destroy(error, callback) {
          setImmediate(() => callback(suppressErrorEvent ? null : error));
        } });
        const output = new PassThrough();
        const inheritedInput = listeners(input), inheritedOutput = listeners(output);
        const port = new SerialLineStreamPort({ input, output });
        input.end("stale");
        await tick();
        expect(input.readableEnded).toBe(true);
        const error = new Error("destruction failure after EOF");
        input.destroy(error);
        await tick();
        await tick();
        try {
          expect(input.closed).toBe(true);
          expect(input.errored).toBe(error);
          await expect(port.readLine()).rejects.toBe(error);
          await expect(port.writeLine("x")).rejects.toBe(error);
          expect((port as unknown as { buffer: string }).buffer).toBe("");
          expect(output.destroyed).toBe(true);
          expect(listeners(input)).toEqual(inheritedInput);
          expect(listeners(output)).toEqual(inheritedOutput);
          port.close();
          await expect(port.readLine()).rejects.toBe(error);
        } finally { port.close(); }
      });
    }

    it(`preserves normal EOF data after error-free destruction: emitClose=${emitClose}`, async () => {
      const input = new PassThrough({ autoDestroy: false, emitClose, destroy(error, callback) {
        setImmediate(() => callback(error));
      } });
      const output = new PassThrough();
      const port = new SerialLineStreamPort({ input, output });
      input.end("tail");
      await tick();
      input.destroy();
      await tick();
      await tick();
      try {
        expect(input.closed).toBe(true);
        expect(input.errored).toBeNull();
        expect(await port.readLine()).toBe("tail");
        expect(await port.readLine()).toBeNull();
        expect(output.destroyed).toBe(false);
      } finally { port.close(); }
    });

    for (const asyncDestroy of [false, true]) {
      for (const shared of [false, true]) {
        it(`cleans completed destruction: emitClose=${emitClose}, async=${asyncDestroy}, shared=${shared}`, async () => {
          const options = { emitClose, ...(asyncDestroy ? {
            destroy(error: Error | null, callback: (error?: Error | null) => void) {
              setImmediate(() => callback(error));
            }
          } : {}) };
          const input = new PassThrough(options), output = shared ? input : new PassThrough(options);
          const inheritedInput = listeners(input), inheritedOutput = listeners(output);
          const port = new SerialLineStreamPort({ input, output });
          port.close();
          port.close();
          await tick();
          await tick();
          expect(input.closed && output.closed).toBe(true);
          expect(listeners(input)).toEqual(inheritedInput);
          expect(listeners(output)).toEqual(inheritedOutput);
        });
      }
    }

    it(`keeps errors handled until delayed destruction completes: emitClose=${emitClose}`, async () => {
      const completions: (() => void)[] = [];
      const error = new Error("asynchronous destruction failure");
      const options = { emitClose, destroy(_error: Error | null, callback: (error?: Error | null) => void) {
        completions.push(() => callback(error));
      } };
      const input = new PassThrough(options), output = new PassThrough(options);
      const inheritedInput = listeners(input), inheritedOutput = listeners(output);
      const port = new SerialLineStreamPort({ input, output });
      const pendingRead = expect(port.readLine()).rejects.toThrow(/closed/);
      port.close();
      await pendingRead;
      await tick();
      expect(input.closed || output.closed).toBe(false);
      expect(input.listenerCount("error")).toBe(1);
      expect(output.listenerCount("error")).toBe(1);
      completions.forEach(complete => complete());
      await tick();
      await tick();
      expect(input.closed && output.closed).toBe(true);
      expect(listeners(input)).toEqual(inheritedInput);
      expect(listeners(output)).toEqual(inheritedOutput);
      await expect(port.readLine()).rejects.toThrow(/closed/);
    });

    it(`keeps errors handled after synchronous destruction callback: emitClose=${emitClose}`, async () => {
      const error = new Error("synchronous destruction failure");
      const options = { emitClose, destroy(_error: Error | null, callback: (error?: Error | null) => void) { callback(error); } };
      const input = new PassThrough(options), output = new PassThrough(options);
      const errors: Error[] = [];
      const observer = (failure: Error) => { errors.push(failure); };
      input.on("error", observer);
      output.on("error", observer);
      const inheritedInput = listeners(input), inheritedOutput = listeners(output);
      const port = new SerialLineStreamPort({ input, output });
      port.close();
      // .closed already true does not mean Node's queued error event has fired.
      const guarded = input.listenerCount("error") === 2 && output.listenerCount("error") === 2;
      await tick();
      await tick();
      expect(guarded).toBe(true);
      expect(errors).toEqual([error, error]);
      expect(listeners(input)).toEqual(inheritedInput);
      expect(listeners(output)).toEqual(inheritedOutput);
    });
  }

  it("restores the destruction hook and its property descriptor, preserving this and the first callback", async () => {
    const error = new Error("first destruction error");
    let calls = 0;
    const input = new PassThrough({ emitClose: false, destroy(failure, callback) {
      expect(this).toBe(input);
      expect(failure).toBe(error);
      ++calls;
      setImmediate(() => { callback(failure); callback(new Error("duplicate callback")); });
    } });
    const output = new PassThrough();
    const original = input._destroy;
    Object.defineProperty(input, "_destroy", { get: () => original, configurable: true, enumerable: false });
    const descriptor = Object.getOwnPropertyDescriptor(input, "_destroy");
    const inheritedInput = listeners(input), inheritedOutput = listeners(output);
    const port = new SerialLineStreamPort({ input, output });
    const pendingRead = expect(port.readLine()).rejects.toBe(error);
    input.destroy(error);
    await pendingRead;
    await tick();
    await tick();
    expect(calls).toBe(1);
    expect(Object.getOwnPropertyDescriptor(input, "_destroy")).toEqual(descriptor);
    expect(Object.hasOwn(output, "_destroy")).toBe(false);
    expect(listeners(input)).toEqual(inheritedInput);
    expect(listeners(output)).toEqual(inheritedOutput);
  });

  for (const side of ["input", "output"] as const) {
    for (const outcome of ["throw", "suppress-error"] as const) {
      it(`observes ${side} destruction with ${outcome} and no close event`, async () => {
        const error = new Error(`${side} failure`);
        const options = { emitClose: false, destroy(_error: Error | null, callback: (error?: Error | null) => void) {
          if (outcome === "throw") throw error;
          setImmediate(() => callback(null));
        } };
        const input = new PassThrough(side === "input" ? options : {});
        const output = new PassThrough(side === "output" ? options : {});
        const inheritedInput = listeners(input), inheritedOutput = listeners(output);
        const port = new SerialLineStreamPort({ input, output });
        const pendingRead = expect(port.readLine()).rejects.toBe(error);
        ({ input, output })[side].destroy(error);
        await pendingRead;
        await tick();
        await tick();
        expect(input.closed && output.closed).toBe(true);
        expect(listeners(input)).toEqual(inheritedInput);
        expect(listeners(output)).toEqual(inheritedOutput);
      });
    }
    for (const restriction of ["readonly", "nonextensible", "already-destroying"] as const) {
      it(`rejects ${restriction} ${side} without partially installing hooks or listeners`, async () => {
        let finishDestroy = () => {};
        const input = new PassThrough(), output = new PassThrough();
        const stream = ({ input, output })[side];
        if (restriction === "readonly") Object.defineProperty(stream, "_destroy", { value: stream._destroy, writable: false, configurable: false });
        else if (restriction === "nonextensible") Object.preventExtensions(stream);
        else {
          stream._destroy = (_error, callback) => { finishDestroy = () => callback(null); };
          stream.destroy();
        }
        const inputHook = Object.getOwnPropertyDescriptor(input, "_destroy"), outputHook = Object.getOwnPropertyDescriptor(output, "_destroy");
        const inheritedInput = listeners(input), inheritedOutput = listeners(output);
        expect(() => new SerialLineStreamPort({ input, output })).toThrow(/replaceable|already closed/);
        expect(listeners(input)).toEqual(inheritedInput);
        expect(listeners(output)).toEqual(inheritedOutput);
        expect(Object.getOwnPropertyDescriptor(input, "_destroy")).toEqual(inputHook);
        expect(Object.getOwnPropertyDescriptor(output, "_destroy")).toEqual(outputHook);
        input.destroy();
        output.destroy();
        finishDestroy();
        await tick();
      });
    }
  }

  it("does not overwrite a later destruction-hook replacement", async () => {
    const input = new PassThrough({ emitClose: false });
    const port = new SerialLineStreamPort({ input, output: input });
    const ownedHook = input._destroy;
    input._destroy = function (error, callback) { ownedHook.call(this, error, callback); };
    const replacement = input._destroy;
    port.close();
    await tick();
    expect(input._destroy).toBe(replacement);
    expect(input.listenerCount("error")).toBe(0);
    expect(input.listenerCount("close")).toBe(0);
  });

  it("bounds complete line count independently from byte count", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 128, maxBufferedLines: 2 });
    input.write("a\nb\nc");
    await expect(port.readLine()).rejects.toThrow(/maxBufferedLines/);
    expect((port as unknown as { buffer: string }).buffer).toBe("");
    expect(input.destroyed).toBe(true);
    expect(output.destroyed).toBe(true);
  });

  it("drains the exact line bound including the trailing partial line at EOF", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4, maxBufferedLines: 2 });
    input.end("a\nb");
    try {
      expect(await port.readLine()).toBe("a\n");
      expect(await port.readLine()).toBe("b");
      expect(await port.readLine()).toBeNull();
    } finally { port.close(); }
  });

  it("counts UTF-8 bytes and CRLF delimiters at the exact boundary", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4 });
    try {
      const bytes = Buffer.from("€\n");
      input.write(bytes.subarray(0, 1));
      input.write(bytes.subarray(1));
      expect(await port.readLine()).toBe("€\n");
      input.write("ab\r\n");
      expect(await port.readLine()).toBe("ab\r\n");
      input.write("€\r\n");
      await expect(port.readLine()).rejects.toThrow(/maxBufferedBytes/);
    } finally { port.close(); }
  });

  it("honors input backpressure for repeated short writes", async () => {
    const input = new PassThrough({ highWaterMark: 4 }), output = new PassThrough();
    const port = new SerialLineStreamPort({ input, output, maxBufferedBytes: 4 });
    let accepted = 0;
    while (accepted < 10000) {
      ++accepted;
      if (!input.write("x\n")) break;
    }
    try {
      expect(accepted).toBeLessThan(10);
      expect(Buffer.byteLength((port as unknown as { buffer: string }).buffer)).toBeLessThanOrEqual(4);
      for (let i = 0; i < accepted; ++i) expect(await port.readLine()).toBe("x\n");
    } finally { port.close(); }
  });

  it("waits for output backpressure and caps pending writes", async () => {
    let complete: (error?: Error | null) => void = () => undefined;
    const output = new Writable({ highWaterMark: 1, write(_chunk, _encoding, callback) { complete = callback; } });
    const port = new SerialLineStreamPort({ input: new PassThrough(), output });
    try {
      let settled = false;
      const write = port.writeLine("x").then(() => { settled = true; });
      await expect(port.writeLine("second")).rejects.toThrow(/pending/);
      await Promise.resolve();
      expect(settled).toBe(false);
      complete();
      await write;
      expect(settled).toBe(true);
      expect(output.listenerCount("drain")).toBe(0);
    } finally { port.close(); }
  });

  it("discards buffered data and permanently preserves the first error", async () => {
    const input = new PassThrough(), output = new PassThrough();
    const observer = () => undefined;
    input.on("data", observer);
    const port = new SerialLineStreamPort({ input, output });
    input.write("stale\n");
    const failure = new Error("device fault");
    input.emit("error", failure);
    input.emit("data", "x\n".repeat(10000));
    port.close();
    await expect(port.readLine()).rejects.toBe(failure);
    await expect(port.writeLine("x")).rejects.toBe(failure);
    expect((port as unknown as { buffer: string }).buffer).toBe("");
    await new Promise(resolve => setImmediate(resolve));
    expect(input.listenerCount("data")).toBe(1);
    expect(input.listenerCount("error")).toBe(0);
    expect(input.listenerCount("close")).toBe(0);
    expect(output.listenerCount("error")).toBe(0);
    expect(output.listenerCount("close")).toBe(0);
    input.off("data", observer);
  });

  it("handles premature input and output close without hanging a read", async () => {
    for (const side of ["input", "output"] as const) {
      const input = new PassThrough(), output = new PassThrough();
      const port = new SerialLineStreamPort({ input, output });
      const check = expect(port.readLine()).rejects.toThrow(/closed/);
      ({ input, output })[side].destroy();
      await check;
      expect(input.destroyed && output.destroyed).toBe(true);
    }
  });

  it("settles callback failures, removes listeners and supports shared duplex", async () => {
    const error = new Error("output fault");
    const output = new Writable({ write(_chunk, _encoding, callback) { callback(error); } });
    const port = new SerialLineStreamPort({ input: new PassThrough(), output });
    await expect(port.writeLine("x")).rejects.toBe(error);
    await new Promise(resolve => setImmediate(resolve));
    expect(output.listenerCount("error")).toBe(0);
    const duplex = new PassThrough();
    const inheritedEvents = duplex.eventNames();
    const shared = new SerialLineStreamPort({ input: duplex, output: duplex });
    const check = expect(shared.readLine()).rejects.toThrow(/clos/);
    shared.close();
    shared.close();
    await check;
    await new Promise(resolve => setImmediate(resolve));
    expect(duplex.eventNames()).toEqual(inheritedEvents);
  });

  it("rejects invalid resource settings and over-limit writes before buffering", async () => {
    for (const maxBufferedBytes of [0, -1, NaN, Infinity, 1.5, 1048577]) {
      expect(() => new SerialLineStreamPort({ input: new PassThrough(), output: new PassThrough(), maxBufferedBytes })).toThrow();
    }
    for (const maxBufferedLines of [0, 4097, 1.5]) {
      expect(() => new SerialLineStreamPort({ input: new PassThrough(), output: new PassThrough(), maxBufferedLines })).toThrow();
    }
    const port = new SerialLineStreamPort({ input: new PassThrough(), output: new PassThrough() });
    await expect(port.writeLine("x".repeat(1024))).rejects.toThrow(/max_serial_frame_bytes/);
    port.close();
  });
});
