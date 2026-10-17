#!/usr/bin/env python3
"""Capa race-strategist forecast brief. Pure stdlib.
Usage: python3 forecast_brief.py [--out site/data/forecast.json] [--analogs analogs.json] [--clim results.json] [--input saved_raw.json]
Fetches AROME (Open-Meteo /v1/meteofrance; HD for wind, AROME France for temp/cloud/pressure and to fill), land temperature
inland of Palma, sea-surface temperature (Open-Meteo marine), then applies the decision rules in KNOWLEDGE.md section 6.
Every number in the output is either a model value, a value computed from the local archive (analogs.json / results.json), or a
value from Capa's tuning table. Rules that are inference are labelled 'basis': 'inference'."""
import json, math, os, sys, urllib.request
from datetime import datetime, timezone, timedelta

PORTALS = (39.515, 2.565)          # race-area AROME point, same as fetch_data.py
LAND = (39.60, 2.70)               # Palma basin inland point (AROME elevation 40 m) for land-sea contrast
SEA = (39.50, 2.60)                # Bay of Palma SST point (Open-Meteo marine)
COAST_OFFSHORE_FROM = 20           # Bay of Palma north shore faces ~SSW; wind FROM ~20 deg is straight offshore (map inference)
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "capa-wind-forecast/1.0"}
COMPASS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]

# ---------------- helpers
def compass(d): return None if d is None else COMPASS[int((d % 360) / 22.5 + 0.5) % 16]
def circ_mean(ds):
    ds = [d for d in ds if d is not None]
    if not ds: return None
    s = sum(math.sin(math.radians(d)) for d in ds); c = sum(math.cos(math.radians(d)) for d in ds)
    return round((math.degrees(math.atan2(s, c)) + 360) % 360, 1)
def ddiff(a, b): return (a - b + 180) % 360 - 180          # + = a is clockwise (veered) from b
def mean(xs):
    xs = [x for x in xs if x is not None]; return sum(xs) / len(xs) if xs else None
def rnd(x, n=1): return None if x is None else round(x, n)
def speed_band(s):
    if s is None: return None
    return "0-6" if s < 6 else "6-10" if s < 10 else "10-15" if s < 15 else "15-20" if s < 20 else "20+"
def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r: return json.loads(r.read())

REGIMES = {
 "LIGHT":     {"name": "Light / variable", "clim_key": "Light/variable (<4 kt)", "color": "#8FA8C4"},
 "EMBAT":     {"name": "Sea breeze (Embat, S-SW)", "clim_key": "Sea breeze (Embat, S-SW)", "color": "#4CAF7D"},
 "NORTH":     {"name": "Northerly (Tramuntana / Mestral)", "clim_key": "Northerly (NW-N-NNE, Tramuntana/Mestral)", "color": "#64B5F6"},
 "NE_E":      {"name": "NE-E (Gregal / Llevant)", "clim_key": "NE-E (Gregal/Llevant)", "color": "#BA68C8"},
 "SOUTH_SYN": {"name": "Synoptic S-SE-SW (Xaloc / Migjorn / Llebeig)", "clim_key": "Synoptic S-SE-SW (Xaloc/Migjorn)", "color": "#F2C14E"},
 "WEST":      {"name": "W-WNW (Ponent)", "clim_key": "W-WNW (Ponent)", "color": "#E57373"},
}

# ---------------- rule R1: regime (identical thresholds to climatology/analyse.py so analogs are like-for-like)
def classify_regime(rows):
    """rows: [{'h':hour Madrid,'spd','gst','dir'}]. Window 11-16 h, morning 07-10 h."""
    win = [r for r in rows if 11 <= r["h"] <= 16 and r.get("spd") is not None]
    mor = [r for r in rows if 7 <= r["h"] < 10 and r.get("spd") is not None]
    if not win: return {"code": None, "why": "no 11-16 h data"}
    sp = mean([r["spd"] for r in win]); di = circ_mean([r["dir"] for r in win])
    md = circ_mean([r["dir"] for r in mor]) if mor else None; ms = mean([r["spd"] for r in mor]) if mor else None
    why = f"11-16 h mean {sp:.1f} kt from {di:.0f}°" + (f"; 07-10 h {ms:.1f} kt from {md:.0f}°" if md is not None else "")
    if sp < 4: code = "LIGHT"
    elif 150 <= di <= 250 and md is not None and (md >= 290 or md <= 90 or ms < 4) and sp < 16: code = "EMBAT"
    elif di >= 290 or di < 45: code = "NORTH"
    elif di < 120: code = "NE_E"
    elif di < 250: code = "SOUTH_SYN"
    else: code = "WEST"
    return {"code": code, "why": why, "mean_spd": round(sp, 1), "mean_dir": di, "morning_dir": md, "morning_spd": rnd(ms)}

