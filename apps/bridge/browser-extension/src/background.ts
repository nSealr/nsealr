import {
  type PairableLocalServiceOperation
} from "@nsealr/client/browser";
import {
  type BrowserNativeMessageSender,
  type LocalServiceBrowserProviderBackendOptions
} from "@nsealr/browser-provider";
import {
  handleBrowserExtensionSenderRequest,
  type BrowserExtensionOriginPermissionAuthorization,
  type BrowserExtensionResponse
} from "./handler.js";
import { createBrowserExtensionNativeMessagingProviderSelector } from "./local-service.js";
import {
  requestBrowserExtensionNativeMessagingPairingIntent,
  requestBrowserExtensionNativeMessagingOriginPermissionReview,
  requestBrowserExtensionNativeMessagingPairingReview,
  type BrowserExtensionPairingIntentResult,
  type BrowserExtensionOriginPermissionReviewResult,
  type BrowserExtensionPairingReviewResult,
  type BrowserExtensionNativeMessagingPairingOptions,
  approveBrowserExtensionOriginPermissionReview,
  type BrowserExtensionOriginPermissionApproval
} from "./pairing.js";
import {
  upsertBrowserExtensionOriginPermissionApprovalInStorage,
  type BrowserExtensionOriginPermissionStorageArea,
  type BrowserExtensionOriginPermissionStorageWriteResult
} from "./origin-permission-storage.js";
import { type BrowserExtensionClientContext } from "./sender.js";

export type BrowserExtensionBackgroundControllerOptions = {
  sendNativeMessage: BrowserNativeMessageSender;
  routeRequest: LocalServiceBrowserProviderBackendOptions["routeRequest"];
  hostName?: string;
  nextServiceRequestId?: () => string;
  nextSignerRequestId?: () => string;
  signingUnavailableMessage?: string;
  pairingOperations?: readonly PairableLocalServiceOperation[];
  originPermissions?: BrowserExtensionOriginPermissionAuthorization;
  originPermissionStorage?: BrowserExtensionOriginPermissionStorageArea;
  originPermissionApprovalNow?: () => number;
  originPermissionStorageEmptyUpdatedAt?: number;
  nativeMessageTimeoutMs?: number;
  nativeMessageAbortSignal?: AbortSignal;
};

export type BrowserExtensionBackgroundRequestOptions = {
  nativeMessageAbortSignal?: AbortSignal;
};

export type BrowserExtensionBackgroundController = {
  handleRequest(
    value: unknown,
    sender: unknown,
    requestOptions?: BrowserExtensionBackgroundRequestOptions
  ): Promise<BrowserExtensionResponse>;
  requestPairing(
    sender: unknown,
    requestOptions?: BrowserExtensionBackgroundRequestOptions
  ): Promise<BrowserExtensionPairingIntentResult>;
  requestPairingReview(
    sender: unknown,
    requestOptions?: BrowserExtensionBackgroundRequestOptions
  ): Promise<BrowserExtensionPairingReviewResult>;
  requestOriginPermissionReview(
    sender: unknown,
    requestOptions?: BrowserExtensionBackgroundRequestOptions
  ): Promise<BrowserExtensionOriginPermissionReviewResult>;
  approveOriginPermission(
    originReview: unknown,
    reviewedLocalPairingDigest: string
  ): Promise<{
    approval: BrowserExtensionOriginPermissionApproval;
    storageWrite: BrowserExtensionOriginPermissionStorageWriteResult;
  }>;
};

function defaultNowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

