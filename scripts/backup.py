"""Write a backup of the database (DATABASE_URL, or the local SQLite file) to a folder.

Usage:  python scripts/backup.py [output_dir]      (default: backups/)

Creates <output_dir>/workouts.json (complete, restorable with scripts/restore.py) and
<output_dir>/sets.csv (all sets, for spreadsheets).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.backup import export_data, sets_csv  # noqa: E402
from app.db import SessionLocal  # noqa: E402


def main(argv):
    out = Path(argv[0]) if argv else ROOT / "backups"
    out.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        data = export_data(db)
    (out / "workouts.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "sets.csv").write_text(sets_csv(data), encoding="utf-8")
    n_sets = sum(len(w["sets"]) for w in data["workouts"])
    print(f"Backed up {len(data['workouts'])} workouts, {n_sets} sets -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
