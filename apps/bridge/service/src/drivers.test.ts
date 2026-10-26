import { createHash as independentPlanHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { clientIdForIdentity, handleLocalServiceRequestAsync, type SignerDispatchRequest, type SignerCompatibilitySnapshot } from "@nsealr/client";
import { parseAccountDescriptor } from "@nsealr/policy";
import { resolveSpecsRoot } from "@nsealr/fixtures";
import { encodeSerialFrame } from "@nsealr/framing";
import {
  MAX_SERIAL_LINE_IGNORED_LINES,
  MAX_SERIAL_LINE_RESPONSE_TIMEOUT_MS,
  SERVICE_ROUTE_DRIVER_STORE_FORMAT,
  createServiceRouteDispatcher,
  parseServiceRouteDriverStore
} from "./drivers.js";

const specsRoot = resolveSpecsRoot();
const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-kind-1-basic.json"), "utf8"));
const response = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));
const dispatchRequest: SignerDispatchRequest = {
  client: {
    surface: "native_host_test",
    origin: "app:nsealr-service-test",
    app_name: "nSealr service test"
  },
  route_selection: JSON.parse(readFileSync(resolve(specsRoot, "vectors/route-selections/esp32-usb-sign-event-slot-0.json"), "utf8")).selection,
  before_write: () => undefined,
  effective_limits: (() => {
    const common = JSON.parse(readFileSync(resolve(specsRoot, "vectors/profile-capabilities/cases-v1.json"), "utf8"));
    return { method: common.limits_manifest.methods.find((entry: {method_id: string}) => entry.method_id === "sign_event"), transport: common.limits_manifest.transports.find((entry: {transport_id: string}) => entry.transport_id === "usb") };
  })(),

  request
};

function routeDriver(route: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    account_id: "acct-esp32-usb-slot-0",
    route_type: "esp32_usb_nip46",
    transport: "usb",
    driver: "serial_line",
    serial_line: {
      path: "/dev/cu.usbmodem-test",
      response_timeout_ms: 1000
    },
    ...route
  };
}

function routeDriverStore(route: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    format: SERVICE_ROUTE_DRIVER_STORE_FORMAT,
    updated_at: 1_900_000_000,
    contains_secret_material: false,
    routes: [routeDriver(route)]
  };
}

function serialRoute(store: ReturnType<typeof parseServiceRouteDriverStore>) {
  const route = store.routes[0];
  expect(route.driver).toBe("serial_line");
  if (route.driver !== "serial_line") throw new Error("expected serial-line fixture");
  return route;
}

