"""Seed the exercise catalogue and the training plan into an empty database."""
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (register tables)
from .db import Base, SessionLocal, engine
from .models import Exercise, Routine, RoutineExercise
from .plan import EXERCISES, FINISHER, ROUTINES


def init_db(bind=engine, session_factory=SessionLocal) -> None:
    """Create missing tables and seed the plan into an empty database."""
    Base.metadata.create_all(bind)
    add_missing_columns(bind)
    with session_factory() as db:
        seed(db)
        sync_plan(db)


# Columns added after the first deploy: create_all() only creates missing tables, not columns.
NEW_COLUMNS = {"exercises": {"setup": "VARCHAR(300)"}}


def add_missing_columns(bind) -> None:
    insp = inspect(bind)
    for table, columns in NEW_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        missing = [(n, t) for n, t in columns.items() if n not in existing]
        if missing:
            with bind.begin() as conn:
                for name, type_ in missing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {type_}"))


def get_or_create_exercise(db: Session, name: str) -> Exercise:
    name = " ".join(name.split())
    ex = db.scalar(select(Exercise).where(Exercise.name.ilike(name)))
    if ex is None:
        muscle, equip, kind, unit = EXERCISES.get(name, (None, None, None, "reps"))
        ex = Exercise(name=name, muscle_group=muscle, equipment=equip, kind=kind, unit=unit)
        db.add(ex)
        db.flush()
    return ex


def seed(db: Session) -> None:
    """Insert the exercise catalogue and plan if the database has no routines yet."""
    if db.scalar(select(Routine.id).limit(1)) is not None:
        return
    for name in EXERCISES:
        get_or_create_exercise(db, name)
    for position, name, focus, kind, items in ROUTINES:
        r = Routine(position=position, name=name, focus=focus, kind=kind)
        entries = [(*item, "main") for item in items] + [(*item, "finisher") for item in FINISHER]
        r.items = [
            RoutineExercise(exercise=get_or_create_exercise(db, ex), position=i, sets=sets,
                            target=target, note=note, section=section)
            for i, (ex, sets, target, note, section) in enumerate(entries)
        ]
        db.add(r)
    db.commit()


def sync_plan(db: Session) -> None:
    """Copy sets, targets and notes from plan.py onto routine items that already exist.

    Matches items by routine name, exercise name and section. Never adds, removes or reorders
    anything, and never touches logged workouts.
    """
    wanted = {}
    for _, routine, _, _, items in ROUTINES:
        for ex, sets, target, note in items:
            wanted[(routine, ex, "main")] = (sets, target, note)
        for ex, sets, target, note in FINISHER:
            wanted[(routine, ex, "finisher")] = (sets, target, note)
    changed = False
    for r in db.scalars(select(Routine)):
        for item in r.items:
            plan = wanted.get((r.name, item.exercise.name, item.section))
            if plan and (item.sets, item.target, item.note) != plan:
                item.sets, item.target, item.note = plan
                changed = True
    if changed:
        db.commit()
