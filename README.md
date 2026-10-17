# CAPA wind

Live wind for **CAPA** (Dragon, ESP 99) in the **Bahía de Palma**. A GitHub Action samples the bay every 10 minutes, keeps a rolling history in this repo, and publishes `site/` to Cloudflare Pages with Direct Upload. The site asks for a shared username and password on every request.

`https://capa-wind.pages.dev` is the Pages hostname the Twitch player is allowed to embed on (`parent=capa-wind.pages.dev`).

Wind numbers come from the [Open-Meteo](https://open-meteo.com/) grid at 39.55°N, 2.63°E. They are bay conditions, not an onboard anemometer. Change the point at the top of `fetch_data.py` if you want a different mark. The page reads `data/live.json` and `config.json` with relative URLs.

## What runs

| Path | Role |
| --- | --- |
| `fetch_data.py` | Fetches the current wind and appends it to a 7-day history |
| `site/data/history.json` | Rolling samples committed by the Action |
| `site/data/live.json` | Current reading and the last 24 hours, loaded by the page |
| `site/config.json` | Twitch channel. Parents always include `capa-wind.pages.dev` |
| `site/functions/_middleware.js` | Basic auth using Pages secrets `SITE_USER` and `SITE_PASS` |
| `.github/workflows/update.yml` | Every 10 minutes and on manual run |

The Action has no `push` trigger. Its data commit message includes `[skip ci]`, so a later push trigger would not start another run from the bot commit. There is no GitHub Pages deploy.

Preview locally (auth is enforced only on Cloudflare):

```bash
python3 fetch_data.py
python3 -m http.server -d site
```

## One-time Cloudflare and GitHub setup

Do this once. Nothing in the repo can create the Cloudflare project; there are no Cloudflare credentials here yet.

1. In the Cloudflare dashboard, **Workers & Pages → Create → Pages → Direct Upload**. Name the project exactly `capa-wind`.
   Do not connect this Git repository. Cloudflare’s free plan limits Git-integration builds. This repo publishes with Wrangler Direct Upload:

   `npx wrangler pages deploy site --project-name=capa-wind --branch=main`

2. Open the `capa-wind` project → **Settings → Environment variables**. On **Production**, add two **encrypted** secrets:
   - `SITE_USER` — the shared username
   - `SITE_PASS` — the shared password

   The middleware reads only those names. If either one is missing or empty, every request gets **503** and the files are not served.

3. Create an API token: **My Profile → API Tokens → Create Token → Create Custom Token**.
   - Permission: **Account → Cloudflare Pages → Edit**
   - Account resources: the account that owns `capa-wind`

   Copy the token when Cloudflare shows it.

4. Copy the **Account ID** (Workers & Pages overview, right-hand column).

5. On GitHub, open this repo → **Settings → Secrets and variables → Actions → New repository secret** and add both:
   - `CLOUDFLARE_API_TOKEN` — the token from step 3
   - `CLOUDFLARE_ACCOUNT_ID` — the account ID from step 4

6. Run **Actions → Update wind data → Run workflow**, or wait for the 10-minute schedule. The job pulls, rebases, runs `fetch_data.py`, and commits `site/data/` when it changed. It then deploys `site/`. While either secret is absent, that deploy step logs a notice and exits successfully. It does not fail the job.

7. Open `https://capa-wind.pages.dev` and sign in with `SITE_USER` and `SITE_PASS`. The same login covers the page, `data/live.json`, and the rest of the files. The Twitch iframe is loaded from Twitch itself.

The Pages site is password-protected. This repository still stores the wind history. Make the GitHub repository private if that history should not be public.

To point the embed at a different channel, change `twitchChannel` in `site/config.json`. Keep `capa-wind.pages.dev` in `parents`.
