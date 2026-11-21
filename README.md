# workout_tracker
A small application to track my training sessions while providing useful stats on the go.

## Prototype

- **Log** tab: pick a date and the day of the split (Push, Pull, Legs, …). The routine's exercises are pre-filled with last time's sets shown in grey. Enter weight and reps, add or remove sets and exercises, then save. Saving the same date and routine again updates that workout.
- **History** tab: all past workouts. Tap one to see its sets, edit it or delete it.

Stack: FastAPI + SQLAlchemy, with SQLite (`data/workouts.db`) by default. Set `DATABASE_URL` to use Postgres. The front end is plain HTML/JS in `app/static/`.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/import_history.py      # load past workouts (safe to re-run)
.venv/bin/uvicorn app.main:app --reload         # http://127.0.0.1:8000
```

Tests: `.venv/bin/python -m pytest`

## Data

| File | What it is |
|---|---|
| `data/_chat.txt` | Original WhatsApp log |
| `data/workout_history.xlsx` | Cleaned history: Workouts, Sets and Exercises sheets |
| `scripts/parse_chat.py` | Parses the chat (name clean-up, drop sets, `12x3`, lb → kg) |
| `scripts/export_clean.py` | Chat → `workout_history.xlsx` |
| `scripts/import_history.py` | `workout_history.xlsx` → database (`--replace` to overwrite) |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/routines` | Split days with their exercises |
| GET | `/api/exercises` | Exercise catalogue |
| GET | `/api/last?names=…&before=YYYY-MM-DD` | Most recent sets per exercise |
| GET | `/api/workouts` | Workout summaries (newest first) |
| GET | `/api/workouts/find?date=…&routine_id=…` | Workout for a given day/routine |
| GET | `/api/workouts/{id}` | Full workout |
| PUT | `/api/workouts` | Create or replace the workout for a date + routine |
| DELETE | `/api/workouts/{id}` | Delete a workout |
