//! Exact disabled-development device response replay. The retired universal
//! readiness/status and enabled-target vectors are no longer active contracts.
//! Typed profile truth tables live in nsealr-core/tests/profile_capabilities.rs.

use super::{assert_json_eq, compact_bytes, ReplayResult};
use nsealr_core::protocol::{development_device_protocol_context, handle_serial_frame};
use serde_json::Value;

pub(super) fn replay(value: &Value) -> ReplayResult {
    let request = value
        .get("request")
        .ok_or("device vector requires request")?;
    let expected = value
        .get("response")
        .ok_or("device vector requires response")?;
    let frame = super::encode_serial_request_frame(&compact_bytes(request))?;
    let response = handle_serial_frame(&frame, &development_device_protocol_context())
        .map_err(|error| format!("handle_serial_frame: {error}"))?;
    let (_, actual) = super::decode_serial_frame_json(response.as_bytes())?;
    assert_json_eq("wire2 device response", &actual, expected)
}