# ---------------- fetch
def fetch(day_count=2):
    base = "https://api.open-meteo.com/v1/meteofrance?latitude={}&longitude={}&timezone=Europe%2FMadrid&forecast_days={}&wind_speed_unit=kn"
    v = "wind_speed_10m,wind_gusts_10m,wind_direction_10m,temperature_2m,cloud_cover,pressure_msl"
    p = _get(base.format(*PORTALS, day_count) + f"&hourly={v}&models=meteofrance_arome_france_hd,meteofrance_arome_france")
    land = _get(base.format(*LAND, day_count) + "&hourly=temperature_2m&models=meteofrance_arome_france")
    try:
        sea = _get(f"https://marine-api.open-meteo.com/v1/marine?latitude={SEA[0]}&longitude={SEA[1]}&hourly=sea_surface_temperature&timezone=Europe%2FMadrid&forecast_days={day_count}")
    except Exception as e:
        sea = {"error": str(e)}
    return {"portals": p, "land": land, "sea": sea, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}

def build_rows(raw):
    h = raw["portals"]["hourly"]; lt = dict(zip(raw["land"]["hourly"]["time"], raw["land"]["hourly"]["temperature_2m"]))
    sst = {}
    if "hourly" in raw.get("sea", {}): sst = dict(zip(raw["sea"]["hourly"]["time"], raw["sea"]["hourly"]["sea_surface_temperature"]))
    def pick(k, i, prefer="hd"):
        a = h.get(f"{k}_meteofrance_arome_france_hd", [None]*len(h["time"]))[i]; b = h.get(f"{k}_meteofrance_arome_france", [None]*len(h["time"]))[i]
        return (a, "AROME HD") if a is not None else (b, "AROME France") if b is not None else (None, None)
    days = {}
    for i, t in enumerate(h["time"]):
        spd, src = pick("wind_speed_10m", i); gst, _ = pick("wind_gusts_10m", i); d, _ = pick("wind_direction_10m", i)
        fr_s = h.get("wind_speed_10m_meteofrance_arome_france", [None]*len(h["time"]))[i]
        fr_d = h.get("wind_direction_10m_meteofrance_arome_france", [None]*len(h["time"]))[i]
        days.setdefault(t[:10], []).append({"time": t[11:16], "h": int(t[11:13]), "spd": spd, "gst": gst, "dir": d, "compass": compass(d),
            "temp": pick("temperature_2m", i)[0], "cloud": pick("cloud_cover", i)[0], "pmsl": pick("pressure_msl", i)[0],
            "land_t": lt.get(t), "sst": sst.get(t), "src": src, "fr_spd": fr_s, "fr_dir": fr_d})
    return days

# ---------------- decision rules
def load_json(p):
    try: return json.load(open(p))
    except Exception: return None

