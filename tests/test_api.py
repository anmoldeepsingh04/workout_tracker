import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app import main
from app.db import get_db


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(main, "init_db", lambda: None)
    main.Base.metadata.create_all(engine)
    with factory() as db:
        main.seed(db)

    def override():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()


def push_id(client):
    return next(r["id"] for r in client.get("/api/routines").json() if r["name"] == "Push")


def test_routines_seeded(client):
    routines = client.get("/api/routines").json()
    assert [r["name"] for r in routines] == [
        "Push", "Pull", "Legs", "Upper Body", "Shoulders + Arms", "Legs + Core"]
    assert routines[0]["exercises"][0]["name"] == "Incline Dumbbell Press"


def test_save_find_update_delete(client):
    rid = push_id(client)
    body = {"date": "2026-11-23", "routine_id": rid, "exercises": [
        {"name": "Incline Dumbbell Press", "sets": [{"weight": 15, "reps": 12}, {"weight": 15, "reps": 10}]},
        {"name": "Shoulder Press", "sets": []},
    ]}
    w = client.put("/api/workouts", json=body).json()
    assert [e["name"] for e in w["exercises"]] == ["Incline Dumbbell Press"]
    assert [s["set_number"] for s in w["exercises"][0]["sets"]] == [1, 2]

    found = client.get("/api/workouts/find", params={"date": "2026-11-23", "routine_id": rid}).json()
    assert found["id"] == w["id"]

    # saving again for the same day replaces instead of duplicating
    body["exercises"] = [{"name": "Brand New Exercise", "sets": [{"weight": 7.5, "reps": 12}]}]
    w2 = client.put("/api/workouts", json=body).json()
    assert w2["id"] == w["id"]
    assert [e["name"] for e in w2["exercises"]] == ["Brand New Exercise"]
    assert len(client.get("/api/workouts").json()) == 1

    assert client.delete(f"/api/workouts/{w['id']}").status_code == 204
    assert client.get("/api/workouts").json() == []


def test_last_performance(client):
    rid = push_id(client)
    for date, weight in [("2026-11-09", 12.5), ("2026-11-16", 15)]:
        client.put("/api/workouts", json={"date": date, "routine_id": rid, "exercises": [
            {"name": "Shoulder Press", "sets": [{"weight": weight, "reps": 10}]}]})
    last = client.get("/api/last", params={"names": ["Shoulder Press"], "before": "2026-11-16"}).json()
    assert last["Shoulder Press"]["date"] == "2026-11-09"
    assert last["Shoulder Press"]["sets"][0]["weight"] == 12.5


def test_validation(client):
    rid = push_id(client)
    r = client.put("/api/workouts", json={"date": "2026-11-23", "routine_id": rid, "exercises": []})
    assert r.status_code == 422
    r = client.put("/api/workouts", json={"date": "2026-11-23", "routine_id": rid, "exercises": [
        {"name": "Shoulder Press", "sets": [{"weight": 10, "reps": 0}]}]})
    assert r.status_code == 422
