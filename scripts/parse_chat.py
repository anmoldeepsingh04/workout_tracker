"""Parse the WhatsApp workout log (data/_chat.txt) into sessions and sets."""
import re
import sys
import datetime as dt
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAT = ROOT / "data" / "_chat.txt"

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