def rule_flags(rows, reg):
    """R2 transition, R3 front/instability, R4 sea-breeze potential, R5 stability over water."""
    win = [r for r in rows if 11 <= r["h"] <= 16 and r["spd"] is not None]
    f = {}
    dirs = [(r["h"], r["dir"], r["spd"]) for r in win if r["spd"] >= 4]
    f["dir_11"] = next((d for h, d, s in dirs if h == 11), None); f["dir_16"] = next((d for h, d, s in reversed(dirs) if h == 16), None)
    if len(dirs) >= 2:
        f["dir_change_race"] = round(ddiff(dirs[-1][1], dirs[0][1]))
        steps = [abs(ddiff(dirs[i+1][1], dirs[i][1])) for i in range(len(dirs)-1)]; f["max_hourly_step"] = round(max(steps))
    sp = [r["spd"] for r in win]; f["spd_min"] = rnd(min(sp)) if sp else None; f["spd_max"] = rnd(max(sp)) if sp else None
    f["spd_trend"] = rnd(win[-1]["spd"] - win[0]["spd"]) if len(win) >= 2 else None
    # R2 transition: big direction change, or any race hour < 4 kt while others >= 6
    f["transition"] = bool((abs(f.get("dir_change_race") or 0) >= 60) or (f.get("max_hourly_step") or 0) >= 45 or
                           (sp and min(sp) < 4 and max(sp) >= 6))
    # R3 front / pressure tendency
    pm = [r["pmsl"] for r in rows if r["pmsl"] is not None and 8 <= r["h"] <= 18]
    f["pmsl_change_8_18"] = rnd(pm[-1] - pm[0]) if len(pm) >= 2 else None
    gf = [r["gst"] / r["spd"] for r in win if r["gst"] and r["spd"] and r["spd"] >= 6]
    f["arome_gust_factor"] = rnd(mean(gf), 2)
    f["front_risk"] = bool((f["pmsl_change_8_18"] is not None and abs(f["pmsl_change_8_18"]) >= 3) or (f["arome_gust_factor"] or 0) >= 1.6)
    # R4 sea-breeze potential (Biggs & Graves 1962 style index; threshold ~3 from lake-breeze literature, NOT calibrated for Palma)
    lt = [r["land_t"] for r in rows if 12 <= r["h"] <= 15 and r["land_t"] is not None]
    ss = [r["sst"] for r in rows if 10 <= r["h"] <= 16 and r["sst"] is not None]
    f["land_tmax_12_15"] = rnd(max(lt)) if lt else None; f["sst"] = rnd(mean(ss)) if ss else None
    f["dT_land_sea"] = rnd(f["land_tmax_12_15"] - f["sst"]) if lt and ss else None
    mo = [r for r in rows if 9 <= r["h"] <= 11 and r["spd"] is not None]
    off = mean([max(0.0, r["spd"] * math.cos(math.radians(ddiff(r["dir"], COAST_OFFSHORE_FROM)))) for r in mo]) if mo else None
    f["offshore_component_09_11_kt"] = rnd(off)
    if f["dT_land_sea"] is not None and off is not None:
        if f["dT_land_sea"] <= 0: f["sb_index"] = None; f["sea_breeze_potential"] = "none (land not warmer than sea)"
        else:
            u = off * 0.5144; eps = u * u / (1003 * f["dT_land_sea"]) * 1000  # scaled: see KNOWLEDGE 6.R4
            f["sb_index"] = rnd(eps, 2)
            f["sea_breeze_potential"] = ("good" if f["dT_land_sea"] >= 3 and off < 6 else "marginal" if f["dT_land_sea"] >= 1.5 and off < 10 else "poor")
    else: f["sea_breeze_potential"] = "unknown"
    # R5 stability: air colder than sea -> unstable, gustier / puffier; air warmer -> stable, smoother, more shear
    at = mean([r["temp"] for r in win]); f["air_minus_sea"] = rnd(at - f["sst"]) if at is not None and f["sst"] is not None else None
    f["stability"] = None if f["air_minus_sea"] is None else ("unstable (air colder than sea)" if f["air_minus_sea"] <= -2 else
                      "stable (air warmer than sea)" if f["air_minus_sea"] >= 1 else "near-neutral")
    cl = [r["cloud"] for r in win if r["cloud"] is not None]; f["cloud_mean_race"] = rnd(mean(cl), 0)
    return f

def analog(analogs, code, band):
    if not analogs: return None, None
    k = f"{code}|{band}"; a = analogs["by_regime_band"].get(k)
    if a and (a.get("buoy_spd") or {}).get("n", 0) >= 8: return a, f"{REGIMES[code]['name']}, AROME {band} kt"
    return analogs["by_regime"].get(code), f"{REGIMES[code]['name']} (all speeds; fewer than 8 buoy days in the {band} kt band)"

