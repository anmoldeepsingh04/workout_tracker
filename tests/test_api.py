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
    from app.seed import init_db
    init_db(engine, factory)

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


def test_plan_seeded(client):
    routines = client.get("/api/routines").json()
    assert [r["name"] for r in routines] == [
        "Push", "Pull", "Legs", "Upper Body", "Shoulders + Arms", "Legs + Core", "Full Body"]
    assert [r["kind"] for r in routines].count("backup") == 1

    push = routines[0]["exercises"]
    main_ = [e for e in push if e["section"] == "main"]
    finisher = [e for e in push if e["section"] == "finisher"]
    assert main_[0] == {**main_[0], "name": "Incline Dumbbell Press", "sets": 3, "target": "8-12",
                        "kind": "compound"}
    assert [e["name"] for e in finisher] == ["Farmer Walk", "Floor Crunch", "Superman", "Side Heel Touch"]
    assert finisher[0]["unit"] == "seconds"

    upper = next(r for r in routines if r["name"] == "Upper Body")
    assert upper["exercises"][0]["name"] == "Flat Dumbbell Press"
    # every day ends with the same finisher
    assert all(r["exercises"][-1]["name"] == "Side Heel Touch" for r in routines)


def test_bodyweight_and_timed_sets(client):
    rid = push_id(client)
    w = client.put("/api/workouts", json={"date": "2026-11-23", "routine_id": rid, "exercises": [
        {"name": "Farmer Walk", "sets": [{"weight": 20, "reps": 45}]},
        {"name": "Superman", "sets": [{"weight": 0, "reps": 15}]},
    ]}).json()
    by_name = {e["name"]: e for e in w["exercises"]}
    assert by_name["Farmer Walk"]["unit"] == "seconds"
    assert by_name["Superman"]["sets"][0] == {"set_number": 1, "weight": 0, "reps": 15, "note": None}


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


def test_list_workouts_by_date(client):
    rid = push_id(client)
    for date in ["2026-11-20", "2026-11-23"]:
        client.put("/api/workouts", json={"date": date, "routine_id": rid, "exercises": [
            {"name": "Shoulder Press", "sets": [{"weight": 10, "reps": 10}]}]})
    found = client.get("/api/workouts", params={"date": "2026-11-23"}).json()
    assert [w["date"] for w in found] == ["2026-11-23"]
    assert found[0]["routine_id"] == rid
    assert client.get("/api/workouts", params={"date": "2026-11-21"}).json() == []


def test_login_required_when_password_set(client, monkeypatch):
    from app import auth
    monkeypatch.setattr(auth, "PASSWORD", "s3cret")
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/routines").status_code == 401
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"

    r = client.post("/login", data={"password": "wrong"}, follow_redirects=False)
    assert r.headers["location"] == "/login?error=1"
    assert client.get("/api/routines").status_code == 401

    r = client.post("/login", data={"password": "s3cret"}, follow_redirects=False)
    assert r.headers["location"] == "/"
    assert client.get("/api/routines").status_code == 200

    client.post("/logout")
    assert client.get("/api/routines").status_code == 401


def test_backup_round_trip(client):
    from app.backup import export_data, import_data, is_empty
    rid = push_id(client)
    client.put("/api/workouts", json={"date": "2026-11-23", "routine_id": rid, "notes": "good day",
               "exercises": [{"name": "Shoulder Press", "sets": [{"weight": 15, "reps": 10}]},
                             {"name": "Farmer Walk", "sets": [{"weight": 20, "reps": 45}]}]})
    data = client.get("/api/export/json").json()
    assert data["format"] == "workout-tracker-backup"
    assert data["workouts"][0]["notes"] == "good day"
    csv_text = client.get("/api/export/csv").text
    assert csv_text.splitlines()[0].startswith("date,routine,exercise")
    assert "2026-11-23,Push,Farmer Walk,Full body,1,20.0,45,seconds," in csv_text

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    from app.db import Base
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        assert is_empty(db)
        counts = import_data(db, data)
        assert counts["workouts"] == 1 and counts["sets"] == 2
        assert export_data(db) == data  # restored database exports identically
        with pytest.raises(ValueError):
            import_data(db, data)  # refuses to restore over existing data
