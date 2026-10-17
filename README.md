# CAPA wind

Live wind for **CAPA** (Dragon, ESP 99) in the Bahía de Palma. `fetch_data.py` reads the public station feeds every 10 minutes, writes `site/data/live.json`, and keeps a rolling 12-hour history in `history.json` at the repo root. GitHub Actions then Direct Uploads `site/` to Cloudflare Pages. The site asks for a shared username and password on every request.

The page is one file, `site/index.html`. It loads `data/live.json` with a relative URL. The Pipeline Twitch player is embedded with `parent=capa-wind.pages.dev` (plus the current hostname when that is different). Webcam snapshots are Conecta Balear Visiona and IB-red.

Stations: Weathercloud Puerto Portals, Windalytics (RCN Palma, CN Cala Gamba, Can Pastilla CMSAP, CN Arenal), SOCIB Bay of Palma buoy, Palma port tide gauge, Dragonera buoy, METAR LEPA and LESB, Meteoclimatic Ciutat Jardí, and the AROME HD forecast from Open-Meteo.

## GitHub Actions secrets

Add these four repository secrets (**Settings → Secrets and variables → Actions**):

| Secret | Value |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | API token with **Account → Cloudflare Pages → Edit** |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID from the Workers & Pages overview |
| `SITE_USER` | Shared username for the site |
| `SITE_PASS` | Shared password for the site |

`functions/_middleware.js` (repo root, not inside `site/`) reads `SITE_USER` and `SITE_PASS` from the Pages **production** environment. Wrangler only bundles `./functions` from the directory it is run in. If either secret is missing or empty, every request gets **503** and the files are not served. A wrong password gets **401**.

## What the Action does

`.github/workflows/update.yml` runs every 10 minutes and on **Run workflow**. There is no `push` trigger. Data commits use `[skip ci]`.

1. Pull and rebase `main`, then run `python3 fetch_data.py`.
2. Commit `site/data/live.json` and `history.json` when they changed.
3. If `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` is absent, log a notice and skip the deploy. The job still succeeds.
4. Otherwise create the Pages project if needed, then upload `site/`:

   ```bash
   npx wrangler pages project create capa-wind --production-branch main || true
   npx wrangler pages deploy site --project-name=capa-wind --branch=main
   ```

   Do not connect this Git repository in Cloudflare. Free-plan Git builds are limited; this repo uses Direct Upload.

5. On a manual run, or when `wrangler pages secret list --env production` shows `SITE_USER` or `SITE_PASS` is not on the production environment, upload those two with `--env production` and deploy once more so they take effect. A normal 10-minute run does not repeat that when both production secrets are already present. The deploy log must include `Uploading Functions bundle`.

Create the API token under **My Profile → API Tokens → Create Custom Token**, permission **Account → Cloudflare Pages → Edit**, limited to the account that owns the project.

Open `https://capa-wind.pages.dev` and sign in with `SITE_USER` and `SITE_PASS`.

The Pages site is password-protected. This repository still stores `live.json` and `history.json`. Make the GitHub repository private if that history should not be public.

Preview locally (auth is enforced only on Cloudflare):

```bash
OBS_ARCHIVE_DIR=/nonexistent python3 fetch_data.py
python3 -m http.server -d site
```
