#!/usr/bin/env python3
"""Bay of Palma live wind: fetch real observations from public, keyless sources -> site/data/live.json.
Run every ~5 min. Keeps a rolling 12 h history (history.json) so single-reading sources
(Meteoclimatic) also get trends. Never fabricates values: missing/QC-failed -> null.
The Portals AROME block is HD where Open-Meteo returns it, otherwise AROME France, and stops at the last returned hour."""
import json, re, os, sys, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "site", "data")
HIST = os.path.join(HERE, "history.json")
MS2KT, KMH2KT = 1.943844, 1 / 1.852
UTC = timezone.utc
KEEP_H = 12
ARCHIVE_DIR = os.environ.get("OBS_ARCHIVE_DIR", "/workspace/dragon-kb/obs-archive")

STATIONS = [
  {"id": "WC_PORTALS", "name": "Puerto Portals (Weathercloud)", "short": "Puerto Portals", "lat": 39.52968, "lon": 2.56546,
   "kind": "race venue, harbour", "cadence": "~1 min (10-min avg)", "color": "#FFD54F", "priority": True,
   "src": "Weathercloud 0773927031", "link": "https://app.weathercloud.net/rt0773927031"},
  {"id": "WA_RCNP", "name": "Real Club N\u00e1utico de Palma (Windalytics)", "short": "RCN Palma", "lat": 39.566895, "lon": 2.634551,
   "kind": "marina, Palma bay", "cadence": "1 min", "color": "#9575CD",
   "src": "Windalytics rcnp", "link": "https://meteo.windalytics.com/station/rcnp"},
  {"id": "WA_CNCG", "name": "CN Cala Gamba (Windalytics)", "short": "Cala Gamba", "lat": 39.547514, "lon": 2.694319,
   "kind": "marina, Bay of Palma", "cadence": "1 min", "color": "#4DB6AC",
   "src": "Windalytics cncg", "link": "https://meteo.windalytics.com/station/cncg"},
  {"id": "WA_CMSAP", "name": "Can Pastilla CMSAP (Windalytics)", "short": "Can Pastilla", "lat": 39.532245, "lon": 2.716469,
   "kind": "beach club, Can Pastilla", "cadence": "1 min", "color": "#FF8A65",
   "src": "Windalytics cmsap", "link": "https://meteo.windalytics.com/station/cmsap"},
  {"id": "WA_CNARENAL", "name": "Club N\u00e1utico Arenal (Windalytics)", "short": "S'Arenal", "lat": 39.502427, "lon": 2.746801,
   "kind": "marina, S'Arenal", "cadence": "1 min", "color": "#DCE775",
   "src": "Windalytics cnarenal", "link": "https://meteo.windalytics.com/station/cnarenal"},
  {"id": "SOCIB", "name": "Bay of Palma buoy (SOCIB)", "short": "SOCIB buoy", "lat": 39.4929, "lon": 2.7004,
   "kind": "on water", "cadence": "10 min", "color": "#81C784",
   "src": "SOCIB / Puertos del Estado", "link": "https://apps.socib.es/dataviewer/"},
  {"id": "PALMA_PORT", "name": "Palma port tide gauge (Puertos del Estado)", "short": "Palma port", "lat": 39.56015, "lon": 2.63748,
   "kind": "harbour wall", "cadence": "1 min", "color": "#4DD0E1",
   "src": "PORTUS REDMAR 3851", "link": "https://portus.puertos.es/#/"},
  {"id": "LEPA", "name": "Palma airport METAR (LEPA)", "short": "LEPA airport", "lat": 39.5517, "lon": 2.7388,
   "kind": "coast, airport", "cadence": "30 min", "color": "#4FC3F7",
   "src": "aviationweather.gov", "link": "https://aviationweather.gov/data/metar/?ids=LEPA&hours=3"},
  {"id": "MC_CJ", "name": "Palma Ciutat Jardí (Meteoclimatic)", "short": "Ciutat Jardí", "lat": 39.553, "lon": 2.699, "approx": True,
   "kind": "beach, amateur", "cadence": "~10 min", "color": "#CE93D8",
   "src": "Meteoclimatic ESIBA0700000107007A", "link": "https://www.meteoclimatic.net/perfil/ESIBA0700000107007A"},
  {"id": "LESB", "name": "Son Bonet METAR (LESB, inland)", "short": "LESB inland", "lat": 39.5989, "lon": 2.7027,
   "kind": "inland airfield", "cadence": "30 min, daytime", "color": "#BCAAA4",
   "src": "aviationweather.gov", "link": "https://aviationweather.gov/data/metar/?ids=LESB&hours=3"},
  {"id": "DRAGONERA", "name": "Dragonera buoy (Puertos del Estado, offshore)", "short": "Dragonera buoy", "lat": 39.5633, "lon": 2.0967,
   "kind": "offshore, W of bay", "cadence": "1 h", "color": "#F48FB1",
   "src": "PORTUS REDEXT 2820", "link": "https://portus.puertos.es/#/"},
]

