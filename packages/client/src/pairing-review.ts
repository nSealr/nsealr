import {
  parsePairingIntent,
  type LocalClientIdentity,
  type PairableLocalServiceOperation
} from "./service.js";

export const LOCAL_PAIRING_REVIEW_FORMAT = "nsealr-local-pairing-review-v0";

export type LocalPairingReviewOperation = {
  operation: PairableLocalServiceOperation;
  label: string;
  effect: string;
};

export type LocalPairingReview = {
  format: typeof LOCAL_PAIRING_REVIEW_FORMAT;
  client_id: string;
  client: LocalClientIdentity;
  requested_operations: LocalPairingReviewOperation[];
  pairing_digest: string;
  requires_user_approval: true;
  stores_production_secrets: false;
  contains_secret_material: false;
};

const OPERATION_EFFECTS: Record<PairableLocalServiceOperation, { label: string; effect: string }> = {
  select_account_route: {
    label: "Read selected account route",
    effect: "The client can read selected account public key and route metadata."
  },
  validate_signer_request: {
    label: "Validate signer requests",
    effect: "The client can ask the service to validate signer-request payloads before signer transport."
  },
  dispatch_signer_request: {
    label: "Dispatch signer requests",
    effect: "The client can ask the service to validate, route, dispatch, and verify signer requests through an approved signer route."
  },
  verify_signer_response: {
    label: "Verify signer responses",
    effect: "The client can ask the service to verify signer responses before returning them upstream."
  }
};

function operationReview(operation: PairableLocalServiceOperation): LocalPairingReviewOperation {
  const review = OPERATION_EFFECTS[operation];
  return {
    operation,
    label: review.label,
    effect: review.effect
  };
}

export function reviewPairingIntent(intent: unknown): LocalPairingReview {
  const pairing = parsePairingIntent(intent);
  return {
    format: LOCAL_PAIRING_REVIEW_FORMAT,
    client_id: pairing.client_id,
    client: pairing.client,
    requested_operations: pairing.requested_operations.map(operationReview),
    pairing_digest: pairing.pairing_digest,
    requires_user_approval: true,
    stores_production_secrets: false,
    contains_secret_material: false
  };
}
