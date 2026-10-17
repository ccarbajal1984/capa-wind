# Capa race-meteorologist / strategist knowledge base
Scope: X Puerto Portals Winter Series (Nov–Feb), race area ~39.53N 2.57E, racing ~11:00–16:00 Madrid. Units: kt, ° true wind FROM.
Tags: **[V]** verified against Capa's local data (climatology/results.json, shift_results.json, meteo-strategist/analogs.json);
**[L]** from cited literature; **[I]** inference / seamanship, not verified for Portals.
Built 17 Oct 2026. Local data: SOCIB Bahía de Palma buoy 10-min (2013–2026, gaps; 312 winter race-window days), LEPA METAR (2010–2026),
historical AROME HD/France at the Portals and buoy points (Open-Meteo historical-forecast, Nov 2022–Oct 2026), live obs archive (only a few days, not yet usable).

## 1. Physical background
### 1.1 Embat (Bay of Palma sea breeze)
- Mallorca's sea breeze ("embat") enters mainly through the Bay of Palma from the SW and converges in the island centre; the Serra de Tramuntana blocks inflow on the W flank. [L] Jansà & Jaume 1946, summarised in https://www.mdpi.com/2673-964X/2/1/2 ; Ramis, Jansà & Alonso 1990, Meteorol. Atmos. Phys. 42, https://doi.org/10.1007/bf01314828
- Classic phases (Campos basin, Sep/Jun campaigns): land breeze until ~sunrise → preparatory (≈3 h after sunrise coastal wind starts veering toward SB direction) → onset ≈5 h after sunrise → mature from noon → decays and turns back to land-to-sea near sunset. Low-level SB jet 4–6 m/s (8–12 kt) at ~250 m, 12–15 UTC. [L] Jiménez et al., http://hdl.handle.net/20.500.11765/11991 ; https://meetingorganizer.copernicus.org/EGU2016/EGU2016-9616.pdf
- **Winter at the buoy [V]** (results.json diurnal_by_regime, Oct–Mar): morning N–NE land breeze ~5 kt 08–10 h, near-calm ~3.7 kt at 11 h, ~215° from 12 h, peak 8.5 kt at 14 h, 8.0 kt at 16 h. Weaker than the summer embat. Embat-classified days are 24.4 % of buoy winter race-window days (66/312) and 18.9 % at LEPA 2010–26.
- Embat shifts [V]: buoy shift std 7.4°, peak-to-peak 16.5°, cycle ~51 min; 11→15 h median trend +7.3° (veer 53 % / back 31 % / steady 16 %, n=45, shift_results.json). Analog file (AROME-classified, buoy-observed): veer 60 % / back 30 % (n=10 only).
### 1.2 Opposing/aligned gradient and onset/kill criteria
- SB needs land warmer than sea; it forms on a 1–2 °C contrast; an offshore gradient delays it, and stronger offshore flow keeps it out at sea. The strongest SBs are those that just reach the coast against an opposing wind. [L] Biggs & Graves 1962 index ε=U²/(cp·ΔT), critical ≈3 (lake breeze); Porson et al. 2007 https://doi.org/10.1175/jam2525.1 ; Arritt 1993 (cited there); offshore wind >6 m/s (~12 kt) used as an SB-blocking filter: https://wes.copernicus.org/articles/7/815/2022/wes-7-815-2022.pdf
- With an offshore gradient the onset is later the stronger the gradient. [L] Defant/Haurwitz review https://doi.org/10.1175/1520-0477-27.6.272
- Aligned gradient (synoptic SW) → SB adds to it, stronger and earlier wind, little turning. [I/L general]
- **Nov–Feb**: the sea (Bay of Palma SST typically warmer than the winter air) often makes ΔT small or negative → embat weak/absent except on sunny, slack-gradient days. Today's (17 Oct) AROME/marine: inland max 25.1 °C, SST 25.1 °C → ΔT 0. Thresholds for Palma are **not calibrated [unverified]**.
### 1.3 Nocturnal land breeze / katabatics
- Under weak gradients, katabatic flows from the Serra de Tramuntana, the Randa slope and the central platform converge in the Palma basin; a cold pool forms there and drains to sea through the bay (the only exit, to the S). Quasi-steady ~5 h after sunset. [L] Cuxart, Jiménez & Martínez 2007 MWR https://journals.ametsoc.org/view/journals/mwre/135/3/mwr3329.1.pdf ; Martínez & Cuxart https://revistas.ucm.es/index.php/FITE/en/article/download/FITE0707110021A/11532 ; Jiménez et al. https://tethys.cat/sites/default/files/pdf/articles/3tethys-09-cas.pdf
- Racing relevance: the N–NE morning land breeze at the buoy (above, [V]) is this drainage; it dies around 10–11 h and leaves the calm gap before an embat. Na Burgesa-specific drainage onto Portals is **[unverified]**.
### 1.4 Winter synoptic regimes (frequencies [V], buoy winter race window / LEPA 2010–26)
| Regime | Buoy % | LEPA % | Typical (buoy, 11–16 h) | AROME HD skill at buoy, Oct–Mar 11–16 h [V] |
|---|---|---|---|---|
| Northerly (Tramuntana/Mestral, NW–N–NNE) | 20.7 | 22.1 | 11–12.6 kt, backs ~7° (median) 11→16 h | bias −0.1 kt, MAE 2.7, dir MAE 20° (n=107) |
| NE–E (Gregal/Llevant) | 15.9 | 17.2 | 10–11.5 kt, veers 52°→77° through the day | bias −2.1 kt, MAE 2.9, dir MAE 33° (n=66) |
| W–WNW (Ponent) | 21.5 | 14.4 | 12.6 kt median (analogs) | bias +0.9, MAE 2.3, dir MAE 18° (n=113) |
| Synoptic S–SE–SW (Xaloc/Migjorn/Llebeig-Garbí) | 7.0 | 11.5 | steady dir (std 5.9°) | bias +2.0, MAE 2.9, dir MAE 8° (n=64) |
| Embat | 24.4 | 18.9 | see 1.1 | bias −0.7, MAE 2.1, dir MAE 20° (n=230) |
| Light/variable (<4 kt) | 10.4 | 15.9 | direction meaningless | bias +0.8, MAE 1.8 (n=24) |
- Tramuntana = cold N wind; Mestral = NW, linked to Mistral outbreaks from the Gulf of Lion and cyclonic weather; Gregal (NE) and Llevant (E) are moister, linked to Mediterranean lows and rain. [L] AEMET https://repositorio.aemet.es/bitstream/20.500.11765/1898/2/notasmet_cal98.pdf ; AEMET LEPA aeronautical climatology https://repositorio.aemet.es/handle/20.500.11765/3642
- Gust factor is low in every regime at the buoy (median 1.11–1.15, [V]) — the buoy anemometer is ~3 m above the sea and over open water; on-course puffs near shore in offshore winds can be bigger **[I]**.
### 1.5 Frontal passages, stability, cloud
- Cold front: pressure fall then rise, a veer (SW→W→NW) at passage, gusty unstable NW behind it. [L general marine meteorology; I for Portals] Rule R3 flags ≥3 hPa change over 08–18 h or AROME gust/mean ≥1.6.
- Air colder than the sea → unstable surface layer, more mixing of stronger wind aloft → bigger puffs/lulls and shifts; air warmer than the sea → stable, smoother but sheared and lighter at the surface. [L general boundary-layer meteorology; thresholds −2/+1 °C in R5 are **[I]**].
- Thick cloud cuts land heating → weaker/later embat. [L via SB mechanism; threshold 70 % is **[I]**].
### 1.6 Model notes (AROME)
- AROME France HD 0.01° (~1.3 km), AROME France 0.025°, hourly, ~42–48 h, runs every 3 h; HD carries a reduced variable set (no cloud/pressure via Open-Meteo — verified today: those fields null). https://open-meteo.com/en/docs/meteofrance-api ; https://donneespubliques.meteofrance.fr/client/document/doc_arome_pour-portail_20250806_410.pdf
- **Portals point vs reality [V]**: AROME at the Portals grid point is ~0.74× AROME at the buoy point (n=2146; 0.63 in NW–N). Observed buoy mean / AROME-Portals mean on analog days: Embat 1.17, NE–E 1.35, North 1.32, West 1.29, South 1.19 (n 10–22 days per regime) — i.e. AROME-Portals reads well below the open-bay wind. The race course is between the two; whether it is closer to the buoy or to Portals is **[unverified]** — calibrate with Vakaros logs from the first event.
- Direction: buoy minus AROME-Portals median on Embat days +22° (n=38) and NE–E −24° (n=17) **[V, small samples]**; Portals' own vane read 171–187° vs 216–259° elsewhere in the 16 Oct sea breeze (playbook) — check vane.

