import datetime as dt

from pydantic import BaseModel, Field


class ExerciseOut(BaseModel):
    id: int
    name: str
    muscle_group: str | None = None


class RoutineOut(BaseModel):
    id: int
    day_of_week: int
    name: str
    exercises: list[ExerciseOut]


class SetIn(BaseModel):
    weight: float = Field(ge=0, le=1000)
    reps: int = Field(ge=1, le=500)
    note: str | None = Field(default=None, max_length=200)


class ExerciseEntryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sets: list[SetIn]


class WorkoutIn(BaseModel):
    date: dt.date
    routine_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    exercises: list[ExerciseEntryIn]


class SetOut(BaseModel):
    set_number: int
    weight: float
    reps: int
    note: str | None = None


class ExerciseEntryOut(BaseModel):
    exercise_id: int
    name: str
    muscle_group: str | None = None
    sets: list[SetOut]


class WorkoutOut(BaseModel):
    id: int
    date: dt.date
    routine_id: int | None
    routine_name: str | None
    notes: str | None
    exercises: list[ExerciseEntryOut]


class WorkoutSummary(BaseModel):
    id: int
    date: dt.date
    routine_id: int | None
    routine_name: str | None
    exercise_count: int
    set_count: int
    volume: float


class LastPerformance(BaseModel):
    date: dt.date
    sets: list[SetOut]
