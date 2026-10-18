from __future__ import annotations

import importlib
import io
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from .controls import ButtonAction
from .display import DisplayFrameLimits
from .limits import NSEALR_V0_LIMITS
from .qr import ANIMATED_QR_ENVELOPE_PREFIX, QR_ENVELOPE_PREFIX, decode_animated_qr_envelope_frames, decode_qr_envelope
from .seed_entry import SessionImportSource
from .session_import_flow import SessionImportFlowResult, StatelessSessionKeyring, run_session_import_io_flow
from .session_source_qr import (
    SessionSourceQrError,
    parse_compact_seedqr_session_source,
    parse_session_source_qr_text,
)
from .st7789_layout import (
    SEEDSIGNER_ST7789_HEIGHT,
    SEEDSIGNER_ST7789_WIDTH,
    layout_seed_signer_st7789_review_frame,
)


BOARD_MODE = "BOARD"
GPIO_INPUT = "IN"
GPIO_LOW = 0
GPIO_PUD_UP = "PUD_UP"
REVIEW_ACTIONS: tuple[ButtonAction, ...] = ("reject", "approve", "next", "scroll")
ST7789_GLYPH_WIDTH = 6
PIL_COLOR_MAP = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "green": (0, 255, 0),
    "yellow": (255, 255, 0),
}


class GpioLike(Protocol):
    def setmode(self, mode: object) -> None:
        ...

    def setup(self, pin: int, mode: object, pull_up_down: object) -> None:
        ...

    def input(self, pin: int) -> object:
        ...


class CameraFrameSource(Protocol):
    def capture_frame(self) -> object:
        ...


class QrDecoder(Protocol):
    def decode_qr(self, frame: object) -> str | bytes | None:
        ...


class St7789DrawTarget(Protocol):
    def fill_rect(self, x: int, y: int, width: int, height: int, color: str) -> None:
        ...

    def draw_text(self, text: str, x: int, y: int, scale: int, color: str, max_width: int | None = None) -> None:
        ...

    def present(self) -> None:
        ...


class QrMatrixRenderer(Protocol):
    def render_qr_matrix(self, payload: str) -> Sequence[Sequence[bool]]:
        ...


class SessionSourceScanner(Protocol):
    def scan_session_source_qr(self, label: str, max_frames: int | None = None) -> SessionImportSource:
        ...


class SessionImportReviewDisplay(Protocol):
    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        ...


class SessionImportButtonInput(Protocol):
    def read_review_button(self) -> ButtonAction:
        ...


@dataclass(frozen=True)
class SeedSignerButtonProfile:
    numbering: str
    key_up: int
    key_down: int
    key_left: int
    key_right: int
    key_press: int
    key1: int
    key2: int
    key3: int

    @property
    def all_pins(self) -> tuple[int, ...]:
        return (
            self.key_up,
            self.key_down,
            self.key_left,
            self.key_right,
            self.key_press,
            self.key1,
            self.key2,
            self.key3,
        )

    @property
    def action_pins(self) -> dict[str, tuple[int, ...]]:
        return {
            "next": (self.key_right,),
            "scroll": (self.key_down,),
            "approve": (self.key_press,),
            "reject": (self.key1,),
        }


SEEDSIGNER_40_PIN_BUTTON_PROFILE = SeedSignerButtonProfile(
    numbering=BOARD_MODE,
    key_up=31,
    key_down=35,
    key_left=29,
    key_right=37,
    key_press=33,
    key1=40,
    key2=38,
    key3=36,
)


