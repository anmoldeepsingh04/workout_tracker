"""Parse the WhatsApp workout log (data/_chat.txt) and build a formatted Excel tracker.

Usage:  python3 scripts/build_tracker.py [chat_path] [output_path]
"""
import re
import sys
import datetime as dt
from collections import OrderedDict, defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, ScatterChart, Reference, Series
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.comments import Comment
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule, CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent.parent
CHAT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "_chat.txt"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "workout_tracker.xlsx"

LB_TO_KG = 0.45359237

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
ROUTINES = OrderedDict([
    ("Monday", "Push"),
    ("Tuesday", "Pull"),
    ("Wednesday", "Legs"),
    ("Thursday", "Upper Body"),
    ("Friday", "Shoulders + Arms"),
    ("Saturday", "Legs + Core"),
])

PLAN = OrderedDict([
    ("Monday — Push (Chest Priority)", [
        "Incline dumbbell press", "Machine chest press", "Low-to-high cable flies",
        "Cable lateral raises", "Shoulder press", "Overhead cable triceps extensions",
        "Triceps pushdowns", "Crunches and Russian Twists"]),
    ("Tuesday — Pull (Back/Lats Priority)", [
        "Single-arm cable lat pulldowns", "Chest-supported T-bar rows", "Lat pulldowns",
        "Straight-arm cable pullovers", "Reverse pec deck", "Incline dumbbell curls",
        "Dumbell curls with support", "Hammer curls"]),
    ("Wednesday — Legs", [
        "Hack squats", "Romanian deadlifts", "Leg press", "Leg curls (Hamstrings)",
        "Leg extensions (Quads)", "Calf raises", "Crunches and Russian Twists"]),
    ("Thursday — Upper Body (Chest + Back Priority)", [
        "Incline chest press", "Low-to-high cable flies", "Chest-supported T-bar rows",
        "Single-arm cable lat pulldowns", "Straight-arm cable pullovers",
        "Cable lateral raises", "Reverse pec deck"]),
    ("Friday — Shoulders + Arms", [
        "Cable lateral raises", "Rear delt flies", "Shoulder press",
        "Overhead cable triceps extensions", "Triceps pushdowns", "Dumbbell curls",
        "Hammer curls", "Crunches and Russian Twists"]),
    ("Saturday — Legs + Core", [
        "Romanian deadlifts", "Leg curls (Hamstrings)", "Hack squats",
        "Leg extensions (Quads)", "Calf raises", "Cable crunches", "Hanging leg raises"]),
])

# canonical name -> (muscle group, equipment). Order = display order.
EXERCISES = OrderedDict([
    ("Incline Dumbbell Press", ("Chest", "Dumbbell")),
    ("Incline Chest Press", ("Chest", "Dumbbell")),
    ("Machine Chest Press", ("Chest", "Machine")),
    ("Cable Fly (Upper Chest)", ("Chest", "Cable")),
    ("Cable Fly (Mid Chest)", ("Chest", "Cable")),
    ("Cable Fly (Lower Chest)", ("Chest", "Cable")),
    ("Single-arm Cable Lat Pulldown", ("Back", "Cable")),
    ("Lat Pulldown", ("Back", "Machine")),
    ("Chest-supported T-bar Row", ("Back", "Machine")),
    ("Seated Cable Row", ("Back", "Cable")),
    ("Straight-arm Cable Pullover", ("Back", "Cable")),
    ("Shoulder Press", ("Shoulders", "Dumbbell")),
    ("Cable Lateral Raise", ("Shoulders", "Cable")),
    ("Reverse Pec Deck", ("Shoulders", "Machine")),
    ("Rear Delt Fly", ("Shoulders", "Machine")),
    ("Triceps Pushdown", ("Triceps", "Cable")),
    ("Overhead Cable Triceps Extension", ("Triceps", "Cable")),
    ("Dumbbell Curl", ("Biceps", "Dumbbell")),
    ("Supported Dumbbell Curl", ("Biceps", "Dumbbell")),
    ("Incline Dumbbell Curl", ("Biceps", "Dumbbell")),
    ("Preacher Curl", ("Biceps", "Dumbbell")),
    ("Single-arm Preacher Curl", ("Biceps", "Dumbbell")),
    ("Hammer Curl", ("Biceps", "Dumbbell")),
    ("Dumbbell Squat", ("Legs", "Dumbbell")),
    ("Barbell Squat", ("Legs", "Barbell")),
    ("Leg Press", ("Legs", "Machine")),
    ("Romanian Deadlift", ("Legs", "Dumbbell")),
    ("Leg Extension", ("Legs", "Machine")),
    ("Leg Curl", ("Legs", "Machine")),
    ("Calf Raise", ("Legs", "Machine")),
])
MUSCLES = ["Chest", "Back", "Shoulders", "Triceps", "Biceps", "Legs"]

# raw (lowercased) header -> (canonical, variant)
HEADER_MAP = {
    "single-arm cable lat pulldowns": ("Single-arm Cable Lat Pulldown", ""),
    "chest-supported t-bar rows": ("Chest-supported T-bar Row", ""),
    "lat pulldowns": ("Lat Pulldown", ""),
    "straight-arm cable pullovers": ("Straight-arm Cable Pullover", ""),
    "reverse pec deck": ("Reverse Pec Deck", ""),
    "r reverse pec deck": ("Reverse Pec Deck", ""),
    "rear delt flies": ("Rear Delt Fly", ""),
    "incline dumbbell curls": ("Incline Dumbbell Curl", ""),
    "dumbell curls with support": ("Supported Dumbbell Curl", ""),
    "dumbell curls": ("Dumbbell Curl", ""),
    "dumbbell curls": ("Dumbbell Curl", ""),
    "hammer curls": ("Hammer Curl", ""),
    "preacher curls": ("Preacher Curl", ""),
    "tom preacher curls": ("Preacher Curl", ""),
    "single hand preacher curls": ("Single-arm Preacher Curl", ""),
    "dumbell squats": ("Dumbbell Squat", ""),
    "barbell squats": ("Barbell Squat", ""),
    "hack squats": ("Hack Squat", ""),  # logged without sets -> skipped
    "romanian deadlifts": ("Romanian Deadlift", ""),
    "leg press": ("Leg Press", ""),
    "leg press all variations": ("Leg Press", "All variations"),
    "leg curls (hamstrings)": ("Leg Curl", ""),
    "leg extensions (quads)": ("Leg Extension", ""),
    "calf raises": ("Calf Raise", ""),
    "incline dumbbell press": ("Incline Dumbbell Press", ""),
    "incline chest press": ("Incline Chest Press", ""),
    "machine chest press": ("Machine Chest Press", ""),
    "low-to-high cable flies upper chest": ("Cable Fly (Upper Chest)", "Low-to-high"),
    "low-to-high cable flies lower chest": ("Cable Fly (Lower Chest)", "Low-to-high"),
    "low-to-high cable flies mid chest": ("Cable Fly (Mid Chest)", "Low-to-high"),
    "high-to-low cable flies mid chest": ("Cable Fly (Mid Chest)", "High-to-low"),
    "high-to-low cable flies lower chest": ("Cable Fly (Lower Chest)", "High-to-low"),
    "seated rows": ("Seated Cable Row", ""),
    "cable lateral raises": ("Cable Lateral Raise", ""),
    "shoulder press": ("Shoulder Press", ""),
    "overhead cable triceps extensions": ("Overhead Cable Triceps Extension", ""),
    "triceps pushdowns": ("Triceps Pushdown", ""),
    "triceps pushdowns (with straight bar)": ("Triceps Pushdown", "Straight bar"),
}
FLY_PARENT = "low-to-high cable flies"
FLY_SUB = {"upper chest": "Cable Fly (Upper Chest)", "mid chest": "Cable Fly (Mid Chest)",
           "lower chest": "Cable Fly (Lower Chest)"}
