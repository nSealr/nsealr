import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { type SignerDispatchRequest } from "@nsealr/client";
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
  route_selection: {
    format: "nsealr-route-selection-v0",
    account_id: "acct-esp32-usb-slot-0",
    public_key: "4f355bdcb7cc0af728ef3cceb9615d90684bb5b2ca5f859ab0f0b704075871aa",
    route_type: "esp32_usb_nip46",
    repository: "firmware",
    transport: "usb",
    custody: "device_persistent",
    trusted_review: "device_display",
    policy_support: "scoped_automation",
    policy_profile_id: "policy-scoped-automation-daily-use",
    physical_review: true,
    physical_approval: true,
    persistent_grants: true,
    contains_secret_material: false
  },
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

describe("service route drivers", () => {
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
      expect(parseServiceRouteDriverStore(routeDriverStore({
        serial_line: {
          path
        }
      })).routes[0].serial_line.path).toBe(path);
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
    expect(parseServiceRouteDriverStore(routeDriverStore({
      serial_line: {
        path: "/dev/cu.usbmodem-test",
        max_ignored_lines: MAX_SERIAL_LINE_IGNORED_LINES,
        response_timeout_ms: MAX_SERIAL_LINE_RESPONSE_TIMEOUT_MS
      }
    })).routes[0].serial_line).toEqual({
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