class SeedSignerGpioButtonInput:
    """GPIO button adapter for the 40-pin SeedSigner/Waveshare LCD HAT layout."""

    def __init__(
        self,
        *,
        gpio: GpioLike,
        profile: SeedSignerButtonProfile = SEEDSIGNER_40_PIN_BUTTON_PROFILE,
        sleep: Callable[[float], None] | None = None,
        poll_delay_s: float = 0.01,
        require_release: bool = True,
        release_timeout_polls: int | None = None,
    ) -> None:
        if poll_delay_s < 0:
            raise ValueError("GPIO poll delay must be non-negative")
        if release_timeout_polls is not None and release_timeout_polls <= 0:
            raise ValueError("GPIO release timeout polls must be positive")
        self.gpio = gpio
        self.profile = profile
        self.sleep = sleep or _default_sleep
        self.poll_delay_s = poll_delay_s
        self.require_release = require_release
        self.release_timeout_polls = release_timeout_polls
        self._configure_gpio()

    def _configure_gpio(self) -> None:
        self.gpio.setmode(getattr(self.gpio, "BOARD", BOARD_MODE))
        input_mode = getattr(self.gpio, "IN", GPIO_INPUT)
        pull_up = getattr(self.gpio, "PUD_UP", GPIO_PUD_UP)
        for pin in self.profile.all_pins:
            self.gpio.setup(pin, input_mode, pull_up_down=pull_up)

    def read_review_button(self, max_polls: int | None = None) -> ButtonAction:
        polls = 0
        while max_polls is None or polls < max_polls:
            action = self._pressed_action()
            if action is not None:
                if self.require_release:
                    self._wait_for_release()
                return action
            polls += 1
            self.sleep(self.poll_delay_s)
        raise TimeoutError("no SeedSigner-compatible button press observed")

    def _pressed_action(self) -> ButtonAction | None:
        for action in REVIEW_ACTIONS:
            for pin in self.profile.action_pins[action]:
                if self.gpio.input(pin) == getattr(self.gpio, "LOW", GPIO_LOW):
                    return action
        return None

    def _wait_for_release(self) -> None:
        release_polls = 0
        while self._pressed_action() is not None:
            if self.release_timeout_polls is not None and release_polls >= self.release_timeout_polls:
                raise TimeoutError("SeedSigner-compatible button release not observed")
            release_polls += 1
            self.sleep(self.poll_delay_s)


class SeedSignerCameraQrScanner:
    """Camera QR scanner boundary for the SeedSigner-compatible Pi target."""

    def __init__(
        self,
        *,
        frame_source: CameraFrameSource,
        qr_decoder: QrDecoder,
        sleep: Callable[[float], None] | None = None,
        poll_delay_s: float = 0.05,
    ) -> None:
        self.frame_source = frame_source
        self.qr_decoder = qr_decoder
        self.sleep = sleep or _default_sleep
        self.poll_delay_s = poll_delay_s

    def scan_request_qr(self, max_frames: int | None = None) -> str:
        frames = 0
        animated_frames: list[str] = []
        while max_frames is None or frames < max_frames:
            frame = self.frame_source.capture_frame()
            decoded = self.qr_decoder.decode_qr(frame)
            if decoded is not None:
                payload = _decoded_qr_text(decoded)
                if payload is None:
                    frames += 1
                    self.sleep(self.poll_delay_s)
                    continue
                if payload.startswith(QR_ENVELOPE_PREFIX):
                    return payload
                if payload.startswith(ANIMATED_QR_ENVELOPE_PREFIX):
                    if payload not in animated_frames:
                        animated_frames.append(payload)
                    if len(animated_frames) > NSEALR_V0_LIMITS["max_animated_qr_frame_count"]:
                        animated_frames = [payload]
                    try:
                        decode_animated_qr_envelope_frames(animated_frames)
                    except ValueError:
                        pass
                    else:
                        return "\n".join(animated_frames)
            frames += 1
            self.sleep(self.poll_delay_s)
        raise TimeoutError("no nSealr request QR decoded")


