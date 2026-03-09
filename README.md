# GS Artiglio App

Web application built with Flask for the internal management of a volleyball team. The project combines classic CRUD workflows with push notifications, PWA support, lightweight game features, and several role-based admin tools.

## Main Features

- User authentication and role-based access control
- Team roster and profile management
- Fines workflow with voting and approval logic
- Match, attendance, and team activity management
- Push notifications and PWA integration
- Admin panels for releases, feedback, badges, and game-related features
- Flappy Eagle minigame with progress and leaderboard endpoints

## Tech Stack

- Python 3
- Flask
- SQLAlchemy
- Flask-Login
- Flask-WTF
- Bootstrap 5
- Vanilla JavaScript
- SQLite

## Project Structure

```text
app/
  __init__.py
  admin.py
  models.py
  routes/
  utils/
static/
templates/
tests/
config.py
run.py
requirements.txt
sw.js
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

Create a local `.env`-style configuration or export variables in your shell using `.env.example` as reference.

Minimum recommended variables:

- `SECRET_KEY`
- `VAPID_PRIVATE_KEY`
- `VAPID_PUBLIC_KEY`
- `VAPID_CLAIM_EMAIL`

Optional variables:

- `DATABASE_URL`
- `APP_HOST`
- `APP_PORT`
- `FLASK_DEBUG`
- `ALLOW_SETUP_ROUTES`
- `SETUP_TOKEN`
- `BOOTSTRAP_ADMIN_*`

### 4. Run the application

```powershell
python run.py
```

By default the local runner uses:

- host: `127.0.0.1`
- port: `5000`
- debug: `false`

These can be overridden with `APP_HOST`, `APP_PORT`, and `FLASK_DEBUG`.

## Database Notes

The application uses SQLite by default. If `DATABASE_URL` is not provided, the app falls back to a local `artiglio.db` file in the project root.

This public repository does not include production or personal database files.

## Push Notifications

Push notifications require VAPID configuration. The app first checks environment variables and then falls back to a local configuration file if present in a private deployment.

Do not commit real VAPID keys to the repository.

## Setup Routes

Some setup routes are protected by environment flags and tokens. They are intended only for controlled bootstrap scenarios.

Recommended default:

- `ALLOW_SETUP_ROUTES=false`

## Tests

The project includes a smoke test suite for critical flows.

Run it with:

```powershell
python tests/smoke_critical_flows.py
```

## Notes

This repository is the public presentation version of the project. Local deployment files, private credentials, personal databases, and historical private Git data are intentionally excluded.