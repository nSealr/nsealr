from __future__ import annotations

import json
import unittest
from pathlib import Path

from nsealr_vault.seed_signer_hardware import (
    BOARD_MODE,
    GPIO_LOW,
    GPIO_PUD_UP,
    PiCameraJpegFrameSource,
    PillowSt7789DrawTarget,
    PythonQrcodeMatrixRenderer,
    PyzbarQrDecoder,
    SEEDSIGNER_40_PIN_BUTTON_PROFILE,
    SeedSignerCameraQrScanner,
    SeedSignerGpioButtonInput,
    SeedSignerSessionSourceImportIO,
    SeedSignerSessionSourceQrScanner,
    SeedSignerSt7789ResponseQrDisplay,
    SeedSignerSt7789ReviewDisplay,
    run_seed_signer_session_source_qr_import_flow,
)
from nsealr_vault.seed_entry import SessionImportSource
from nsealr_vault.session_import_flow import SessionImportFlowError, StatelessSessionKeyring
from nsealr_vault.qr import decode_animated_qr_envelope_frames, encode_animated_qr_envelope_frames, encode_qr_envelope


SPECS = Path(__file__).resolve().parent / "fixtures/specs"


class FakeGpio:
    BOARD = "BOARD"
    IN = "IN"
    PUD_UP = "PUD_UP"
    LOW = 0
    HIGH = 1

    def __init__(self, low_pins: set[int] | None = None) -> None:
        self.low_pins = low_pins or set()
        self.mode: str | None = None
        self.setups: list[tuple[int, str, str]] = []

    def setmode(self, mode: str) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: str, pull_up_down: str) -> None:
        self.setups.append((pin, mode, pull_up_down))

    def input(self, pin: int) -> int:
        return self.LOW if pin in self.low_pins else self.HIGH


class ReleasingGpio(FakeGpio):
    def __init__(self, pressed_pin: int) -> None:
        super().__init__()
        self.pressed_pin = pressed_pin
        self.pressed_reads = 0

    def input(self, pin: int) -> int:
        if pin != self.pressed_pin:
            return self.HIGH
        self.pressed_reads += 1
        return self.LOW if self.pressed_reads == 1 else self.HIGH


class FakeFrameSource:
    def __init__(self, frames: list[object]) -> None:
        self.frames = list(frames)

    def capture_frame(self) -> object:
        if not self.frames:
            raise RuntimeError("no more camera frames")
        return self.frames.pop(0)


class FakeQrDecoder:
    def __init__(self, payloads: list[str | bytes | None]) -> None:
        self.payloads = list(payloads)
        self.frames: list[object] = []

    def decode_qr(self, frame: object) -> str | bytes | None:
        self.frames.append(frame)
        if not self.payloads:
            return None
        return self.payloads.pop(0)


class FakeDrawTarget:
    def __init__(self) -> None:
        self.operations: list[tuple[object, ...]] = []

    def fill_rect(self, x: int, y: int, width: int, height: int, color: str) -> None:
        self.operations.append(("fill_rect", x, y, width, height, color))

    def draw_text(self, text: str, x: int, y: int, scale: int, color: str, max_width: int | None = None) -> None:
        self.operations.append(("draw_text", text, x, y, scale, color, max_width))

    def present(self) -> None:
        self.operations.append(("present",))


class FakePillowImage:
    def __init__(self, mode: str, size: tuple[int, int], color: object) -> None:
        self.mode = mode
        self.size = size
        self.color = color
        self.operations: list[tuple[object, ...]] = []


class FakePillowImageModule:
    def new(self, mode: str, size: tuple[int, int], color: object) -> FakePillowImage:
        return FakePillowImage(mode, size, color)


class FakePillowDraw:
    def __init__(self, image: FakePillowImage) -> None:
        self.image = image

    def rectangle(self, box: tuple[int, int, int, int], fill: object) -> None:
        self.image.operations.append(("rectangle", box, fill))

    def text(self, position: tuple[int, int], text: str, fill: object, font: object) -> None:
        self.image.operations.append(("text", position, text, fill, font))


class FakePillowImageDrawModule:
    def Draw(self, image: FakePillowImage) -> FakePillowDraw:
        return FakePillowDraw(image)


class FakeQrMatrixRenderer:
    def __init__(self, matrix: list[list[bool]]) -> None:
        self.matrix = matrix
        self.payloads: list[str] = []

    def render_qr_matrix(self, payload: str) -> list[list[bool]]:
        self.payloads.append(payload)
        return self.matrix