class SeedSignerSessionSourceQrScanner:
    """Camera QR scanner boundary for RAM-only session source import."""

    def __init__(
        self,
        *,
        frame_source: CameraFrameSource,
        qr_decoder: QrDecoder,
        sleep: Callable[[float], None] | None = None,
        poll_delay_s: float = 0.05,
    ) -> None:
        self.frame_source = frame_source
        self.qr_decoder = qr_decoder
        self.sleep = sleep or _default_sleep
        self.poll_delay_s = poll_delay_s

    def scan_session_source_qr(self, label: str, max_frames: int | None = None) -> SessionImportSource:
        frames = 0
        while max_frames is None or frames < max_frames:
            frame = self.frame_source.capture_frame()
            decoded = self.qr_decoder.decode_qr(frame)
            if decoded is not None:
                for source_parser in _session_source_parsers(label, decoded):
                    try:
                        return source_parser()
                    except SessionSourceQrError:
                        pass
            frames += 1
            self.sleep(self.poll_delay_s)
        raise TimeoutError("no supported nSealr session source QR decoded")


@dataclass
class SeedSignerSessionSourceImportIO:
    """Composed SeedSigner-style IO for RAM-only session-source import."""

    scanner: SessionSourceScanner
    review_display: SessionImportReviewDisplay
    button_input: SessionImportButtonInput

    def scan_session_source_qr(self, label: str, max_frames: int | None = None) -> SessionImportSource:
        return self.scanner.scan_session_source_qr(label, max_frames=max_frames)

    def display_review_frame(self, screen_review: dict[str, Any], page_index: int, frame: dict[str, Any]) -> None:
        self.review_display.display_review_frame(screen_review, page_index, frame)

    def read_review_button(self) -> ButtonAction:
        return self.button_input.read_review_button()


def run_seed_signer_session_source_qr_import_flow(
    *,
    keyring: StatelessSessionKeyring,
    io: SeedSignerSessionSourceImportIO,
    label: str,
    max_scan_frames: int | None = None,
    display_limits: DisplayFrameLimits = DisplayFrameLimits(),
    max_button_steps: int = 32,
) -> SessionImportFlowResult:
    source = io.scan_session_source_qr(label, max_frames=max_scan_frames)
    return run_session_import_io_flow(
        keyring,
        source,
        io,
        display_limits=display_limits,
        max_button_steps=max_button_steps,
    )


class PiCameraJpegFrameSource:
    """Legacy Pi Zero camera source matching SeedSigner-style picamera usage."""

    def __init__(
        self,
        *,
        camera: object | None = None,
        resolution: tuple[int, int] = (480, 480),
        framerate: int = 24,
        start_preview: bool = False,
    ) -> None:
        if camera is None:
            try:
                picamera = importlib.import_module("picamera")
            except ModuleNotFoundError as exc:
                raise RuntimeError("picamera is required for the SeedSigner-compatible Pi camera source") from exc
            camera = picamera.PiCamera(resolution=resolution, framerate=framerate)
            if start_preview:
                camera.start_preview()
        self.camera = camera

    def capture_frame(self) -> bytes:
        stream = io.BytesIO()
        self.camera.capture(stream, format="jpeg")
        return stream.getvalue()

    def close(self) -> None:
        close = getattr(self.camera, "close", None)
        if callable(close):
            close()


class PyzbarQrDecoder:
    """QR decoder boundary using pyzbar/zbar without making it a CI dependency."""

    def __init__(
        self,
        *,
        pyzbar: object | None = None,
        qrcode_symbol: object | None = None,
        image_loader: Callable[[bytes], object] | None = None,
    ) -> None:
        if pyzbar is None or qrcode_symbol is None:
            try:
                pyzbar_module = importlib.import_module("pyzbar.pyzbar")
            except ModuleNotFoundError as exc:
                raise RuntimeError("pyzbar and zbar are required for SeedSigner-compatible QR decoding") from exc
            pyzbar = pyzbar or pyzbar_module
            qrcode_symbol = qrcode_symbol or pyzbar_module.ZBarSymbol.QRCODE
        self.pyzbar = pyzbar
        self.qrcode_symbol = qrcode_symbol
        self.image_loader = image_loader or _load_image_from_jpeg_bytes

    def decode_qr(self, frame: object) -> str | bytes | None:
        image = self.image_loader(frame) if isinstance(frame, bytes) else frame
        barcodes = self.pyzbar.decode(image, symbols=[self.qrcode_symbol])
        if not barcodes:
            return None
        data = getattr(barcodes[0], "data", barcodes[0])
        if isinstance(data, str):
            return data.strip()
        if isinstance(data, bytes):
            return data
        raise ValueError("QR decoder returned unsupported payload type")