describe("service route drivers", () => {
  it("applies the effective serial frame ceiling to actual peer errors as well as positive responses", async () => {
    const request = JSON.parse(readFileSync(resolve(specsRoot, "examples/request-get-public-key.json"), "utf8"));
    const positive = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-get-public-key.json"), "utf8"));
    const error = { version: 2, request_id: request.request_id, ok: false,
      error: { code: "user_rejected", message: "x".repeat(200), retryable: false } };
    expect(JSON.stringify(error).length).toBeLessThan(704);
    for (const response of [positive, error]) {
      let writes = 0, closes = 0;
      const dispatcher = createServiceRouteDispatcher(parseServiceRouteDriverStore(routeDriverStore()), {
        openSerialLinePort: () => ({ writeLine: async () => { writes++; },
          readLine: async () => encodeSerialFrame({ type: "response", payload: response }), close: () => { closes++; } })
      });
      const effective = structuredClone(dispatchRequest.effective_limits!);
      effective.transport.frame_bytes = 226;
      const operation = dispatcher({ ...dispatchRequest, request, effective_limits: effective });
      if (response === positive) await expect(operation).resolves.toEqual(positive);
      else await expect(operation).rejects.toMatchObject({ code: "signer_transport_protocol_error" });
      expect({ writes, closes }).toEqual({ writes: 1, closes: 1 });
    }
  });

  it("parses explicit secretless serial-line route driver stores", () => {
    expect(parseServiceRouteDriverStore(routeDriverStore())).toEqual({
      format: SERVICE_ROUTE_DRIVER_STORE_FORMAT,
      updated_at: 1_900_000_000,
      contains_secret_material: false,
      routes: [{
        account_id: "acct-esp32-usb-slot-0",
        route_type: "esp32_usb_nip46",
        transport: "usb",
        driver: "serial_line",
        serial_line: {
          path: "/dev/cu.usbmodem-test",
          response_timeout_ms: 1000
        }
      }]
    });
  });

  it("rejects broad, secret-bearing, or QR route driver stores", () => {
    expect(() => parseServiceRouteDriverStore({
      ...routeDriverStore(),
      routes: []
    })).toThrow(/routes must be a non-empty array/u);
    expect(() => parseServiceRouteDriverStore({
      ...routeDriverStore(),
      routes: [routeDriver(), routeDriver()]
    })).toThrow(/duplicate account\/route\/transport/u);
    expect(() => parseServiceRouteDriverStore(routeDriverStore({ account_id: "*" }))).toThrow(
      /account_id must be a stable string id/u
    );
    expect(() => parseServiceRouteDriverStore(routeDriverStore({ account_id: undefined }))).toThrow(
      /account_id must be a stable string id/u
    );
    expect(() => parseServiceRouteDriverStore(routeDriverStore({ route_type: "raspberry_qr_vault" }))).toThrow(
      /route_type is unsupported for serial_line/u
    );
    expect(() => parseServiceRouteDriverStore(routeDriverStore({ transport: "qr" }))).toThrow(
      /transport must be usb/u
    );
    expect(() => parseServiceRouteDriverStore({
      ...routeDriverStore(),
      contains_secret_material: true
    })).toThrow(/must not contain secret material/u);
    expect(() => parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        mnemonic: "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
      }
    }))).toThrow(/secret field routes\[0\]\.serial_line\.mnemonic/u);
  });

  it("accepts only supported local serial device paths", () => {
    const validPaths = [
      "/dev/cu.usbmodem-test",
      "/dev/ttyUSB0",
      "/dev/serial/by-id/usb-Espressif_USB_JTAG_serial_debug_unit-40:22:D8:00-if00",
      "/dev/serial/by-path/pci-0000:00:14.0-usb-0:6:1.0-port0",
      "COM3",
      "\\\\.\\COM10"
    ];
    for (const path of validPaths) {
      expect(serialRoute(parseServiceRouteDriverStore(routeDriverStore({
        serial_line: {
          path
        }
      }))).serial_line.path).toBe(path);
    }

    const invalidPaths = [
      "cu.usbmodem-test",
      "/tmp/cu.usbmodem-test",
      "/dev/cu.usbmodem-test\n--flag",
      "/dev/cu.usbmodem-test ",
      "https://example.com/serial",
      "/dev/serial/by-id/../ttyUSB0",
      "COM0",
      "\\\\.\\COM0"
    ];
    for (const path of invalidPaths) {
      expect(() => parseServiceRouteDriverStore(routeDriverStore({
        serial_line: {
          path
        }
      }))).toThrow(/serial_line\.path/u);
    }
  });

  it("bounds serial-line route timing and ignored-log controls", () => {
    expect(serialRoute(parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        max_ignored_lines: MAX_SERIAL_LINE_IGNORED_LINES,
        response_timeout_ms: MAX_SERIAL_LINE_RESPONSE_TIMEOUT_MS
      }
    }))).serial_line).toEqual({
      path: "/dev/cu.usbmodem-test",
      max_ignored_lines: MAX_SERIAL_LINE_IGNORED_LINES,
      response_timeout_ms: MAX_SERIAL_LINE_RESPONSE_TIMEOUT_MS
    });

    expect(() => parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        max_ignored_lines: MAX_SERIAL_LINE_IGNORED_LINES + 1
      }
    }))).toThrow(/max_ignored_lines exceeds max/u);

    expect(() => parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        response_timeout_ms: MAX_SERIAL_LINE_RESPONSE_TIMEOUT_MS + 1
      }
    }))).toThrow(/response_timeout_ms exceeds max/u);
  });

  it("dispatches matching requests through an injected serial-line opener", async () => {
    const store = parseServiceRouteDriverStore(routeDriverStore());
    const written: string[] = [];
    const dispatcher = createServiceRouteDispatcher(store, {
      openSerialLinePort: (path) => {
        expect(path).toBe("/dev/cu.usbmodem-test");
        return {
          writeLine: async (line) => {
            written.push(line);
          },
          readLine: async () => encodeSerialFrame({ type: "response", payload: response }),
          close: async () => {
            written.push("closed");
          }
        };
      }
    });

    await expect(dispatcher(dispatchRequest)).resolves.toEqual(response);
    expect(written[0]).toMatch(/^nsealr1f:request:/u);
    expect(written.at(-1)).toBe("closed");
  });

  it("R-01/R-05: actual service and serial driver bind the selected account before open and again before write", async () => {
    for (const stale of ["none", "generation", "geometry", "context", "pages"]) {
      const common = JSON.parse(readFileSync(resolve(specsRoot, "vectors/profile-capabilities/cases-v1.json"), "utf8"));
      const implementation = JSON.parse(readFileSync(resolve(specsRoot, common.implementation_examples.esp32_no_se), "utf8"));
      const adapter = structuredClone(implementation);
      const { conformance_only: _, ...body } = structuredClone(implementation);
      const reported = { ...body, format: "nsealr.capabilities.v1", form: "full" };
      for (const source of [adapter, reported]) for (const method of source.methods) Object.assign(method, { configuration: "configured", availability: "available", reason: null });
      const snapshot: SignerCompatibilitySnapshot = { implementation, adapter, reported, limits: structuredClone(common.limits_manifest), adapter_limits: structuredClone(common.limits_manifest), connection_id: "conformance.recording-usb", generation: 1, review_plan: { request_sha256: independentPlanHash("sha256").update(JSON.stringify(request)).digest("hex"), implementation_id: implementation.implementation_id, connection_id: "conformance.recording-usb", generation: 1, context_id: "conformance.no-authority", geometry_id: "conformance.recording.synthetic", pages: 7 } };
      const account = parseAccountDescriptor(JSON.parse(readFileSync(resolve(specsRoot, "vectors/accounts/esp32-usb-device-slot-0.json"), "utf8")));
      const written: string[] = []; let opens = 0; let closes = 0;
      const dispatcher = createServiceRouteDispatcher(parseServiceRouteDriverStore(routeDriverStore()), {
        openSerialLinePort: async () => {
          opens++;
          if (stale === "generation") snapshot.generation++;
          else if (stale === "geometry") snapshot.review_plan!.geometry_id = "changed.geometry";
          else if (stale === "context") snapshot.review_plan!.context_id = "changed.context";
          else if (stale === "pages") snapshot.review_plan!.pages++;
          return { writeLine: async (line) => { written.push(line); }, readLine: async () => encodeSerialFrame({ type: "response", payload: response }), close: async () => { closes++; } };
        }
      });
      const result = await handleLocalServiceRequestAsync({
        version: 1, request_id: "service.recording.usb", operation: "dispatch_signer_request",
        params: { client: dispatchRequest.client, route_request: { account_id: account.account_id, method: "sign_event" }, request }
      }, {
        accounts: [account], now: 1, monotonicNow: () => 0,
        grants: [{ client_id: clientIdForIdentity(dispatchRequest.client), origin: dispatchRequest.client.origin, surface: dispatchRequest.client.surface, allowed_operations: ["dispatch_signer_request"] }],
        signerCompatibility: () => snapshot, signerDispatcher: dispatcher
      });
      expect(result).toMatchObject({ ok: stale === "none" });
      expect(opens).toBe(1); expect(closes).toBe(1);
      expect(written).toEqual(stale === "none" ? [encodeSerialFrame({ type: "request", payload: request })] : []);
    }
  });

  it("maps serial-line route failures to deterministic transport error codes", async () => {
    const store = parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        max_ignored_lines: 1,
        response_timeout_ms: 5
      }
    }));

    const openFailed = createServiceRouteDispatcher(store, {
      openSerialLinePort: () => {
        throw new Error("EACCES: permission denied");
      }
    });
    await expect(openFailed(dispatchRequest)).rejects.toMatchObject({
      code: "signer_transport_open_failed",
      message: "EACCES: permission denied"
    });

    const timedOut = createServiceRouteDispatcher(store, {
      openSerialLinePort: () => ({
        writeLine: async () => {},
        readLine: async () => new Promise<string | null>(() => {})
      })
    });
    await expect(timedOut(dispatchRequest)).rejects.toMatchObject({
      code: "signer_transport_timeout"
    });

    const protocolFailed = createServiceRouteDispatcher(store, {
      openSerialLinePort: () => ({
        writeLine: async () => {},
        readLine: async () => "I boot log without protocol frame\n"
      })
    });
    await expect(protocolFailed(dispatchRequest)).rejects.toMatchObject({
      code: "signer_transport_protocol_error"
    });

    const ioFailed = createServiceRouteDispatcher(store, {
      openSerialLinePort: () => ({
        writeLine: async () => {
          throw new Error("write failed");
        },
        readLine: async () => encodeSerialFrame({ type: "response", payload: response })
      })
    });
    await expect(ioFailed(dispatchRequest)).rejects.toMatchObject({
      code: "signer_transport_io_failed",
      message: "write failed"
    });

    const closeFailed = createServiceRouteDispatcher(store, {
      openSerialLinePort: () => ({
        writeLine: async () => {},
        readLine: async () => encodeSerialFrame({ type: "response", payload: response }),
        close: async () => {
          throw new Error("close failed");
        }
      })
    });
    await expect(closeFailed(dispatchRequest)).rejects.toMatchObject({
      code: "signer_transport_close_failed",
      message: "close failed"
    });
  });
});
