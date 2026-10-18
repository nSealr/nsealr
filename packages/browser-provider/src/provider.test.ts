import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  LocalServiceClient,
  handleLocalServiceRequest,
  type LocalClientGrant,
  type LocalClientIdentity
} from "@nsealr/client";
import { type EventTemplate } from "@nsealr/core";
import { loadSpecsFixtures, resolveSpecsRoot } from "@nsealr/fixtures";
import {
  NATIVE_HOST_NAME,
  createBrowserNativeMessagingLocalServiceClient,
  createLocalServiceBrowserProviderBackend,
  createNip07Provider,
  type BrowserProviderBackend
} from "./provider.js";

const specsRoot = resolveSpecsRoot();
const fixtures = loadSpecsFixtures(specsRoot);
const accessSurfaceVector = fixtures.accessSurfaces.find(
  (surface) => surface.name === "browser-provider-local-service-esp32-usb-unavailable"
);
if (!accessSurfaceVector) throw new Error("browser provider access-surface fixture is missing");
const request = JSON.parse(readFileSync(resolve(specsRoot, accessSurfaceVector.sign_event_request_vector), "utf8"));
const response = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-kind-1-basic.json"), "utf8"));
const responseError = JSON.parse(readFileSync(resolve(specsRoot, "examples/response-error-rejected.json"), "utf8"));
const routeVector = fixtures.routeSelections.find((selection) => selection.name === accessSurfaceVector.route_selection_vector);
if (!routeVector) throw new Error("route selection fixture is missing");
const publicKey = response.result.event.pubkey as string;
const client: LocalClientIdentity = accessSurfaceVector.client;
const localServiceGrant: LocalClientGrant = accessSurfaceVector.client_grant as LocalClientGrant;

function backend(overrides: Partial<BrowserProviderBackend> = {}): BrowserProviderBackend {
  return {
    getPublicKey: async (backendClient) => {
      expect(backendClient).toEqual(client);
      return publicKey;
    },
    signEventRequest: async (signerRequest, backendClient) => {
      expect(backendClient).toEqual(client);
      expect(signerRequest).toEqual(request);
      return response;
    },
    ...overrides
  };
}

