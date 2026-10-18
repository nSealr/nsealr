"""Only four read tools promoted. One rejected mutation is a negative probe."""

import asyncio
import json
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from common import runtime, output, digest, require, write_json, now
from kipy import KiCad


async def main():
    base, out = runtime(), output()
    board = out / "fixtures/roundtrip/canary.kicad_pcb"
    before = digest(board)
    socket = "ipc://" + str(base / "runtime/kicad/api.sock")
    direct = KiCad(socket_path=socket, timeout_ms=1000)
    version = {
        "live_version": str(direct.get_version()),
        "binding_api": str(direct.get_api_version()),
    }
    try:
        version["result"] = direct.check_version()
    except Exception as exc:
        version["exception"] = {"type": type(exc).__name__, "message": str(exc)}
    write_json(out / "version-probe.json", version)
    env = dict(
        os.environ,
        KICAD_API_SOCKET=socket,
        KIPILOT_ENABLE_MUTATIONS="false",
        KIPILOT_KICAD_TIMEOUT_MS="5000",
    )
    params = StdioServerParameters(
        command=str(base / "venv/bin/kipilot-mcp"), args=[], env=env
    )
    rows = {"start_utc": now(), "board_before": before, "calls": []}

    async def call(session, name, args):
        result = await session.call_tool(name, args)
        data = result.structuredContent or json.loads(result.content[0].text)
        rows["calls"].append(
            {"name": name, "arguments": args, "isError": result.isError, "data": data}
        )
        return data

    try:
        with (out / "logs/mcp-server.stderr").open("x") as err:
            async with stdio_client(params, errlog=err) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    summary = await call(session, "kicad_get_board_summary", {})
                    require(summary["ok"], "Summary failed")
                    require(
                        Path(summary["board"]["document"]["project"]["path"]).resolve()
                        == board.parent,
                        "Unexpected project",
                    )
                    require(
                        summary["counts"]["footprints"] == 3
                        and summary["counts"]["tracks"] == 13,
                        "Unexpected board geometry",
                    )
                    fps = await call(session, "kicad_get_footprints", {})
                    expected_positions = {
                        "J1": (25, 30),
                        "R1": (35, 32.54),
                        "R2": (40, 32.54),
                    }
                    require(
                        {x["reference"] for x in fps["footprints"]}
                        == set(expected_positions),
                        "Unexpected references",
                    )
                    for f in fps["footprints"]:
                        require(
                            (f["position"]["x_mm"], f["position"]["y_mm"])
                            == expected_positions[f["reference"]],
                            "Wrong coordinate",
                        )
                        require(
                            f["orientation"] == "0deg" and f["layer"] == 3,
                            "Wrong IPC front layer/orientation",
                        )
                    expected = {
                        "J1": {
                            "1": ("/VIN", 25, 30),
                            "2": ("/VOUT", 25, 32.54),
                            "3": ("/GND", 25, 35.08),
                        },
                        "R1": {
                            "1": ("/VIN", 34.0875, 32.54),
                            "2": ("/VOUT", 35.9125, 32.54),
                        },
                        "R2": {
                            "1": ("/VOUT", 39.0875, 32.54),
                            "2": ("/GND", 40.9125, 32.54),
                        },
                    }
                    for ref, mapping in expected.items():
                        pads = await call(session, "kicad_get_pads", {"reference": ref})
                        actual = {
                            p["number"]: (
                                p["net"]["name"],
                                p["position"]["x_mm"],
                                p["position"]["y_mm"],
                            )
                            for p in pads["pads"]
                        }
                        require(actual == mapping, "Pad net/position mismatch")
                        for p in pads["pads"]:
                            layers = {x["name"] for x in p["layers"]}
                            require("F.Cu" in layers, "Missing front copper")
                            require(
                                ("B.Cu" in layers) == (ref == "J1"),
                                "Wrong back layer membership",
                            )
                    texts = await call(session, "kicad_get_board_text", {})
                    require(
                        texts["count"] == 1
                        and texts["text_items"][0]["text"] == "CANARY",
                        "Wrong text",
                    )
                    item = texts["text_items"][0]
                    result = await call(
                        session,
                        "kicad_update_board_text",
                        {
                            "text_id": item["id"],
                            "new_text": "FORBIDDEN",
                            "expected_current_text": "CANARY",
                        },
                    )
                    require(not result["ok"], "Disabled mutation succeeded")
                    after = await call(session, "kicad_get_board_text", {})
                    require(after == texts, "Rejected mutation changed memory")
                    require(digest(board) == before, "Read-only session changed disk")
                    rows["passed"] = True
    finally:
        rows["board_after"] = digest(board)
        rows["end_utc"] = now()
        write_json(out / "mcp-read.json", rows)


asyncio.run(main())
