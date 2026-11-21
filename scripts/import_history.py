"""Import past workouts from data/workout_history.xlsx (Sets sheet) into the app database.

Usage:  python scripts/import_history.py [xlsx_path] [--replace]

Workouts already in the database (same date + routine) are skipped unless --replace is given.
Uses DATABASE_URL if set, otherwise data/workouts.db.
"""
import datetime as dt
import sys
from collections import OrderedDict
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.db import SessionLocal  # noqa: E402
from app.models import Routine, Workout, WorkoutSet  # noqa: E402
from app.seed import get_or_create_exercise, init_db  # noqa: E402


def plan_name(exercise, variant):
    """Map logged cable-fly names onto the plan's names (direction decides the exercise)."""
    if exercise.startswith("Cable Fly"):
        if variant == "High-to-low":
            return "High-to-Low Cable Fly"
        if exercise == "Cable Fly (Upper Chest)":
            return "Low-to-High Cable Fly"
    return exercise


def read_sets(path):
    wb = load_workbook(path, read_only=True)
    ws = wb["Sets"]
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    idx = {h: i for i, h in enumerate(header)}
    for r in rows:
        if r[idx["Date"]] is None:
            continue
        d = r[idx["Date"]]
        yield {
            "date": d.date() if isinstance(d, dt.datetime) else d,
            "routine": r[idx["Routine"]],
            "exercise": plan_name(r[idx["Exercise"]], r[idx["Variant"]]),
            "weight": float(r[idx["Weight (kg)"]]),
            "reps": int(r[idx["Reps"]]),
            "note": "; ".join(str(x) for x in (r[idx["Variant"]], r[idx["Notes"]]) if x) or None,
        }


def main(argv):
    replace = "--replace" in argv
    paths = [a for a in argv if not a.startswith("--")]
    path = Path(paths[0]) if paths else ROOT / "data" / "workout_history.xlsx"

    init_db()
    workouts = OrderedDict()
    for s in read_sets(path):
        workouts.setdefault((s["date"], s["routine"]), []).append(s)

    added = skipped = 0
    with SessionLocal() as db:
        routines = {r.name: r for r in db.scalars(select(Routine)).unique()}
        for (date, routine_name), sets in workouts.items():
            routine = routines.get(routine_name)
            rid = routine.id if routine else None
            existing = db.scalars(select(Workout).where(
                Workout.date == date,
                Workout.routine_id == rid if rid is not None else Workout.routine_id.is_(None))).unique().first()
            if existing:
                if not replace:
                    skipped += 1
                    continue
                db.delete(existing)
                db.flush()
            w = Workout(date=date, routine_id=rid)
            positions, counts = {}, {}
            for s in sets:
                ex = get_or_create_exercise(db, s["exercise"])
                pos = positions.setdefault(ex.id, len(positions))
                counts[ex.id] = counts.get(ex.id, 0) + 1
                w.sets.append(WorkoutSet(exercise=ex, position=pos, set_number=counts[ex.id],
                                         weight=s["weight"], reps=s["reps"], note=s["note"]))
            db.add(w)
            added += 1
        db.commit()
    print(f"Imported {added} workouts, skipped {skipped} already present.")


if __name__ == "__main__":
    main(sys.argv[1:])
