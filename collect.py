"""
AIS relay collector — runs on GitHub Actions every ~15 min (outside the
corporate firewall, which blocks aisstream.io from the office LAN).

Connects to AISStream.io with the key from the AISSTREAM_KEY secret, listens
~75s for the fleet's 6 MMSIs, merges with the previous positions.json (vessels
silent this window keep their last position), stamps port arrivals, writes
positions.json. The office app pulls the raw file from GitHub.

No scraping anywhere: AISStream is queried with our own API key per their ToS;
GitHub Actions is our own scheduled compute.
"""
import asyncio
import json
import math
import os
import time
from pathlib import Path

FLEET = {
    "538005042": "MUKADDES KALKAVAN",
    "271042759": "NEVZAT KALKAVAN",
    "271043028": "KAAN KALKAVAN",
    "256042000": "EMMA A",
    "565382000": "MELCHIOR SCHULTE",
    "256318000": "SINE A",
}
PORTS = {  # keep in sync with config/vessels_ais.yaml in the app repo
    "NYC": (40.60, -74.05, 20),
    "ORF": (36.95, -76.20, 20),
    "SAV": (32.08, -81.00, 20),
}
BBOX = [[[-5.0, -85.0], [62.0, 45.0]]]       # full lane: US E-coast + N.Atlantic + Med + Turkey
LISTEN_S = 150
OUT = Path(__file__).resolve().parent / "positions.json"


def _dist_nm(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 3440.065 * math.asin(math.sqrt(a))


def _in_port(lat, lon):
    for name, (plat, plon, r) in PORTS.items():
        if _dist_nm(lat, lon, plat, plon) <= r:
            return name
    return None


async def main():
    import websockets
    key = os.environ["AISSTREAM_KEY"]
    positions = {}
    try:
        positions = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        pass

    sub = {"APIKey": key, "BoundingBoxes": BBOX,
           "FiltersShipMMSI": list(FLEET), "FilterMessageTypes": ["PositionReport"]}
    deadline = time.time() + LISTEN_S
    got = 0
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream",
                                      open_timeout=20, ping_interval=20) as ws:
            await ws.send(json.dumps(sub))
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(1, deadline - time.time()))
                except asyncio.TimeoutError:
                    break
                try:
                    msg = json.loads(raw)
                    if msg.get("MessageType") != "PositionReport":
                        continue
                    rep = msg["Message"]["PositionReport"]
                    meta = msg.get("MetaData") or {}
                    mmsi = str(rep.get("UserID") or meta.get("MMSI") or "")
                    if mmsi not in FLEET:
                        continue
                    prev = positions.get(mmsi) or {}
                    rec = {"lat": rep.get("Latitude"), "lon": rep.get("Longitude"),
                           "sog": rep.get("Sog"), "cog": rep.get("Cog"),
                           "name": FLEET[mmsi], "ts": time.time(),
                           "arrived_ts": prev.get("arrived_ts"),
                           "arrived_port": prev.get("arrived_port")}
                    now_port = _in_port(rec["lat"], rec["lon"])
                    if now_port and prev.get("_in_port") != now_port:
                        rec["arrived_ts"] = time.time()
                        rec["arrived_port"] = now_port
                    rec["_in_port"] = now_port
                    positions[mmsi] = rec
                    got += 1
                except Exception:
                    continue
    except Exception as e:
        print(f"stream problem: {e} (keeping previous positions)")

    OUT.write_text(json.dumps(positions, indent=1), encoding="utf-8")
    print(f"updates this window: {got}; vessels in file: {len(positions)}")


if __name__ == "__main__":
    asyncio.run(main())