class FakeQrCode:
    def __init__(self, matrix: list[list[bool]]) -> None:
        self.matrix = matrix
        self.data: list[str] = []
        self.made_fit: bool | None = None

    def add_data(self, payload: str) -> None:
        self.data.append(payload)

    def make(self, fit: bool) -> None:
        self.made_fit = fit

    def get_matrix(self) -> list[list[bool]]:
        return self.matrix


class FakeQrcodeModule:
    def __init__(self, qr: FakeQrCode) -> None:
        self.qr = qr
        self.kwargs: dict[str, object] | None = None

    def QRCode(self, **kwargs: object) -> FakeQrCode:
        self.kwargs = kwargs
        return self.qr


class FakePiCamera:
    def __init__(self) -> None:
        self.captures: list[str] = []
        self.closed = False

    def capture(self, stream: object, format: str) -> None:
        self.captures.append(format)
        stream.write(b"jpeg-frame")

    def close(self) -> None:
        self.closed = True


class FakeBarcode:
    def __init__(self, data: bytes | str) -> None:
        self.data = data


class FakePyzbarModule:
    def __init__(self, barcodes: list[FakeBarcode]) -> None:
        self.barcodes = barcodes
        self.calls: list[tuple[object, object]] = []

    def decode(self, image: object, symbols: object) -> list[FakeBarcode]:
        self.calls.append((image, symbols))
        return self.barcodes


class FakeSessionSourceScanner:
    def __init__(self, source: SessionImportSource) -> None:
        self.source = source
        self.calls: list[tuple[str, int | None]] = []

    def scan_session_source_qr(self, label: str, max_frames: int | None = None) -> SessionImportSource:
        self.calls.append((label, max_frames))
        return self.source


class FakeSessionImportDisplay:
    def __init__(self) -> None:
        self.frames: list[tuple[int, dict[str, object]]] = []

    def display_review_frame(self, screen_review: dict[str, object], page_index: int, frame: dict[str, object]) -> None:
        self.frames.append((page_index, frame))


class FakeSessionImportButtons:
    def __init__(self, buttons: list[str]) -> None:
        self.buttons = list(buttons)

    def read_review_button(self) -> str:
        if not self.buttons:
            raise RuntimeError("no more session import buttons")
        return self.buttons.pop(0)