TUNING = [  # PLIS_PLAY_TUNING_TABLE.md (North Dec 2024, corrected by Carlos 2026-10-16) + genoa per North speed guide (playbook §4)
 ("0-6", 123.0, 14, "loose", "V-6M"), ("6-10", 123.0, 16, 9, "V-6M"), ("10-15", 122.5, 18, 10, "V-6M"),
 ("15-20", 122.0, 20, 12, "V-6H"), ("20+", 121.5, 24, 14, "V-6H")]

def rig(lo, hi):
    order = [t[0] for t in TUNING]
    i0, i1 = order.index(speed_band(lo)), order.index(speed_band(hi)); bands = order[i0:i1 + 1]
    out = [{"band": b, "rake_cm": t[1], "uppers_V": t[2], "lowers_D": t[3], "genoa": t[4]} for t in TUNING for b in bands if t[0] == b]
    notes = ["Runner (burda): Gold Cup notes say mostly ~45-60 % of the scale; ease in lulls/chop, max in the top of the range.",
             "Rake used at the Gold Cup: 122.5 (max loose), 122.0, 121.5 (windiest days).",
             "Gold Cup shroud extremes: max tight 20 V / 12 D, max loose 14-15 V / 7-8 D."]
    if hi is not None and 14 <= hi <= 18: notes.append("Top of range is in North's V-6M/V-6H overlap (14-18 kt): decide on trend and sea state.")
    return {"settings": out, "notes": notes, "source": "PLIS_PLAY_TUNING_TABLE.md; DRAGON_COACH.md Gold Cup notes; North Sails Dragon speed guide"}

def strategy(code, f, shift_clim, trend_split, regime_trend_clim):
    """R6 shift pattern, R7 favoured side, start/mark notes."""
    ch = f.get("dir_change_race")
    s = {}
    if f["transition"]:
        s["pattern"] = "transition"; s["text"] = (f"AROME has the wind changing character during racing (direction change {ch:+d}° 11→16 h, max hourly step {f.get('max_hourly_step')}°)."
            " Treat as a transition day: new wind arrives from one side, expect a postponement or a big one-way shift.")
    elif ch is not None and abs(ch) >= 15:
        s["pattern"] = "persistent " + ("veer (right)" if ch > 0 else "back (left)")
        s["text"] = f"AROME trends {abs(ch)}° {'right (veer)' if ch>0 else 'left (back)'} from 11 to 16 h: play it as persistent, sail the headed tack first toward the new wind, don't overstand."
    else:
        s["pattern"] = "oscillating"
        if shift_clim: s["text"] = (f"AROME is steady (≤15° over the race window). Climatology for this regime at the buoy: shift std {shift_clim['std']}°, "
                                   f"peak-to-peak {shift_clim['p2p']}°, cycle ~{shift_clim['period']:.0f} min. Tack on headers vs the median heading.")
        else: s["text"] = "AROME is steady (≤15° over the race window): play oscillations, tack on headers."
    # bias from history
    if trend_split and trend_split["veer"] >= trend_split["back"] + 15: s["history_bias"] = f"History leans VEER: {trend_split['veer']}% of analog days veered >5° 11→15 h, {trend_split['back']}% backed."
    elif trend_split and trend_split["back"] >= trend_split["veer"] + 15: s["history_bias"] = f"History leans BACK: {trend_split['back']}% of analog days backed >5° 11→15 h, {trend_split['veer']}% veered."
    elif trend_split: s["history_bias"] = f"History has no clear lean: veer {trend_split['veer']}% / back {trend_split['back']}% / steady {trend_split['steady']}%."
    # favoured side
    lean = (ch or 0) if s["pattern"].startswith("persistent") else 0
    if lean == 0 and trend_split:
        lean = 5 if trend_split["veer"] >= trend_split["back"] + 15 else -5 if trend_split["back"] >= trend_split["veer"] + 15 else 0
    side = "right" if lean > 0 else "left" if lean < 0 else "middle"
    geo = {
     "EMBAT": "Embat fills from the SW across the bay; the Portals/Illetes shore is to the right (north/west) of a SW beat. (inference, verify on the water)",
     "NORTH": "Offshore wind: puffs come off the Serra/Na Burgesa valleys in streaks; look upwind for dark patches, expect more pressure and bigger shifts nearer the shore. (inference)",
     "NE_E": "NE-E crosses the whole bay from the Arenal side: the east of the bay gets it first, and the wind is more steady at sea. (inference)",
     "SOUTH_SYN": "Onshore synoptic wind with fetch: chop builds, little geographic shift except near the shore. (inference)",
     "WEST": "W-WNW comes over the Calvià/Portals headland: expect wind shadows and bends near the shore, steadier outside. (inference)",
     "LIGHT": "Light day: pressure beats shifts; go where there is visible wind, keep the boat moving."}.get(code, "")
    s["favoured_side"] = side; s["side_text"] = (f"Favoured side: {side.upper()}." + (" " + geo if geo else "")) 
    pat = s["pattern"]
    if pat == "transition":
        s["start"] = "Transition: delay committing. In the sequence watch the new wind's side (webcams/stations upwind); start at the end nearer it and keep clear air to tack."
        s["windward_mark"] = "Don't take a layline early; the mark can swing a long way. Stay between the fleet and the new wind."
        return s
    s["start"] = ("Check line bias with transits several times; in a persistent shift start at the end nearer the new wind, even if it is slightly unfavoured. "
                  "In oscillations, start where you can tack onto the lifted tack freely.") if side != "middle" else (
                  "Pick the favoured end by bias at the gun; keep the option to tack. Middle-of-line starts reduce risk in oscillating wind.")
    s["windward_mark"] = ("Expected drift to the " + side + (" (persistent)" if pat.startswith("persistent") else " (history lean, oscillating)") + ": approach on the tack that keeps you inside the shift, and tack short of the layline (it moves)."
                          if side != "middle" else "Oscillating: avoid early laylines; come in on the lifted tack from the middle.")
    return s

