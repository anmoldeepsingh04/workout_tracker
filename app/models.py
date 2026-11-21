import datetime as dt

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Exercise(Base):
    __tablename__ = "exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    muscle_group: Mapped[str | None] = mapped_column(String(30))
    equipment: Mapped[str | None] = mapped_column(String(30))


class Routine(Base):
    """A training day of the split, e.g. Monday = Push."""
    __tablename__ = "routines"
    id: Mapped[int] = mapped_column(primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer, unique=True)  # 0 = Monday
    name: Mapped[str] = mapped_column(String(50))
    items: Mapped[list["RoutineExercise"]] = relationship(
        order_by="RoutineExercise.position", cascade="all, delete-orphan")


class RoutineExercise(Base):
    __tablename__ = "routine_exercises"
    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    position: Mapped[int] = mapped_column(Integer)
    exercise: Mapped[Exercise] = relationship(lazy="joined")


class Workout(Base):
    __tablename__ = "workouts"
    __table_args__ = (UniqueConstraint("date", "routine_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    routine_id: Mapped[int | None] = mapped_column(ForeignKey("routines.id"))
    notes: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    routine: Mapped[Routine | None] = relationship(lazy="joined")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        order_by=lambda: [WorkoutSet.position, WorkoutSet.set_number], cascade="all, delete-orphan")


class WorkoutSet(Base):
    __tablename__ = "workout_sets"
    id: Mapped[int] = mapped_column(primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)  # exercise order within the workout
    set_number: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float)
    reps: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(200))
    exercise: Mapped[Exercise] = relationship(lazy="joined")