CURL_VARIANT = {"I": "Incline (logged 'I')", "N": "Normal (logged 'N')"}

# Data-quality flags: (date, exercise) -> note shown on every set of that block
FLAGS = {
    ("12/10/26", "Cable Fly (Upper Chest)"): "Weights (15-35) far above usual 2.5-8.75 - likely a different machine/stack",
    ("12/10/26", "Cable Fly (Lower Chest)"): "Weights (15-35) far above usual 2.5-8.75 - likely a different machine/stack",
    ("12/10/26", "Cable Fly (Mid Chest)"): "Weights (15-35) far above usual 2.5-8.75 - likely a different machine/stack",
    ("13/11/26", "Single-arm Preacher Curl"): "Logged as 0 reps - set failed or skipped",
}
SESSION_FLAGS = {
    "29/10/26": "Log is identical to the 25/09 Thursday entry - possibly copy-pasted; verify",
    "25/09/26": "'Upper chest' fly block logged twice - kept as 6 sets",
}

NUM = r"\d+(?:\.\d+)?"
RE_MSG = re.compile(r"^\[(\d\d/\d\d/\d\d), (\d\d:\d\d):\d\d\] [^:]+: (.*)$")
RE_SET = re.compile(rf"^(?:([IN])\s+)?({NUM})\s*(pounds|lbs?)?\s+({NUM})\s*(?:x\s*(\d+)|(\d+)\s*sets)?$", re.I)
RE_DROP = re.compile(rf"^({NUM})\s+({NUM})\s+({NUM})\s+({NUM})$")
RE_MIXED = re.compile(rf"^mixed\s+({NUM})\s+({NUM}),\s*({NUM})\s+({NUM})$", re.I)
RE_TRAIL = re.compile(rf"^(.*?[A-Za-z].*?)\s+({NUM})\s+({NUM})$")


def num(s):
    f = float(s)
    return int(f) if f.is_integer() else f


def parse(path):
    text = path.read_text(encoding="utf-8").replace("\u200e", "")
    text = text.replace("<This message was edited>", "")
    messages = []
    for line in text.splitlines():
        m = RE_MSG.match(line)
        if m:
            messages.append([m.group(1), m.group(2), [m.group(3)]])
        elif messages:
            messages[-1][2].append(line)

    sets, sessions, skipped = [], [], []
    for date_s, time_s, lines in messages:
        title = lines[0].strip()
        day_label = title.split("—")[0].strip()
        if day_label not in ROUTINES:
            continue  # plan/template messages
        body = [l.strip() for l in lines[1:]]
        if not any(RE_SET.match(l) or RE_TRAIL.match(l) for l in body):
            continue  # template with no numbers
        date = dt.datetime.strptime(date_s, "%d/%m/%y").date()
        sess = dict(date=date, date_s=date_s, time=time_s, day_label=day_label,
                    routine=f"{day_label} — {ROUTINES[day_label]}", workout=ROUTINES[day_label],
                    note=SESSION_FLAGS.get(date_s, ""))
        if day_label != date.strftime("%A"):
            extra = f"Logged on a {date.strftime('%A')} for the {day_label} routine"
            sess["note"] = "; ".join(x for x in [sess["note"], extra] if x)
        sessions.append(sess)

        cur = None  # dict(ex, variant, note)
        fly_parent = False
        counters = defaultdict(int)
        had_sets = defaultdict(bool)

        def add(weight, reps, raw, set_type="Normal", variant=None, note="", unit_note=""):
            counters[cur["ex"]] += 1
            had_sets[cur["ex"]] = True
            notes = [n for n in [cur.get("note", ""), note, unit_note,
                                 FLAGS.get((date_s, cur["ex"]), "")] if n]
            sets.append(dict(
                date=date, routine=sess["routine"], workout=sess["workout"], exercise=cur["ex"],
                variant=variant if variant is not None else cur["variant"],
                set_no=counters[cur["ex"]], weight=weight, reps=reps, set_type=set_type,
                flagged="Yes" if FLAGS.get((date_s, cur["ex"])) or reps == 0 else "",
                notes="; ".join(notes), raw=raw))

        def start(name, variant=""):
            nonlocal cur
            cur = dict(ex=name, variant=variant, note="")
            had_sets.setdefault(name, False)

        for raw in body:
            line = raw.strip()
            if not line:
                continue
            low = line.lower()
            if line.startswith("(") and line.endswith(")"):
                cur["note"] = line.strip("()")
                continue
            if fly_parent and low in FLY_SUB:
                start(FLY_SUB[low], "Low-to-high")
                continue
            m = RE_MIXED.match(line)
            if m:
                w1, r1, w2, r2 = map(num, m.groups())
                add(w1, r1, line, "Drop set", note="Drop set - first part")
                add(w2, r2, line, "Drop set", note="Drop set - after drop")
                continue
            m = RE_DROP.match(line)
            if m:
                w1, r1, w2, r2 = map(num, m.groups())
                add(w1, r1, line, "Drop set", note="Drop set - first part")
                add(w2, r2, line, "Drop set", note="Drop set - after drop")
                continue
            m = RE_SET.match(line)
            if m and cur:
                tag, w, unit, r, x1, x2 = m.groups()
                w, r = num(w), num(r)
                n = int(x1 or x2 or 1)
                unit_note = ""
                if unit:
                    unit_note = f"Logged as {w} lb, converted to kg"
                    w = round(w * LB_TO_KG, 2)
                variant = CURL_VARIANT[tag.upper()] if tag else None
                for _ in range(n):
                    add(w, r, line, variant=variant, unit_note=unit_note)
                continue
            if low in HEADER_MAP:
                start(*HEADER_MAP[low])
                fly_parent = False
                continue
            if low == FLY_PARENT:
                fly_parent = True
                continue
            m = RE_TRAIL.match(line)
            if m:
                head = m.group(1).strip().lower()
                if head in HEADER_MAP:  # header with the first set on the same line
                    start(*HEADER_MAP[head])
                    fly_parent = False
                    add(num(m.group(2)), num(m.group(3)), line)
                    continue
                if cur and cur["ex"] == "Leg Press":  # foot-position variant line
                    variant = m.group(1).strip()
                    add(num(m.group(2)), num(m.group(3)), line, variant=variant)
                    continue
            raise ValueError(f"Unparsed line on {date_s}: {line!r}")

        for ex, ok in had_sets.items():
            if not ok:
                skipped.append((date_s, ex))
    return sessions, sets, skipped


