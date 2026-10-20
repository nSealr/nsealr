# Public API Surface

This file is generated from the public package entrypoints by
`tools/bridge/check_api_docs.mjs`. It documents the pre-release package surface
that consumers may import after the package gates pass.

Regenerate and verify it with:

```sh
pnpm api-docs:update
pnpm api-docs:check
```

The packages are still pre-release. Breaking changes are allowed before the
first public npm publication, but every exported symbol must remain visible
here so API drift is reviewed deliberately.

## @nsealr/sdk

Platform-neutral SDK facade for nSealr browser, companion, and signer integrations.

Source entrypoint: `packages/sdk/src/index.ts`

Exports:
- `browserProvider`
- `browserProvider.BrowserNativeMessageOptions`
- `browserProvider.BrowserNativeMessageSender`
- `browserProvider.BrowserNativeMessagingLocalServiceClientOptions`
- `browserProvider.BrowserProviderBackend`
- `browserProvider.BrowserProviderOptions`
- `browserProvider.LocalServiceBrowserProviderBackendOptions`
- `browserProvider.NATIVE_HOST_NAME`
- `browserProvider.Nip07Provider`
- `browserProvider.createBrowserNativeMessagingLocalServiceClient`
- `browserProvider.createLocalServiceBrowserProviderBackend`
- `browserProvider.createNip07Provider`
- `client`
- `client.LOCAL_CLIENT_SURFACES`
- `client.LOCAL_PAIRING_INTENT_FORMAT`
- `client.LOCAL_SERVICE_NAME`
- `client.LOCAL_SERVICE_OPERATIONS`
- `client.LOCAL_SERVICE_PROTOCOL`
- `client.LocalClientGrant`
- `client.LocalClientIdentity`
- `client.LocalClientSurface`
- `client.LocalPairingReview`
- `client.LocalServiceClient`
- `client.LocalServiceClientOptions`
- `client.LocalServiceExchange`
- `client.LocalServiceExchangeOptions`
- `client.LocalServiceOperation`
- `client.LocalServiceRequest`
- `client.LocalServiceResponse`
- `client.MAX_NATIVE_MESSAGE_BYTES`
- `client.MAX_SERVICE_JSON_BYTES`
- `client.NATIVE_HOST_NAME`
- `client.NATIVE_MESSAGE_LENGTH_BYTES`
- `client.NativeMessageFrameExchange`
- `client.NativeMessagingLocalServiceClientOptions`
- `client.PairableLocalServiceOperation`
- `client.PairingIntent`
- `client.clientIdForIdentity`
- `client.createNativeMessagingLocalServiceClient`
- `client.decodeNativeMessage`
- `client.encodeNativeMessage`
- `client.parseLocalClientIdentity`
- `client.reviewPairingIntent`
- `core`
- `core.EventTemplate`
- `core.SignEventRequest`
- `core.SignEventResponse`
- `core.SignedEvent`
- `core.VerificationResult`
- `core.bytesToHex`
- `core.canonicalEventSerialization`
- `core.computeEventId`
- `core.decrypt`
- `core.encrypt`
- `core.getConversationKey`
- `core.hexToBytes`
- `core.sha256Utf8Hex`
- `core.verifySchnorrSignature`
- `core.verifySignedEventResponse`
- `policy`
- `policy.AccountDescriptor`
- `policy.GrantDescriptor`
- `policy.GrantPermission`
- `policy.GrantUsageSnapshot`
- `policy.PolicyChangeProposal`
- `policy.PolicyChangeReview`
- `policy.PolicyChangeReviewContext`
- `policy.PolicyChangeReviewPage`
- `policy.PolicyChangeReviewVector`
- `policy.PolicyDecision`
- `policy.PolicyDecisionRequest`
- `policy.PolicyProfile`
- `policy.ProfileId`
- `policy.RouteCustody`
- `policy.RouteSelection`
- `policy.RouteSelectionRequest`
- `policy.RouteType`
- `policy.SignerRoute`
- `policy.decidePolicyRequest`
- `policy.parseAccountDescriptor`
- `policy.parseGrantDescriptor`
- `policy.parsePolicyChangeProposal`
- `policy.parsePolicyChangeReviewContext`
- `policy.parsePolicyChangeReviewVector`
- `policy.parsePolicyDecisionRequest`
- `policy.parsePolicyProfile`
- `policy.parseRouteSelection`
- `policy.parseRouteSelectionRequest`
- `policy.reviewPolicyChangeProposal`
- `policy.selectAccountRoute`
- `policy.validatePolicyChangeProposalContext`
- `protocol`
- `protocol.AlgorithmId`
- `protocol.Availability`
- `protocol.AvailabilityReason`
- `protocol.Base64UrlPayloadErrorMessages`
- `protocol.CAPABILITY_BOUNDS`
- `protocol.CapabilityError`
- `protocol.CapabilityMethodId`
- `protocol.CompatibilityReason`
- `protocol.Configuration`
- `protocol.CustodyMode`
- `protocol.FullCapabilities`
- `protocol.ImplementationProfile`
- `protocol.LimitsManifest`
- `protocol.MessageFeature`
- `protocol.MessageFeatures`
- `protocol.MethodLimits`
- `protocol.NSEALR_V0_LIMITS`
- `protocol.ProfileId`
- `protocol.ReferenceCapabilities`
- `protocol.ReportedCapabilities`
- `protocol.ReportedFeature`
- `protocol.ReportedMethod`
- `protocol.ReportedTransport`
- `protocol.RuntimeMethodDelta`
- `protocol.SIGNING_CONTRACT`
- `protocol.SIGNING_VERSION`
- `protocol.Support`
- `protocol.TransportId`
- `protocol.TransportLimits`
- `protocol.ValidationResult`
- `protocol.assertBase64UrlPayload`
- `protocol.checkedProduct`
- `protocol.compactJsonUtf8ByteLength`
- `protocol.compactReportedCapabilities`
- `protocol.decodeBase64Url`
- `protocol.encodeBase64Url`
- `protocol.intersectMethodLimits`
- `protocol.isSafeNonNegativeInteger`
- `protocol.jsonToUtf8Bytes`
- `protocol.nSealrV0Limits`
- `protocol.parseImplementationProfile`
- `protocol.parseLimitsManifest`
- `protocol.parseReportedCapabilities`
- `protocol.parseSigningPayload`
- `protocol.parseSigningRequest`
- `protocol.parseSigningResponse`
- `protocol.parseStrictJson`
- `protocol.requireMessageFeature`
- `protocol.resolveReportedCapabilities`
- `protocol.utf8ByteLength`
- `protocol.validateReportedCapabilities`
- `protocol.validateRequest`
- `protocol.validateResponse`
- `qr`
- `qr.ANIMATED_QR_ENVELOPE_PREFIX`
- `qr.AnimatedQrEnvelopeOptions`
- `qr.QR_ENVELOPE_PREFIX`
- `qr.decodeAnimatedQrEnvelopeFrames`
- `qr.decodeQrEnvelope`
- `qr.encodeAnimatedQrEnvelopeFrames`
- `qr.encodeQrEnvelope`
- `review`
- `review.DEVELOPMENT_REVIEW_AUTHOR_PUBKEY`
- `review.EventReview`
- `review.REVIEW_DETAIL_BODY_LINE_STYLES`
- `review.ReviewBodyLineStyle`
- `review.ReviewDetailPage`
- `review.ReviewDetailPageLimits`
- `review.ReviewPage`
- `review.ScreenReview`
- `review.approvalDigestForRequest`
- `review.renderReviewDetailPages`
- `review.renderReviewPages`
- `review.reviewEventTemplate`
- `review.screenReviewForRequest`

