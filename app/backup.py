"""Provider-independent backup format: everything in the database as plain JSON (plus a CSV of
all sets for spreadsheets). Records refer to each other by name, not database id, so a backup can
be restored into any empty database (SQLite or Postgres)."""
import csv
import datetime as dt
import io

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Exercise, Routine, RoutineExercise, Workout, WorkoutSet

FORMAT = "workout-tracker-backup"
VERSION = 1
CSV_FIELDS = ["date", "routine", "exercise", "muscle_group", "set", "weight_kg", "reps", "unit", "note"]


def export_data(db: Session) -> dict:
    """The whole database as a dict. Ordered deterministically so unchanged data gives an identical
    file (keeps the backup history in git clean)."""
    exercises = db.scalars(select(Exercise).order_by(Exercise.name)).all()
    routines = db.scalars(select(Routine).order_by(Routine.position, Routine.name)).unique().all()
    workouts = db.scalars(select(Workout).order_by(Workout.date, Workout.id)).unique().all()
    return {
        "format": FORMAT,
        "version": VERSION,
        "exercises": [
            {"name": e.name, "muscle_group": e.muscle_group, "equipment": e.equipment,
             "kind": e.kind, "unit": e.unit}
            for e in exercises
        ],
        "routines": [
            {"name": r.name, "position": r.position, "focus": r.focus, "kind": r.kind,
             "items": [{"exercise": i.exercise.name, "sets": i.sets, "target": i.target,
                        "note": i.note, "section": i.section} for i in r.items]}
            for r in routines
        ],
        "workouts": [
            {"date": w.date.isoformat(), "routine": w.routine.name if w.routine else None,
             "notes": w.notes,
             "created_at": w.created_at.isoformat(timespec="seconds") if w.created_at else None,
             "sets": [{"exercise": s.exercise.name, "position": s.position,
                       "set_number": s.set_number, "weight": s.weight, "reps": s.reps,
                       "note": s.note} for s in w.sets]}
            for w in workouts
        ],
    }


def sets_csv(data: dict) -> str:
    """All sets as one flat CSV table (opens in Excel / Google Sheets)."""
    units = {e["name"]: e for e in data["exercises"]}
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for w in data["workouts"]:
        for s in w["sets"]:
            ex = units.get(s["exercise"], {})
            writer.writerow({
                "date": w["date"], "routine": w["routine"] or "", "exercise": s["exercise"],
                "muscle_group": ex.get("muscle_group") or "", "set": s["set_number"],
                "weight_kg": s["weight"], "reps": s["reps"], "unit": ex.get("unit") or "reps",
                "note": s["note"] or "",
            })
    return buf.getvalue()


def is_empty(db: Session) -> bool:
    return all(db.scalar(select(m.id).limit(1)) is None for m in (Exercise, Routine, Workout))


def wipe(db: Session) -> None:
    for model in (WorkoutSet, Workout, RoutineExercise, Routine, Exercise):
        db.execute(delete(model))
    db.flush()


def import_data(db: Session, data: dict) -> dict:
    """Load a backup into an empty database. Returns counts of what was restored."""
    if data.get("format") != FORMAT:
        raise ValueError("Not a workout tracker backup file")
    if data.get("version", 0) > VERSION:
        raise ValueError(f"Backup version {data['version']} is newer than this app supports")
    if not is_empty(db):
        raise ValueError("Database is not empty")

    exercises = {}
    for e in data["exercises"]:
        exercises[e["name"]] = Exercise(name=e["name"], muscle_group=e["muscle_group"],
                                        equipment=e["equipment"], kind=e["kind"],
                                        unit=e["unit"] or "reps")
    db.add_all(exercises.values())

    def exercise(name):  # tolerate sets/items naming an exercise missing from the list
        if name not in exercises:
            exercises[name] = Exercise(name=name, unit="reps")
            db.add(exercises[name])
        return exercises[name]

    routines = {}
    for r in data["routines"]:
        routine = Routine(name=r["name"], position=r["position"], focus=r["focus"], kind=r["kind"])
        routine.items = [RoutineExercise(exercise=exercise(i["exercise"]), position=n,
                                         sets=i["sets"], target=i["target"], note=i["note"],
                                         section=i["section"] or "main")
                         for n, i in enumerate(r["items"])]
        routines[r["name"]] = routine
        db.add(routine)

    n_sets = 0
    for w in data["workouts"]:
        workout = Workout(date=dt.date.fromisoformat(w["date"]), notes=w["notes"],
                          routine=routines.get(w["routine"]) if w["routine"] else None)
        if w.get("created_at"):
            workout.created_at = dt.datetime.fromisoformat(w["created_at"])
        workout.sets = [WorkoutSet(exercise=exercise(s["exercise"]), position=s["position"],
                                   set_number=s["set_number"], weight=s["weight"], reps=s["reps"],
                                   note=s["note"]) for s in w["sets"]]
        n_sets += len(workout.sets)
        db.add(workout)
    db.commit()
    return {"exercises": len(exercises), "routines": len(routines),
            "workouts": len(data["workouts"]), "sets": n_sets}
