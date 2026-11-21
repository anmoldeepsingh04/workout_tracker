"""Export the parsed chat log to a clean, data-only Excel file (data/workout_history.xlsx).

Sheets:
  Workouts  - one row per session
  Sets      - one row per set (the source for importing into the app database)
  Exercises - exercise catalogue with muscle group / equipment

Cleaning rules (on top of the parser's name normalisation):
  * sets logged with 0 reps are dropped
  * notes are shortened to the facts that matter (drop set, unit conversion, data flags)
"""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_chat import CHAT, EXERCISES, FLAGS, ROOT, parse  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "workout_history.xlsx"


def short_notes(s):
    keep = []
    for part in filter(None, s["notes"].split("; ")):
        if part.startswith("Drop set"):
            keep.append(part)
        elif part.startswith("Logged as") and "lb" in part:
            keep.append(part)
        elif "different machine" in part:
            keep.append("Unusual weight - likely a different machine")
        elif part == "Pull arm same leg down":
            keep.append(part)
    return "; ".join(dict.fromkeys(keep))


def write_sheet(wb, name, headers, rows, widths, formats=None):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial", size=10)
            fmt = (formats or {}).get(cell.column - 1)
            if fmt:
                cell.number_format = fmt
    ref = f"A1:{chr(64 + len(headers))}{max(len(rows) + 1, 2)}"
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)
    ws.freeze_panes = "A2"
    return ws


def main():
    sessions, sets, _ = parse(CHAT)
    sets = [s for s in sets if s["reps"] > 0]

    ids = {s["date"]: i + 1 for i, s in enumerate(sessions)}
    wb = Workbook()
    wb.remove(wb.active)

    write_sheet(
        wb, "Workouts",
        ["Workout ID", "Date", "Day", "Routine", "Notes"],
        [[ids[s["date"]], s["date"], s["day_label"], s["workout"], s["note"]] for s in sessions],
        [12, 13, 12, 18, 80], {1: "yyyy-mm-dd"},
    )

    # renumber sets per workout+exercise after dropping 0-rep sets
    counter = {}
    rows = []
    for s in sets:
        key = (s["date"], s["exercise"])
        counter[key] = counter.get(key, 0) + 1
        muscle, _equip = EXERCISES[s["exercise"]]
        rows.append([ids[s["date"]], s["date"], s["workout"], s["exercise"], muscle,
                     counter[key], s["weight"], s["reps"], s["variant"], short_notes(s)])
    write_sheet(
        wb, "Sets",
        ["Workout ID", "Date", "Routine", "Exercise", "Muscle Group", "Set", "Weight (kg)",
         "Reps", "Variant", "Notes"],
        rows, [12, 13, 18, 32, 13, 6, 12, 7, 24, 45], {1: "yyyy-mm-dd", 6: "0.0#"},
    )

    used = [e for e in EXERCISES if any(s["exercise"] == e for s in sets)]
    write_sheet(
        wb, "Exercises",
        ["Exercise", "Muscle Group", "Equipment"],
        [[e, *EXERCISES[e]] for e in used], [32, 14, 12],
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"{len(sessions)} workouts, {len(rows)} sets, {len(used)} exercises -> {OUT}")


if __name__ == "__main__":
    main()
