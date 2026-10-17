#!/usr/bin/env python3
"""Sample Bay of Palma wind for CAPA (ESP 99) and roll the on-site history.

Stdlib only. Writes:
  site/data/history.json  samples kept for RETENTION_DAYS
  site/data/live.json     current reading plus the last 24 hours

The page loads live.json by a relative URL. Coordinates are the racing area
off Palma, not an onboard sensor.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "site" / "data"
HISTORY_PATH = DATA_DIR / "history.json"
LIVE_PATH = DATA_DIR / "live.json"

LATITUDE = 39.55
LONGITUDE = 2.63
PLACE = "Bahía de Palma"
BOAT = "CAPA"
SAIL_NUMBER = "ESP 99"
SOURCE = "Open-Meteo"
MADRID = ZoneInfo("Europe/Madrid")
RETENTION_DAYS = 7
CHART_HOURS = 24
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

POINTS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


def direction_label(degrees: float) -> str:
    deg = float(degrees) % 360
    index = math.floor(deg / 22.5 + 0.5) % 16
    return POINTS[index]


def one_decimal(value: float) -> float:
    return float(f"{float(value):.1f}")


def as_madrid(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=MADRID)
    return value.astimezone(MADRID)


def stamp(value: datetime) -> str:
    return as_madrid(value).replace(microsecond=0).isoformat(timespec="seconds")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return as_madrid(parsed)


def sample(when: datetime, wind, gust, direction, temp) -> dict | None:
    if None in (wind, gust, direction, temp):
        return None
    moment = as_madrid(when).replace(second=0, microsecond=0)
    direction_value = float(direction) % 360
    return {
        "t": stamp(moment),
        "wind_kt": one_decimal(wind),
        "gust_kt": one_decimal(gust),
        "dir_deg": int(round(direction_value)) % 360,
        "dir": direction_label(direction_value),
        "temp_c": one_decimal(temp),
    }


def fetch_forecast() -> dict:
    query = urllib.parse.urlencode(
        {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "current": ",".join(
                [
                    "temperature_2m",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                ]
            ),
            "wind_speed_unit": "kn",
            "timezone": "Europe/Madrid",
            "forecast_days": 1,
            "past_days": 1,
        }
    )
    request = urllib.request.Request(
        f"{OPEN_METEO}?{query}",
        headers={"User-Agent": "capa-wind/1.0 (ESP 99; Bahia de Palma)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "current" not in payload or "hourly" not in payload:
        raise RuntimeError("Open-Meteo response did not include current and hourly wind")
    return payload


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    samples = payload.get("samples", [])
    if not isinstance(samples, list):
        raise RuntimeError(f"{HISTORY_PATH} does not contain a samples list")
    return samples


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    now = datetime.now(MADRID).replace(second=0, microsecond=0)
    forecast = fetch_forecast()
    current_raw = forecast["current"]
    current = sample(
        now,
        current_raw.get("wind_speed_10m"),
        current_raw.get("wind_gusts_10m"),
        current_raw.get("wind_direction_10m"),
        current_raw.get("temperature_2m"),
    )
    if current is None:
        raise RuntimeError("Open-Meteo current wind reading is incomplete")

    by_time = {item["t"]: item for item in load_history() if isinstance(item, dict) and "t" in item}
    hourly = forecast["hourly"]
    times = hourly.get("time", [])
    for index, raw_time in enumerate(times):
        moment = parse_time(raw_time)
        if moment > now or moment < now - timedelta(hours=CHART_HOURS):
            continue
        point = sample(
            moment,
            hourly["wind_speed_10m"][index],
            hourly["wind_gusts_10m"][index],
            hourly["wind_direction_10m"][index],
            hourly["temperature_2m"][index],
        )
        if point is not None and point["t"] not in by_time:
            by_time[point["t"]] = point

    by_time[current["t"]] = current
    cutoff = now - timedelta(days=RETENTION_DAYS)
    samples = sorted(
        (item for item in by_time.values() if parse_time(item["t"]) >= cutoff),
        key=lambda item: item["t"],
    )
    chart_start = now - timedelta(hours=CHART_HOURS)
    recent = [item for item in samples if parse_time(item["t"]) >= chart_start]

    write_json(
        HISTORY_PATH,
        {
            "boat": BOAT,
            "sail_number": SAIL_NUMBER,
            "place": PLACE,
            "retention_days": RETENTION_DAYS,
            "samples": samples,
        },
    )
    write_json(
        LIVE_PATH,
        {
            "boat": BOAT,
            "sail_number": SAIL_NUMBER,
            "place": PLACE,
            "source": SOURCE,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "updated": stamp(now),
            "current": current,
            "history": recent,
        },
    )
    print(
        f"{current['t']} {current['dir']} wind {current['wind_kt']} kt "
        f"gust {current['gust_kt']} kt {current['temp_c']} C "
        f"({len(recent)} points in 24h, {len(samples)} retained)"
    )


if __name__ == "__main__":
    main()