## 2. Race strategy (general [L], Portals application [I])
- Oscillating: stay near the middle, tack on headers relative to the median heading taken pre-start; avoid early laylines. Persistent: sail the headed tack first toward the new wind, accept sterns, don't overstand because the layline keeps moving; commit only after several readings confirm the trend; leverage is good in persistent, bad in oscillating. https://www.sailingworld.com/how-to/windshift-rules-of-thumb/ ; https://www.windcheckmagazine.com/article/sail-fast-up-the-first-beat-in-persistent-shifts/ ; https://waypointamsterdam.com/performance_racing_tactics_7b/
- Start: in a persistent shift start toward the new wind even if slightly unfavoured, only if the expected shift exceeds the line bias (WindCheck, above).
- Geography near Portals: N/NW offshore wind arrives in streaks from the valleys; W–WNW bends round the Calvià/Portals headland and Illetes; NE–E fills from the east bay first; embat fills from the SW/open bay. All **[I]**, verify on the water.
- Current: tidal range in the Bay of Palma is negligible; wind-driven currents exist but no local race-area current data was found **[unverified]**.
- Dragon modes and rig: use Capa's tuning table (PLIS_PLAY_TUNING_TABLE.md) and Gold Cup notes (runner/burda mostly 45–60 %, rake 122.5 / 122.0 / 121.5, shrouds max tight 20 V / 12 D, max loose 14–15 V / 7–8 D); genoa V-6M ≤15 kt, V-6H above, overlap 14–18 kt (North speed guide). Light air: power and pressure first; breeze-on: depower with rake/runner, flat boat.