class PillowSt7789DrawTarget:
    """PIL framebuffer draw target for SeedSigner-compatible ST7789 adapters."""

    def __init__(
        self,
        *,
        present_image: Callable[[object], None],
        image_module: object | None = None,
        image_draw_module: object | None = None,
        font_factory: Callable[[int], object] | None = None,
        width: int = SEEDSIGNER_ST7789_WIDTH,
        height: int = SEEDSIGNER_ST7789_HEIGHT,
        background_color: str = "black",
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("display dimensions must be positive")
        if image_module is None:
            try:
                image_module = importlib.import_module("PIL.Image")
            except ModuleNotFoundError as exc:
                raise RuntimeError("Pillow is required for the ST7789 framebuffer draw target") from exc
        if image_draw_module is None:
            try:
                image_draw_module = importlib.import_module("PIL.ImageDraw")
            except ModuleNotFoundError as exc:
                raise RuntimeError("Pillow is required for the ST7789 framebuffer draw target") from exc
        self.present_image = present_image
        self.font_factory = font_factory or _default_pil_font
        self.width = width
        self.height = height
        self.image = image_module.new("RGB", (width, height), _pil_color(background_color))
        self.draw = image_draw_module.Draw(self.image)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: str) -> None:
        if width <= 0 or height <= 0:
            return
        self.draw.rectangle((x, y, x + width - 1, y + height - 1), fill=_pil_color(color))

    def draw_text(self, text: str, x: int, y: int, scale: int, color: str, max_width: int | None = None) -> None:
        if max_width is not None and max_width <= 0:
            return
        self.draw.text(
            (x, y),
            _clip_text_for_width(text, scale, max_width),
            fill=_pil_color(color),
            font=self.font_factory(scale),
        )

    def present(self) -> None:
        self.present_image(self.image)


class SeedSignerSt7789ReviewDisplay:
    """Review-display adapter that applies bounded ST7789 layout commands."""

    def __init__(self, *, target: St7789DrawTarget) -> None:
        self.target = target

    def display_review_frame(
        self,
        _screen_review: dict[str, object],
        _page_index: int,
        frame: dict[str, object],
    ) -> None:
        for command in layout_seed_signer_st7789_review_frame(frame):
            self._apply_command(command)
        self.target.present()

    def _apply_command(self, command: dict[str, object]) -> None:
        command_type = command.get("type")
        if command_type == "rect":
            self.target.fill_rect(
                int(command["x"]),
                int(command["y"]),
                int(command["width"]),
                int(command["height"]),
                str(command["color"]),
            )
            return
        if command_type == "text":
            self.target.draw_text(
                str(command["text"]),
                int(command["x"]),
                int(command["y"]),
                int(command["scale"]),
                str(command["color"]),
                max_width=int(command["width"]),
            )
            return
        raise ValueError(f"unsupported ST7789 layout command type: {command_type}")


