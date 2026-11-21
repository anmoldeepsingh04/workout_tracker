"""Default split and exercise catalogue, based on what was actually logged most recently."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exercise, Routine, RoutineExercise

EXERCISES = {
    # name: (muscle group, equipment)
    "Incline Dumbbell Press": ("Chest", "Dumbbell"),
    "Incline Chest Press": ("Chest", "Dumbbell"),
    "Machine Chest Press": ("Chest", "Machine"),
    "Cable Fly (Upper Chest)": ("Chest", "Cable"),
    "Cable Fly (Mid Chest)": ("Chest", "Cable"),
    "Cable Fly (Lower Chest)": ("Chest", "Cable"),
    "Single-arm Cable Lat Pulldown": ("Back", "Cable"),
    "Lat Pulldown": ("Back", "Machine"),
    "Chest-supported T-bar Row": ("Back", "Machine"),
    "Seated Cable Row": ("Back", "Cable"),
    "Straight-arm Cable Pullover": ("Back", "Cable"),
    "Shoulder Press": ("Shoulders", "Dumbbell"),
    "Cable Lateral Raise": ("Shoulders", "Cable"),
    "Reverse Pec Deck": ("Shoulders", "Machine"),
    "Rear Delt Fly": ("Shoulders", "Machine"),
    "Triceps Pushdown": ("Triceps", "Cable"),
    "Overhead Cable Triceps Extension": ("Triceps", "Cable"),
    "Dumbbell Curl": ("Biceps", "Dumbbell"),
    "Supported Dumbbell Curl": ("Biceps", "Dumbbell"),
    "Incline Dumbbell Curl": ("Biceps", "Dumbbell"),
    "Preacher Curl": ("Biceps", "Dumbbell"),
    "Single-arm Preacher Curl": ("Biceps", "Dumbbell"),
    "Hammer Curl": ("Biceps", "Dumbbell"),
    "Dumbbell Squat": ("Legs", "Dumbbell"),
    "Barbell Squat": ("Legs", "Barbell"),
    "Leg Press": ("Legs", "Machine"),
    "Romanian Deadlift": ("Legs", "Dumbbell"),
    "Leg Extension": ("Legs", "Machine"),
    "Leg Curl": ("Legs", "Machine"),
    "Calf Raise": ("Legs", "Machine"),
}

ROUTINES = [
    (0, "Push", ["Incline Dumbbell Press", "Machine Chest Press", "Cable Fly (Upper Chest)",
                 "Cable Fly (Mid Chest)", "Cable Fly (Lower Chest)", "Shoulder Press",
                 "Cable Lateral Raise", "Triceps Pushdown", "Overhead Cable Triceps Extension"]),
    (1, "Pull", ["Single-arm Cable Lat Pulldown", "Chest-supported T-bar Row", "Lat Pulldown",
                 "Straight-arm Cable Pullover", "Reverse Pec Deck", "Preacher Curl",
                 "Dumbbell Curl", "Hammer Curl"]),
    (2, "Legs", ["Barbell Squat", "Leg Press", "Leg Curl", "Leg Extension", "Calf Raise"]),
    (3, "Upper Body", ["Incline Chest Press", "Cable Fly (Upper Chest)", "Cable Fly (Lower Chest)",
                       "Cable Fly (Mid Chest)", "Chest-supported T-bar Row",
                       "Single-arm Cable Lat Pulldown", "Seated Cable Row",
                       "Straight-arm Cable Pullover", "Reverse Pec Deck"]),
    (4, "Shoulders + Arms", ["Shoulder Press", "Cable Lateral Raise", "Rear Delt Fly",
                             "Triceps Pushdown", "Overhead Cable Triceps Extension",
                             "Dumbbell Curl", "Single-arm Preacher Curl", "Hammer Curl"]),
    (5, "Legs + Core", ["Dumbbell Squat", "Leg Press", "Leg Extension", "Leg Curl", "Calf Raise"]),
]


def get_or_create_exercise(db: Session, name: str) -> Exercise:
    name = " ".join(name.split())
    ex = db.scalar(select(Exercise).where(Exercise.name.ilike(name)))
    if ex is None:
        muscle, equip = EXERCISES.get(name, (None, None))
        ex = Exercise(name=name, muscle_group=muscle, equipment=equip)
        db.add(ex)
        db.flush()
    return ex


def seed(db: Session) -> None:
    """Insert the exercise catalogue and split if the database is empty."""
    if db.scalar(select(Routine.id).limit(1)) is not None:
        return
    for name in EXERCISES:
        get_or_create_exercise(db, name)
    for dow, name, exercises in ROUTINES:
        r = Routine(day_of_week=dow, name=name)
        r.items = [RoutineExercise(exercise=get_or_create_exercise(db, e), position=i)
                   for i, e in enumerate(exercises)]
        db.add(r)
    db.commit()
