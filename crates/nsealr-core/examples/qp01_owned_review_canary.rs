// HRT-C01 PROPOSED compile-only source; not executed or product implementation.
use nsealr_core::{
    authorization::{AuthorizationSession, LocalDisplayError, LocalInput,
                    LocalPresentation, LocalReviewIo},
    event::OperationLimits, nip19::SecretKey,
    qr::envelope::decode_qr_envelope,
    review::event::InspectionGeometry,
};
struct Snapshot { kind: u32, index: usize, total: usize,
                  label: Vec<u8>, body: Vec<u8>, position: Vec<u8> }
struct CopyOnly { tick: u64, page: Option<Snapshot> }
impl LocalReviewIo for CopyOnly {
    fn now(&mut self) -> Option<u64> { Some(self.tick) }
    fn present(&mut self, view: LocalPresentation<'_>) -> Result<LocalInput, LocalDisplayError> {
        let (kind, frame) = match view {
            LocalPresentation::Data(frame) => (0, frame),
            LocalPresentation::Decision(frame) => (1, frame),
        };
        self.page = Some(Snapshot { kind, index: frame.index(), total: frame.total(),
            label: frame.label().as_bytes().to_vec(), body: frame.body().as_bytes().to_vec(),
            position: frame.position().as_bytes().to_vec() });
        Ok(LocalInput::None) // No gesture/consent, and no later cached-action replay.
    }
}
struct Waiting { raw: Vec<u8>, owner: AuthorizationSession, page: Snapshot }
fn move_owned(raw: Vec<u8>, trusted_sample: u64) -> Waiting {
    let limits = OperationLimits { input_bytes: 704, content_bytes: 512,
        tags: 16, fields_per_tag: 8, field_bytes: 64, ..OperationLimits::conformance() };
    let mut owner = AuthorizationSession::new(limits,
        InspectionGeometry { columns: 32, lines: 8 }).unwrap();
    let mut public_fixture = [0x11u8; 32];
    owner.select_key(SecretKey::take_from(&mut public_fixture).unwrap()).unwrap();
    {
        let mut decoded = [0u8; 704];
        let frame = decode_qr_envelope(&raw, &mut decoded).unwrap();
        owner.begin_request(frame.payload_json, Some(trusted_sample)).unwrap();
    } // Prove Pending does not borrow this decoded stack buffer.
    let mut io = CopyOnly { tick: trusted_sample, page: None };
    owner.review_step(&mut io).unwrap();
    Waiting { raw, owner, page: io.page.unwrap() }
}
fn require_static<T: 'static>() {}
fn main() {
    require_static::<Waiting>();
    let _ = move_owned as fn(Vec<u8>, u64) -> Waiting;
    let _ = include_bytes!("../../../docs/restart/implementation/QH01/native-qr-probe/expected/request-kind-1-basic.envelope");
}
