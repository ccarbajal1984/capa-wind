# CAPA wind

Live wind for **CAPA** (Dragon, ESP 99) in the Bahía de Palma. `fetch_data.py` reads the public station feeds every 5 minutes, writes `site/data/live.json`, and keeps a rolling 12-hour history in `history.json` at the repo root. GitHub Actions then Direct Uploads `site/` to Cloudflare Pages. Sign-in is on unless the Pages env var `AUTH_ENABLED` is exactly `false`.

The page is one file, `site/index.html`. It loads `data/live.json` with a relative URL. The Pipeline Twitch player is embedded with `parent=capa-wind.pages.dev` (plus the current hostname when that is different). Webcam snapshots are Conecta Balear Visiona and IB-red.

Stations: Weathercloud Puerto Portals, Windalytics (RCN Palma, CN Cala Gamba, Can Pastilla CMSAP, CN Arenal), SOCIB Bay of Palma buoy, Palma port tide gauge, Dragonera buoy, METAR LEPA and LESB, Meteoclimatic Ciutat Jardí, and the AROME HD forecast from Open-Meteo.

## GitHub Actions secrets

Add these repository secrets (**Settings → Secrets and variables → Actions**):

| Secret | Value |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | API token with **Account → Cloudflare Pages → Edit** and **Account → Workers Scripts → Edit** |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID from the Workers & Pages overview |
| `SITE_USER` | Shared username for the site |
| `SITE_PASS` | Shared password for the site |
| `GH_DISPATCH_TOKEN` | GitHub token that can dispatch Actions (`workflow` scope, or fine-grained Actions read and write). The ticker stores it as the Worker secret `GH_TOKEN`. |

`functions/_middleware.js` (repo root, not inside `site/`) requires a login for every request, including `site/data/*.json`, unless `AUTH_ENABLED` on the Pages **production** environment is exactly `false`. Wrangler only bundles `./functions` from the directory it is run in. The login form POSTs to `/login` and checks `SITE_USER` (trimmed, case-insensitive) and `SITE_PASS` (trimmed) from that environment. A match sets an HttpOnly, Secure, SameSite=Lax session cookie for 30 days, signed with `SESSION_SECRET` when that env var is set, otherwise with a key derived from `SITE_PASS`. If either credential is missing or empty, every request gets **503** and the files are not served. A wrong password stays on the login page with **401**. `/logout` clears the cookie. Leave the secrets in place; set `AUTH_ENABLED=false` only to open the site.

## What the Action does

A Worker, `capa-wind-ticker` (`worker/`), runs `*/5 * * * *` and dispatches this workflow. `.github/workflows/update.yml` also has a backup schedule of every 15 minutes, plus **Run workflow**. One concurrency group queues runs and does not cancel the one already going. `fetch_data.py` uses the standard library; Actions caches pip from `requirements.txt` and caches npm so Wrangler is not downloaded from scratch each time.

The ticker is deployed only when `main` is pushed with a change under `worker/` or in this workflow file, or when **Run workflow** is started with **deploy_worker** checked. A 5-minute dispatch does not redeploy the Worker. Data commits use `[skip ci]` and only touch the JSON files, so they do not match that push filter.

1. Pull and rebase `main`, then run `python3 fetch_data.py`.
2. Commit `site/data/live.json` and `history.json` when they changed. An unchanged tree is not committed.
3. If `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` is absent, log a notice and skip the deploy. The job still succeeds.
4. Otherwise create the Pages project if needed, then upload `site/`:

   ```bash
   npx wrangler pages project create capa-wind --production-branch main || true
   npx wrangler pages deploy site --project-name=capa-wind --branch=main
   ```

   Do not connect this Git repository in Cloudflare. Free-plan Git builds are limited; this repo uses Direct Upload.

5. On a manual run, or when `wrangler pages secret list --env production` shows `SITE_USER` or `SITE_PASS` is not on the production environment, upload those two with `--env production` and deploy once more so they take effect. A normal 5-minute run does not repeat that when both production secrets are already present. The deploy log must include `Uploading Functions bundle`.
6. On a worker-path push, or a manual run with **deploy_worker**, from `worker/`: `npx wrangler deploy`, then `echo -n "$GH_DISPATCH_TOKEN" | npx wrangler secret put GH_TOKEN`. The `-n` keeps a newline out of the bearer token.

Create the API token under **My Profile → API Tokens → Create Custom Token**, permissions **Account → Cloudflare Pages → Edit** and **Account → Workers Scripts → Edit**, limited to the account that owns the project.

Open `https://capa-wind.pages.dev` and sign in with `SITE_USER` and `SITE_PASS`. The browser keeps that session for 30 days. Set `AUTH_ENABLED=false` on the Pages project to turn the login off.

This repository still stores `live.json` and `history.json`. Make the GitHub repository private if that history should not be public.

Preview locally (auth is enforced only on Cloudflare):

```bash
OBS_ARCHIVE_DIR=/nonexistent python3 fetch_data.py
python3 -m http.server -d site
```
