# Fixed-image native QR feasibility on the host

The first run passed four fixed public image roundtrips plus a blank-image
negative. This is x86_64 host feasibility, not camera, display, ARM/Pi support,
optical readability, hostile-image decoder bounds or a completed QH01/QP01 task.
No app/runtime/protocol/limit/graph/CI file changes. `result.json` is the entry.

Input is accepted main `d41a37e25cd0a86d3a47294f8d0ba24913128a21`.
Independent expectations were committed at `6feb8abe` before implementation:
stdlib compact JSON and base64url from the four existing public wire2 examples,
with the sign-request envelope also matching its existing fixed transport vector.
The executed probe is `426eb1fd0d9cacb9743db16c85e156d96da418eb`;
`execution-01-command.json` binds argv/environment/harness/source/raw outputs.
There was one actual run, with no geometry/ECC/cap retuning or further campaign.

The actual existing `PythonQrcodeMatrixRenderer` calls python-qrcode with border0,
its default ECC_M and fit=True. The existing response-display interface adds its
unchanged quiet zone4 and integer fit to the real `PillowSt7789DrawTarget` 240x240
RGB framebuffer. Its callback captures an image instead of performing SPI. The
probe checks all pixels against that integer geometry, preserves raw RGB and PNG,
reopens the PNG and confirms identical pixels. Existing `PyzbarQrDecoder` then
uses real pyzbar/native ZBar on both forms. Native output must be bytes identical
to the frozen ORIGINAL envelope, with no dictionary parse/reserialization.
The same display interface is used for request and response fixtures; this does
not create a production request-display workflow.

| Public fixture | Envelope bytes | Matrix modules | Total with quiet zone | Pixels/module | Matrix render ms | Native framebuffer decode ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| get-key request | 98 | 41 | 49 | 4 | 4.228 | 1.346 |
| get-key response | 198 | 57 | 65 | 3 | 8.618 | 0.653 |
| sign-event request | 259 | 65 | 73 | 3 | 10.535 | 0.681 |
| sign-event response | 611 | 93 | 101 | 2 | 23.091 | 0.832 |

The white240x240 blank decoded None (0.363ms). These are single observed
perf-counter intervals, not worst-case or actual client/optical timing. Two
pixels/module is an observation of one fixed hosted image, not a new threshold.
No actual sensor, JPEG path, native input bound or physical sample was tested.

The [qrcode8.2 release API](https://pypi.org/project/qrcode/8.2/) identifies its
fit/default-ECC controls; the [pyzbar0.1.9 API](https://pypi.org/project/pyzbar/0.1.9/)
accepts Pillow images and requires a separate native ZBar on Linux. Exact wheel
URLs/SHA256, metadata, source-archive identities where supplied and installed
license bodies are bound in `sources/`. Pillow11.1.0 is pinned by its exact
CPython312 manylinux x86_64 wheel, rather than the unrelated system Pillow.
Debian [ZBar0.23.93-8 source](https://sources.debian.org/src/zbar/0.23.93-8/)
and its exact amd64 runtime package are distinguished from source-build proof.

Reproduce with the original R00 Python3.12.15 interpreter, without altering it.
Create a venv beneath this directory using its `-m venv .venv`; fetch the exact
three wheel URLs in `sources/python-inputs.json`, verify SHA256 and install them
plus the four existing pinned R00 wheels with the actual `pip --no-index
--no-deps` argv in `setup/commands.json`. Those four are required by the existing
module import closure (mnemonic/secp256k1/cffi/pycparser); no seed, key generation,
derivation or signing is called. The venv/cache/tmp are isolated and ignored.

Download the three exact Debian packages in `sources/native-inputs.json`, verify
SHA256 and `dpkg-deb -x` into `.runtime/native`. This is extraction only, with no
root/global package installation. The ZBar ELF requires the two V4L packages even
though no camera operation is called. Create the recorded local discovery link
`libzbar.so -> libzbar.so.0` and set LD_LIBRARY_PATH to that extracted lib directory
as in `setup/local-loader.json`. There is no resolver monkeypatch or ELF change.
The first ldd without that path printed a missing dependency despite exit0; its
raw log is retained. `native-loaded-proof.json` binds ZBar/V4L actually mapped in
the successful process to package versions/SHA256. The observation records all32
loaded ELF files, Python ABI and exact native image timings.

Run `.venv/bin/python probe.py --out NEW_OUTPUT_DIRECTORY` from this directory,
with the explicit map in `setup/execution-environment.json` (adjust only the
experiment's absolute paths for another checkout). Existing output directories
are refused. The recipe's archives/venv/native binaries are not committed or
adopted as a Pi image. `setup/observations.json` retains the one-off metadata
collector's missing-sdist assumption correction; no product or image failure is
relabelled. All5QH01/all3QP01/all6Q02 criteria remain incomplete.