class SeedSignerSt7789ResponseQrDisplay:
    """Response-QR display adapter for a centered matrix on a 240x240 ST7789."""

    def __init__(
        self,
        *,
        target: St7789DrawTarget,
        qr_renderer: QrMatrixRenderer,
        width: int = SEEDSIGNER_ST7789_WIDTH,
        height: int = SEEDSIGNER_ST7789_HEIGHT,
        quiet_zone_modules: int = 4,
        frame_repetitions: int = 3,
        frame_delay_s: float = 0.25,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("display dimensions must be positive")
        if quiet_zone_modules < 0:
            raise ValueError("QR quiet zone must be non-negative")
        if frame_repetitions <= 0:
            raise ValueError("QR frame repetitions must be positive")
        if frame_delay_s < 0:
            raise ValueError("QR frame delay must be non-negative")
        self.target = target
        self.qr_renderer = qr_renderer
        self.width = width
        self.height = height
        self.quiet_zone_modules = quiet_zone_modules
        self.frame_repetitions = frame_repetitions
        self.frame_delay_s = frame_delay_s
        self.sleep = sleep or _default_sleep

    def emit_response_qr(self, response_qr: str) -> None:
        frames = _response_qr_frames(response_qr)
        cycles = self.frame_repetitions if len(frames) > 1 else 1
        for _ in range(cycles):
            for frame in frames:
                self._render_response_qr_frame(frame)
                if len(frames) > 1:
                    self.sleep(self.frame_delay_s)

    def _render_response_qr_frame(self, response_qr: str) -> None:
        matrix = _validated_qr_matrix(self.qr_renderer.render_qr_matrix(response_qr))
        modules = len(matrix) + (self.quiet_zone_modules * 2)
        module_size = min(self.width, self.height) // modules
        if module_size <= 0:
            raise ValueError("QR matrix does not fit display")
        qr_size = modules * module_size
        origin_x = (self.width - qr_size) // 2
        origin_y = (self.height - qr_size) // 2

        self.target.fill_rect(0, 0, self.width, self.height, "black")
        self.target.fill_rect(origin_x, origin_y, qr_size, qr_size, "white")
        for row_index, row in enumerate(matrix):
            for column_index, enabled in enumerate(row):
                if enabled:
                    self.target.fill_rect(
                        origin_x + ((column_index + self.quiet_zone_modules) * module_size),
                        origin_y + ((row_index + self.quiet_zone_modules) * module_size),
                        module_size,
                        module_size,
                        "black",
                    )
        self.target.present()


class PythonQrcodeMatrixRenderer:
    """Optional python-qrcode matrix renderer for signed response QR output."""

    def __init__(self, *, qrcode_module: object | None = None, border: int = 0) -> None:
        if border < 0:
            raise ValueError("QR border must be non-negative")
        if qrcode_module is None:
            try:
                qrcode_module = importlib.import_module("qrcode")
            except ModuleNotFoundError as exc:
                raise RuntimeError("python-qrcode is required for response QR matrix rendering") from exc
        self.qrcode_module = qrcode_module
        self.border = border

    def render_qr_matrix(self, payload: str) -> Sequence[Sequence[bool]]:
        qr = self.qrcode_module.QRCode(border=self.border)
        qr.add_data(payload)
        qr.make(fit=True)
        return _validated_qr_matrix(qr.get_matrix())


def create_seed_signer_gpio_button_input() -> SeedSignerGpioButtonInput:
    try:
        gpio = importlib.import_module("RPi.GPIO")
    except ModuleNotFoundError as exc:
        raise RuntimeError("RPi.GPIO is required for SeedSigner-compatible GPIO input") from exc
    return SeedSignerGpioButtonInput(gpio=gpio)


def create_seed_signer_camera_qr_scanner() -> SeedSignerCameraQrScanner:
    return SeedSignerCameraQrScanner(
        frame_source=PiCameraJpegFrameSource(),
        qr_decoder=PyzbarQrDecoder(),
    )


def create_seed_signer_session_source_qr_scanner() -> SeedSignerSessionSourceQrScanner:
    return SeedSignerSessionSourceQrScanner(
        frame_source=PiCameraJpegFrameSource(),
        qr_decoder=PyzbarQrDecoder(),
    )


def create_seed_signer_st7789_review_display(
    *,
    present_image: Callable[[object], None],
) -> SeedSignerSt7789ReviewDisplay:
    return SeedSignerSt7789ReviewDisplay(target=PillowSt7789DrawTarget(present_image=present_image))


def create_seed_signer_st7789_response_qr_display(
    *,
    present_image: Callable[[object], None],
) -> SeedSignerSt7789ResponseQrDisplay:
    return SeedSignerSt7789ResponseQrDisplay(
        target=PillowSt7789DrawTarget(present_image=present_image),
        qr_renderer=PythonQrcodeMatrixRenderer(),
    )


def _load_image_from_jpeg_bytes(value: bytes) -> object:
    try:
        pil_image = importlib.import_module("PIL.Image")
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required to decode picamera JPEG frames") from exc
    return pil_image.open(io.BytesIO(value))


def _decoded_qr_text(decoded: str | bytes) -> str | None:
    if isinstance(decoded, str):
        return decoded.strip()
    try:
        return decoded.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None


def _session_source_parsers(label: str, decoded: str | bytes) -> list[Callable[[], SessionImportSource]]:
    parsers: list[Callable[[], SessionImportSource]] = []
    if isinstance(decoded, bytes):
        parsers.append(lambda: parse_compact_seedqr_session_source(label, decoded))
        text = _decoded_qr_text(decoded)
        if text is not None:
            parsers.append(lambda: parse_session_source_qr_text(label, text))
        return parsers
    parsers.append(lambda: parse_session_source_qr_text(label, decoded))
    return parsers


def _default_pil_font(scale: int) -> object:
    try:
        image_font = importlib.import_module("PIL.ImageFont")
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required for ST7789 text rendering") from exc
    try:
        return image_font.load_default(size=max(8, 8 * max(1, scale)))
    except TypeError:
        return image_font.load_default()


def _pil_color(color: str) -> tuple[int, int, int]:
    try:
        return PIL_COLOR_MAP[color]
    except KeyError as exc:
        raise ValueError(f"unsupported ST7789 color: {color}") from exc


def _validated_qr_matrix(matrix: Sequence[Sequence[bool]]) -> Sequence[Sequence[bool]]:
    if not matrix:
        raise ValueError("QR matrix must not be empty")
    width = len(matrix[0])
    if width == 0:
        raise ValueError("QR matrix must not be empty")
    for row in matrix:
        if len(row) != width:
            raise ValueError("QR matrix must be rectangular")
        if any(type(item) is not bool for item in row):
            raise ValueError("QR matrix values must be booleans")
    if len(matrix) != width:
        raise ValueError("QR matrix must be square")
    return matrix


def _response_qr_frames(response_qr: str) -> list[str]:
    frames = [line.strip() for line in response_qr.splitlines() if line.strip()]
    if not frames:
        raise ValueError("response QR payload must not be empty")
    if len(frames) == 1:
        if frames[0].startswith(QR_ENVELOPE_PREFIX):
            try:
                decode_qr_envelope(frames[0])
            except ValueError as exc:
                raise ValueError("static response QR payload is invalid") from exc
            return frames
        if frames[0].startswith(ANIMATED_QR_ENVELOPE_PREFIX):
            _validate_animated_response_qr_frames(frames)
            return frames
        raise ValueError("response QR payload must be nsealr1 or nsealr1a")
    if len(frames) > NSEALR_V0_LIMITS["max_animated_qr_frame_count"]:
        raise ValueError("animated response QR frame count exceeds nSealr v0 limit")
    if all(frame.startswith(ANIMATED_QR_ENVELOPE_PREFIX) for frame in frames):
        _validate_animated_response_qr_frames(frames)
        return frames
    raise ValueError("animated response QR payload must contain only nsealr1a frames")


def _validate_animated_response_qr_frames(frames: Sequence[str]) -> None:
    try:
        decode_animated_qr_envelope_frames(frames)
    except ValueError as exc:
        raise ValueError("animated response QR payload is invalid") from exc


def _clip_text_for_width(text: str, scale: int, max_width: int | None) -> str:
    if max_width is None:
        return text
    char_width = ST7789_GLYPH_WIDTH * max(1, scale)
    max_chars = max_width // char_width
    return text[:max_chars]


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)
