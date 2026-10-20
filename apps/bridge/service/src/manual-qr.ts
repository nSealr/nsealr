import {
  createRouteDispatcher, SignerRouteUnavailableError, SignerTransportError,
  type SignerDispatchRequest, type SignerRequestDispatcher
} from "@nsealr/client";
import { type RouteType } from "@nsealr/policy";
import { CapabilityError, NSEALR_V0_LIMITS, validateRequest, validateResponse } from "@nsealr/protocol";
import { decodeQrEnvelope, encodeQrEnvelope, QR_ENVELOPE_PREFIX } from "@nsealr/qr";

type ManualQrRouteType = Extract<RouteType, "raspberry_qr_vault" | "esp32_qr_vault">;

export type ManualQrPortControl = {
  account_id: string;
  route_type: ManualQrRouteType;
  request_id: string;
  expected_public_key: string;
  /** Host currentness only. A port delaying presentation must call this again
   * immediately before exposing bytes; it is never physical consent/recall. */
  before_present: () => void;
  abort_signal: AbortSignal;
  /** The injected port must enforce these before its own allocation/decoding. */
  maximum_response_frame_bytes: number;
  maximum_response_json_bytes: number;
};

/** Trusted, exclusively owned software port. present settles after actual
 * presentation; scan returns ONE original static envelope (null means cancel).
 * close resolves only after callbacks/buffers/native resources are reusable.
 * A rejected open/close cannot establish quiescence and quarantines this owner.
 * No camera, optical, native-memory or device-cancellation proof is implied. */
export type ManualQrPort = {
  present(envelope: string): void | Promise<void>;
  scan(): Promise<string | null>;
  close(): void | Promise<void>;
};

function protocolFailure(message: string): never {
  throw new SignerTransportError("signer_transport_protocol_error", message);
}

function frameBytes(decoded: number): number {
  // decoded is already bounded by the existing provisional static codec cap.
  return QR_ENVELOPE_PREFIX.length + Math.ceil(decoded * 4 / 3);
}

async function portIo<T>(operation: () => T | Promise<T>): Promise<T> {
  try { return await operation(); }
  catch (error) {
    if (error instanceof CapabilityError || error instanceof SignerTransportError) throw error;
    throw new SignerTransportError("signer_transport_io_failed", "manual QR port operation failed");
  }
}

/** Service-only, explicitly injected experimental static codec. Do not share
 * its physical port through another factory. No default route/readiness is set.
 * The actual client retains account/capability/deadline/pending and independent
 * expected-key/canonical-ID/signature checks; this is not another lifecycle. */