describe("NIP-07 browser provider boundary", () => {
  it("returns a validated public key from an injected companion backend", async () => {
    const provider = createNip07Provider({ backend: backend(), client });

    await expect(provider.getPublicKey()).resolves.toBe(publicKey);
  });

  it("converts signEvent templates into nSealr signer requests", async () => {
    const provider = createNip07Provider({
      backend: backend(),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.signEvent(request.params.event_template)).resolves.toEqual(response.result.event);
  });

  it("rejects unsafe event templates before contacting the backend", async () => {
    let called = false;
    const provider = createNip07Provider({
      backend: backend({
        signEventRequest: async () => {
          called = true;
          return response;
        }
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.signEvent({
      ...request.params.event_template,
      pubkey: publicKey
    } as unknown as EventTemplate)).rejects.toThrow(/forbidden fields/u);
    expect(called).toBe(false);
  });

  it("rejects malformed backend outputs and explicit signer refusals", async () => {
    const invalidPublicKeyProvider = createNip07Provider({
      backend: backend({ getPublicKey: async () => "not-a-pubkey" }),
      client
    });
    await expect(invalidPublicKeyProvider.getPublicKey()).rejects.toThrow(/public key/u);

    const mismatchedResponseProvider = createNip07Provider({
      backend: backend({
        signEventRequest: async () => ({
          ...response,
          request_id: "other-request"
        })
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });
    await expect(mismatchedResponseProvider.signEvent(request.params.event_template)).rejects.toThrow(/request_id/u);

    const refusedProvider = createNip07Provider({
      backend: backend({
        signEventRequest: async () => ({
          ...responseError,
          request_id: "req-kind-1-basic"
        })
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });
    await expect(refusedProvider.signEvent(request.params.event_template)).rejects.toThrow(/rejected/u);
  });

  it("can back NIP-07 getPublicKey with authorized local-service route selection", async () => {
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [localServiceGrant],
        now: 1_900_000_000
      })
    });
    const localServiceBackend = createLocalServiceBrowserProviderBackend({
      service,
      routeRequest: routeVector.request
    });
    const provider = createNip07Provider({
      backend: localServiceBackend,
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.getPublicKey()).resolves.toBe(accessSurfaceVector.expected.get_public_key.public_key);
    await expect(localServiceBackend.signEventRequest(request, client)).resolves.toEqual(
      accessSurfaceVector.expected.sign_event_without_dispatcher.response
    );
    await expect(provider.signEvent(request.params.event_template)).rejects.toThrow(/Signer dispatch is not configured/u);
  });

  it("can back NIP-07 signEvent with an explicit local-service signer dispatcher", async () => {
    const dispatched: unknown[] = [];
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [localServiceGrant],
        now: 1_900_000_000,
        signerDispatcher: (dispatchRequest) => {
          dispatched.push(dispatchRequest);
          return response;
        }
      })
    });
    const provider = createNip07Provider({
      backend: createLocalServiceBrowserProviderBackend({
        service,
        routeRequest: routeVector.request
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.signEvent(request.params.event_template)).resolves.toEqual(response.result.event);
    expect(dispatched).toEqual([{
      client,
      route_selection: routeVector.selection,
      request
    }]);
  });

  it("rejects wrong-route signer responses before browser callers trust signatures", async () => {
    const wrongRoutePublicKey = "e".repeat(64);
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts.map((account) => account.account_id === routeVector.selection.account_id
          ? { ...account, public_key: wrongRoutePublicKey }
          : account),
        grants: [localServiceGrant],
        now: 1_900_000_000,
        signerDispatcher: () => response
      })
    });
    const provider = createNip07Provider({
      backend: createLocalServiceBrowserProviderBackend({
        service,
        routeRequest: routeVector.request
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.signEvent(request.params.event_template)).rejects.toThrow(
      /signer response public key does not match selected route/u
    );
  });

  it("creates browser native-messaging local-service clients over explicit senders", async () => {
    const sentHostNames: string[] = [];
    const service = createBrowserNativeMessagingLocalServiceClient({
      nextRequestId: () => "browser-native-status",
      sendNativeMessage: (hostName, message) => {
        sentHostNames.push(hostName);
        return handleLocalServiceRequest(message);
      }
    });

    await expect(service.serviceStatus()).resolves.toMatchObject({
      request_id: "browser-native-status",
      ok: true,
      result: {
        service: {
          name: "nsealr-companion-service",
          stores_production_secrets: false
        }
      }
    });
    expect(sentHostNames).toEqual([NATIVE_HOST_NAME]);
  });

  it("rejects invalid browser native-messaging host names before sending", async () => {
    let called = false;

    expect(() => createBrowserNativeMessagingLocalServiceClient({
      hostName: "bad host name",
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    })).toThrow(/native host name/u);
    expect(called).toBe(false);
  });

  it("rejects invalid or silent browser native-messaging exchanges deterministically", async () => {
    expect(() => createBrowserNativeMessagingLocalServiceClient({
      timeoutMs: 0,
      sendNativeMessage: () => handleLocalServiceRequest({
        version: 1,
        request_id: "unused",
        operation: "service_status"
      })
    })).toThrow(/timeout/u);

    const service = createBrowserNativeMessagingLocalServiceClient({
      timeoutMs: 1,
      sendNativeMessage: () => new Promise(() => undefined)
    });

    await expect(service.serviceStatus("browser-native-timeout")).rejects.toThrow(/response timed out/u);
  });

  it("cancels browser native-messaging exchanges without contacting an already-aborted sender", async () => {
    const abortController = new AbortController();
    abortController.abort();
    let called = false;
    const alreadyAbortedService = createBrowserNativeMessagingLocalServiceClient({
      abortSignal: abortController.signal,
      sendNativeMessage: () => {
        called = true;
        return {};
      }
    });

    await expect(alreadyAbortedService.serviceStatus("browser-native-already-cancelled")).rejects.toThrow(/cancelled/u);
    expect(called).toBe(false);

    const inFlightAbortController = new AbortController();
    const service = createBrowserNativeMessagingLocalServiceClient({
      abortSignal: inFlightAbortController.signal,
      sendNativeMessage: (_hostName, _message, options) => {
        expect(options.abortSignal).toBe(inFlightAbortController.signal);
        return new Promise(() => undefined);
      }
    });

    const request = service.serviceStatus("browser-native-cancelled");
    inFlightAbortController.abort();

    await expect(request).rejects.toThrow(/cancelled/u);
  });

  it("surfaces browser native-messaging sender failures deterministically", async () => {
    const service = createBrowserNativeMessagingLocalServiceClient({
      sendNativeMessage: () => {
        throw new Error("native host disconnected");
      }
    });

    await expect(service.serviceStatus("browser-native-disconnect")).rejects.toThrow(/native host disconnected/u);
  });

  it("surfaces local-service authorization failure before browser callers trust a key", async () => {
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        now: 1_900_000_000
      })
    });
    const provider = createNip07Provider({
      backend: createLocalServiceBrowserProviderBackend({
        service,
        routeRequest: routeVector.request
      }),
      client
    });

    await expect(provider.getPublicKey()).rejects.toThrow(/client is not paired/u);
  });

  it("surfaces latest local-service revocation before browser callers trust routes or signatures", async () => {
    let dispatched = false;
    const revokedGrant: LocalClientGrant = {
      ...localServiceGrant,
      approved_at: 1_900_000_010,
      revoked: true
    };
    const service = new LocalServiceClient({
      exchange: (message) => handleLocalServiceRequest(message, {
        accounts: fixtures.accounts,
        grants: [localServiceGrant, revokedGrant],
        now: 1_900_000_020,
        signerDispatcher: () => {
          dispatched = true;
          return response;
        }
      })
    });
    const provider = createNip07Provider({
      backend: createLocalServiceBrowserProviderBackend({
        service,
        routeRequest: routeVector.request
      }),
      client,
      nextRequestId: () => "req-kind-1-basic"
    });

    await expect(provider.getPublicKey()).rejects.toThrow(/revoked/u);
    await expect(provider.signEvent(request.params.event_template)).rejects.toThrow(/revoked/u);
    expect(dispatched).toBe(false);
  });
});
