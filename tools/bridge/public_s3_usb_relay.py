#!/usr/bin/env python3
"""Root-only PUBLIC S3 byte relay on the USB Mac. No nSealr parsing or signing."""
import argparse
import datetime
import json
import os
from pathlib import Path
import select
import socket
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--socket", required=True)
    p.add_argument("--capture-dir", required=True)
    a = p.parse_args()
    endpoint = Path(a.socket)
    if not endpoint.name.startswith("nsealr-s3-public-") or endpoint.suffix != ".sock":
        p.error("use a new named nsealr-s3-public-*.sock")
    if endpoint.exists():
        p.error("socket path exists; inspect the old owner, never clobber it")
    capture = Path(a.capture_dir)
    capture.mkdir(mode=0o700, parents=False, exist_ok=False)
    import serial  # Existing isolated root pyserial environment; no install here.
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    owned = None
    report = {"scope": "public scalar3 raw lab plumbing only", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "usb_opened": False, "rx_bytes": 0, "tx_bytes": 0, "reason": "not-started"}
    try:
        listener.bind(str(endpoint))
        os.chmod(endpoint, 0o600)
        owned = endpoint.stat()
        listener.listen(1)
        listener.settimeout(120)
        print(json.dumps({"relay_socket_ready": str(endpoint), "usb_opened": False}), flush=True)
        conn, _ = listener.accept()  # One client, no reconnection loop.
        with conn, serial.Serial(a.port, baudrate=115200, timeout=0, write_timeout=1, exclusive=True) as usb, \
             (capture / "usb-rx.raw").open("xb") as rx, (capture / "usb-tx.raw").open("xb") as tx:
            conn.settimeout(1)
            usb.dtr = True
            report["usb_opened"] = True
            conn.sendall(b"nsealr-public-usb-open-v1\n")  # Private plumbing header, never sent to S3.
            print(json.dumps({"usb_handle_open": True, "scope": "Enable locally; host Enter only starts transmission"}), flush=True)
            until = time.monotonic() + 180  # Separate setup/lease ceiling, not a signer deadline.
            while time.monotonic() < until:
                ready, _, _ = select.select([conn, usb.fileno()], [], [], min(.05, max(0, until-time.monotonic())))
                if conn in ready:
                    data = conn.recv(1024)
                    if not data:
                        report["reason"] = "stream-EOF"
                        break
                    report["tx_bytes"] += len(data)
                    if report["tx_bytes"] > 65536:
                        raise ValueError("finite TX budget exceeded")
                    tx.write(data); tx.flush()
                    if usb.write(data) != len(data):
                        raise OSError("partial USB write; no retry")
                if usb.fileno() in ready:
                    data = usb.read(1024)
                    if data:
                        report["rx_bytes"] += len(data)
                        if report["rx_bytes"] > 65536:
                            raise ValueError("finite RX budget exceeded")
                        rx.write(data); rx.flush()
                        conn.sendall(data)
            else:
                report["reason"] = "lease-wall-expired"
        report["usb_close_returned"] = True
    except BaseException as error:
        report["reason"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        listener.close()
        if owned is not None:
            try:
                current = endpoint.stat()
                if (owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino):
                    endpoint.unlink()
            except FileNotFoundError:
                pass
        report["ended_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (capture / "relay.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