export function createBrowserExtensionBackgroundController(
  options: BrowserExtensionBackgroundControllerOptions
): BrowserExtensionBackgroundController {
  const providerOptions = {
    sendNativeMessage: options.sendNativeMessage,
    routeRequest: options.routeRequest,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextServiceRequestId: options.nextServiceRequestId } : {}),
    ...(options.nextSignerRequestId !== undefined ? { nextSignerRequestId: options.nextSignerRequestId } : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { nativeMessageTimeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {}),
    ...(options.signingUnavailableMessage !== undefined
      ? { signingUnavailableMessage: options.signingUnavailableMessage }
      : {})
  };
  const pairingOptions: BrowserExtensionNativeMessagingPairingOptions = {
    sendNativeMessage: options.sendNativeMessage,
    ...(options.hostName !== undefined ? { hostName: options.hostName } : {}),
    ...(options.nextServiceRequestId !== undefined ? { nextServiceRequestId: options.nextServiceRequestId } : {}),
    ...(options.pairingOperations !== undefined ? { requestedOperations: options.pairingOperations } : {}),
    ...(options.nativeMessageTimeoutMs !== undefined ? { nativeMessageTimeoutMs: options.nativeMessageTimeoutMs } : {}),
    ...(options.nativeMessageAbortSignal !== undefined
      ? { nativeMessageAbortSignal: options.nativeMessageAbortSignal }
      : {})
  };
  const providerForClient = createBrowserExtensionNativeMessagingProviderSelector(providerOptions);

  return {
    handleRequest(
      value: unknown,
      sender: unknown,
      requestOptions: BrowserExtensionBackgroundRequestOptions = {}
    ): Promise<BrowserExtensionResponse> {
      if (requestOptions.nativeMessageAbortSignal === undefined) {
        return handleBrowserExtensionSenderRequest(value, sender, {
          providerForClient,
          ...(options.originPermissions !== undefined ? { originPermissions: options.originPermissions } : {})
        });
      }
      return handleBrowserExtensionSenderRequest(value, sender, {
        providerForClient: createBrowserExtensionNativeMessagingProviderSelector({
          ...providerOptions,
          nativeMessageAbortSignal: requestOptions.nativeMessageAbortSignal
        }),
        ...(options.originPermissions !== undefined ? { originPermissions: options.originPermissions } : {})
      });
    },

    requestPairing(
      sender: unknown,
      requestOptions: BrowserExtensionBackgroundRequestOptions = {}
    ): Promise<BrowserExtensionPairingIntentResult> {
      return requestBrowserExtensionNativeMessagingPairingIntent(sender, {
        ...pairingOptions,
        ...(requestOptions.nativeMessageAbortSignal !== undefined
          ? { nativeMessageAbortSignal: requestOptions.nativeMessageAbortSignal }
          : {})
      });
    },

    requestPairingReview(
      sender: unknown,
      requestOptions: BrowserExtensionBackgroundRequestOptions = {}
    ): Promise<BrowserExtensionPairingReviewResult> {
      return requestBrowserExtensionNativeMessagingPairingReview(sender, {
        ...pairingOptions,
        ...(requestOptions.nativeMessageAbortSignal !== undefined
          ? { nativeMessageAbortSignal: requestOptions.nativeMessageAbortSignal }
          : {})
      });
    },

    requestOriginPermissionReview(
      sender: unknown,
      requestOptions: BrowserExtensionBackgroundRequestOptions = {}
    ): Promise<BrowserExtensionOriginPermissionReviewResult> {
      return requestBrowserExtensionNativeMessagingOriginPermissionReview(sender, {
        ...pairingOptions,
        ...(requestOptions.nativeMessageAbortSignal !== undefined
          ? { nativeMessageAbortSignal: requestOptions.nativeMessageAbortSignal }
          : {})
      });
    },

    async approveOriginPermission(
      originReview: unknown,
      reviewedLocalPairingDigest: string
    ): Promise<{
      approval: BrowserExtensionOriginPermissionApproval;
      storageWrite: BrowserExtensionOriginPermissionStorageWriteResult;
    }> {
      if (options.originPermissionStorage === undefined) {
        throw new Error("browser extension origin permission storage is unavailable");
      }
      const approvedAt = (options.originPermissionApprovalNow ?? defaultNowSeconds)();
      const approval = approveBrowserExtensionOriginPermissionReview(originReview, {
        reviewedLocalPairingDigest,
        approvedAt
      });
      const storageWrite = await upsertBrowserExtensionOriginPermissionApprovalInStorage(
        options.originPermissionStorage,
        approval,
        {
          ...(options.originPermissionStorageEmptyUpdatedAt !== undefined
            ? { emptyUpdatedAt: options.originPermissionStorageEmptyUpdatedAt }
            : {}),
          updatedAt: approvedAt
        }
      );
      return {
        approval,
        storageWrite
      };
    }
  };
}

export type { BrowserExtensionClientContext };
