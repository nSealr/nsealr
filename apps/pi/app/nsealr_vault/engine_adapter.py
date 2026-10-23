"""Trusted host engineering bridge to the public-fixture-only Rust owner.

No request JSON parsing, Python signing, key API, hardware route or image decoder.
Callbacks and this process are trusted; cancellation cannot interrupt a callback.
"""
import ctypes as C
from dataclasses import dataclass
import hashlib
from pathlib import Path
import threading
import time

MAX_FRAME_BYTES = 947
PRESENT = C.CFUNCTYPE(C.c_int32, C.c_uint32, C.c_uint32, C.c_uint32,
                     C.POINTER(C.c_uint8), C.c_size_t, C.POINTER(C.c_uint8),
                     C.c_size_t, C.POINTER(C.c_uint8), C.c_size_t)
NOW = C.CFUNCTYPE(C.c_int32, C.POINTER(C.c_uint64))
AUX = C.CFUNCTYPE(C.c_int32, C.POINTER(C.c_uint8), C.c_size_t)
CANCEL = C.CFUNCTYPE(C.c_int32)


@dataclass(frozen=True)
class Presentation:
    kind: int
    index: int
    total: int
    label: bytes
    body: bytes
    position: bytes


class EngineError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"public-fixture request refused: {status}")


class MonotonicSeconds:
    """Elapsed whole host seconds; not a qualified device clock/deadline."""
    def __init__(self):
        self.origin = time.monotonic_ns()

    def __call__(self):
        return (time.monotonic_ns() - self.origin) // 1_000_000_000


class EngineAdapter:
    """Explicit source-matched ELF, synchronous ownership until native return."""
    def __init__(self, library_path, library_sha256):
        path = Path(library_path).resolve(strict=True)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != library_sha256 or len(library_sha256) != 64:
            raise ValueError("native library SHA256 mismatch")
        self._library = C.CDLL(str(path))
        self._run = self._library.qp01_fixture_request_v1
        self._run.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, PRESENT, NOW,
                              AUX, CANCEL, C.POINTER(C.c_uint8), C.c_size_t,
                              C.POINTER(C.c_size_t)]
        self._run.restype = C.c_int32
        if hashlib.sha256(path.read_bytes()).hexdigest() != actual:
            raise ValueError("native library changed during load")
        self.library_path = path
        self.library_sha256 = actual
        self._reservation = threading.Lock()
        self._quarantined = False

    def run_request_frame(self, original_frame, local_io, monotonic_clock,
                          auxiliary, cancel):
        if not self._reservation.acquire(blocking=False):
            raise EngineError(-2)
        try:
            if self._quarantined:
                raise RuntimeError("uncertain native outcome: adapter quarantined")
            if not isinstance(original_frame, bytes) or not 1 <= len(original_frame) <= MAX_FRAME_BYTES:
                raise EngineError(-1)
            incoming = (C.c_uint8 * len(original_frame)).from_buffer_copy(original_frame)
            output = (C.c_uint8 * MAX_FRAME_BYTES)()
            written = C.c_size_t(0)

            @PRESENT
            def present(kind, index, total, label, label_len, body, body_len, position, position_len):
                try:
                    page = Presentation(kind, index, total, C.string_at(label, label_len),
                                        C.string_at(body, body_len), C.string_at(position, position_len))
                    action = local_io(page)
                    return action if type(action) is int and 0 <= action <= 4 else -1
                except BaseException:
                    return -1

            @NOW
            def now(destination):
                try:
                    tick = monotonic_clock()
                    if type(tick) is not int or not 0 <= tick <= (1 << 64)-1:
                        return -1
                    destination[0] = tick
                    return 0
                except BaseException:
                    return -1

            @AUX
            def aux(destination, capacity):
                try:
                    value = auxiliary()
                    if capacity != 32 or not isinstance(value, bytes) or len(value) > 33:
                        return -1
                    C.memmove(destination, value, min(len(value), capacity))
                    return len(value)
                except BaseException:
                    return -1

            @CANCEL
            def cancelled():
                try:
                    value = cancel()
                    return int(value) if type(value) is bool else -1
                except BaseException:
                    return -1

            # Strong references above survive until the complete synchronous call
            # settles. Never free/reload/reserve early on a host timeout.
            try:
                status = self._run(incoming, len(incoming), present, now, aux, cancelled,
                                   output, len(output), C.byref(written))
            except BaseException:
                self._quarantined = True
                raise
            if status != 0:
                if written.value != 0 or any(output):
                    self._quarantined = True
                    raise RuntimeError("native failure returned partial public output")
                raise EngineError(status)
            if not 1 <= written.value <= len(output) or any(output[written.value:]):
                self._quarantined = True
                raise RuntimeError("native success returned invalid result bounds")
            return bytes(output[:written.value])
        finally:
            self._reservation.release()