def confidence(rows, reg, f, skill, a):
    win = [r for r in rows if 11 <= r["h"] <= 16 and r["spd"] is not None]
    sd = mean([abs(r["spd"] - r["fr_spd"]) for r in win if r["fr_spd"] is not None])
    dd = mean([abs(ddiff(r["dir"], r["fr_dir"])) for r in win if r["fr_dir"] is not None and r["spd"] and r["spd"] >= 4])
    score = 3; why = []
    if sd is not None: why.append(f"AROME HD vs AROME France 11-16 h: mean |Δspeed| {sd:.1f} kt" + (f", |Δdir| {dd:.0f}°" if dd is not None else ""))
    if sd is not None and sd > 3: score -= 1
    if dd is not None and dd > 30: score -= 1
    if f["transition"]: score -= 1; why.append("transition in the race window")
    if reg["code"] == "LIGHT": score -= 1; why.append("light wind: direction is unreliable at <4 kt")
    if f["front_risk"]: score -= 1; why.append("front/instability flags (pressure change ≥3 hPa or AROME gust factor ≥1.6)")
    if skill: why.append(f"AROME HD historical error in this regime at the buoy (Oct-Mar 11-16 h): MAE {skill['mae_kt']} kt, bias {skill['bias_kt']:+} kt, dir MAE {skill['dir_mae']}° (n={skill['n']})")
    if skill and skill["mae_kt"] >= 2.8: score -= 1
    nb = ((a or {}).get("buoy_spd") or {}).get("n", 0)
    if nb < 8: score -= 1; why.append(f"few historical buoy analogs (n={nb})")
    lvl = "high" if score >= 3 else "medium" if score == 2 else "low"
    return {"level": lvl, "score": score, "why": why}

