# Build-input attribution

The existing application notices remain in place. No C/Rust application, SDK or
vendor implementation is changed by this maintenance recipe.

* ESP-IDF at the pinned commit: Apache-2.0 and the notices/licenses of its pinned
  submodules; https://github.com/espressif/esp-idf/blob/7101770dc6db2667b3c477cc31365dd1acd6db4e/LICENSE .
* Waveshare origin870588e6: Apache-2.0, preserved in ../vendor/Waveshare-LICENSE.txt.
  sdkconfig.base is the exact previously admitted generated rev3_x baseline;
  it retains its generated heading and SDK version.
* esp_lvgl_adapter0.6.4: Espressif Apache-2.0. The downloaded LICENSE and source
  copyright/SPDX notices are retained. The versioned patch only changes four
  LVGL9.6 header include paths and retains its explicit local-change notice.
  Original source commit5d75f3f0dc499d9ed4b69284a3741187c2b75a70 is recorded in pins.json.
* Components: versions/content hashes and registry locations in ../dependencies.lock;
  original package LICENSE/COPYING/SPDX files remain in each downloaded component.
  They are not copied into this repository as a second component store.
* GCC toolchain: GPL with the GCC runtime exception; CMake BSD-3-Clause;
  Ninja Apache-2.0; ROM ELFs Apache-2.0. Exact archive/license identifiers are in
  pins.json and the upstream SDK tools.json.
* Rust/Rustup: MIT OR Apache-2.0, https://github.com/rust-lang/rust and
  https://github.com/rust-lang/rustup ; exact version/distribution pins in pins.json.
* Python standalone: Python Software Foundation and bundled-library licenses in
  the authenticated archive; https://github.com/astral-sh/python-build-standalone .
* uv0.11.28: MIT OR Apache-2.0 at source ebf0f43d7c4267876fc256f5fce75982c33f4399;
  https://github.com/astral-sh/uv/tree/ebf0f43d7c4267876fc256f5fce75982c33f4399 .
* esptool5.6.0: GPL-2.0-or-later; the authenticated publisher sdist carries
  LICENSE and headers, retained by the unmodified local setuptools build.
  https://pypi.org/project/esptool/5.6.0/ .
* Other Python packages: exact publisher wheel identities are in
  python-sources.json; their dist-info license/metadata files remain installed
  verbatim. python-requirements.lock pins all57 versions/input hashes. The only
  admitted upstream constraint amendment is cryptography==50.0.0 in place of
  the historical vulnerable range; all other constraint bytes remain unchanged.

The recipe downloads/uses those inputs externally. Redistributing binaries needs
their corresponding notices/source obligations; this lot publishes no toolchain,
SDK, firmware image, Python wheel or component cache.