export function createManualQrRouteDispatcher(options: {
  account_id: string;
  route_type: ManualQrRouteType;
  openPort: (control: ManualQrPortControl) => ManualQrPort | Promise<ManualQrPort>;
}): SignerRequestDispatcher {
  let busy = false;
  const dispatch = async (dispatch: SignerDispatchRequest): Promise<unknown> => {
    const { route_selection: route, before_write: beforeWrite, effective_limits: limits, abort_signal: signal } = dispatch;
    if (!beforeWrite || !limits || !signal || route.contract !== "nsealr.signing.v2" ||
      (route.method !== "get_public_key" && route.method !== "sign_event")) {
      throw new SignerRouteUnavailableError("manual QR requires the existing client lifecycle and an admitted method");
    }
    if (busy) throw new SignerTransportError("signer_transport_failed", "manual QR port is reserved or quarantined");
    const current = (): void => {
      if (signal.aborted) throw new SignerTransportError("signer_transport_failed", "manual QR operation is no longer active");
      beforeWrite();
    };
    // Reserve before currentness invokes the external compatibility provider.
    // A nested actual client call in another context still shares this owner.
    busy = true;
    let reusable = true, presenting = false, failed = false;
    let port: ManualQrPort | undefined;
    let response: unknown;
    try {
      current();
      const validRequest = validateRequest(dispatch.request);
      if (!validRequest.ok || (dispatch.request as { method: unknown }).method !== route.method) {
        protocolFailure("manual QR request does not match the selected method");
      }
      const request = dispatch.request as { request_id: string };
      const requestBytes = Buffer.byteLength(JSON.stringify(request), "utf8");
      const encodedRequestBytes = frameBytes(requestBytes);
      const { method, transport } = limits;
      const work = Math.min(method.parse_work, transport.parse_work);
      const maximumJson = Math.min(NSEALR_V0_LIMITS.max_static_qr_decoded_json_bytes,
        method.response_json_bytes, transport.static_decoded_json_bytes!, transport.reassembly_bytes);
      const maximumFrame = Math.min(transport.frame_bytes, frameBytes(maximumJson), work - encodedRequestBytes);
      if (requestBytes > method.request_json_bytes || requestBytes > transport.reassembly_bytes ||
        requestBytes > transport.static_decoded_json_bytes! || encodedRequestBytes > transport.frame_bytes ||
        encodedRequestBytes > work || maximumFrame <= QR_ENVELOPE_PREFIX.length || maximumJson < 1) {
        protocolFailure("manual QR exchange exceeds effective request/frame/work capacity");
      }
      // Logical public payload accounting, not a measurement of JS/native heap.
      // Reserve the largest permitted incoming payload BEFORE opening/encoding.
      const retained = requestBytes + encodedRequestBytes + maximumJson + maximumFrame;
      if (!Number.isSafeInteger(retained) || retained > method.retained_bytes || retained > transport.retained_bytes) {
        protocolFailure("manual QR exchange exceeds effective retained payload capacity");
      }

      current();
      const envelope = encodeQrEnvelope(request);
      const control: ManualQrPortControl = {
        account_id: route.account_id, route_type: options.route_type,
        request_id: request.request_id, expected_public_key: route.public_key,
        abort_signal: signal, maximum_response_frame_bytes: maximumFrame,
        maximum_response_json_bytes: maximumJson,
        before_present: () => {
          if (!presenting) throw new SignerTransportError("signer_transport_failed", "manual QR presentation is not active");
          current();
        }
      };
      // Even a rejected opener may have partial native effects. Only a port's
      // confirmed close can establish reuse after the attempt starts.
      reusable = false;
      try { port = await options.openPort(control); }
      catch { throw new SignerTransportError("signer_transport_open_failed", "manual QR port could not be opened safely"); }
      if (!port || typeof port.present !== "function" || typeof port.scan !== "function" || typeof port.close !== "function") {
        protocolFailure("manual QR opener did not supply a complete port");
      }
      current();
      presenting = true;
      try {
        control.before_present();
        await portIo(() => port!.present(envelope));
      } finally { presenting = false; }
      current();
      const scanned = await portIo(() => port!.scan());
      current(); // Discard late/cancelled scans before any conversion.
      if (scanned === null) throw new SignerTransportError("signer_transport_failed", "manual QR scan was cancelled");
      // Whole raw guard precedes UTF8 conversion, slice, base64 and JSON work.
      if (typeof scanned !== "string" || scanned.length > maximumFrame) protocolFailure("manual QR response exceeds effective raw frame capacity");
      const rawBytes = Buffer.byteLength(scanned, "utf8");
      if (rawBytes > maximumFrame || encodedRequestBytes + rawBytes > work) protocolFailure("manual QR response exceeds effective raw frame/work capacity");
      if (!scanned.startsWith(QR_ENVELOPE_PREFIX)) protocolFailure("manual QR response requires a static envelope");
      const payloadChars = scanned.length - QR_ENVELOPE_PREFIX.length;
      if (payloadChars === 0 || payloadChars % 4 === 1 || Math.floor(payloadChars * 3 / 4) > maximumJson) {
        protocolFailure("manual QR response exceeds effective decoded JSON capacity or has an invalid length");
      }
      try { response = decodeQrEnvelope(scanned); }
      catch { protocolFailure("manual QR response is not a valid strict static envelope"); }
      if (!validateResponse(response).ok) protocolFailure("manual QR payload is not a signing response");
      // Expected request/key/template/ID/signature verification is performed by
      // the existing client after this actual exchange, never fabricated here.
    } catch (error) { failed = true; throw error; }
    finally {
      presenting = false;
      try {
        if (port && typeof port.close === "function") {
          try { await port.close(); reusable = true; }
          catch {
            if (!failed) throw new SignerTransportError("signer_transport_close_failed", "manual QR cleanup did not establish reuse");
          }
        }
      } finally { busy = !reusable; }
    }
    current();
    return response;
  };
  return createRouteDispatcher([{
    account_id: options.account_id, route_type: options.route_type, transport: "qr", dispatch
  }]);
}