def day_brief(date, rows, analogs, clim):
    reg = classify_regime(rows)
    if not reg.get("code"): return {"date": date, "error": reg["why"]}
    code = reg["code"]; meta = REGIMES[code]; f = rule_flags(rows, reg)
    band = speed_band(reg["mean_spd"]); a, a_label = analog(analogs, code, band)
    shift_clim = (clim or {}).get("shift_by_regime", {}).get(meta["clim_key"])
    skill = (clim or {}).get("model_skill_OctMar_window", {}).get("meteofrance_arome_france_hd", {}).get(meta["clim_key"])
    ts = a.get("trend_split_pct") if a else None
    strat = strategy(code, f, shift_clim, ts, None)
    conf = confidence(rows, reg, f, skill, a)
    # expected observed range: AROME race-window range x buoy/AROME ratio quartiles from analogs (if >=8 days)
    ratio = a.get("buoy_over_arome_portals_ratio") if a else None
    exp = None
    if ratio and ratio["n"] >= 8:
        m = reg["mean_spd"]
        exp = {"lo": rnd(m * ratio["q25"]), "mid": rnd(m * ratio["median"]), "hi": rnd(m * ratio["q75"]), "ratio": ratio,
               "text": f"AROME 11-16 h mean {m} kt × historical ratio of buoy-observed to AROME-Portals (q25 {ratio['q25']}, median {ratio['median']}, q75 {ratio['q75']}, n={ratio['n']} days). Hourly AROME range {f['spd_min']}-{f['spd_max']} kt. This is open-bay (SOCIB buoy) wind; inshore Portals usually reads lighter."}
    lo = min(reg["mean_spd"], exp["lo"]) if exp else reg["mean_spd"]; hi = exp["mid"] if exp else reg["mean_spd"]  # race area lies between the Portals point and the open-bay buoy
    # evolution text through race hours
    rh = [r for r in rows if r["h"] in (11, 12, 13, 14, 15, 16) and r["spd"] is not None]
    evo = [f"{r['time']} {r['spd']:.0f} kt (g{r['gst']:.0f}) {r['compass']} {r['dir']:.0f}°" for r in rh if r["gst"] is not None]
    # headline
    head = f"{meta['name']}: {reg['mean_spd']:.0f} kt avg from {compass(reg['mean_dir'])} ({reg['mean_dir']:.0f}°) 11-16 h"
    if strat["pattern"].startswith("persistent"): head += f", {strat['pattern']}"
    elif strat["pattern"] == "transition": head += ", TRANSITION day"
    else: head += ", oscillating"
    head += f". Favoured: {strat['favoured_side']}. Confidence {conf['level']}."
    interp = []
    if code == "EMBAT":
        interp.append(f"Sea-breeze day per AROME: morning {reg['morning_dir'] and compass(reg['morning_dir'])} land breeze, then S-SW filling. Climatology (buoy, winter): calm patch ~11 h, ~215° from 12 h, peak ~8.5 kt at 14 h.")
    if code == "NORTH": interp.append("Offshore northerly: gusty and shifty near shore, flatter water close in; expect the wind to ease or back late if the gradient weakens (watch AROME trend).")
    if code == "NE_E": interp.append("Gregal/Llevant: wind with fetch from the east bay, usually steadier; watch for chop building through the day.")
    if code == "WEST": interp.append("Ponent over the land: watch the Calvià headland shadows; AROME historically biased +0.9 kt here (HD, buoy point).")
    if code == "SOUTH_SYN": interp.append("Synoptic southerly: onshore, steady direction (AROME dir MAE 8° historically), AROME historically over-forecasts by ~2 kt at the buoy.")
    if code == "LIGHT": interp.append("Light/variable: expect postponements; any thermal from the S-SW in the afternoon is the likely racing wind.")
    sbp = f.get("sea_breeze_potential")
    if f.get("dT_land_sea") is not None:
        interp.append(f"Land-sea contrast: inland max {f['land_tmax_12_15']} °C vs sea {f['sst']} °C (ΔT {f['dT_land_sea']:+} °C); morning offshore component {f['offshore_component_09_11_kt']} kt → sea-breeze potential {sbp}.")
    if f.get("stability"): interp.append(f"Over the water: air {f['air_minus_sea']:+} °C vs sea → {f['stability']}." + (" Expect puffs and lulls bigger than AROME gusts suggest." if f["air_minus_sea"] <= -2 else " Expect smoother but layered wind; gusts weaker than AROME may show." if f["air_minus_sea"] >= 1 else ""))
    if f["front_risk"]: interp.append(f"Front/instability warning: MSL pressure change 08→18 h {f['pmsl_change_8_18']} hPa, AROME gust factor {f['arome_gust_factor']}.")
    if f.get("cloud_mean_race") is not None and code in ("EMBAT", "LIGHT"):
        interp.append(f"Cloud {f['cloud_mean_race']:.0f}% during racing" + (" — heavy cloud weakens or delays the thermal." if f["cloud_mean_race"] >= 70 else "."))
    if a and a.get("buoy_spd"):
        interp.append(f"History ({a_label}, {a['days']} days, Oct-Mar since {analogs['period'][:7]}): buoy averaged {a['buoy_spd']['median']} kt (q25-q75 {a['buoy_spd']['q25']}-{a['buoy_spd']['q75']}, n={a['buoy_spd']['n']}) when AROME said {a['arome_spd']['median']} kt (median of all {a['arome_spd']['n']} days)." + (f" LEPA airport averaged {a['lepa_spd']['median']} kt (n={a['lepa_spd']['n']})." if a.get('lepa_spd') else "") + (f" Direction 11→15 h at the buoy: veer {ts['veer']}% / back {ts['back']}% / steady {ts['steady']}% (n={a['buoy_trend_15_minus_11']['n']})." if ts else ""))
    return {"date": date, "regime": {"code": code, **meta, **reg}, "headline": head, "flags": f,
            "evolution": evo, "interpretation": interp, "strategy": strat, "confidence": conf,
            "expected_observed": exp, "analogs": {"label": a_label, "stats": a} if a else None,
            "climatology": {"shift": shift_clim, "arome_hd_skill": skill,
                            "diurnal_buoy": (clim or {}).get("diurnal_by_regime", {}).get(meta["clim_key"])},
            "rig": rig(lo, hi), "hourly": [{k: r[k] for k in ("time","spd","gst","dir","compass","temp","cloud","pmsl","src")} for r in rows if 8 <= r["h"] <= 20]}