Additional package subpaths:
- `@nsealr/sdk/browser`: `browserProvider`, `browserProvider.BrowserNativeMessageOptions`, `browserProvider.BrowserNativeMessageSender`, `browserProvider.BrowserNativeMessagingLocalServiceClientOptions`, `browserProvider.BrowserProviderBackend`, `browserProvider.BrowserProviderOptions`, `browserProvider.LocalServiceBrowserProviderBackendOptions`, `browserProvider.NATIVE_HOST_NAME`, `browserProvider.Nip07Provider`, `browserProvider.createBrowserNativeMessagingLocalServiceClient`, `browserProvider.createLocalServiceBrowserProviderBackend`, `browserProvider.createNip07Provider`, `client`, `client.LOCAL_CLIENT_SURFACES`, `client.LOCAL_PAIRING_INTENT_FORMAT`, `client.LOCAL_SERVICE_NAME`, `client.LOCAL_SERVICE_OPERATIONS`, `client.LOCAL_SERVICE_PROTOCOL`, `client.LocalClientGrant`, `client.LocalClientIdentity`, `client.LocalClientSurface`, `client.LocalPairingReview`, `client.LocalServiceClient`, `client.LocalServiceClientOptions`, `client.LocalServiceExchange`, `client.LocalServiceExchangeOptions`, `client.LocalServiceOperation`, `client.LocalServiceRequest`, `client.LocalServiceResponse`, `client.MAX_NATIVE_MESSAGE_BYTES`, `client.MAX_SERVICE_JSON_BYTES`, `client.NATIVE_HOST_NAME`, `client.NATIVE_MESSAGE_LENGTH_BYTES`, `client.NativeMessageFrameExchange`, `client.NativeMessagingLocalServiceClientOptions`, `client.PairableLocalServiceOperation`, `client.PairingIntent`, `client.clientIdForIdentity`, `client.createNativeMessagingLocalServiceClient`, `client.decodeNativeMessage`, `client.encodeNativeMessage`, `client.parseLocalClientIdentity`, `client.reviewPairingIntent`, `core`, `core.EventTemplate`, `core.SignEventRequest`, `core.SignEventResponse`, `core.SignedEvent`, `core.VerificationResult`, `core.bytesToHex`, `core.canonicalEventSerialization`, `core.computeEventId`, `core.decrypt`, `core.encrypt`, `core.getConversationKey`, `core.hexToBytes`, `core.sha256Utf8Hex`, `core.verifySchnorrSignature`, `core.verifySignedEventResponse`, `policy`, `policy.AccountDescriptor`, `policy.GrantDescriptor`, `policy.GrantPermission`, `policy.GrantUsageSnapshot`, `policy.PolicyChangeProposal`, `policy.PolicyChangeReview`, `policy.PolicyChangeReviewContext`, `policy.PolicyChangeReviewPage`, `policy.PolicyChangeReviewVector`, `policy.PolicyDecision`, `policy.PolicyDecisionRequest`, `policy.PolicyProfile`, `policy.ProfileId`, `policy.RouteCustody`, `policy.RouteSelection`, `policy.RouteSelectionRequest`, `policy.RouteType`, `policy.SignerRoute`, `policy.decidePolicyRequest`, `policy.parseAccountDescriptor`, `policy.parseGrantDescriptor`, `policy.parsePolicyChangeProposal`, `policy.parsePolicyChangeReviewContext`, `policy.parsePolicyChangeReviewVector`, `policy.parsePolicyDecisionRequest`, `policy.parsePolicyProfile`, `policy.parseRouteSelection`, `policy.parseRouteSelectionRequest`, `policy.reviewPolicyChangeProposal`, `policy.selectAccountRoute`, `policy.validatePolicyChangeProposalContext`, `protocol`, `protocol.AlgorithmId`, `protocol.Availability`, `protocol.AvailabilityReason`, `protocol.Base64UrlPayloadErrorMessages`, `protocol.CAPABILITY_BOUNDS`, `protocol.CapabilityError`, `protocol.CapabilityMethodId`, `protocol.CompatibilityReason`, `protocol.Configuration`, `protocol.CustodyMode`, `protocol.FullCapabilities`, `protocol.ImplementationProfile`, `protocol.LimitsManifest`, `protocol.MessageFeature`, `protocol.MessageFeatures`, `protocol.MethodLimits`, `protocol.NSEALR_V0_LIMITS`, `protocol.ProfileId`, `protocol.ReferenceCapabilities`, `protocol.ReportedCapabilities`, `protocol.ReportedFeature`, `protocol.ReportedMethod`, `protocol.ReportedTransport`, `protocol.RuntimeMethodDelta`, `protocol.SIGNING_CONTRACT`, `protocol.SIGNING_VERSION`, `protocol.Support`, `protocol.TransportId`, `protocol.TransportLimits`, `protocol.ValidationResult`, `protocol.assertBase64UrlPayload`, `protocol.checkedProduct`, `protocol.compactJsonUtf8ByteLength`, `protocol.compactReportedCapabilities`, `protocol.decodeBase64Url`, `protocol.encodeBase64Url`, `protocol.intersectMethodLimits`, `protocol.isSafeNonNegativeInteger`, `protocol.jsonToUtf8Bytes`, `protocol.nSealrV0Limits`, `protocol.parseImplementationProfile`, `protocol.parseLimitsManifest`, `protocol.parseReportedCapabilities`, `protocol.parseSigningPayload`, `protocol.parseSigningRequest`, `protocol.parseSigningResponse`, `protocol.parseStrictJson`, `protocol.requireMessageFeature`, `protocol.resolveReportedCapabilities`, `protocol.utf8ByteLength`, `protocol.validateReportedCapabilities`, `protocol.validateRequest`, `protocol.validateResponse`, `qr`, `qr.ANIMATED_QR_ENVELOPE_PREFIX`, `qr.AnimatedQrEnvelopeOptions`, `qr.QR_ENVELOPE_PREFIX`, `qr.decodeAnimatedQrEnvelopeFrames`, `qr.decodeQrEnvelope`, `qr.encodeAnimatedQrEnvelopeFrames`, `qr.encodeQrEnvelope`, `review`, `review.DEVELOPMENT_REVIEW_AUTHOR_PUBKEY`, `review.EventReview`, `review.REVIEW_DETAIL_BODY_LINE_STYLES`, `review.ReviewBodyLineStyle`, `review.ReviewDetailPage`, `review.ReviewDetailPageLimits`, `review.ReviewPage`, `review.ScreenReview`, `review.approvalDigestForRequest`, `review.renderReviewDetailPages`, `review.renderReviewPages`, `review.reviewEventTemplate`, `review.screenReviewForRequest`
- `@nsealr/sdk/node`: `browserProvider`, `browserProvider.BrowserNativeMessageOptions`, `browserProvider.BrowserNativeMessageSender`, `browserProvider.BrowserNativeMessagingLocalServiceClientOptions`, `browserProvider.BrowserProviderBackend`, `browserProvider.BrowserProviderOptions`, `browserProvider.LocalServiceBrowserProviderBackendOptions`, `browserProvider.NATIVE_HOST_NAME`, `browserProvider.Nip07Provider`, `browserProvider.createBrowserNativeMessagingLocalServiceClient`, `browserProvider.createLocalServiceBrowserProviderBackend`, `browserProvider.createNip07Provider`, `client`, `client.ChromiumNativeHostManifest`, `client.EXTERNAL_REVIEW_ACKNOWLEDGEMENT_FORMAT`, `client.EffectiveSignerLimits`, `client.ExternalReviewAcknowledgement`, `client.FirefoxNativeHostManifest`, `client.LOCAL_CLIENT_SURFACES`, `client.LOCAL_GRANT_STORE_FORMAT`, `client.LOCAL_PAIRING_APPROVAL_FORMAT`, `client.LOCAL_PAIRING_INTENT_FORMAT`, `client.LOCAL_PAIRING_REVIEW_FORMAT`, `client.LOCAL_SERVICE_NAME`, `client.LOCAL_SERVICE_OPERATIONS`, `client.LOCAL_SERVICE_PROTOCOL`, `client.LOCAL_STORAGE_ACCESS_MODES`, `client.LOCAL_STORAGE_APPROVAL_FORMAT`, `client.LOCAL_STORAGE_PURPOSES`, `client.LOCAL_STORAGE_REVIEW_FORMAT`, `client.LocalClientGrant`, `client.LocalClientIdentity`, `client.LocalClientSurface`, `client.LocalGrantRevocationOptions`, `client.LocalGrantSelector`, `client.LocalGrantStore`, `client.LocalGrantStoreOptions`, `client.LocalGrantStoreRevocationOptions`, `client.LocalPairingApproval`, `client.LocalPairingReview`, `client.LocalPairingReviewOperation`, `client.LocalServiceClient`, `client.LocalServiceClientOptions`, `client.LocalServiceContext`, `client.LocalServiceDispatchSignerRequestOptions`, `client.LocalServiceExchange`, `client.LocalServiceExchangeOptions`, `client.LocalServiceOperation`, `client.LocalServiceRequest`, `client.LocalServiceResponse`, `client.LocalStorageAccessMode`, `client.LocalStorageApproval`, `client.LocalStorageApprovalRequirement`, `client.LocalStoragePurpose`, `client.LocalStorageReview`, `client.LocalStorageReviewEntry`, `client.MAX_LOCAL_GRANT_STORE_GRANTS`, `client.MAX_LOCAL_GRANT_STORE_JSON_BYTES`, `client.MAX_NATIVE_MESSAGE_BYTES`, `client.MAX_SERVICE_JSON_BYTES`, `client.NATIVE_HOST_DESCRIPTION`, `client.NATIVE_HOST_INSTALL_APPROVAL_FORMAT`, `client.NATIVE_HOST_INSTALL_EXECUTION_FORMAT`, `client.NATIVE_HOST_INSTALL_PLAN_FORMAT`, `client.NATIVE_HOST_NAME`, `client.NATIVE_MESSAGE_LENGTH_BYTES`, `client.NativeHostBrowser`, `client.NativeHostInstallApproval`, `client.NativeHostInstallApprovalOptions`, `client.NativeHostInstallExecution`, `client.NativeHostInstallExecutionOptions`, `client.NativeHostInstallPlan`, `client.NativeHostInstallPlanOptions`, `client.NativeHostManifest`, `client.NativeHostManifestOptions`, `client.NativeMessageFrameExchange`, `client.NativeMessagingLocalServiceClientOptions`, `client.PairableLocalServiceOperation`, `client.PairingIntent`, `client.RouteDispatchEntry`, `client.SIGNER_TRANSPORT_ERROR_CODES`, `client.SignerCompatibilitySnapshot`, `client.SignerDispatchRequest`, `client.SignerRequestDispatcher`, `client.SignerRouteUnavailableError`, `client.SignerTransportError`, `client.SignerTransportErrorCode`, `client.appendLocalGrant`, `client.appendLocalGrantRevocation`, `client.approveLocalStorageReview`, `client.approveNativeHostInstallPlan`, `client.approvePairingIntent`, `client.assessSignerCompatibility`, `client.buildNativeHostInstallPlan`, `client.buildNativeHostManifest`, `client.clientIdForIdentity`, `client.createLocalGrantStore`, `client.createLocalStorageReview`, `client.createNativeMessagingLocalServiceClient`, `client.createRouteDispatcher`, `client.decodeNativeMessage`, `client.encodeNativeMessage`, `client.executeNativeHostInstallApproval`, `client.handleLocalServiceRequest`, `client.handleLocalServiceRequestAsync`, `client.parseLocalClientIdentity`, `client.parseLocalGrant`, `client.parseLocalGrantStore`, `client.parseLocalPairingApproval`, `client.parseLocalStorageApproval`, `client.parseLocalStorageReview`, `client.parseLocalStorageReviewEntry`, `client.parseNativeHostInstallApproval`, `client.parseNativeHostInstallExecution`, `client.parseNativeHostInstallPlan`, `client.parsePairingIntent`, `client.requireLocalStorageApprovalEntry`, `client.reviewPairingIntent`, `client.revokeLocalGrant`, `client.serializeLocalGrantStore`, `client.validateLocalServiceResponse`, `core`, `core.EventTemplate`, `core.SignEventRequest`, `core.SignEventResponse`, `core.SignedEvent`, `core.VerificationResult`, `core.bytesToHex`, `core.canonicalEventSerialization`, `core.computeEventId`, `core.decrypt`, `core.encrypt`, `core.getConversationKey`, `core.hexToBytes`, `core.sha256Utf8Hex`, `core.verifySchnorrSignature`, `core.verifySignedEventResponse`, `framing`, `framing.SERIAL_FRAME_PREFIX`, `framing.SerialFrame`, `framing.SerialFrameType`, `framing.decodeSerialFrame`, `framing.encodeSerialFrame`, `nip46`, `nip46.ActiveSessionRecordInput`, `nip46.InMemoryRelay`, `nip46.InMemorySessionStore`, `nip46.NIP46_SESSION_ACTIVE_PHASE_FLAGS`, `nip46.NIP46_SESSION_SECRET_FIELDS`, `nip46.Nip46AuthChallengeApproval`, `nip46.Nip46AuthChallengeApprovalOptions`, `nip46.Nip46AuthChallengeReview`, `nip46.Nip46BridgeDecision`, `nip46.Nip46ConnectApproval`, `nip46.Nip46ConnectApprovalOptions`, `nip46.Nip46ConnectIntent`, `nip46.Nip46ConnectReview`, `nip46.Nip46ConnectionTokenResponse`, `nip46.Nip46ConnectionUriDescriptor`, `nip46.Nip46Permission`, `nip46.Nip46PermissionRequirement`, `nip46.Nip46RelayEventDirection`, `nip46.Nip46RelayEventEnvelope`, `nip46.Nip46RelayRequestStep`, `nip46.Nip46RelayResponseResultType`, `nip46.Nip46RelayResponseStep`, `nip46.Nip46RequestMessage`, `nip46.Nip46ResponseMessage`, `nip46.Nip46SessionActive`, `nip46.Nip46SessionActivePhase`, `nip46.Nip46SessionLifecycle`, `nip46.Nip46SessionLifecycleCheckpointOptions`, `nip46.Nip46SessionManager`, `nip46.Nip46SessionManagerOptions`, `nip46.Nip46SessionRequestGate`, `nip46.NostrToolsRelay`, `nip46.RelayEvent`, `nip46.RelayEventHandler`, `nip46.RelayFilter`, `nip46.RelayPool`, `nip46.RelaySubscription`, `nip46.RelayTransport`, `nip46.SessionPhase`, `nip46.SessionStore`, `nip46.approveNip46AuthChallengeReview`, `nip46.approveNip46ConnectReview`, `nip46.buildNip46RequestEvent`, `nip46.createNip46SessionLifecycleCheckpoint`, `nip46.decideNip46BridgeAction`, `nip46.decryptNip46Event`, `nip46.evaluateNip46RelayRequestStep`, `nip46.evaluateNip46RelayResponseStep`, `nip46.evaluateNip46SessionRequestGate`, `nip46.eventMatchesFilter`, `nip46.isNip46RequestPermitted`, `nip46.nip46PermissionLabel`, `nip46.nip46PermissionRequirementFromRequest`, `nip46.nip46ResponseFromNSealr`, `nip46.nsealrRequestFromNip46`, `nip46.parseNip46ApprovedPermissions`, `nip46.parseNip46AuthChallengeApproval`, `nip46.parseNip46AuthChallengeReview`, `nip46.parseNip46ConnectApproval`, `nip46.parseNip46ConnectIntent`, `nip46.parseNip46ConnectReview`, `nip46.parseNip46ConnectionUri`, `nip46.parseNip46Permissions`, `nip46.parseNip46PolicyFile`, `nip46.parseNip46RelayEventEnvelope`, `nip46.parseNip46SessionActive`, `nip46.parseNip46SessionLifecycle`, `nip46.requireResponseMessage`, `nip46.respondToLocalNip46Request`, `nip46.reviewNip46AuthChallengeStep`, `nip46.reviewNip46ConnectIntent`, `nip46.reviewNip46ConnectMessage`, `nip46.toActiveSessionRecord`, `nip46.verifyNip46ConnectionTokenResponse`, `policy`, `policy.AccountDescriptor`, `policy.GrantDescriptor`, `policy.GrantPermission`, `policy.GrantUsageSnapshot`, `policy.PolicyChangeProposal`, `policy.PolicyChangeReview`, `policy.PolicyChangeReviewContext`, `policy.PolicyChangeReviewPage`, `policy.PolicyChangeReviewVector`, `policy.PolicyDecision`, `policy.PolicyDecisionRequest`, `policy.PolicyProfile`, `policy.ProfileId`, `policy.RouteCustody`, `policy.RouteSelection`, `policy.RouteSelectionRequest`, `policy.RouteType`, `policy.SignerRoute`, `policy.decidePolicyRequest`, `policy.parseAccountDescriptor`, `policy.parseGrantDescriptor`, `policy.parsePolicyChangeProposal`, `policy.parsePolicyChangeReviewContext`, `policy.parsePolicyChangeReviewVector`, `policy.parsePolicyDecisionRequest`, `policy.parsePolicyProfile`, `policy.parseRouteSelection`, `policy.parseRouteSelectionRequest`, `policy.reviewPolicyChangeProposal`, `policy.selectAccountRoute`, `policy.validatePolicyChangeProposalContext`, `protocol`, `protocol.AlgorithmId`, `protocol.Availability`, `protocol.AvailabilityReason`, `protocol.Base64UrlPayloadErrorMessages`, `protocol.CAPABILITY_BOUNDS`, `protocol.CapabilityError`, `protocol.CapabilityMethodId`, `protocol.CompatibilityReason`, `protocol.Configuration`, `protocol.CustodyMode`, `protocol.FullCapabilities`, `protocol.ImplementationProfile`, `protocol.LimitsManifest`, `protocol.MessageFeature`, `protocol.MessageFeatures`, `protocol.MethodLimits`, `protocol.NSEALR_V0_LIMITS`, `protocol.ProfileId`, `protocol.ReferenceCapabilities`, `protocol.ReportedCapabilities`, `protocol.ReportedFeature`, `protocol.ReportedMethod`, `protocol.ReportedTransport`, `protocol.RuntimeMethodDelta`, `protocol.SIGNING_CONTRACT`, `protocol.SIGNING_VERSION`, `protocol.Support`, `protocol.TransportId`, `protocol.TransportLimits`, `protocol.ValidationResult`, `protocol.assertBase64UrlPayload`, `protocol.checkedProduct`, `protocol.compactJsonUtf8ByteLength`, `protocol.compactReportedCapabilities`, `protocol.decodeBase64Url`, `protocol.encodeBase64Url`, `protocol.intersectMethodLimits`, `protocol.isSafeNonNegativeInteger`, `protocol.jsonToUtf8Bytes`, `protocol.nSealrV0Limits`, `protocol.parseImplementationProfile`, `protocol.parseLimitsManifest`, `protocol.parseReportedCapabilities`, `protocol.parseSigningPayload`, `protocol.parseSigningRequest`, `protocol.parseSigningResponse`, `protocol.parseStrictJson`, `protocol.requireMessageFeature`, `protocol.resolveReportedCapabilities`, `protocol.utf8ByteLength`, `protocol.validateReportedCapabilities`, `protocol.validateRequest`, `protocol.validateResponse`, `qr`, `qr.ANIMATED_QR_ENVELOPE_PREFIX`, `qr.AnimatedQrEnvelopeOptions`, `qr.QR_ENVELOPE_PREFIX`, `qr.decodeAnimatedQrEnvelopeFrames`, `qr.decodeQrEnvelope`, `qr.encodeAnimatedQrEnvelopeFrames`, `qr.encodeQrEnvelope`, `review`, `review.DEVELOPMENT_REVIEW_AUTHOR_PUBKEY`, `review.EventReview`, `review.REVIEW_DETAIL_BODY_LINE_STYLES`, `review.ReviewBodyLineStyle`, `review.ReviewDetailPage`, `review.ReviewDetailPageLimits`, `review.ReviewPage`, `review.ScreenReview`, `review.approvalDigestForRequest`, `review.renderReviewDetailPages`, `review.renderReviewPages`, `review.reviewEventTemplate`, `review.screenReviewForRequest`
