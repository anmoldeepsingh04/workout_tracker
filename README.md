# workout_tracker
A small application to track my training sessions while providing useful stats on the go.

## Prototype

- **Log** tab: choose what you're hitting (Day 1–6 of the split, or the Full Body backup; the next day in the rotation is marked "next up"). Each exercise shows its planned sets × reps, whether it's compound (C) or isolation (I), and last time's sets in grey. The finisher follows the main exercises. Enter weight and reps (seconds for carries), add or remove sets and exercises, then save. Saving the same date and routine again updates that workout.
- **History** tab: all past workouts. Tap one to see its sets, edit it or delete it.

The training plan lives in [docs/workout_plan.md](docs/workout_plan.md), and the app seeds its routines from [app/plan.py](app/plan.py).

Stack: FastAPI + SQLAlchemy, with SQLite (`data/workouts.db`) by default. Set `DATABASE_URL` to use Postgres. The front end is plain HTML/JS in `app/static/`.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/import_history.py      # first run only: load past workouts (safe to re-run)
.venv/bin/uvicorn app.main:app --reload         # http://127.0.0.1:8000
```

Tests: `.venv/bin/python -m pytest`

## Deploy (free: Render + Neon)

The app runs on a free [Render](https://render.com) web service (config in `render.yaml`), and the data is kept in a free [Neon](https://neon.com) Postgres database. Hosted, the app needs a password (`APP_PASSWORD`).

1. **Neon:** create a project (region: Frankfurt) and copy its connection string with connection pooling **off**.
2. **Load history** into it, once, from this folder:
   ```bash
   DATABASE_URL='postgresql://…neon.tech/neondb?sslmode=require' .venv/bin/python scripts/import_history.py
   ```
3. **Push** the code to GitHub.
4. **Render:** New → Blueprint → pick this repo. Enter `DATABASE_URL` (the Neon string) and `APP_PASSWORD` (the password you'll log in with). `SECRET_KEY` is generated for you.
5. Open the `onrender.com` link on your phone, log in, and use "Add to Home Screen".

The free Render service sleeps after 15 minutes without visits, so the first visit after a break takes about a minute to load.

## Data

Workouts are logged through the web interface and stored in `data/workouts.db`, which is the file to back up.

| File | What it is |
|---|---|
| `data/workouts.db` | The database with all logged workouts (not committed to git) |
| `data/workout_history.xlsx` | Workouts from Sep to Nov 2026, from before the app existed |
| `scripts/import_history.py` | Loads `workout_history.xlsx` into a database. Needed once when setting up a new database (e.g. when deploying), then both files can be deleted |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/routines` | Split days with their exercises, planned sets × reps and finisher |
| GET | `/api/plan` | Plan-wide info (finisher stretching note) |
| GET | `/api/exercises` | Exercise catalogue |
| GET | `/api/last?names=…&before=YYYY-MM-DD` | Most recent sets per exercise |
| GET | `/api/workouts` | Workout summaries (newest first) |
| GET | `/api/workouts/find?date=…&routine_id=…` | Workout for a given day/routine |
| GET | `/api/workouts/{id}` | Full workout |
| PUT | `/api/workouts` | Create or replace the workout for a date + routine |
| DELETE | `/api/workouts/{id}` | Delete a workout |