def main(argv):
    args = dict(zip(argv[1::2], argv[2::2]))
    analogs = load_json(args.get("--analogs", os.path.join(HERE, "analogs.json")))
    clim = load_json(args.get("--clim", os.path.join(HERE, "climatology_results.json")))
    raw = load_json(args["--input"]) if "--input" in args else fetch(2)
    if "--save-raw" in args: json.dump(raw, open(args["--save-raw"], "w"))
    days = build_rows(raw)
    out = {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "fetched_utc": raw.get("fetched_utc"),
           "point": {"lat": PORTALS[0], "lon": PORTALS[1], "name": "Puerto Portals race area"},
           "units": {"speed": "kt", "direction": "deg true FROM", "temp": "°C", "cloud": "%", "pressure": "hPa"},
           "days": [day_brief(d, rows, analogs, clim) for d, rows in sorted(days.items())],
           "sources": [
             {"name": "AROME HD 1.3 km / AROME France 2.5 km (Météo-France) via Open-Meteo", "url": "https://open-meteo.com/en/docs/meteofrance-api"},
             {"name": "Sea-surface temperature: Open-Meteo Marine API", "url": "https://open-meteo.com/en/docs/marine-weather-api"},
             {"name": "SOCIB Bahía de Palma buoy (historical analogs)", "url": "https://www.socib.es/"},
             {"name": "LEPA METAR archive (Iowa Environmental Mesonet)", "url": "https://mesonet.agron.iastate.edu/request/download.phtml?network=ES__ASOS"},
             {"name": "Historical AROME forecasts (Open-Meteo historical-forecast API)", "url": "https://open-meteo.com/en/docs/historical-forecast-api"},
             {"name": "Decision rules", "url": "https://github.com/ccarbajal1984/capa-wind/blob/main/docs/KNOWLEDGE.md"}]}
    p = args.get("--out", os.path.join(HERE, "forecast.json"))
    os.makedirs(os.path.dirname(os.path.abspath(p)) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    print("wrote", p); [print(" ", d["date"], d.get("headline", d.get("error"))) for d in out["days"]]

if __name__ == "__main__": main(sys.argv)
