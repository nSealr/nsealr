#!/usr/bin/env python3
"""Optional Chromium-family smoke for the packaged browser extension."""

from __future__ import annotations

import argparse
import http.server
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

try:
    from scripts.browser_integration_support import (
        build_browser_package_build_command,
        build_browser_package_plan_command,
        build_browser_package_verify_command,
        build_browser_route_config_approval_command,
        build_browser_route_config_review_command,
        run_json_command,
    )
    from scripts.integration_support import build_pnpm_workspace, install_pnpm_workspace
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from browser_integration_support import (
        build_browser_package_build_command,
        build_browser_package_plan_command,
        build_browser_package_verify_command,
        build_browser_route_config_approval_command,
        build_browser_route_config_review_command,
        run_json_command,
    )
    from integration_support import build_pnpm_workspace, install_pnpm_workspace


ROOT = Path(__file__).resolve().parents[1]
ORG = ROOT.parent
COMPANION = ORG / "companion"
SMOKE_FORMAT = "nsealr-browser-extension-chromium-smoke-v0"
LOCAL_PAIRING_DIGEST = "a" * 64
ROUTE_ACCOUNT_ID = "esp32-usb-slot-0"
ROUTE_TYPE = "esp32_usb_nip46"
PROVIDER_INJECTED_TITLE = "nsealr-provider-injected"
PROVIDER_DENIED_TITLE = "nsealr-provider-denied"


def probe_page_html() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>nsealr-provider-pending</title>
  <script>
    async function checkProvider() {
      const ok = Boolean(
        window.nostr &&
        typeof window.nostr.getPublicKey === "function" &&
        typeof window.nostr.signEvent === "function"
      );
      if (!ok) {
        document.title = "nsealr-provider-missing";
        document.body.textContent = document.title;
        return;
      }
      document.title = "nsealr-provider-injected";
      try {
        await window.nostr.getPublicKey();
        document.title = "nsealr-provider-unexpected-success";
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        document.title = message.includes("origin permission denied")
          ? "nsealr-provider-denied"
          : "nsealr-provider-error-" + message.replace(/[^a-z0-9]+/gi, "-").slice(0, 80);
      }
      document.body.textContent = document.title;
    }
    setTimeout(checkProvider, 1200);
  </script>
