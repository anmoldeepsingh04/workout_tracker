import datetime as dt
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (register tables)
from .db import Base, SessionLocal, engine, get_db
from .models import Exercise, Routine, Workout, WorkoutSet
from .schemas import (ExerciseEntryOut, ExerciseOut, LastPerformance, RoutineOut, SetOut,
                      WorkoutIn, WorkoutOut, WorkoutSummary)
from .seed import get_or_create_exercise, seed

STATIC = Path(__file__).resolve().parent / "static"


def init_db(bind=engine, session_factory=SessionLocal):
    Base.metadata.create_all(bind)
    with session_factory() as db:
        seed(db)


@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(title="Workout Tracker", lifespan=lifespan)


# ---------------------------------------------------------------- helpers
def workout_out(w: Workout) -> WorkoutOut:
    groups: dict[int, ExerciseEntryOut] = {}
    for s in w.sets:
        g = groups.setdefault(s.exercise_id, ExerciseEntryOut(
            exercise_id=s.exercise_id, name=s.exercise.name,
            muscle_group=s.exercise.muscle_group, sets=[]))
        g.sets.append(SetOut(set_number=s.set_number, weight=s.weight, reps=s.reps, note=s.note))
    return WorkoutOut(id=w.id, date=w.date, routine_id=w.routine_id,
                      routine_name=w.routine.name if w.routine else None,
                      notes=w.notes, exercises=list(groups.values()))


def find(db: Session, date: dt.date, routine_id: int | None) -> Workout | None:
    q = select(Workout).where(Workout.date == date)
    q = q.where(Workout.routine_id.is_(None)) if routine_id is None \
        else q.where(Workout.routine_id == routine_id)
    return db.scalars(q).unique().first()


def summary(w: Workout) -> WorkoutSummary:
    return WorkoutSummary(
        id=w.id, date=w.date, routine_id=w.routine_id,
        routine_name=w.routine.name if w.routine else None,
        exercise_count=len({s.exercise_id for s in w.sets}), set_count=len(w.sets),
        volume=round(sum(s.weight * s.reps for s in w.sets), 1))


# ---------------------------------------------------------------- API
@app.get("/api/routines", response_model=list[RoutineOut])
def list_routines(db: Session = Depends(get_db)):
    routines = db.scalars(select(Routine).order_by(Routine.day_of_week)).unique().all()
    return [RoutineOut(id=r.id, day_of_week=r.day_of_week, name=r.name,
                       exercises=[ExerciseOut(id=i.exercise.id, name=i.exercise.name,
                                              muscle_group=i.exercise.muscle_group)
                                  for i in r.items])
            for r in routines]


@app.get("/api/exercises", response_model=list[ExerciseOut])
def list_exercises(db: Session = Depends(get_db)):
    return [ExerciseOut(id=e.id, name=e.name, muscle_group=e.muscle_group)
            for e in db.scalars(select(Exercise).order_by(Exercise.name))]


@app.get("/api/last", response_model=dict[str, LastPerformance])
def last_performance(names: list[str] = Query(default=[]), before: dt.date | None = None,
                     db: Session = Depends(get_db)):
    """Most recent logged sets for each exercise name (strictly before `before`, if given)."""
    out: dict[str, LastPerformance] = {}
    for name in names:
        ex = db.scalar(select(Exercise).where(Exercise.name.ilike(name.strip())))
        if ex is None:
            continue
        q = (select(Workout).join(WorkoutSet).where(WorkoutSet.exercise_id == ex.id)
             .order_by(Workout.date.desc()).limit(1))
        if before:
            q = q.where(Workout.date < before)
        w = db.scalars(q).unique().first()
        if w:
            out[name] = LastPerformance(date=w.date, sets=[
                SetOut(set_number=s.set_number, weight=s.weight, reps=s.reps, note=s.note)
                for s in w.sets if s.exercise_id == ex.id])
    return out


@app.get("/api/workouts", response_model=list[WorkoutSummary])
def list_workouts(limit: int = Query(50, ge=1, le=500), date: dt.date | None = None,
                  db: Session = Depends(get_db)):
    q = select(Workout).order_by(Workout.date.desc(), Workout.id.desc()).limit(limit)
    if date:
        q = q.where(Workout.date == date)
    return [summary(w) for w in db.scalars(q).unique()]


@app.get("/api/workouts/find", response_model=WorkoutOut | None)
def find_workout(date: dt.date, routine_id: int | None = None, db: Session = Depends(get_db)):
    w = find(db, date, routine_id)
    return workout_out(w) if w else None


@app.get("/api/workouts/{workout_id}", response_model=WorkoutOut)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    w = db.get(Workout, workout_id)
    if not w:
        raise HTTPException(404, "Workout not found")
    return workout_out(w)


@app.put("/api/workouts", response_model=WorkoutOut)
def save_workout(data: WorkoutIn, db: Session = Depends(get_db)):
    """Create the workout for (date, routine), or replace it if it already exists."""
    entries = [e for e in data.exercises if e.sets]
    if not entries:
        raise HTTPException(422, "Add at least one set with weight and reps")
    if data.routine_id is not None and db.get(Routine, data.routine_id) is None:
        raise HTTPException(422, "Unknown routine")

    w = find(db, data.date, data.routine_id)
    if w is None:
        w = Workout(date=data.date, routine_id=data.routine_id)
        db.add(w)
    w.notes = data.notes
    w.sets.clear()
    db.flush()

    seen: dict[int, int] = {}  # exercise_id -> position (merge duplicate entries)
    counts: dict[int, int] = {}
    for entry in entries:
        ex = get_or_create_exercise(db, entry.name)
        pos = seen.setdefault(ex.id, len(seen))
        for s in entry.sets:
            counts[ex.id] = counts.get(ex.id, 0) + 1
            w.sets.append(WorkoutSet(exercise=ex, position=pos, set_number=counts[ex.id],
                                     weight=s.weight, reps=s.reps, note=s.note))
    db.commit()
    db.refresh(w)
    return workout_out(w)


@app.delete("/api/workouts/{workout_id}", status_code=204)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    w = db.get(Workout, workout_id)
    if not w:
        raise HTTPException(404, "Workout not found")
    db.delete(w)
    db.commit()


# ---------------------------------------------------------------- front end
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")