# ---------------------------------------------------------------------------
# Styling helpers
# ---------------------------------------------------------------------------
FONT = "Arial"
NAVY = "1F3864"
ACCENT = "2E75B6"
LIGHT = "DDEBF7"
GREY = "F2F2F2"
MUSCLE_COLORS = {"Chest": "C00000", "Back": "2E75B6", "Shoulders": "ED7D31",
                 "Triceps": "7030A0", "Biceps": "00B050", "Legs": "806000"}
MUSCLE_FILLS = {"Chest": "FCE4E4", "Back": "DDEBF7", "Shoulders": "FCE9D9",
                "Triceps": "EDE2F6", "Biceps": "E2F0D9", "Legs": "F2EBD9"}
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
F_TITLE = Font(name=FONT, size=18, bold=True, color=NAVY)
F_SUB = Font(name=FONT, size=10, italic=True, color="595959")
F_H = Font(name=FONT, size=10, bold=True, color="FFFFFF")
F_SEC = Font(name=FONT, size=12, bold=True, color=NAVY)
F_B = Font(name=FONT, size=10)
F_BOLD = Font(name=FONT, size=10, bold=True)
FILL_H = PatternFill("solid", fgColor=NAVY)
FILL_LIGHT = PatternFill("solid", fgColor=LIGHT)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center")
DATE_FMT = "ddd dd mmm yy"
W_FMT = "0.0#"
VOL_FMT = "#,##0"


def header(ws, row, col, labels, fill=FILL_H, height=30):
    for i, lab in enumerate(labels):
        c = ws.cell(row=row, column=col + i, value=lab)
        c.font, c.fill, c.alignment, c.border = F_H, fill, CENTER, BORDER
    ws.row_dimensions[row].height = height


def style_range(ws, r1, r2, c1, c2, font=F_B, border=True):
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = font
            if border:
                cell.border = BORDER


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


def title(ws, text, sub=None):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws.row_dimensions[1].height = 30
    if sub:
        ws["A2"] = sub
        ws["A2"].font = F_SUB
    ws.sheet_view.showGridLines = False


def add_table(ws, ref, name, style="TableStyleMedium2"):
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name=style, showRowStripes=True)
    ws.add_table(t)


def fix_chart(ch, x_title=None, y_title=None):
    ch.roundedCorners = False
    if ch.legend is not None:
        ch.legend.overlay = False
        ch.legend.position = "b"
    if ch.title is not None:
        ch.title.overlay = False
    if x_title:
        ch.x_axis.title = x_title
        ch.x_axis.title.overlay = False
    if y_title:
        ch.y_axis.title = y_title
        ch.y_axis.title.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False