</head>
<body>pending</body>
</html>
"""


def local_content_script_match(port: int) -> str:
    if port < 1 or port > 65535:
        raise ValueError("local smoke server port is invalid")
    return f"http://127.0.0.1:{port}/*"


def resolve_chromium_browser(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return path
        raise RuntimeError(f"explicit Chromium-family browser path is not executable: {path}")

    candidates = [
        os.environ.get("NSEALR_CHROMIUM_BROWSER"),
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("brave-browser"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.exists() and path.is_file() and os.access(path, os.X_OK):
            return path
    raise RuntimeError(
        "no Chromium-family browser found; set NSEALR_CHROMIUM_BROWSER or pass --browser"
    )


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        return


def start_probe_server(site_dir: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    def handler(*args: Any, **kwargs: Any) -> QuietHandler:
        return QuietHandler(*args, directory=str(site_dir), **kwargs)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    return server, int(server.server_address[1])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def require_new_json_output_path(path: Path) -> Path:
    output = path.expanduser()
    if output.exists():
        raise RuntimeError(f"browser-extension Chromium smoke output already exists: {output}")
    return output


def write_json_new(path: Path, payload: dict[str, Any]) -> None:
    output = require_new_json_output_path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")


def build_extension_package(temp: Path, content_script_match: str) -> dict[str, Any]:
    install_pnpm_workspace(COMPANION)
    build_pnpm_workspace(COMPANION)
    package_plan_review = run_json_command(build_browser_package_plan_command(
        companion=COMPANION,
        target="chromium",
        content_script_match=content_script_match,
        origin_permission_mode="extension-storage",
        review=True,
    ))
    package_plan_review_path = temp / "package-plan-review.json"
    write_json(package_plan_review_path, package_plan_review)
    route_config_review = run_json_command(build_browser_route_config_review_command(
        companion=COMPANION,
        route_account_id=ROUTE_ACCOUNT_ID,
        route_type=ROUTE_TYPE,
    ))
    route_config_review_path = temp / "route-config-review.json"
    write_json(route_config_review_path, route_config_review)
    route_config_approval = run_json_command(build_browser_route_config_approval_command(
        companion=COMPANION,
        review_path=route_config_review_path,
        route_config_digest=str(route_config_review["route_config_digest"]),
        approved_at=1_900_000_000,
    ))
    route_config_approval_path = temp / "route-config-approval.json"
    write_json(route_config_approval_path, route_config_approval)
    package_result = run_json_command(build_browser_package_build_command(
        companion=COMPANION,
        target="chromium",
        out_dir=temp / "extension",
        package_plan_review=package_plan_review_path,
        route_account_id=ROUTE_ACCOUNT_ID,
        route_type=ROUTE_TYPE,
        route_config_approval=route_config_approval_path,
        content_script_match=content_script_match,
        origin_permission_mode="extension-storage",
        local_pairing_digest=LOCAL_PAIRING_DIGEST,
    ))
    package_result_path = temp / "package-build-result.json"
    write_json(package_result_path, package_result)
    verified_result = run_json_command(build_browser_package_verify_command(
        companion=COMPANION,
        build_result=package_result_path,
        package_plan_review=package_plan_review_path,
    ))
    if verified_result != package_result:
        raise RuntimeError("browser-extension package verifier output drifted before smoke load")
    return package_result


def reserve_tcp_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, *, method: str = "GET", timeout: float = 1.0) -> Any:
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def process_output(process: subprocess.Popen[str]) -> str:
    try:
        stdout, stderr = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        return ""
    return f"{stdout}\n{stderr}".strip()


def wait_for_devtools(base_url: str, process: subprocess.Popen[str], deadline: float) -> None:
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Chromium exited before DevTools was ready: {process_output(process)}")
        try:
            http_json(f"{base_url}/json/version", timeout=0.5)
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("Chromium DevTools endpoint did not become ready")


def open_probe_tab(base_url: str, url: str) -> None:
    encoded_url = urllib.parse.quote(url, safe=":/?&=%")
    http_json(f"{base_url}/json/new?{encoded_url}", method="PUT", timeout=2.0)


def wait_for_provider_title(
    base_url: str,
    page_url: str,
    process: subprocess.Popen[str],
    deadline: float,
) -> str:
    last_title = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Chromium exited during smoke: {process_output(process)}")
        tabs = http_json(f"{base_url}/json/list", timeout=1.0)
        if isinstance(tabs, list):
            for tab in tabs:
                if isinstance(tab, dict) and tab.get("url") == page_url:
                    last_title = str(tab.get("title", ""))
                    if last_title == PROVIDER_DENIED_TITLE:
                        return last_title
        time.sleep(0.25)
    raise RuntimeError(f"browser extension provider gate did not deny as expected; last page title: {last_title!r}")


def run_smoke(browser: Path, timeout_seconds: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nsealr-chromium-smoke-") as temp_root:
        temp = Path(temp_root)
        site_dir = temp / "site"
        site_dir.mkdir()
        (site_dir / "index.html").write_text(probe_page_html(), encoding="utf-8")
        server, server_port = start_probe_server(site_dir)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        content_script_match = local_content_script_match(server_port)
        package_result = build_extension_package(temp, content_script_match)
        extension_dir = Path(str(package_result["out_dir"]))
        debug_port = reserve_tcp_port()
        profile_dir = temp / "profile"
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                [
                    str(browser),
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-background-networking",
                    f"--user-data-dir={profile_dir}",
                    f"--disable-extensions-except={extension_dir}",
                    f"--load-extension={extension_dir}",
                    f"--remote-debugging-port={debug_port}",
                    "about:blank",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + timeout_seconds
            devtools_base = f"http://127.0.0.1:{debug_port}"
            page_url = f"http://127.0.0.1:{server_port}/index.html"
            wait_for_devtools(devtools_base, process, deadline)
            open_probe_tab(devtools_base, page_url)
            title = wait_for_provider_title(devtools_base, page_url, process, deadline)
            browser_version = subprocess.check_output([str(browser), "--version"], text=True).strip()
            return {
                "format": SMOKE_FORMAT,
                "browser": browser_version,
                "page_url": page_url,
                "content_script_match": content_script_match,
                "provider_injected": title == PROVIDER_DENIED_TITLE,
                "get_public_key_denied_before_native_host": title == PROVIDER_DENIED_TITLE,
                "package_format": package_result["format"],
                "manifest_permissions": package_result["manifest_permissions"],
                "origin_permission_mode": package_result["origin_permission_mode"],
                "native_host_name": package_result["native_host_name"],
                "stores_production_secrets": package_result["stores_production_secrets"],
                "dispatches_signers": package_result["dispatches_signers"],
                "files": [item["path"] for item in package_result["files"]],
            }
        finally:
            server.shutdown()
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and load the nSealr browser-extension developer artifact in a Chromium-family browser."
    )
    parser.add_argument("--browser", help="path to Chromium/Chrome/Brave executable")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--out", type=Path, help="optional path for a JSON smoke report; refuses existing files")
    args = parser.parse_args()
    try:
        output_path = require_new_json_output_path(args.out) if args.out is not None else None
        browser = resolve_chromium_browser(args.browser)
        result = run_smoke(browser, args.timeout_seconds)
        if output_path is not None:
            write_json_new(output_path, result)
    except RuntimeError as error:
        parser.exit(1, f"error: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