## 3. Decision rules (implemented in forecast_brief.py)
Inputs per day (Madrid hours): AROME HD (fallback AROME France) speed/gust/dir; AROME France temp, cloud, MSLP; AROME France 2 m temp at 39.60N 2.70E (inland); Open-Meteo marine SST at 39.50N 2.60E.
- **R1 Regime** (identical to climatology/analyse.py so analogs match): S = mean speed 11–16 h, D = circular-mean dir 11–16 h, M/Ms = 07–10 h dir/speed.
  S<4 → LIGHT; 150≤D≤250 and (M≥290 or M≤90 or Ms<4) and S<16 → EMBAT; D≥290 or D<45 → NORTH; D<120 → NE_E; D<250 → SOUTH_SYN; else WEST.
- **R2 Transition**: |dir(16 h)−dir(11 h)| ≥60°, or any hourly step ≥45° (hours ≥4 kt), or min <4 kt while max ≥6 kt in the window.
- **R3 Front/instability**: |MSLP(18 h)−MSLP(08 h)| ≥3 hPa or mean AROME gust/mean ≥1.6 (hours ≥6 kt).
- **R4 Sea-breeze potential**: ΔT = inland Tmax(12–15 h) − SST; U_off = mean 09–11 h component of wind from 020° (offshore for the Portals shore). ΔT≤0 → none; ΔT≥3 and U_off<6 kt → good; ΔT≥1.5 and U_off<10 → marginal; else poor. Also reports a scaled Biggs–Graves value (informational). Thresholds **[I]**.
- **R5 Stability**: air(11–16 h mean) − SST ≤ −2 → unstable/puffy; ≥ +1 → stable/smoother; else neutral **[I]**.
- **R6 Shift pattern**: R2 → "transition"; else |Δdir 11→16| ≥15° → persistent veer/back; else oscillating, with buoy climatological std / p2p / period for that regime.
- **R7 Favoured side**: persistent → toward the shift (veer = right, back = left); oscillating → use history lean if veer% − back% ≥15 points on analogs (or reverse), else middle. Regime geographic note appended (marked inference).
- **R8 Expected open-bay wind**: S × (q25, median, q75) of buoy-observed / AROME-Portals ratio on analog days (only if ≥8 buoy days). Rig = tuning-table rows from min(S, low) to median.
- **R9 Confidence**: start 3; −1 if HD vs France |Δspeed|>3 kt; −1 if |Δdir|>30°; −1 transition; −1 LIGHT; −1 front flag; −1 if historical AROME HD MAE in regime ≥2.8 kt; −1 if <8 buoy analog days. ≥3 high, 2 medium, else low.

## 4. Historical analogs (build_analogs.py → analogs.json)
Every Oct–Mar day 2022-11-14..2026-10-16 with ≥6 race-window hours of historical AROME at the Portals point (HD preferred, France fill) is classified with R1 and binned by AROME 11–16 h mean speed (0-6/6-10/10-15/15-20/20+). For each day the SOCIB buoy (≥18 ten-minute obs 11–16 h) and LEPA METAR (≥8 reports) observed values are attached. Per regime and per regime×band: medians/quartiles of buoy mean, strongest hour, gust factor, buoy/AROME ratios, buoy−AROME direction error, LEPA mean, and the 11→15 h direction trend (veer/back/steady split, |trend|≤5° = steady). forecast_brief uses the regime×band bucket when it has ≥8 buoy days, else the whole regime. 701 days classified, only 123 have buoy data; trend samples are 6–14 days per regime — **treat percentages as indicative**.

## 5. Unverified / open items
- Calibration of R4/R5 thresholds for Palma; race-course position between Portals point and buoy; Portals vane alignment; Na Burgesa drainage effect on the course; local current; all geographic shift notes; LEPA-based trend (not computed — would add many more trend days).
