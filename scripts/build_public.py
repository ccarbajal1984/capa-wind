#!/usr/bin/env python3
"""Build dist-public/ from site/ for the public Pages project.

site/ stays the private source of truth. This script copies it, drops team
pages, rewrites the shared header and forecast sections, and writes a forecast
JSON without rig or boat-plan fields. It does not modify site/.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "dist-public"

SKIP = {
    "tuning.html",
    "playbook.html",
    "assets/dragon_capa_final_transparent.svg",
    "assets/capa-logo.svg",
    "data/briefing.json",
}

# Case-insensitive substrings that must not remain in public HTML or JSON.
FORBIDDEN = ("esp 99", "esp-99", "capa", "rake", "tuning", "gold cup", "burda")

BRAND = (
    '<a class="brand" href="./"><img class="mark" src="assets/mark.svg" alt="" '
    'width="36" height="48"><span class="word"><span class="name">Bay of Palma</span>'
    '<span class="eye">live wind</span></span></a>'
)


def must_replace(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"public build: expected one {label}, found {count}")
    return text.replace(old, new, 1)


def scrub_svg(text):
    return (
        text.replace("capaLogoTitle", "markTitle")
        .replace(">CAPA</title>", ">Bay of Palma</title>")
        .replace("CAPA ESP-99 - International Dragon", "Bay of Palma")
    )


def public_forecast(doc):
    out = json.loads(json.dumps(doc))
    kept = []
    for src in out.get("sources") or []:
        blob = json.dumps(src, ensure_ascii=False)
        if "KNOWLEDGE.md" in blob or "/capa-wind/" in blob:
            continue
        kept.append(src)
    out["sources"] = kept
    for day in out.get("days") or []:
        if not isinstance(day, dict):
            continue
        day.pop("rig", None)
        strat = day.get("strategy")
        if isinstance(strat, dict):
            day["strategy"] = {
                key: strat[key] for key in ("pattern", "favoured_side") if key in strat
            }
    return out


def build_index(text):
    text = must_replace(
        text,
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<title>Live wind · CAPA ESP 99</title>',
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<meta name="robots" content="index, follow">\n<title>Bay of Palma · live wind</title>',
        "index title",
    )
    text = must_replace(
        text,
        '<a class="brand" href="./"><img class="mark" src="assets/capa-logo.svg" alt="" width="36" height="48"><span class="word"><span class="capa">CAPA</span><span class="eye">ESP 99 · Bay of Palma</span></span></a>',
        BRAND,
        "index brand",
    )
    text = must_replace(
        text,
        '<nav class="sitenav" aria-label="Site"><a href="./" aria-current="page">Live wind</a><a href="forecast.html">Forecast</a><a href="playbook.html">Wind playbook</a><a href="tuning.html">Tuning</a><a href="#webcams">Webcams</a><a href="/logout">Log out</a></nav>',
        '<nav class="sitenav" aria-label="Site"><a href="./" aria-current="page">Live wind</a><a href="forecast.html">Forecast</a><a href="#webcams">Webcams</a></nav>',
        "index nav",
    )
    text = must_replace(
        text,
        "Ranges match Capa's tuning card. ",
        "Colour bands are 0–6, 6–10, 10–15, 15–20 and 20+ kt. ",
        "index range note",
    )
    text = must_replace(
        text,
        "const parents=[...new Set(['capa-wind.pages.dev','localhost',location.hostname].filter(Boolean))];",
        "const parents=[...new Set(['localhost',location.hostname].filter(Boolean))];",
        "twitch parent",
    )
    return text


def build_forecast(text):
    text = must_replace(
        text,
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<title>Forecast · CAPA ESP 99</title>',
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<meta name="robots" content="index, follow">\n<title>Bay of Palma · forecast</title>',
        "forecast title",
    )
    text = must_replace(
        text,
        '<a class="brand" href="./"><img class="mark" src="assets/capa-logo.svg" alt="" width="36" height="48"><span class="word"><span class="capa">CAPA</span><span class="eye">ESP 99 · Bay of Palma</span></span></a>',
        BRAND,
        "forecast brand",
    )
    text = must_replace(
        text,
        '<nav class="sitenav" aria-label="Site"><a href="./">Live wind</a><a href="forecast.html" aria-current="page">Forecast</a><a href="playbook.html">Wind playbook</a><a href="tuning.html">Tuning</a><a href="./#webcams">Webcams</a><a href="/logout">Log out</a></nav>',
        '<nav class="sitenav" aria-label="Site"><a href="./">Live wind</a><a href="forecast.html" aria-current="page">Forecast</a><a href="./#webcams">Webcams</a></nav>',
        "forecast nav",
    )
    text = must_replace(
        text,
        "const RULES='https://github.com/ccarbajal1984/capa-wind/blob/main/docs/KNOWLEDGE.md';\n",
        "",
        "decision-rules link",
    )
    text = must_replace(
        text,
        """  h+=`<div class="grid"><div class="card"><h3>What the wind will do</h3><ul>${d.interpretation.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
  <div class="small muted" style="margin-top:6px">Race hours: ${d.evolution.map(esc).join(' · ')}</div>
  ${e?`<div style="margin-top:6px"><b>Expected open-bay wind: ${e.lo}–${e.hi} kt (mid ${e.mid})</b><div class="small muted">${esc(e.text)}</div></div>`:''}</div>
  <div class="card"><h3>Strategy</h3><ul><li><b>Shifts:</b> ${esc(s.text)}</li>${s.history_bias?`<li>${esc(s.history_bias)}</li>`:''}<li>${esc(s.side_text)}</li><li><b>Start:</b> ${esc(s.start)}</li><li><b>Windward mark:</b> ${esc(s.windward_mark)}</li></ul></div></div>`;
  h+=`<div class="grid"><div class="card"><h3>Confidence · ${c.level}</h3><ul>${c.why.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></div>
  <div class="card"><h3>Rig · Capa tuning table</h3><table><tr><th>TWS kt</th><th>Rake</th><th>V</th><th>D</th><th>Genoa</th></tr>${d.rig.settings.map(r=>`<tr><td>${r.band}</td><td>${r.rake_cm}</td><td>${r.uppers_V}</td><td>${r.lowers_D}</td><td>${r.genoa}</td></tr>`).join('')}</table><ul class="small">${d.rig.notes.map(t=>`<li>${esc(t)}</li>`).join('')}</ul><div class="small muted">${esc(d.rig.source)}</div><div class="small" style="margin-top:6px"><a href="tuning.html">Tuning &amp; sails</a></div></div></div>`;""",
        """  h+=`<div class="card"><h3>What the wind will do</h3><ul>${d.interpretation.map(t=>`<li>${esc(t)}</li>`).join('')}</ul>
  <div class="small muted" style="margin-top:6px">Race hours: ${d.evolution.map(esc).join(' · ')}</div>
  ${e?`<div style="margin-top:6px"><b>Expected open-bay wind: ${e.lo}–${e.hi} kt (mid ${e.mid})</b><div class="small muted">${esc(e.text)}</div></div>`:''}</div>`;
  h+=`<div class="card"><h3>Confidence · ${c.level}</h3><ul>${c.why.map(t=>`<li>${esc(t)}</li>`).join('')}</ul></div>`;""",
        "forecast private cards",
    )
    text = must_replace(
        text,
        "'. Interpretation rules are documented in <a href=\"'+RULES+'\">KNOWLEDGE.md</a>; statements marked (inference) are not yet verified on the water.'",
        "'.'",
        "forecast sources footer",
    )
    return text


def build_css(text):
    text = must_replace(
        text,
        "/* Shared CAPA chrome. Sticky nav and the Dragon line-drawing mark. */",
        "/* Public Bay of Palma chrome. Sticky nav and the Dragon line-drawing mark. */",
        "css comment",
    )
    text = must_replace(
        text,
        ".word .capa{font-weight:800;letter-spacing:.06em;font-size:18px;color:#fff}",
        ".word .name{font-weight:800;letter-spacing:.01em;font-size:16px;color:#fff}",
        "css wordmark",
    )
    text = must_replace(
        text,
        ".word .capa{font-size:16px}",
        ".word .name{font-size:15px}",
        "css wordmark mobile",
    )
    return text


def scan(path):
    hits = []
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() not in {".html", ".json"}:
            continue
        low = file.read_text(encoding="utf-8").lower()
        for needle in FORBIDDEN:
            start = 0
            while True:
                at = low.find(needle, start)
                if at < 0:
                    break
                excerpt = low[max(0, at - 24):at + len(needle) + 24].replace("\n", " ")
                hits.append(f"{file.relative_to(path)}: {needle!r} in …{excerpt}…")
                start = at + len(needle)
    return hits


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(
        SITE,
        OUT,
        ignore=lambda directory, names: [
            name for name in names
            if str((Path(directory) / name).relative_to(SITE)).replace("\\", "/") in SKIP
            or name in SKIP and Path(directory) == SITE
        ],
    )
    # copytree ignore receives directory as str and names. relative_to works.

    mark = scrub_svg((SITE / "assets" / "capa-logo.svg").read_text(encoding="utf-8"))
    (OUT / "assets" / "mark.svg").write_text(mark, encoding="utf-8")

    for rel in ("favicon.svg", "assets/apple-touch.svg"):
        file = OUT / rel
        file.write_text(scrub_svg(file.read_text(encoding="utf-8")), encoding="utf-8")

    (OUT / "index.html").write_text(build_index((OUT / "index.html").read_text(encoding="utf-8")), encoding="utf-8")
    (OUT / "forecast.html").write_text(build_forecast((OUT / "forecast.html").read_text(encoding="utf-8")), encoding="utf-8")
    css = OUT / "assets" / "brand.css"
    css.write_text(build_css(css.read_text(encoding="utf-8")), encoding="utf-8")

    forecast_path = OUT / "data" / "forecast.json"
    forecast_path.write_text(
        json.dumps(public_forecast(json.loads(forecast_path.read_text(encoding="utf-8"))), indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (OUT / "_headers").write_text(
        "/data/*\n  Cache-Control: public, max-age=60, must-revalidate\n\n/*\n  X-Robots-Tag: index, follow\n",
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    # Pages pretty URLs usually serve /forecast from forecast.html. This rewrite
    # keeps that URL working even if pretty URLs are off. Team pages are absent.
    (OUT / "_redirects").write_text("/forecast /forecast.html 200\n/forecast/ /forecast.html 200\n", encoding="utf-8")

    missing = [rel for rel in SKIP if (OUT / rel).exists()]
    if missing:
        raise SystemExit("public build still contains private files: " + ", ".join(missing))
    for rel in ("tuning.html", "playbook.html", "functions", "_middleware.js"):
        if (OUT / rel).exists() or list(OUT.rglob(rel)):
            raise SystemExit(f"public build still contains {rel}")
    hits = scan(OUT)
    if hits:
        raise SystemExit("public HTML/JSON still contains private terms:\n" + "\n".join(hits))
    print(f"wrote {OUT} (forbidden-term scan clean)")


if __name__ == "__main__":
    sys.exit(main())
