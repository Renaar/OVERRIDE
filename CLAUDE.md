# OVERRIDE — notes for Claude

Personal LitRPG training app, single user, French UI. Spec phases: 1 core, 2 full engine, 3 living System, 4 comfort.

## Stack
- Backend: Python 3.12, FastAPI, SQLite (stdlib `sqlite3`), no ORM. Front: vanilla ES modules, no build, no CDN.
- One container (`Dockerfile`, port 8087, volume `./data`, TZ Europe/Zurich). CI (`.github/workflows/docker.yml`)
  publishes `ghcr.io/renaar/override` (main → `latest`); `compose.yaml` pulls it (Dockge, no source on the server).

## Layout
- `app/engine/` — pure game logic (no I/O, no clock). All rules live here and are unit-tested.
- `app/service.py` — DB ↔ engine glue only. `app/db.py` — schema. `app/main.py` — routes.
- `web/` — `index.html`, `css/app.css`, `js/app.js` (hash router), `js/screens/*.js`, embedded fonts.
- `data/*.json` — tunable program data (config, skills, ranks, titles, system_messages). The DB `data/override.db` is gitignored.
  In Docker these JSON files are copied from `/app/defaults` into the volume only when missing.

## Commands
- Tests: `python -m pytest -q`
- Dev server: `DATA_DIR=/tmp/ov uvicorn app.main:app --reload --port 8087` (copy `data/*.json` there first, or let it copy them).

## Conventions
- Code, identifiers, comments: English. UI text, README, System messages: French, using the spec's lexicon
  (Système, Éveil, Patch, Épreuve de rang, Donjon, Compétences, Inventaire, Mode hors-ligne, Journal du Système).
- App name is the single `APP_NAME` setting.
- Back safety first: never add loaded hinge / heavy load to redemption, urgent or penalty quests.
- New rules → engine function + pytest. Keep generated quests ≤ 25 min (`estimate_seconds`).
- Ask before any command touching Docker, Tailscale or the system on the user's server.
