import {
  createBrowserNativeMessagingLocalServiceClient,
  createLocalServiceBrowserProviderBackend,
  createNip07Provider,
  type BrowserNativeMessageSender,
  type LocalServiceBrowserProviderBackendOptions,
  type Nip07Provider
} from "@nsealr/browser-provider";
import { type BrowserExtensionClientContext } from "./sender.js";

export type BrowserExtensionNativeMessagingProviderSelectorOptions = {
  sendNativeMessage: BrowserNativeMessageSender;
  routeRequest: LocalServiceBrowserProviderBackendOptions["routeRequest"];
  hostName?: string;
  nextServiceRequestId?: () => string;
  nextSignerRequestId?: () => string;
  signingUnavailableMessage?: string;
  nativeMessageTimeoutMs?: number;
  nativeMessageAbortSignal?: AbortSignal;
};

export function createBrowserExtensionNativeMessagingProviderSelector(
  options: BrowserExtensionNativeMessagingProviderSelectorOptions
): (context: BrowserExtensionClientContext) => Pick<Nip07Provider, "getPublicKey" | "signEvent"> {
  const service = createBrowserNativeMessagingLocalServiceClient({
    sendNativeMessage: options.sendNativeMessage,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextRequestId: options.nextServiceRequestId } : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { timeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined ? { abortSignal: options.nativeMessageAbortSignal } : {})
  });
  const backend = createLocalServiceBrowserProviderBackend({
    service,
    routeRequest: options.routeRequest,
    ...(options.signingUnavailableMessage !== undefined
      ? { signingUnavailableMessage: options.signingUnavailableMessage }
      : {})
  });

  return (context) => createNip07Provider({
    backend,
    client: context.client,
    ...(options.nextSignerRequestId !== undefined ? { nextRequestId: options.nextSignerRequestId } : {})
  });
}
