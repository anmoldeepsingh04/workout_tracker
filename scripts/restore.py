"""Restore a backup (workouts.json) into a database (DATABASE_URL, or the local SQLite file).

Usage:  python scripts/restore.py path/to/workouts.json [--replace]

The target database must be empty. --replace deletes everything in it first; the app may already
have created the default plan there, which is fine to replace because the backup contains the plan.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import models  # noqa: E402,F401
from app.backup import import_data, is_empty, wipe  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402


def main(argv):
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        sys.exit(__doc__)
    data = json.loads(Path(paths[0]).read_text(encoding="utf-8"))

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not is_empty(db):
            if "--replace" not in argv:
                sys.exit("The database already has data. Re-run with --replace to overwrite it.")
            wipe(db)
        counts = import_data(db, data)
    print("Restored " + ", ".join(f"{v} {k}" for k, v in counts.items()))


if __name__ == "__main__":
    main(sys.argv[1:])