class SeedSignerHardwareTests(unittest.TestCase):
    def test_profile_matches_seedsigner_40_pin_hat_pins(self) -> None:
        profile = SEEDSIGNER_40_PIN_BUTTON_PROFILE

        self.assertEqual(profile.numbering, BOARD_MODE)
        self.assertEqual(profile.key_up, 31)
        self.assertEqual(profile.key_down, 35)
        self.assertEqual(profile.key_left, 29)
        self.assertEqual(profile.key_right, 37)
        self.assertEqual(profile.key_press, 33)
        self.assertEqual(profile.key1, 40)
        self.assertEqual(profile.key2, 38)
        self.assertEqual(profile.key3, 36)
        self.assertEqual(profile.action_pins["next"], (profile.key_right,))
        self.assertEqual(profile.action_pins["scroll"], (profile.key_down,))
        self.assertEqual(profile.action_pins["approve"], (profile.key_press,))
        self.assertEqual(profile.action_pins["reject"], (profile.key1,))

    def test_gpio_input_configures_all_hat_buttons_as_pullups(self) -> None:
        gpio = FakeGpio()

        SeedSignerGpioButtonInput(gpio=gpio, sleep=lambda _seconds: None)

        self.assertEqual(gpio.mode, BOARD_MODE)
        configured = {pin for pin, _mode, _pull in gpio.setups}
        self.assertEqual(configured, set(SEEDSIGNER_40_PIN_BUTTON_PROFILE.all_pins))
        self.assertTrue(all(mode == "IN" and pull == GPIO_PUD_UP for _pin, mode, pull in gpio.setups))

    def test_gpio_input_maps_right_down_press_key1_to_review_actions(self) -> None:
        cases = {
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right: "next",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_down: "scroll",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_press: "approve",
            SEEDSIGNER_40_PIN_BUTTON_PROFILE.key1: "reject",
        }
        for pin, expected in cases.items():
            with self.subTest(pin=pin):
                gpio = FakeGpio({pin})
                buttons = SeedSignerGpioButtonInput(
                    gpio=gpio,
                    sleep=lambda _seconds: None,
                    require_release=False,
                )

                self.assertEqual(buttons.read_review_button(max_polls=1), expected)

    def test_gpio_input_waits_for_button_release_before_returning_action(self) -> None:
        gpio = ReleasingGpio(SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right)
        buttons = SeedSignerGpioButtonInput(gpio=gpio, sleep=lambda _seconds: None)

        self.assertEqual(buttons.read_review_button(max_polls=1), "next")
        self.assertEqual(gpio.pressed_reads, 2)

    def test_gpio_input_times_out_when_button_release_is_not_observed(self) -> None:
        gpio = FakeGpio({SEEDSIGNER_40_PIN_BUTTON_PROFILE.key_right})
        buttons = SeedSignerGpioButtonInput(
            gpio=gpio,
            sleep=lambda _seconds: None,
            release_timeout_polls=2,
        )

        with self.assertRaisesRegex(TimeoutError, "button release not observed"):
            buttons.read_review_button(max_polls=1)

    def test_gpio_input_times_out_without_a_pressed_button(self) -> None:
        buttons = SeedSignerGpioButtonInput(gpio=FakeGpio(), sleep=lambda _seconds: None)

        with self.assertRaisesRegex(TimeoutError, "no SeedSigner-compatible button press"):
            buttons.read_review_button(max_polls=2)

    def test_camera_qr_scanner_polls_until_payload_is_decoded(self) -> None:
        frames = FakeFrameSource(["frame-a", "frame-b"])
        decoder = FakeQrDecoder([None, "  nsealr1:test-request  "])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        self.assertEqual(scanner.scan_request_qr(max_frames=2), "nsealr1:test-request")
        self.assertEqual(decoder.frames, ["frame-a", "frame-b"])

    def test_camera_qr_scanner_ignores_unrelated_payloads_until_nsealr_request(self) -> None:
        frames = FakeFrameSource(["frame-a", "frame-b", "frame-c"])
        decoder = FakeQrDecoder([None, "bitcoin-seedqr-not-a-request", " nsealr1:test-request "])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        self.assertEqual(scanner.scan_request_qr(max_frames=3), "nsealr1:test-request")
        self.assertEqual(decoder.frames, ["frame-a", "frame-b", "frame-c"])

    def test_camera_qr_scanner_collects_animated_request_frames(self) -> None:
        animated = encode_animated_qr_envelope_frames(
            {
                "version": 1,
                "request_id": "req-camera-animated",
                "method": "sign_event",
                "params": {"event_template": {"created_at": 1710000000, "kind": 1, "tags": [], "content": "hello"}},
            },
            chunk_size_chars=24,
        )
        frames = FakeFrameSource([f"frame-{index}" for index in range(len(animated) + 1)])
        decoder = FakeQrDecoder(["unrelated", *animated])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        scanned = scanner.scan_request_qr(max_frames=len(animated) + 1)

        self.assertEqual(scanned.splitlines(), animated)
        self.assertEqual(decode_animated_qr_envelope_frames(scanned.splitlines())["request_id"], "req-camera-animated")

    def test_camera_qr_scanner_times_out_without_payload(self) -> None:
        scanner = SeedSignerCameraQrScanner(
            frame_source=FakeFrameSource(["frame-a", "frame-b"]),
            qr_decoder=FakeQrDecoder([None, None]),
            sleep=lambda _seconds: None,
        )

        with self.assertRaisesRegex(TimeoutError, "no nSealr request QR decoded"):
            scanner.scan_request_qr(max_frames=2)

    def test_session_source_qr_scanner_ignores_non_source_payloads_until_seedqr(self) -> None:
        seedqr_vector = json.loads((SPECS / "vectors/seedqr/seedsigner-vector-1.json").read_text(encoding="utf-8"))
        frames = FakeFrameSource(["frame-a", "frame-b", "frame-c"])
        decoder = FakeQrDecoder([
            "nsealr1:not-a-session-source",
            "not a valid mnemonic or nsec",
            seedqr_vector["standard_seedqr_digits"],
        ])
        scanner = SeedSignerSessionSourceQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        source = scanner.scan_session_source_qr("SeedQR session", max_frames=3)

        self.assertEqual(source.source_type, "bip39_seed")
        self.assertEqual(source.label, "SeedQR session")
        self.assertEqual(list(source.bip39_word_indexes), seedqr_vector["standard_word_indexes"])

    def test_request_qr_scanner_decodes_utf8_bytes_payloads(self) -> None:
        frames = FakeFrameSource(["frame-a", "frame-b"])
        decoder = FakeQrDecoder([b"not-a-request", b"  nsealr1:request  "])
        scanner = SeedSignerCameraQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        self.assertEqual(scanner.scan_request_qr(max_frames=2), "nsealr1:request")

    def test_session_source_qr_scanner_accepts_compact_seedqr_bytes(self) -> None:
        seedqr_vector = json.loads((SPECS / "vectors/seedqr/seedsigner-vector-1.json").read_text(encoding="utf-8"))
        frames = FakeFrameSource(["frame-a", "frame-b"])
        decoder = FakeQrDecoder([
            b"\xffnot-utf8-or-compact",
            bytes.fromhex(seedqr_vector["compact_seedqr_hex"]),
        ])
        scanner = SeedSignerSessionSourceQrScanner(frame_source=frames, qr_decoder=decoder, sleep=lambda _seconds: None)

        source = scanner.scan_session_source_qr("CompactSeedQR session", max_frames=2)

        self.assertEqual(source.source_type, "bip39_seed")
        self.assertEqual(source.label, "CompactSeedQR session")
        self.assertEqual(list(source.bip39_word_indexes), seedqr_vector["standard_word_indexes"])

    def test_session_source_qr_scanner_times_out_without_supported_source(self) -> None:
        scanner = SeedSignerSessionSourceQrScanner(
            frame_source=FakeFrameSource(["frame-a", "frame-b"]),
            qr_decoder=FakeQrDecoder(["nsealr1:not-a-session-source", None]),
            sleep=lambda _seconds: None,
        )

        with self.assertRaisesRegex(TimeoutError, "no supported nSealr session source QR decoded"):
            scanner.scan_session_source_qr("Session source", max_frames=2)

    def test_session_source_import_io_loads_keyring_after_displayed_approval(self) -> None:
        source = SessionImportSource.nsec("Camera nsec", "00" * 31 + "01")
        scanner = FakeSessionSourceScanner(source)
        display = FakeSessionImportDisplay()
        io = SeedSignerSessionSourceImportIO(
            scanner=scanner,
            review_display=display,
            button_input=FakeSessionImportButtons(["next", "approve"]),
        )
        keyring = StatelessSessionKeyring()

        result = run_seed_signer_session_source_qr_import_flow(
            keyring=keyring,
            io=io,
            label="Camera nsec",
            max_scan_frames=4,
        )

        self.assertTrue(result.approved)
        self.assertTrue(result.loaded)
        self.assertEqual(keyring.source_at(0), source)
        self.assertEqual(scanner.calls, [("Camera nsec", 4)])
        self.assertEqual([page_index for page_index, _frame in display.frames], [0, 1])
        rendered_frames = json.dumps([frame for _page_index, frame in display.frames])
        self.assertIn("Secret: hidden", rendered_frames)
        self.assertNotIn(source.nsec_secret_key, rendered_frames)

    def test_session_source_import_io_rejection_keeps_keyring_empty(self) -> None:
        source = SessionImportSource.nsec("Camera nsec", "00" * 31 + "01")
        display = FakeSessionImportDisplay()
        io = SeedSignerSessionSourceImportIO(
            scanner=FakeSessionSourceScanner(source),
            review_display=display,
            button_input=FakeSessionImportButtons(["reject"]),
        )
        keyring = StatelessSessionKeyring()

        result = run_seed_signer_session_source_qr_import_flow(keyring=keyring, io=io, label="Camera nsec")

        self.assertFalse(result.approved)
        self.assertFalse(result.loaded)
        self.assertTrue(keyring.empty)
        self.assertEqual([page_index for page_index, _frame in display.frames], [0])

    def test_session_source_import_io_bounds_nonterminal_button_streams(self) -> None:
        source = SessionImportSource.nsec("Camera nsec", "00" * 31 + "01")
        display = FakeSessionImportDisplay()
        io = SeedSignerSessionSourceImportIO(
            scanner=FakeSessionSourceScanner(source),
            review_display=display,
            button_input=FakeSessionImportButtons(["next", "next"]),
        )
        keyring = StatelessSessionKeyring()

        with self.assertRaisesRegex(SessionImportFlowError, "max button steps"):
            run_seed_signer_session_source_qr_import_flow(
                keyring=keyring,
                io=io,
                label="Camera nsec",
                max_button_steps=1,
            )

        self.assertTrue(keyring.empty)
        self.assertEqual([page_index for page_index, _frame in display.frames], [0])

    def test_picamera_frame_source_captures_jpeg_bytes(self) -> None:
        camera = FakePiCamera()
        source = PiCameraJpegFrameSource(camera=camera)

        self.assertEqual(source.capture_frame(), b"jpeg-frame")
        self.assertEqual(camera.captures, ["jpeg"])

        source.close()
        self.assertTrue(camera.closed)

    def test_pyzbar_decoder_returns_first_utf8_qr_payload(self) -> None:
        pyzbar = FakePyzbarModule([FakeBarcode(b"nsealr1:request")])
        decoder = PyzbarQrDecoder(pyzbar=pyzbar, qrcode_symbol="QRCODE")

        self.assertEqual(decoder.decode_qr("pil-image"), b"nsealr1:request")
        self.assertEqual(pyzbar.calls, [("pil-image", ["QRCODE"])])

    def test_pyzbar_decoder_returns_none_when_no_qr_is_found(self) -> None:
        decoder = PyzbarQrDecoder(pyzbar=FakePyzbarModule([]), qrcode_symbol="QRCODE")

        self.assertIsNone(decoder.decode_qr("pil-image"))

    def test_pyzbar_decoder_preserves_non_utf8_payload_bytes(self) -> None:
        decoder = PyzbarQrDecoder(pyzbar=FakePyzbarModule([FakeBarcode(b"\xff")]), qrcode_symbol="QRCODE")

        self.assertEqual(decoder.decode_qr("pil-image"), b"\xff")

    def test_pillow_st7789_draw_target_renders_to_presenter(self) -> None:
        presented: list[FakePillowImage] = []
        target = PillowSt7789DrawTarget(
            present_image=presented.append,
            image_module=FakePillowImageModule(),
            image_draw_module=FakePillowImageDrawModule(),
            font_factory=lambda scale: f"font-{scale}",
        )

        target.fill_rect(1, 2, 3, 4, "green")
        target.draw_text("Ready", 5, 6, 2, "white", max_width=100)
        target.present()

        self.assertEqual(len(presented), 1)
        self.assertEqual(presented[0].size, (240, 240))
        self.assertEqual(
            presented[0].operations,
            [
                ("rectangle", (1, 2, 3, 5), (0, 255, 0)),
                ("text", (5, 6), "Ready", (255, 255, 255), "font-2"),
            ],
        )

    def test_pillow_st7789_draw_target_clips_text_to_max_width(self) -> None:
        presented: list[FakePillowImage] = []
        target = PillowSt7789DrawTarget(
            present_image=presented.append,
            image_module=FakePillowImageModule(),
            image_draw_module=FakePillowImageDrawModule(),
            font_factory=lambda scale: f"font-{scale}",
        )

        target.draw_text("abcdef", 0, 0, 1, "yellow", max_width=12)
        target.present()

        self.assertEqual(presented[0].operations, [("text", (0, 0), "ab", (255, 255, 0), "font-1")])

    def test_python_qrcode_renderer_returns_boolean_matrix(self) -> None:
        qr = FakeQrCode([[True, False], [False, True]])
        qrcode_module = FakeQrcodeModule(qr)
        renderer = PythonQrcodeMatrixRenderer(qrcode_module=qrcode_module)
        payload = "renderer-payload"

        self.assertEqual(renderer.render_qr_matrix(payload), [[True, False], [False, True]])
        self.assertEqual(qr.data, [payload])
        self.assertTrue(qr.made_fit)
        self.assertEqual(qrcode_module.kwargs, {"border": 0})

    def test_python_qrcode_renderer_rejects_non_boolean_matrix(self) -> None:
        qr = FakeQrCode([[True, 1]])  # type: ignore[list-item]
        renderer = PythonQrcodeMatrixRenderer(qrcode_module=FakeQrcodeModule(qr))

        with self.assertRaisesRegex(ValueError, "QR matrix values must be booleans"):
            renderer.render_qr_matrix("renderer-payload")

    def test_st7789_review_display_renders_layout_commands_to_target(self) -> None:
        target = FakeDrawTarget()
        display = SeedSignerSt7789ReviewDisplay(target=target)

        display.display_review_frame(
            {"format": "screen-review-v0"},
            0,
            {
                "title": "Event",
                "page_indicator": "Page 1/4",
                "body_lines": ["Kind 1", "Created 1710000000", "Author", "abcdef"],
                "body_line_styles": ["meta", "meta", "meta", "value"],
                "action_hint": "Next",
            },
        )

        self.assertEqual(target.operations[0], ("fill_rect", 0, 0, 240, 240, "black"))
        self.assertIn(("draw_text", "Event", 8, 8, 2, "white", 60), target.operations)
        self.assertIn(("draw_text", "Kind 1", 8, 44, 1, "green", 36), target.operations)
        self.assertEqual(target.operations[-1], ("present",))

    def test_st7789_response_qr_display_renders_centered_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True, False], [False, True]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer, quiet_zone_modules=1)
        response_qr = encode_qr_envelope({"version": 1, "request_id": "req-response-display", "ok": True, "result": {}})

        display.emit_response_qr(response_qr)

        self.assertEqual(renderer.payloads, [response_qr])
        self.assertEqual(target.operations[0], ("fill_rect", 0, 0, 240, 240, "black"))
        self.assertEqual(target.operations[1], ("fill_rect", 0, 0, 240, 240, "white"))
        self.assertIn(("fill_rect", 60, 60, 60, 60, "black"), target.operations)
        self.assertIn(("fill_rect", 120, 120, 60, 60, "black"), target.operations)
        self.assertEqual(target.operations[-1], ("present",))

    def test_st7789_response_qr_display_cycles_animated_frames(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True]])
        sleeps: list[float] = []
        display = SeedSignerSt7789ResponseQrDisplay(
            target=target,
            qr_renderer=renderer,
            frame_repetitions=2,
            frame_delay_s=0.1,
            sleep=sleeps.append,
        )
        animated = encode_animated_qr_envelope_frames(
            {"version": 1, "request_id": "req-response-display-animated", "ok": True, "result": {}},
            chunk_size_chars=24,
        )

        display.emit_response_qr("\n".join(animated))

        self.assertEqual(renderer.payloads, animated * 2)
        self.assertEqual(sleeps, [0.1] * (len(animated) * 2))
        self.assertEqual(
            [operation for operation in target.operations if operation == ("present",)],
            [("present",)] * (len(animated) * 2),
        )

    def test_st7789_response_qr_display_rejects_malformed_static_frame(self) -> None:
        display = SeedSignerSt7789ResponseQrDisplay(
            target=FakeDrawTarget(),
            qr_renderer=FakeQrMatrixRenderer([[True]]),
        )

        with self.assertRaisesRegex(ValueError, "static response QR payload is invalid"):
            display.emit_response_qr("nsealr1:not-valid-base64url-json")

    def test_st7789_response_qr_display_rejects_malformed_animated_frames(self) -> None:
        display = SeedSignerSt7789ResponseQrDisplay(
            target=FakeDrawTarget(),
            qr_renderer=FakeQrMatrixRenderer([[True]]),
        )

        with self.assertRaisesRegex(ValueError, "animated response QR payload is invalid"):
            display.emit_response_qr("nsealr1a:not-a-valid-frame\nnsealr1a:still-invalid")

    def test_st7789_response_qr_display_rejects_mixed_animated_payload(self) -> None:
        display = SeedSignerSt7789ResponseQrDisplay(
            target=FakeDrawTarget(),
            qr_renderer=FakeQrMatrixRenderer([[True]]),
        )

        with self.assertRaisesRegex(ValueError, "only nsealr1a frames"):
            display.emit_response_qr("nsealr1a:frame-1\nnsealr1:static")

    def test_st7789_response_qr_display_rejects_non_nsealr_payload(self) -> None:
        display = SeedSignerSt7789ResponseQrDisplay(
            target=FakeDrawTarget(),
            qr_renderer=FakeQrMatrixRenderer([[True]]),
        )

        with self.assertRaisesRegex(ValueError, "must be nsealr1 or nsealr1a"):
            display.emit_response_qr("not-a-response")

    def test_st7789_response_qr_display_rejects_invalid_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True], [False, True]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer)
        response_qr = encode_qr_envelope({"version": 1, "request_id": "req-invalid-matrix", "ok": True, "result": {}})

        with self.assertRaisesRegex(ValueError, "QR matrix must be rectangular"):
            display.emit_response_qr(response_qr)

    def test_st7789_response_qr_display_requires_square_qr_matrix(self) -> None:
        target = FakeDrawTarget()
        renderer = FakeQrMatrixRenderer([[True, False, True], [False, True, False]])
        display = SeedSignerSt7789ResponseQrDisplay(target=target, qr_renderer=renderer)
        response_qr = encode_qr_envelope({"version": 1, "request_id": "req-non-square-matrix", "ok": True, "result": {}})

        with self.assertRaisesRegex(ValueError, "QR matrix must be square"):
            display.emit_response_qr(response_qr)


if __name__ == "__main__":
    unittest.main()
