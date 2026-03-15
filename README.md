# GS Artiglio App

Web application built with Flask for the internal management of a volleyball team. The project combines classic CRUD workflows with push notifications, PWA support, a minigame, and several role-based admin tools.

## Main Features

- **Authentication & roles** — Login/logout with 17 granular role flags (`admin`, `notaio`, `capitano`, `coach`, `pizza`, `birra`, `smm`, `preparatore`, `convenzioni`, `abbigliamento`, `sponsor`, `pensionato`, `gemellaggi`, `catering`, `scout`, `dirigente`, `presidente`)
- **Team roster & profiles** — Add, edit, and view players ordered by volleyball position; personal bio, nickname, and jersey number
- **Fines workflow** — Submit a *denuncia* (infraction report), democratic voting with quorum, admin approval or rejection, automatic late-fee (*mora*) generation, payment tracking (cash / PayPal), and a team cash register (*cassa*)
- **Matches & stats** — Schedule matches, record set scores, save per-player stats (points, aces, blocks, sets played), MVP voting with auto-close deadline (next Tuesday at noon)
- **Training & attendance** — Auto-generated training sessions (Tue/Wed/Fri), absence and late-arrival tracking, public and private coach notes
- **Calendar & turni** — Monthly calendar view overlaying matches and volunteer duty slots (*pizza* / *birra*)
- **Championship standings** — Manual *classifica* with round tracking
- **Videos** — Upload team videos (MP4/MOV/AVI/WEBM), tag protagonists, per-video likes and threaded comments
- **Badge / achievement system** — Monthly automatic badges: top donator, top accuser, top MVP, top Floppy Eagle score; retroactive skin unlocks for badge holders
- **Floppy Eagle minigame** — In-browser game with all-time and monthly leaderboards, in-game coins, unlockable skins, and mission progress
- **Push notifications & PWA** — VAPID-based Web Push subscriptions; per-user filter preferences for every notification type; service worker and web app manifest for installability
- **App releases & feedback** — Publish release notes; users submit bug reports or feature proposals with optional media attachment; admin push alert on new feedback
- **Admin panel** — Flask-Admin interface with categories for all database models
- **Streak system** — Tracks consecutive days without fines; current and best streak per player with medical-certificate expiry reminders

## Tech Stack

| Layer | Library / Version |
|---|---|
| Web framework | Flask 3.1.2 |
| ORM | Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.0 |
| Auth | Flask-Login 0.6.3, Flask-Bcrypt 1.0.1 |
| Forms / CSRF | Flask-WTF 1.2.2 |
| Admin UI | Flask-Admin 1.6.1 |
| Push notifications | pywebpush 2.0.0 |
| Image processing | Pillow 12.0.0 |
| Compression | flask-compress 1.14 |
| Frontend | Bootstrap 5, vanilla JavaScript |
| Database | SQLite (default) |

## Project Structure

```text
app/
  __init__.py        # App factory, extension init, blueprint registration
  admin.py           # Flask-Admin views
  models.py          # All SQLAlchemy models
  routes/            # Blueprints: auth, dashboard, fines, profile, roster,
  │                  #   attendance, matches, calendar, game, video, api, admin_custom
  utils/             # Service layer: one module per domain
static/
  css/               # Main stylesheet + component/game/dashboard styles
  js/                # Pages JS + shared utilities (toast, theme, PWA, etc.)
  manifest.json      # PWA manifest
  sw.js              # Service worker
templates/           # Jinja2 templates + partials/
tests/               # Unit and smoke tests
config.py            # Config class (reads env vars, VAPID fallback, upload dirs)
run.py               # Entry point
requirements.txt
```

## Local Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure environment variables

Export the variables in your shell or place them in a `.env`-style file loaded before startup.

**Required for full functionality:**

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key |
| `VAPID_PRIVATE_KEY` | Web Push private key |
| `VAPID_PUBLIC_KEY` | Web Push public key |
| `VAPID_CLAIM_EMAIL` | Contact email for VAPID claims |

**Optional:**

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///artiglio.db` | SQLAlchemy connection string |
| `APP_HOST` | `127.0.0.1` | Bind address |
| `APP_PORT` | `5000` | Bind port |
| `FLASK_DEBUG` | `false` | Enable debug mode |
| `ALLOW_SETUP_ROUTES` | `false` | Expose `/setup_db` and `/crea_admin` |
| `SETUP_TOKEN` | — | Token required by setup routes |
| `BOOTSTRAP_ADMIN_USERNAME` | `admin` | Username for bootstrap admin |
| `BOOTSTRAP_ADMIN_PASSWORD` | — | Password for bootstrap admin (required if using `/crea_admin`) |
| `BOOTSTRAP_ADMIN_FULL_NAME` | `Admin User` | Full name for bootstrap admin |
| `BOOTSTRAP_ADMIN_NICKNAME` | `Admin` | Nickname for bootstrap admin |

If VAPID keys are not set as environment variables, the app falls back to a local `vapid_json_config.json` file (not included in this repository).

### 4. Run the application

```powershell
python run.py
```

The server starts at `http://127.0.0.1:5000` by default.

## Database Notes

SQLite is used by default; the database file `artiglio.db` is created automatically in the project root on first run (`db.create_all()` is called inside the app factory).

To use a different database, set `DATABASE_URL` to a valid SQLAlchemy connection string (e.g. `postgresql://user:pass@host/db`).

This public repository does not include production or personal database files.

## Push Notifications

Requires VAPID keys. The app first checks environment variables, then falls back to `vapid_json_config.json` in the project root. Do not commit real VAPID keys to the repository.

Users can manage per-notification-type preferences (MVP, streak, turno, fines, Floppy Eagle, donations, medical certificate, app updates) from their profile.

## Setup Routes

`/crea_admin` and `/setup_db` are gated behind `ALLOW_SETUP_ROUTES=true` **and** a `SETUP_TOKEN` query-string token. Both return `404` when the flag is off.

Recommended default: `ALLOW_SETUP_ROUTES=false`.

## Upload Folders

The following folders are created automatically if missing:

| Path | Content |
|---|---|
| `static/certificati/` | Player medical certificates |
| `static/videos/` | Team match/training videos |
| `static/files/` | Documents (e.g. `regolamento.pdf`) |
| `static/feedback/` | Feedback attachments |

## Tests

```powershell
# Smoke test covering critical flows
python tests/smoke_critical_flows.py

# Individual unit test files
python -m pytest tests/
```

Test modules:

- `smoke_critical_flows.py` — End-to-end critical path smoke tests
- `test_admin_skin_service.py` — Skin assignment and unlock logic
- `test_attendance_service.py` — Absence / late-arrival tracking
- `test_fine_workflow_service.py` — Denuncia, voting, approval, mora
- `test_match_stats_save.py` — Match stats persistence
- `test_video_service.py` — Video upload, likes, comments

## Notes

This repository is the public presentation version of the project. Local deployment files, private VAPID credentials, personal databases, and historical private Git data are intentionally excluded.