def _get(url, data=None, headers=None, timeout=25):
    h = {"User-Agent": "Mozilla/5.0 (CapaWind live; contact via site owner)"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def rnd(x, n=1):
    return None if x is None else round(x, n)

# ---------- sources ----------
SOCIB = ("https://thredds.socib.es/thredds/dodsC/mooring/weather_station/buoy_bahiadepalma-scb_met029/"
         "L1/dep0002_buoy-bahiadepalma_scb-met029_L1_latest.nc")

def fetch_socib(hours=4):
    n = int(re.search(r"time\[time = (\d+)\]", _get(SOCIB + ".dds").decode()).group(1))
    k = hours * 6 + 1; sl = f"%5B{max(0, n-k)}:1:{n-1}%5D"
    vs = ["time", "WIN_SPE", "QC_WIN_SPE", "WIN_SPE_GUS", "QC_WIN_SPE_GUS", "WIN_DIR", "QC_WIN_DIR"]
    txt = _get(SOCIB + ".ascii?" + ",".join(v + sl for v in vs)).decode()
    d = {}
    for v in vs:
        m = re.search(r"^" + v + r"\[\d+\]\s*\n([^\n]+)", txt, re.M)
        d[v] = [float(x) for x in m.group(1).split(",")]
    out = []
    for i, ts in enumerate(d["time"]):
        ok = lambda q: d[q][i] in (1, 2)
        out.append({"t": int(ts),
                    "spd": rnd(d["WIN_SPE"][i] * MS2KT) if ok("QC_WIN_SPE") else None,
                    "gst": rnd(d["WIN_SPE_GUS"][i] * MS2KT) if ok("QC_WIN_SPE_GUS") else None,
                    "dir": d["WIN_DIR"][i] if ok("QC_WIN_DIR") else None})
    return out

PORTUS = "https://portus.puertos.es/portussvr/api/RTData/station/{}?locale=es"

def _portus(sid, params):
    raw = _get(PORTUS.format(sid), data=json.dumps(params).encode(), headers={"Content-Type": "application/json"})
    out = []
    for row in json.loads(raw):
        t = datetime.strptime(row["fecha"][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        vals = {}
        for dd in row["datos"]:
            if dd.get("averia") or dd.get("valor") in (None, ""): continue
            vals[dd["paramEseoo"]] = float(dd["valor"]) / float(dd.get("factor") or 1)
        out.append((int(t.timestamp()), vals))
    out.sort()
    return out

def fetch_palma_port_raw():
    """1-min rows for the last 24 h (archive)."""
    return [{"t": t, "spd": rnd(v["WindSpeed"] * MS2KT) if "WindSpeed" in v else None,
             "gst": rnd(v["WindSpeedMax"] * MS2KT) if "WindSpeedMax" in v else None,
             "dir": v.get("WindDir"), "qc": "portus-rt"} for t, v in _portus(3851, [42, 40, 43, 41])]

def fetch_palma_port(hours=4, raw=None):
    rows = []
    for o in (raw if raw is not None else fetch_palma_port_raw()):
        v = {}
        if o["spd"] is not None: v["WindSpeed"] = o["spd"] / MS2KT
        if o["gst"] is not None: v["WindSpeedMax"] = o["gst"] / MS2KT
        if o["dir"] is not None: v["WindDir"] = o["dir"]
        rows.append((o["t"], v))
    cut = rows[-1][0] - hours * 3600 if rows else 0
    out = []
    # down-sample to 5-min means to keep JSON small (vector-free: scalar mean speed, last dir, max gust)
    buckets = {}
    for t, v in rows:
        if t < cut: continue
        buckets.setdefault(t - t % 300, []).append(v)
    for b in sorted(buckets):
        vs = buckets[b]
        sp = [x["WindSpeed"] for x in vs if "WindSpeed" in x]
        gs = [x["WindSpeedMax"] for x in vs if "WindSpeedMax" in x]
        ds = [x["WindDir"] for x in vs if "WindDir" in x]
        out.append({"t": b + 300 if b + 300 <= rows[-1][0] else rows[-1][0],
                    "spd": rnd(sum(sp) / len(sp) * MS2KT) if sp else None,
                    "gst": rnd(max(gs) * MS2KT) if gs else None,
                    "dir": circmean(ds)})
    return out

def fetch_dragonera(hours=6):
    rows = _portus(2820, [42, 40])
    cut = rows[-1][0] - hours * 3600 if rows else 0
    return [{"t": t, "spd": rnd(v["WindSpeed"] * MS2KT) if "WindSpeed" in v else None, "gst": None,
             "dir": v.get("WindDir")} for t, v in rows if t >= cut]

WC_CODE = "0773927031"

def fetch_weathercloud(code=WC_CODE):
    """Public, anonymous device page JSON (the same /device/values call the public page makes; no login).
    Values in m/s: wspdavg = 10-min mean, wspdhi = gust, wdiravg = mean dir."""
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", "Mozilla/5.0")]
    h = op.open(f"https://app.weathercloud.net/rt{code}", timeout=25).read().decode()
    tok = re.search(r'WEATHERCLOUD_CSRF_TOKEN:"([^"]+)"', h).group(1)
    q = urllib.parse.urlencode({"code": code, "WEATHERCLOUD_CSRF_TOKEN": tok})
    req = urllib.request.Request("https://app.weathercloud.net/device/values?" + q,
                                 headers={"X-Requested-With": "XMLHttpRequest"})
    v = json.loads(op.open(req, timeout=25).read())
    f = lambda k: v.get(k) if isinstance(v.get(k), (int, float)) else None
    return [{"t": int(v["epoch"]),
             "spd": rnd(f("wspdavg") * MS2KT) if f("wspdavg") is not None else None,
             "gst": rnd(f("wspdhi") * MS2KT) if f("wspdhi") is not None else None,
             "dir": f("wdiravg"), "spd_inst": rnd(f("wspd") * MS2KT) if f("wspd") is not None else None,
             "dir_inst": f("wdir"), "temp": f("temp"), "pres": f("bar"), "qc": "raw"}]

WINDALYTICS = "https://meteo.windalytics.com/api/weather_display/{code}/data/latesthour"
# Static app token embedded verbatim in the site's public JS bundle and sent by the page for every
# anonymous visitor (no login, no per-user session). This is the keyless public feed the site serves.
WINDALYTICS_KEY = "1c1eafc81627047d68b8ecaa3e5996d562d95940544d74bd4a95961ef38e9fdf"

def _num(x):
    return x if isinstance(x, (int, float)) else None

def fetch_windalytics(code):
    """Public Windalytics station feed (same /weather_display call the site's JS makes anonymously).
    Wind speeds are already in knots, direction degrees true (wind FROM), temp \u00b0C, pressure hPa.
    Returns the last hour of 1-min readings; archive + history dedupe on timestamp."""
    raw = _get(WINDALYTICS.format(code=code), headers={"X-API-Key": WINDALYTICS_KEY})
    d = (json.loads(raw) or {}).get("data") or {}
    tws, gst, twd = d.get("TWS") or {}, d.get("TWS_GUST") or {}, d.get("TWD") or {}
    temp, pres, tmap = d.get("TEMPERATURE") or {}, d.get("PRESSURE") or {}, d.get("TIME") or {}
    out = []
    for k, tms in tmap.items():
        if not isinstance(tms, (int, float)): continue
        out.append({"t": int(tms / 1000), "spd": rnd(_num(tws.get(k))), "gst": rnd(_num(gst.get(k))),
                    "dir": _num(twd.get(k)), "temp": _num(temp.get(k)), "pres": _num(pres.get(k)), "qc": "raw"})
    # Refine newest sample with the higher-precision LATEST_DATA snapshot (minute arrays are integer-rounded).
    ld = d.get("LATEST_DATA") or {}
    lt = ld.get("TIME")
    if isinstance(lt, (int, float)):
        lp = {"t": int(lt / 1000), "spd": rnd(_num(ld.get("TWS"))), "gst": rnd(_num(ld.get("TWS_GUST"))),
              "dir": _num(ld.get("TWD")), "temp": _num(ld.get("TEMPERATURE")), "pres": _num(ld.get("PRESSURE")), "qc": "raw"}
        out = [o for o in out if o["t"] != lp["t"]] + [lp]
    out.sort(key=lambda o: o["t"])
    return out

METAR = "https://aviationweather.gov/api/data/metar?ids=LEPA,LESB&hours=4&format=json"

def fetch_metar():
    out = {"LEPA": [], "LESB": []}
    for m in json.loads(_get(METAR)):
        sid = m.get("icaoId")
        if sid not in out: continue
        t = datetime.fromisoformat(m["reportTime"].replace("Z", "+00:00"))
        wd = m.get("wdir"); wd = wd if isinstance(wd, (int, float)) else None  # VRB -> null
        out[sid].append({"t": int(t.timestamp()), "spd": m.get("wspd"), "gst": m.get("wgst"), "dir": wd,
                         "raw": m.get("rawOb")})
    for v in out.values(): v.sort(key=lambda o: o["t"])
    return out

MC_URL, MC_ID = "https://www.meteoclimatic.net/feed/rss/ESIBA", "ESIBA0700000107007A"

def fetch_meteoclimatic():
    txt = _get(MC_URL).decode("latin-1")
    m = re.search(r"\[\[<" + MC_ID + r";\(([^)]*)\);\(([^)]*)\);\(([^)]*)\);\(([^)]*)\)", txt)
    i = txt.find(MC_ID); tm = re.search(r"Actualizado: (\d\d-\d\d-\d{4} \d\d:\d\d) UTC", txt[i:])
    w, g, dr = [float(x.replace(",", ".")) for x in m.group(4).split(";")]
    t = datetime.strptime(tm.group(1), "%d-%m-%Y %H:%M").replace(tzinfo=UTC)
    return [{"t": int(t.timestamp()), "spd": None if w < 0 else rnd(w * KMH2KT), "gst": None,
             "gst_day": None if g < 0 else rnd(g * KMH2KT), "dir": None if dr < 0 else dr}]

AROME_URL = ("https://api.open-meteo.com/v1/meteofrance?latitude={lat}&longitude={lon}"
             "&hourly=wind_speed_10m,wind_direction_10m,wind_gusts_10m&models={model}"
             "&wind_speed_unit=kn&timezone=UTC&past_hours={past}&forecast_hours={ahead}")
AROME_HD = "meteofrance_arome_france_hd"
AROME_FR = "meteofrance_arome_france"
AROME_LABEL = {AROME_HD: "AROME HD", AROME_FR: "AROME France"}
AROME_PTS = {"portals": (39.515, 2.565), "buoy": (39.4929, 2.7004)}

def _arome_rows(lat, lon, model, past=24, ahead=48):
    d = json.loads(_get(AROME_URL.format(lat=lat, lon=lon, model=model, past=past, ahead=ahead)))
    h = d["hourly"]
    out = []
    for t, s, g, wd in zip(h["time"], h["wind_speed_10m"], h["wind_gusts_10m"], h["wind_direction_10m"]):
        if s is None and g is None and wd is None:
            continue
        out.append({"t": int(datetime.fromisoformat(t + ":00+00:00").timestamp()),
                    "spd": s, "gst": g, "dir": wd, "model": model})
    return out

def _prefer_hd(hd, fr):
    """HD wins wherever it has speed or direction. France fills hours HD does not return."""
    by = {}
    for row in fr:
        if row.get("spd") is None and row.get("dir") is None:
            continue
        by[row["t"]] = row
    for row in hd:
        if row.get("spd") is None and row.get("dir") is None:
            continue
        by[row["t"]] = row
    return [by[t] for t in sorted(by)]

def _model_segments(hours):
    segs = []
    for p in hours:
        if not segs or segs[-1]["model"] != p["model"]:
            segs.append({"model": p["model"], "label": AROME_LABEL.get(p["model"], p["model"]),
                         "from": p["t"], "to": p["t"], "hours": 1})
        else:
            segs[-1]["to"] = p["t"]
            segs[-1]["hours"] += 1
    return segs

def fetch_arome(now_ts):
    """Portals wind from now through now+48 h. AROME HD first, AROME France only for hours HD lacks.
    Hours the API does not return are left out. portals/buoy keep the past day so history charts can overlay them."""
    la, lo = AROME_PTS["portals"]
    partial = []
    try:
        hd = _arome_rows(la, lo, AROME_HD)
    except Exception as e:
        hd = []
        partial.append(f"HD {type(e).__name__}: {e}"[:160])
    try:
        fr = _arome_rows(la, lo, AROME_FR)
    except Exception as e:
        fr = []
        partial.append(f"France {type(e).__name__}: {e}"[:160])
    portals = _prefer_hd(hd, fr)
    if not portals:
        raise RuntimeError("; ".join(partial) or "no AROME rows")
    bla, blo = AROME_PTS["buoy"]
    try:
        buoy = _arome_rows(bla, blo, AROME_HD)
    except Exception as e:
        buoy = []
        partial.append(f"buoy {type(e).__name__}: {e}"[:160])
    hi = now_ts + 48 * 3600
    hour = now_ts - (now_ts % 3600)
    hd_times = {p["t"] for p in hd if p.get("spd") is not None or p.get("dir") is not None}
    forecast = [p for p in portals if hour <= p["t"] <= hi]
    france_fill = [p for p in fr if hour <= p["t"] <= hi and p["t"] not in hd_times
                   and (p.get("spd") is not None or p.get("dir") is not None)]
    coverage = {
        "place": "Puerto Portals", "lat": la, "lon": lo, "requested_h": 48,
        "from": forecast[0]["t"] if forecast else None,
        "to": forecast[-1]["t"] if forecast else None,
        "hours": len(forecast),
        "span_h": round((forecast[-1]["t"] - now_ts) / 3600, 1) if forecast else 0,
        "segments": _model_segments(forecast),
        "hd_hours": sum(1 for p in forecast if p["model"] == AROME_HD),
        "france_hours": sum(1 for p in forecast if p["model"] == AROME_FR),
        "france_fill_hours": len(france_fill),
    }
    return {"portals": portals, "buoy": buoy,
            "forecast": {"hours": forecast, "coverage": coverage, "partial_errors": partial}}

# ---------- helpers ----------
import math
def circmean(ds):
    ds = [d for d in ds if d is not None]
    if not ds: return None
    s = sum(math.sin(math.radians(d)) for d in ds); c = sum(math.cos(math.radians(d)) for d in ds)
    return round(math.degrees(math.atan2(s, c)) % 360)

def trend(series, now_ts):
    """Compare latest valid reading with the one ~60 min earlier (45-75 min window)."""
    pts = [o for o in series if o.get("spd") is not None]
    if not pts: return None
    last = pts[-1]
    cands = [o for o in pts if 45 * 60 <= last["t"] - o["t"] <= 75 * 60]
    if not cands: return None
    ref = min(cands, key=lambda o: abs(last["t"] - o["t"] - 3600))
    tr = {"mins": round((last["t"] - ref["t"]) / 60), "spd0": ref["spd"], "dspd": rnd(last["spd"] - ref["spd"])}
    if last.get("dir") is not None and ref.get("dir") is not None:
        tr["ddir"] = round((last["dir"] - ref["dir"] + 180) % 360 - 180)
        tr["dir0"] = ref["dir"]
    return tr

def merge(old, new, keep_from):
    by_t = {o["t"]: o for o in old if o["t"] >= keep_from}
    for o in new: by_t[o["t"]] = o
    return [by_t[t] for t in sorted(by_t)]

def main():
    now = datetime.now(UTC); now_ts = int(now.timestamp())
    hist = {}
    if os.path.exists(HIST):
        try: hist = json.load(open(HIST))
        except Exception: hist = {}
    errors, fresh = {}, {}
    raw_arch = {}
    jobs = {"WC_PORTALS": fetch_weathercloud, "SOCIB": fetch_socib, "PALMA_PORT": fetch_palma_port_raw,
            "MC_CJ": fetch_meteoclimatic, "DRAGONERA": fetch_dragonera}
    for wid, wcode in (("WA_RCNP", "rcnp"), ("WA_CNCG", "cncg"), ("WA_CMSAP", "cmsap"), ("WA_CNARENAL", "cnarenal")):
        jobs[wid] = (lambda c: (lambda: fetch_windalytics(c)))(wcode)
    for sid, fn in jobs.items():
        try: fresh[sid] = fn()
        except Exception as e: errors[sid] = f"{type(e).__name__}: {e}"[:200]
    if "PALMA_PORT" in fresh:
        raw_arch["PALMA_PORT"] = fresh["PALMA_PORT"]
        fresh["PALMA_PORT"] = fetch_palma_port(raw=fresh["PALMA_PORT"])
    try: fresh.update(fetch_metar())
    except Exception as e: errors["LEPA"] = errors["LESB"] = f"{type(e).__name__}: {e}"[:200]
    keep_from = now_ts - KEEP_H * 3600
    for sid in [s["id"] for s in STATIONS]:
        hist[sid] = merge(hist.get(sid, []), fresh.get(sid, []), keep_from)
    json.dump(hist, open(HIST, "w"), separators=(",", ":"))
    try: arome = fetch_arome(now_ts)
    except Exception as e: arome = None; errors["AROME"] = f"{type(e).__name__}: {e}"[:200]
    if arome and arome.get("forecast"):
        cov = arome["forecast"]["coverage"]
        print(f'AROME forecast hours={cov["hours"]} span_h={cov["span_h"]} '
              f'hd={cov["hd_hours"]} france={cov["france_hours"]} '
              f'segments={[(s["label"], s["hours"]) for s in cov["segments"]]}')
        if arome["forecast"].get("partial_errors"):
            errors["AROME"] = "; ".join(arome["forecast"]["partial_errors"])[:200]
    if os.path.isdir(ARCHIVE_DIR):
      try:
        sys.path.insert(0, ARCHIVE_DIR); import archive
        archive.store(STATIONS, {**fresh, **raw_arch}, arome, now_ts, errors)
      except Exception as e:
        errors["ARCHIVE"] = f"{type(e).__name__}: {e}"[:200]
    stale_limit = {"WC_PORTALS": 30, "SOCIB": 90, "PALMA_PORT": 30, "LEPA": 75, "LESB": 120, "MC_CJ": 60, "DRAGONERA": 150,
                   "WA_RCNP": 30, "WA_CNCG": 30, "WA_CMSAP": 30, "WA_CNARENAL": 30}
    stations = []
    for s in STATIONS:
        ser = hist.get(s["id"], [])
        valid = [o for o in ser if o.get("spd") is not None]
        last = valid[-1] if valid else None
        age = round((now_ts - last["t"]) / 60) if last else None
        status = "ok" if last and age <= stale_limit[s["id"]] else ("stale" if last else "n/a")
        stations.append({**s, "status": status, "age_min": age, "last": last,
                         "trend": trend(ser, now_ts) if status != "n/a" else None,
                         "series": [o for o in ser if o["t"] >= now_ts - KEEP_H * 3600 - 600],
                         "error": errors.get(s["id"])})
    out = {"generated": now_ts, "generated_iso": now.isoformat(timespec="seconds"),
           "units": {"speed": "kt", "direction": "degrees true, wind FROM", "time": "unix s (UTC)"},
           "stations": stations, "arome": arome, "errors": errors}
    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = os.path.join(OUT_DIR, "live.json.tmp")
    json.dump(out, open(tmp, "w"), separators=(",", ":"))
    os.replace(tmp, os.path.join(OUT_DIR, "live.json"))
    for st in stations:
        l = st["last"]
        print(f'{st["id"]:11s} {st["status"]:5s} age={st["age_min"]}min', 
              (f'{l["spd"]} kt G{l.get("gst")} {l.get("dir")}°' if l else "-"), "trend", st["trend"], st["error"] or "")
    if errors: print("errors:", errors, file=sys.stderr)

if __name__ == "__main__":
    main()
