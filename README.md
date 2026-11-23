# workout_tracker
A small application to track my training sessions while providing useful stats on the go.

## Prototype

- **Log** tab: choose what you're hitting (Day 1–6 of the split, or the Full Body backup; the next day in the rotation is marked "next up"). Each exercise shows its planned sets × reps, whether it's compound (C) or isolation (I), and last time's sets in grey. The finisher follows the main exercises. Enter weight and reps (seconds for carries), add or remove sets and exercises, then save. Saving the same date and routine again updates that workout.
- **Machine settings** (⚙ on each exercise): bench angle, seat pin, foot rest and so on. Saved per exercise right away, and shown every time that exercise comes up.
- **History** tab: all past workouts. Tap one to see its sets, edit it or delete it.

The training plan lives in [docs/workout_plan.md](docs/workout_plan.md), and the app seeds its routines from [app/plan.py](app/plan.py).

Stack: FastAPI + SQLAlchemy, with SQLite (`data/workouts.db`) by default. Set `DATABASE_URL` to use Postgres. The front end is plain HTML/JS in `app/static/`.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload         # http://127.0.0.1:8000
```

Tests: `.venv/bin/python -m pytest`

## Deploy (free: Render + Neon)

The app runs on a free [Render](https://render.com) web service (config in `render.yaml`), and the data is kept in a free [Neon](https://neon.com) Postgres database. Hosted, the app needs a password (`APP_PASSWORD`).

1. **Make this GitHub repo private.** Backups of your data are stored in it.
2. **Neon:** create a project (region: Frankfurt) and copy its connection string with connection pooling **off**.
3. **Copy your data into Neon**, once, from this folder:
   ```bash
   .venv/bin/python scripts/backup.py                     # local database -> backups/
   DATABASE_URL='postgresql://…neon.tech/neondb?sslmode=require' \
     .venv/bin/python scripts/restore.py backups/workouts.json
   ```
4. **GitHub:** Settings → Secrets and variables → Actions → New repository secret `DATABASE_URL` (the Neon string). This turns on the automatic backups.
5. **Push** the code to GitHub.
6. **Render:** New → Blueprint → pick this repo. Enter `DATABASE_URL` (the Neon string) and `APP_PASSWORD` (the password you'll log in with). `SECRET_KEY` is generated for you.
7. Open the `onrender.com` link on your phone, log in, and use "Add to Home Screen".

The free Render service sleeps after 15 minutes without visits, so the first visit after a break takes about a minute to load.

## Backups

Your data never depends on a single provider:

- **Automatic:** every 3 hours, [.github/workflows/backup.yml](.github/workflows/backup.yml) exports the Neon database to the `backups` branch of this repo: `workouts.json` (everything) and `sets.csv` (opens in Excel). A commit is only made when something changed, so the branch history is a dated record of every change. To run it right away: GitHub → Actions → "Backup data" → Run workflow.
- **From the app:** History tab → "Full backup (JSON)" or "Sets (CSV for Excel)".
- **Manually:** `DATABASE_URL=… .venv/bin/python scripts/backup.py [folder]` (default folder: `backups/`, ignored by git).

**Restoring** into any empty database (a new Neon project, another Postgres host, or the local SQLite file):

```bash
DATABASE_URL='<new database>' .venv/bin/python scripts/restore.py workouts.json   # --replace to overwrite
```

Leave out `DATABASE_URL` to restore into the local file `data/workouts.db`. The backup is plain JSON that refers to exercises and routines by name, so it's readable without this app.

## Data

| File | What it is |
|---|---|
| `data/workouts.db` | Local database (not committed to git). Once deployed, the live data is in Neon |
| `scripts/backup.py`, `scripts/restore.py` | Export a database to `workouts.json` + `sets.csv`, and load a backup into a database |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/routines` | Split days with their exercises, planned sets × reps and finisher |
| GET | `/api/plan` | Plan-wide info (finisher stretching note) |
| GET | `/api/exercises` | Exercise catalogue |
| PUT | `/api/exercises/{id}/setup` | Save an exercise's machine settings (`{"setup": "…"}`, empty clears) |
| GET | `/api/last?names=…&before=YYYY-MM-DD` | Most recent sets per exercise |
| GET | `/api/workouts` | Workout summaries (newest first) |
| GET | `/api/workouts/find?date=…&routine_id=…` | Workout for a given day/routine |
| GET | `/api/workouts/{id}` | Full workout |
| PUT | `/api/workouts` | Create or replace the workout for a date + routine |
| DELETE | `/api/workouts/{id}` | Delete a workout |
| GET | `/api/export/json`, `/api/export/csv` | Download a full backup |
