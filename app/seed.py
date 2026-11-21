"""Seed the exercise catalogue and the training plan into an empty database."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exercise, Routine, RoutineExercise
from .plan import EXERCISES, FINISHER, ROUTINES


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