# ---------------------------------------------------------------------------
# Workbook
# ---------------------------------------------------------------------------
def build(sessions, sets, skipped):
    wb = Workbook()
    ws_dash = wb.active
    ws_dash.title = "Dashboard"
    ws_prog = wb.create_sheet("Exercise Progress")
    ws_week = wb.create_sheet("Weekly Progress")
    ws_sess = wb.create_sheet("Sessions")
    ws_exl = wb.create_sheet("Exercise Log")
    ws_set = wb.create_sheet("Set Log")
    ws_cd = wb.create_sheet("Chart Data")
    ws_plan = wb.create_sheet("Split Plan")
    ws_notes = wb.create_sheet("Notes")

    first_date = min(s["date"] for s in sessions)
    last_date = max(s["date"] for s in sessions)
    week_starts = []
    w = first_date - dt.timedelta(days=first_date.weekday())
    while w <= last_date:
        week_starts.append(w)
        w += dt.timedelta(days=7)

    # ---------------- Set Log ----------------
    ws = ws_set
    title(ws, "Set Log", "Every logged set, one row per set. Volume = Weight x Reps; Est. 1RM uses the Epley formula. Edit weights/reps here and every other sheet updates.")
    cols = ["Date", "Week Of", "Routine", "Workout", "Exercise", "Variant", "Muscle Group",
            "Equipment", "Set #", "Weight (kg)", "Reps", "Volume (kg)", "Est. 1RM (kg)",
            "Set Type", "Flagged", "Notes", "Original Log Text"]
    HR = 4
    header(ws, HR, 1, cols)
    for i, s in enumerate(sets):
        r = HR + 1 + i
        muscle, equip = EXERCISES[s["exercise"]]
        vals = [s["date"], f"=A{r}-WEEKDAY(A{r},2)+1", s["routine"], s["workout"], s["exercise"],
                s["variant"], muscle, equip, s["set_no"], s["weight"], s["reps"],
                f"=J{r}*K{r}", f'=IF(K{r}>0,ROUND(J{r}*(1+K{r}/30),1),"")', s["set_type"],
                s["flagged"], s["notes"], s["raw"]]
        for c, v in enumerate(vals, 1):
            ws.cell(row=r, column=c, value=v)
        ws.cell(row=r, column=1).number_format = DATE_FMT
        ws.cell(row=r, column=2).number_format = DATE_FMT
        ws.cell(row=r, column=10).number_format = W_FMT
        ws.cell(row=r, column=12).number_format = VOL_FMT
        ws.cell(row=r, column=13).number_format = W_FMT
        ws.cell(row=r, column=10).font = Font(name=FONT, size=10, color="0000FF")
        ws.cell(row=r, column=11).font = Font(name=FONT, size=10, color="0000FF")
    last = HR + len(sets)
    style_range(ws, HR + 1, last, 1, len(cols), border=False)
    for r in range(HR + 1, last + 1):
        for c in (10, 11):
            ws.cell(row=r, column=c).font = Font(name=FONT, size=10, color="0000FF")
        if ws.cell(row=r, column=15).value == "Yes":
            ws.cell(row=r, column=15).font = Font(name=FONT, size=10, bold=True, color="C00000")
    add_table(ws, f"A{HR}:{L(len(cols))}{last}", "SetLog")
    widths(ws, {"A": 14, "B": 13, "C": 24, "D": 16, "E": 30, "F": 22, "G": 13, "H": 11,
                "I": 7, "J": 11, "K": 7, "L": 11, "M": 11, "N": 11, "O": 9, "P": 60, "Q": 34})
    ws.freeze_panes = ws.cell(row=HR + 1, column=6)
    ws["J3"] = "Blue = values from your log"
    ws["J3"].font = Font(name=FONT, size=9, italic=True, color="0000FF")
    ws.cell(row=HR, column=13).comment = Comment(
        "Estimated one-rep max (Epley): Weight x (1 + Reps/30). Comparable within an exercise only.", "Tracker")
    ws.cell(row=HR, column=10).comment = Comment(
        "Dumbbell exercises: weight of ONE dumbbell. Machines/cables: the number on the stack, as logged. Units assumed kg.", "Tracker")

    # absolute ranges for formulas
    def rng(col):
        return f"'Set Log'!${col}${HR + 1}:${col}${last}"
    S_DATE, S_WEEK, S_EX, S_MUS = rng("A"), rng("B"), rng("E"), rng("G")
    OK = f'{rng("O")},"<>Yes"'  # criterion: exclude flagged sets
    S_W, S_R, S_VOL, S_1RM, S_WK = rng("J"), rng("K"), rng("L"), rng("M"), rng("D")

    # ---------------- Exercise Log (exercise x session) ----------------
    ws = ws_exl
    title(ws, "Exercise Log", "One row per exercise per session - the best place to filter and see how a single exercise is trending.")
    cols = ["Date", "Week Of", "Workout", "Exercise", "Muscle Group", "Sets", "Total Reps",
            "Top Weight (kg)", "Reps @ Top", "Volume (kg)", "Best Est. 1RM (kg)", "vs Last Time (kg)"]
    header(ws, HR, 1, cols)
    blocks = list(OrderedDict(((s["date"], s["exercise"]), s["workout"]) for s in sets).items())
    for i, ((d, ex), wk) in enumerate(blocks):
        r = HR + 1 + i
        crit = f"{S_DATE},$A{r},{S_EX},$D{r}"
        vals = [d, f"=A{r}-WEEKDAY(A{r},2)+1", wk, ex, EXERCISES[ex][0],
                f"=COUNTIFS({crit})", f"=SUMIFS({S_R},{crit})", f"=_xlfn.MAXIFS({S_W},{crit})",
                f"=_xlfn.MAXIFS({S_R},{crit},{S_W},H{r})", f"=SUMIFS({S_VOL},{crit})",
                f"=_xlfn.MAXIFS({S_1RM},{crit})",
                ""]
        for c, v in enumerate(vals, 1):
            ws.cell(row=r, column=c, value=v)
    elast = HR + len(blocks)
    style_range(ws, HR + 1, elast, 1, len(cols), border=False)
    for r in range(HR + 1, elast + 1):
        ws.cell(row=r, column=1).number_format = DATE_FMT
        ws.cell(row=r, column=2).number_format = DATE_FMT
        for c in (8, 11):
            ws.cell(row=r, column=c).number_format = W_FMT
        ws.cell(row=r, column=10).number_format = VOL_FMT
        ws.cell(row=r, column=12).number_format = '+0.0#;-0.0#;0'
    add_table(ws, f"A{HR}:{L(len(cols))}{elast}", "ExerciseLog")
    ws.conditional_formatting.add(f"L{HR + 1}:L{elast}", CellIsRule(operator="greaterThan", formula=["0"], font=Font(color="00B050", bold=True)))
    ws.conditional_formatting.add(f"L{HR + 1}:L{elast}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="C00000", bold=True)))
    widths(ws, {"A": 14, "B": 13, "C": 17, "D": 32, "E": 13, "F": 7, "G": 10, "H": 12,
                "I": 10, "J": 12, "K": 13, "L": 13})
    ws.freeze_panes = ws.cell(row=HR + 1, column=5)
    ws.cell(row=HR, column=12).comment = Comment("Top weight this session minus top weight the previous time you did this exercise.", "Tracker")

    # change in top weight vs the previous session of the same exercise
    for r in range(HR + 2, elast + 1):
        ws.cell(row=r, column=12).value = (
            f'=IF(COUNTIF($D${HR + 1}:$D{r - 1},$D{r})=0,"",H{r}-LOOKUP(2,1/($D${HR + 1}:$D{r - 1}=$D{r}),$H${HR + 1}:$H{r - 1}))')
    ws.cell(row=HR + 1, column=12).value = ""

    def erng(col):
        return f"'Exercise Log'!${col}${HR + 1}:${col}${elast}"
    E_DATE, E_EX, E_TOP = erng("A"), erng("D"), erng("H")

    # ---------------- Sessions ----------------
    ws = ws_sess
    title(ws, "Sessions", "One row per workout session.")
    cols = ["Date", "Week Of", "Logged At", "Routine", "Workout", "Exercises", "Sets",
            "Total Reps", "Volume (kg)", "Notes"]
    header(ws, HR, 1, cols)
    for i, s in enumerate(sessions):
        r = HR + 1 + i
        vals = [s["date"], f"=A{r}-WEEKDAY(A{r},2)+1", s["time"], s["routine"], s["workout"],
                f"=COUNTIFS({E_DATE},A{r})", f"=COUNTIFS({S_DATE},A{r})",
                f"=SUMIFS({S_R},{S_DATE},A{r})", f"=SUMIFS({S_VOL},{S_DATE},A{r})", s["note"]]
        for c, v in enumerate(vals, 1):
            ws.cell(row=r, column=c, value=v)
    slast = HR + len(sessions)
    style_range(ws, HR + 1, slast, 1, len(cols), border=False)
    for r in range(HR + 1, slast + 1):
        ws.cell(row=r, column=1).number_format = DATE_FMT
        ws.cell(row=r, column=2).number_format = DATE_FMT
        ws.cell(row=r, column=9).number_format = VOL_FMT
        for c in (3, 6, 7, 8):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    add_table(ws, f"A{HR}:{L(len(cols))}{slast}", "Sessions")
    ws.conditional_formatting.add(f"I{HR + 1}:I{slast}", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
    widths(ws, {"A": 14, "B": 13, "C": 10, "D": 30, "E": 17, "F": 10, "G": 7, "H": 11, "I": 14, "J": 70})
    ws.freeze_panes = ws.cell(row=HR + 1, column=2)

    def srng(col):
        return f"Sessions!${col}${HR + 1}:${col}${slast}"
    SS_DATE, SS_WEEK, SS_WK = srng("A"), srng("B"), srng("E")

    # ---------------- Exercise Progress ----------------
    ws = ws_prog
    title(ws, "Exercise Progress", "First vs latest session for every exercise. Top Weight = heaviest set in a session.")
    cols = ["Exercise", "Muscle Group", "Equipment", "Sessions", "Total Sets", "First Logged",
            "Last Logged", "First Top Weight (kg)", "Latest Top Weight (kg)", "Best Weight (kg)",
            "Change (kg)", "Change %", "Best Est. 1RM (kg)", "Total Volume (kg)"]
    header(ws, HR, 1, cols, height=36)
    used = [e for e in EXERCISES if any(s["exercise"] == e for s in sets)]
    for i, ex in enumerate(used):
        r = HR + 1 + i
        muscle, equip = EXERCISES[ex]
        vals = [ex, muscle, equip, f"=COUNTIFS({E_EX},A{r})", f"=COUNTIFS({S_EX},A{r})",
                f"=_xlfn.MINIFS({S_DATE},{S_EX},A{r},{OK})", f"=_xlfn.MAXIFS({S_DATE},{S_EX},A{r},{OK})",
                f"=_xlfn.MAXIFS({S_W},{S_EX},A{r},{S_DATE},F{r},{OK})",
                f"=_xlfn.MAXIFS({S_W},{S_EX},A{r},{S_DATE},G{r},{OK})",
                f"=_xlfn.MAXIFS({S_W},{S_EX},A{r},{OK})", f"=I{r}-H{r}",
                f'=IF(H{r}>0,K{r}/H{r},"")', f"=_xlfn.MAXIFS({S_1RM},{S_EX},A{r},{OK})",
                f"=SUMIFS({S_VOL},{S_EX},A{r})"]
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.font, cell.border = F_B, BORDER
        ws.cell(row=r, column=1).font = F_BOLD
        ws.cell(row=r, column=2).fill = PatternFill("solid", fgColor=MUSCLE_FILLS[muscle])
        ws.cell(row=r, column=2).font = Font(name=FONT, size=10, bold=True, color=MUSCLE_COLORS[muscle])
        for c in (6, 7):
            ws.cell(row=r, column=c).number_format = DATE_FMT
        for c in (8, 9, 10, 13):
            ws.cell(row=r, column=c).number_format = W_FMT
        ws.cell(row=r, column=11).number_format = '+0.0#;-0.0#;"-"'
        ws.cell(row=r, column=12).number_format = '+0%;-0%;"-"'
        ws.cell(row=r, column=14).number_format = VOL_FMT
        for c in range(2, 15):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    plast = HR + len(used)
    ws.conditional_formatting.add(f"L{HR + 1}:L{plast}", ColorScaleRule(
        start_type="num", start_value=-0.5, start_color="F8696B", mid_type="num", mid_value=0,
        mid_color="FFFFFF", end_type="num", end_value=1, end_color="63BE7B"))
    ws.conditional_formatting.add(f"N{HR + 1}:N{plast}", DataBarRule(start_type="num", start_value=0, end_type="max", color="5B9BD5"))
    ws.conditional_formatting.add(f"K{HR + 1}:K{plast}", CellIsRule(operator="greaterThan", formula=["0"], font=Font(color="00B050", bold=True)))
    ws.conditional_formatting.add(f"K{HR + 1}:K{plast}", CellIsRule(operator="lessThan", formula=["0"], font=Font(color="C00000", bold=True)))
    ws.auto_filter.ref = f"A{HR}:{L(len(cols))}{plast}"
    widths(ws, {"A": 32, "B": 13, "C": 11, "D": 9, "E": 9, "F": 14, "G": 14, "H": 12, "I": 12,
                "J": 11, "K": 10, "L": 10, "M": 12, "N": 13})
    ws.freeze_panes = ws.cell(row=HR + 1, column=2)
    ws.cell(row=plast + 2, column=1, value="Note: Change compares the heaviest set of your first session with the heaviest set of your latest session. Flagged sets (Set Log, Flagged = Yes) are excluded from these stats - see Notes.").font = F_SUB

    # ---------------- Weekly Progress ----------------
    ws = ws_week
    title(ws, "Weekly Progress", "Heaviest set per exercise per week (top) and weekly volume per exercise (bottom). Weeks start on Monday. Colour scale runs per exercise: red = lightest week, green = heaviest.")
    nW = len(week_starts)

    def weekly_block(start_row, label, value_formula, fmt, scale_colors):
        ws.cell(row=start_row, column=1, value=label).font = F_SEC
        hr = start_row + 1
        header(ws, hr, 1, ["Exercise", "Muscle"] + [None] * nW)
        for j, wst in enumerate(week_starts):
            c = ws.cell(row=hr, column=3 + j, value=wst)
            c.number_format = "dd mmm"
        for i, ex in enumerate(used):
            r = hr + 1 + i
            ws.cell(row=r, column=1, value=ex).font = F_BOLD
            mc = ws.cell(row=r, column=2, value=EXERCISES[ex][0])
            mc.font = Font(name=FONT, size=9, color=MUSCLE_COLORS[EXERCISES[ex][0]], bold=True)
            mc.fill = PatternFill("solid", fgColor=MUSCLE_FILLS[EXERCISES[ex][0]])
            for j in range(nW):
                col = L(3 + j)
                c = ws.cell(row=r, column=3 + j, value=value_formula(f"$A{r}", f"{col}${hr}"))
                c.number_format = fmt
                c.alignment = Alignment(horizontal="center")
            for c in range(1, 3 + nW):
                ws.cell(row=r, column=c).border = BORDER
                if c > 2:
                    ws.cell(row=r, column=c).font = F_B
            ws.conditional_formatting.add(f"C{r}:{L(2 + nW)}{r}", ColorScaleRule(
                start_type="min", start_color=scale_colors[0], mid_type="percentile", mid_value=50,
                mid_color=scale_colors[1], end_type="max", end_color=scale_colors[2]))
        return hr + len(used)

    end1 = weekly_block(4, "Top weight per week (kg)",
                        lambda ex, wk: f'=IF(COUNTIFS({S_EX},{ex},{S_WEEK},{wk},{OK})=0,"",_xlfn.MAXIFS({S_W},{S_EX},{ex},{S_WEEK},{wk},{OK}))',
                        W_FMT, ("F8696B", "FFEB84", "63BE7B"))
    weekly_block(end1 + 3, "Volume per week (kg = weight x reps, summed)",
                 lambda ex, wk: f'=IF(COUNTIFS({S_EX},{ex},{S_WEEK},{wk})=0,"",SUMIFS({S_VOL},{S_EX},{ex},{S_WEEK},{wk}))',
                 VOL_FMT, ("FFFFFF", "9DC3E6", "2E75B6"))
    widths(ws, {"A": 32, "B": 11})
    for j in range(nW):
        ws.column_dimensions[L(3 + j)].width = 9
    ws.freeze_panes = "C6"

    # ---------------- Chart Data ----------------
    ws = ws_cd
    title(ws, "Chart Data", "Helper tables that feed the Dashboard charts. Top weight per session for key lifts.")
    KEY_UPPER = ["Incline Dumbbell Press", "Shoulder Press", "Lat Pulldown", "Chest-supported T-bar Row", "Single-arm Cable Lat Pulldown"]
    KEY_LOWER = ["Leg Press", "Leg Extension", "Leg Curl", "Calf Raise"]
    KEY_ARMS = ["Dumbbell Curl", "Hammer Curl", "Triceps Pushdown", "Overhead Cable Triceps Extension"]
    series_refs = {}
    col = 1
    for ex in KEY_UPPER + KEY_LOWER + KEY_ARMS:
        dates = [d for (d, e), _ in blocks if e == ex]
        ws.cell(row=4, column=col, value=ex).font = F_SEC
        header(ws, 5, col, ["Date", "Top (kg)"])
        for i, d in enumerate(dates):
            r = 6 + i
            ws.cell(row=r, column=col, value=d).number_format = "dd mmm"
            ws.cell(row=r, column=col + 1, value=f"=_xlfn.MAXIFS({E_TOP},{E_DATE},{L(col)}{r},{E_EX},${L(col)}$4)").number_format = W_FMT
            ws.cell(row=r, column=col).font = F_B
            ws.cell(row=r, column=col + 1).font = F_B
        series_refs[ex] = (col, 6, 5 + len(dates))
        ws.column_dimensions[L(col)].width = 11
        ws.column_dimensions[L(col + 1)].width = 10
        ws.column_dimensions[L(col + 2)].width = 3
        col += 3

    # ---------------- Dashboard ----------------
    ws = ws_dash
    title(ws, "Workout Tracker — Dashboard",
          f"Logged sessions {first_date:%d %b %Y} – {last_date:%d %b %Y}. All figures are live formulas on the Set Log.")
    widths(ws, {"A": 2})
    for c in range(2, 26):
        ws.column_dimensions[L(c)].width = 12.5

    kpis = [
        ("Sessions", f"=COUNTA({SS_DATE})", "0"),
        ("Weeks Trained", f"=SUMPRODUCT(1/COUNTIF({SS_WEEK},{SS_WEEK}))", "0"),
        ("Sessions / Week", "=IF(E5>0,B5/E5,0)", "0.0"),
        ("Total Sets", f"=COUNT({S_W})", "#,##0"),
        ("Total Reps", f"=SUM({S_R})", "#,##0"),
        ("Total Volume (kg)", f"=SUM({S_VOL})", "#,##0"),
        ("Exercises Tracked", f"=COUNTA('Exercise Progress'!$A${HR + 1}:$A${plast})", "0"),
        ("Exercises Improved", f"=COUNTIF('Exercise Progress'!$K${HR + 1}:$K${plast},\">0\")", "0"),
    ]
    for i, (lab, f, fmt) in enumerate(kpis):
        c0 = 2 + (i % 4) * 3
        r0 = 4 + (i // 4) * 3
        ws.merge_cells(start_row=r0, start_column=c0, end_row=r0, end_column=c0 + 1)
        ws.merge_cells(start_row=r0 + 1, start_column=c0, end_row=r0 + 1, end_column=c0 + 1)
        lc = ws.cell(row=r0, column=c0, value=lab)
        lc.font = Font(name=FONT, size=9, bold=True, color="FFFFFF")
        lc.fill = PatternFill("solid", fgColor=ACCENT)
        lc.alignment = CENTER
        vc = ws.cell(row=r0 + 1, column=c0, value=f)
        vc.font = Font(name=FONT, size=20, bold=True, color=NAVY)
        vc.fill = FILL_LIGHT
        vc.alignment = CENTER
        vc.number_format = fmt
        ws.cell(row=r0, column=c0 + 1).fill = PatternFill("solid", fgColor=ACCENT)
        ws.cell(row=r0 + 1, column=c0 + 1).fill = FILL_LIGHT
        ws.row_dimensions[r0 + 1].height = 34

    # Weekly summary table (row 11+)
    R = 11
    ws.cell(row=R, column=2, value="Weekly Summary").font = F_SEC
    wcols = ["Week Of", "Sessions", "Sets", "Volume (kg)"] + MUSCLES
    header(ws, R + 1, 2, wcols)
    ws.cell(row=R, column=7, value="Sets per muscle group").font = Font(name=FONT, size=9, italic=True, color="595959")
    for j, wst in enumerate(week_starts):
        r = R + 2 + j
        ws.cell(row=r, column=2, value=wst).number_format = "dd mmm yy"
        ws.cell(row=r, column=3, value=f"=COUNTIFS({SS_WEEK},B{r})")
        ws.cell(row=r, column=4, value=f"=COUNTIFS({S_WEEK},B{r})")
        ws.cell(row=r, column=5, value=f"=SUMIFS({S_VOL},{S_WEEK},B{r})").number_format = VOL_FMT
        for k, m in enumerate(MUSCLES):
            ws.cell(row=r, column=6 + k, value=f'=COUNTIFS({S_WEEK},$B{r},{S_MUS},{L(6 + k)}${R + 1})')
    wlast = R + 1 + nW
    style_range(ws, R + 2, wlast, 2, 1 + len(wcols))
    for r in range(R + 2, wlast + 1):
        for c in range(2, 2 + len(wcols)):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
    tr = wlast + 1
    ws.cell(row=tr, column=2, value="Total")
    for c in range(3, 2 + len(wcols)):
        ws.cell(row=tr, column=c, value=f"=SUM({L(c)}{R + 2}:{L(c)}{wlast})")
    ws.cell(row=tr, column=5).number_format = VOL_FMT
    style_range(ws, tr, tr, 2, 1 + len(wcols), font=F_BOLD)
    for c in range(2, 2 + len(wcols)):
        ws.cell(row=tr, column=c).fill = PatternFill("solid", fgColor=GREY)
        ws.cell(row=tr, column=c).alignment = Alignment(horizontal="center")
    ws.conditional_formatting.add(f"F{R + 2}:K{wlast}", ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF", end_type="max", end_color="5B9BD5"))

    # Workout type + muscle summary (to the right)
    R2 = 11
    ws.cell(row=R2, column=14, value="By Workout").font = F_SEC
    header(ws, R2 + 1, 14, ["Workout", "Sessions", "Avg Volume (kg)", "Last Done"])
    for k, wk in enumerate(ROUTINES.values()):
        r = R2 + 2 + k
        ws.cell(row=r, column=14, value=wk)
        ws.cell(row=r, column=15, value=f"=COUNTIFS({SS_WK},N{r})")
        ws.cell(row=r, column=16, value=f'=IF(O{r}=0,"",SUMIFS({srng("I")},{SS_WK},N{r})/O{r})').number_format = VOL_FMT
        ws.cell(row=r, column=17, value=f'=IF(O{r}=0,"-",_xlfn.MAXIFS({SS_DATE},{SS_WK},N{r}))').number_format = "dd mmm yy"
    style_range(ws, R2 + 2, R2 + 1 + len(ROUTINES), 14, 17)
    for r in range(R2 + 2, R2 + 2 + len(ROUTINES)):
        for c in range(15, 18):
            ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")

    R3 = R2 + 3 + len(ROUTINES)
    ws.cell(row=R3, column=14, value="By Muscle Group").font = F_SEC
    header(ws, R3 + 1, 14, ["Muscle", "Total Sets", "Volume (kg)", "Share of Sets"])
    for k, m in enumerate(MUSCLES):
        r = R3 + 2 + k
        ws.cell(row=r, column=14, value=m).font = Font(name=FONT, size=10, bold=True, color=MUSCLE_COLORS[m])
        ws.cell(row=r, column=15, value=f"=COUNTIFS({S_MUS},N{r})").font = F_B
        ws.cell(row=r, column=16, value=f"=SUMIFS({S_VOL},{S_MUS},N{r})").number_format = VOL_FMT
        ws.cell(row=r, column=17, value=f"=IF(SUM($O${R3 + 2}:$O${R3 + 1 + len(MUSCLES)})=0,0,O{r}/SUM($O${R3 + 2}:$O${R3 + 1 + len(MUSCLES)}))").number_format = "0%"
        for c in range(14, 18):
            ws.cell(row=r, column=c).border = BORDER
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=MUSCLE_FILLS[m])
            if c > 14:
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="center")
                ws.cell(row=r, column=c).font = F_B

    # Charts ---------------------------------------------------------------
    chart_row = max(tr, R3 + 1 + len(MUSCLES)) + 3

    ch = BarChart()
    ch.type = "col"
    ch.title = "Weekly Training Volume (kg)"
    ch.add_data(Reference(ws, min_col=5, min_row=R + 1, max_row=wlast), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=R + 2, max_row=wlast))
    ch.legend = None
    fix_chart(ch, None, "kg")
    ch.series[0].graphicalProperties.solidFill = ACCENT
    ch.x_axis.number_format = "dd mmm"
    ch.height, ch.width = 8, 16
    ws.add_chart(ch, f"B{chart_row}")

    ch = BarChart()
    ch.type = "col"
    ch.grouping = "stacked"
    ch.overlap = 100
    ch.title = "Weekly Sets per Muscle Group"
    ch.add_data(Reference(ws, min_col=6, max_col=5 + len(MUSCLES), min_row=R + 1, max_row=wlast), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=R + 2, max_row=wlast))
    fix_chart(ch, None, "Sets")
    for s, m in zip(ch.series, MUSCLES):
        s.graphicalProperties.solidFill = MUSCLE_COLORS[m]
        s.graphicalProperties.line.solidFill = MUSCLE_COLORS[m]
    ch.x_axis.number_format = "dd mmm"
    ch.height, ch.width = 8, 16
    ws.add_chart(ch, f"K{chart_row}")

    palette = ["2E75B6", "C00000", "00B050", "ED7D31", "7030A0"]

    def key_chart(names, ttl, anchor):
        sc = ScatterChart()
        sc.title = ttl
        sc.style = 13
        for k, ex in enumerate(names):
            col, r1, r2 = series_refs[ex]
            xs = Reference(ws_cd, min_col=col, min_row=r1, max_row=r2)
            ys = Reference(ws_cd, min_col=col + 1, min_row=r1, max_row=r2)
            s = Series(ys, xs, title=ex)
            s.marker.symbol = "circle"
            s.marker.size = 6
            color = palette[k % len(palette)]
            s.graphicalProperties.line.solidFill = color
            s.graphicalProperties.line.width = 22000
            s.marker.graphicalProperties.solidFill = color
            s.marker.graphicalProperties.line.solidFill = color
            s.smooth = False
            sc.series.append(s)
        fix_chart(sc, None, "Top set (kg)")
        sc.x_axis.number_format = "dd mmm"
        sc.x_axis.majorGridlines = None
        sc.x_axis.scaling.min = (week_starts[0] - dt.date(1899, 12, 30)).days
        sc.x_axis.scaling.max = (last_date - dt.date(1899, 12, 30)).days + 2
        sc.height, sc.width = 9, 16
        ws.add_chart(sc, anchor)

    r2c = chart_row + 17
    key_chart(KEY_UPPER, "Key Upper-Body Lifts — Top Set per Session", f"B{r2c}")
    key_chart(KEY_LOWER, "Legs — Top Set per Session", f"K{r2c}")
    key_chart(KEY_ARMS, "Arms — Top Set per Session", f"B{r2c + 19}")

    # ---------------- Split Plan ----------------
    ws = ws_plan
    title(ws, "Split Plan", "Your 6-day split, with how often each routine has actually been logged.")
    for j, (day, exs) in enumerate(PLAN.items()):
        c = 1 + j
        hc = ws.cell(row=4, column=c, value=day)
        hc.font, hc.fill, hc.alignment, hc.border = F_H, FILL_H, CENTER, BORDER
        for i, e in enumerate(exs):
            cell = ws.cell(row=5 + i, column=c, value=e)
            cell.font, cell.border = F_B, BORDER
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            if i % 2:
                cell.fill = PatternFill("solid", fgColor=GREY)
        wk = list(ROUTINES.values())[j]
        lc = ws.cell(row=14, column=c, value=f'="Logged "&COUNTIFS({SS_WK},"{wk}")&" times"')
        lc.font = Font(name=FONT, size=10, bold=True, color=ACCENT)
        lc.alignment = CENTER
        ws.column_dimensions[L(c)].width = 30
    ws.row_dimensions[4].height = 36
    ws.cell(row=16, column=1, value="Planned but never logged with sets: Hack squats, Crunches & Russian twists, Cable crunches, Hanging leg raises. Logged but not in plan: Seated rows, Dumbbell/Barbell squats, Preacher curls, High-to-low cable flies.").font = F_SUB

    # ---------------- Notes ----------------
    ws = ws_notes
    title(ws, "Notes & Assumptions", "How the chat log was converted, and entries worth double-checking.")
    rows = [
        ("How to read", "Dashboard: overview and charts. Exercise Progress: first vs latest per exercise. Weekly Progress: week-by-week heat maps. Exercise Log / Set Log: full detail with filters."),
        ("Units", "All weights are assumed to be kg, as logged. Dumbbell weights are per dumbbell; machine/cable weights are the stack number, so volume is only comparable within the same exercise."),
        ("Pounds", "29/09 Lat pulldown set logged as '23.5 pounds' was converted to 10.66 kg."),
        ("Session date", "The date of the WhatsApp message is used as the session date. Some routines were done/logged on a different weekday (e.g. Monday-Push logged on Thu 08/10); the Routine column keeps the planned day."),
        ("Week Of", "Monday of the week the session falls in."),
        ("Est. 1RM", "Epley formula: weight x (1 + reps/30). An estimate for tracking trends, not a true max."),
        ("Drop sets", "Lines like '46 8 39 4' and 'Mixed 10 6, 7.5 3' are split into two sets with Set Type = Drop set."),
        ("Repeated sets", "'12x3', '12 x 3' and '7.5 8 3 sets' are expanded into that many identical sets."),
        ("Name clean-up", "'Tom Preacher curls', 'R Reverse pec deck', 'Dumbell' etc. are normalised. Tuesday preacher curls (two-arm) and Friday 'Single hand preacher curls' are kept separate."),
        ("Cable flies", "Grouped by target: Upper / Mid / Lower chest. Direction (Low-to-high / High-to-low) is kept in the Variant column."),
        ("Leg press", "'Leg press all variations' sets are logged under Leg Press with the foot position in the Variant column."),
        ("Dumbbell curl I / N", "Interpreted as I = Incline, N = Normal. Both are counted as Dumbbell Curl; see Variant column."),
        ("Flag: 12/10 cable flies", "Weights 15-35 vs the usual 2.5-8.75 - probably a different machine. Marked Flagged = Yes in the Set Log and excluded from Exercise Progress and the weekly top-weight heat map. Clear the flag to include them."),
        ("Flag: 13/11 preacher curls", "Logged as 7.5 kg x 0 reps (3 sets) - kept with 0 reps and flagged."),
        ("Flag: 29/10 Thursday", "Identical to the 25/09 Thursday log - may have been copy-pasted. Verify and edit in the Set Log if needed."),
        ("Flag: 25/09 flies", "'Upper chest' block appears twice in that log - kept as 6 sets."),
        ("Possible typos", "Cable fly weights of 8.25 appear next to 8.75 (12/11, 19/10); kept as logged."),
        ("Skipped", "Exercises listed with no sets: " + ", ".join(f"{e} ({d})" for d, e in skipped) + ". Plan-only messages (18/08, 08/09) are not counted as sessions."),
        ("Updating", "Add new rows to the Set Log table (date, routine, workout, exercise, weight, reps...). Or append new messages to data/_chat.txt and re-run scripts/build_tracker.py."),
    ]
    header(ws, 4, 1, ["Topic", "Detail"])
    for i, (a, b) in enumerate(rows):
        r = 5 + i
        ws.cell(row=r, column=1, value=a).font = F_BOLD
        ws.cell(row=r, column=2, value=b).font = F_B
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")
        ws.cell(row=r, column=1).alignment = Alignment(vertical="top")
        ws.cell(row=r, column=1).border = BORDER
        ws.cell(row=r, column=2).border = BORDER
        if a.startswith("Flag"):
            ws.cell(row=r, column=1).font = Font(name=FONT, size=10, bold=True, color="C00000")
    widths(ws, {"A": 26, "B": 120})

    # tab colours
    for sh, color in [(ws_dash, NAVY), (ws_prog, ACCENT), (ws_week, ACCENT), (ws_sess, "70AD47"),
                      (ws_exl, "70AD47"), (ws_set, "70AD47"), (ws_cd, "A6A6A6"),
                      (ws_plan, "ED7D31"), (ws_notes, "A6A6A6")]:
        sh.sheet_properties.tabColor = color
    return wb


if __name__ == "__main__":
    sessions, sets, skipped = parse(CHAT)
    print(f"Sessions: {len(sessions)}  Sets: {len(sets)}  Skipped: {skipped}")
    wb = build(sessions, sets, skipped)
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(f"Saved {OUT}")
