#!/usr/bin/env python3
"""Preserve a failed SD data transaction across the required cache synchronization."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_SHA256 = "fe02408164a826eeeacb463d38730741b2a3675cb1fd9afcc11cabe264914a2c"
BEFORE = """        ret = esp_cache_msync((void *)cmdinfo->data, cache_sync_len, ESP_CACHE_MSYNC_FLAG_DIR_M2C);
        if (ret != ESP_OK) {
            goto out;
        }"""
AFTER = """        // nSealr: synchronization must not hide a failed data transaction.
        esp_err_t sync_ret = esp_cache_msync((void *)cmdinfo->data, cache_sync_len, ESP_CACHE_MSYNC_FLAG_DIR_M2C);
        if (ret == ESP_OK) {
            ret = sync_ret;
        }
        if (ret != ESP_OK) {
            goto out;
        }"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise SystemExit("SD driver source changed; review its transaction and cache error handling")
    text = source.decode()
    if text.count(BEFORE) != 1:
        raise SystemExit("Expected exactly one admitted SD cache-sync block")
    patched = text.replace(BEFORE, AFTER).encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(json.dumps({"input_sha256": SOURCE_SHA256,
                      "patched_sha256": hashlib.sha256(patched).hexdigest()}))


if __name__ == "__main__":
    main()
