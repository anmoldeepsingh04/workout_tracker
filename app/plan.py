"""The frozen training plan (see docs/workout_plan.md). Used to seed the database."""

C, I = "compound", "isolation"
REPS, SECS = "reps", "seconds"

# name: (muscle group, equipment, kind, unit)
EXERCISES = {
    # chest
    "Incline Dumbbell Press": ("Chest", "Dumbbell", C, REPS),
    "Flat Dumbbell Press": ("Chest", "Dumbbell", C, REPS),
    "Incline Chest Press": ("Chest", "Dumbbell", C, REPS),
    "Machine Chest Press": ("Chest", "Machine", C, REPS),
    "Low-to-High Cable Fly": ("Chest", "Cable", I, REPS),
    "High-to-Low Cable Fly": ("Chest", "Cable", I, REPS),
    "Cable Fly (Mid Chest)": ("Chest", "Cable", I, REPS),
    "Cable Fly (Lower Chest)": ("Chest", "Cable", I, REPS),
    # back
    "Lat Pulldown": ("Back", "Machine", C, REPS),
    "Single-arm Cable Lat Pulldown": ("Back", "Cable", C, REPS),
    "Chest-supported T-bar Row": ("Back", "Machine", C, REPS),
    "Seated Cable Row": ("Back", "Cable", C, REPS),
    "Straight-arm Cable Pullover": ("Back", "Cable", I, REPS),
    # shoulders
    "Shoulder Press": ("Shoulders", "Dumbbell", C, REPS),
    "Cable Lateral Raise": ("Shoulders", "Cable", I, REPS),
    "Reverse Pec Deck": ("Shoulders", "Machine", I, REPS),
    "Rear Delt Fly": ("Shoulders", "Machine", I, REPS),
    # arms
    "Triceps Pushdown": ("Triceps", "Cable", I, REPS),
    "Overhead Cable Triceps Extension": ("Triceps", "Cable", I, REPS),
    "Dumbbell Curl": ("Biceps", "Dumbbell", I, REPS),
    "Hammer Curl": ("Biceps", "Dumbbell", I, REPS),
    "Single-arm Preacher Curl": ("Biceps", "Dumbbell", I, REPS),
    "Preacher Curl": ("Biceps", "Dumbbell", I, REPS),
    "Incline Dumbbell Curl": ("Biceps", "Dumbbell", I, REPS),
    "Supported Dumbbell Curl": ("Biceps", "Dumbbell", I, REPS),
    # legs
    "Barbell Squat": ("Legs", "Barbell", C, REPS),
    "Dumbbell Squat": ("Legs", "Dumbbell", C, REPS),
    "Leg Press": ("Legs", "Machine", C, REPS),
    "Hack Squat": ("Legs", "Machine", C, REPS),
    "Bulgarian Split Squat": ("Legs", "Dumbbell", C, REPS),
    "Romanian Deadlift": ("Legs", "Dumbbell", C, REPS),
    "Hip Thrust": ("Legs", "Barbell", C, REPS),
    "Leg Extension": ("Legs", "Machine", I, REPS),
    "Leg Curl": ("Legs", "Machine", I, REPS),
    "Calf Raise": ("Legs", "Machine", I, REPS),
    # core / finisher
    "Hanging Leg Raise": ("Core", "Bodyweight", I, REPS),
    "Farmer Walk": ("Full body", "Dumbbell", C, SECS),
    "Suitcase Carry": ("Core", "Dumbbell", C, SECS),
    "Floor Crunch": ("Core", "Bodyweight", I, REPS),
    "Superman": ("Core", "Bodyweight", I, REPS),
    "Side Heel Touch": ("Core", "Bodyweight", I, REPS),
    "Plank": ("Core", "Bodyweight", I, SECS),
    "Dead Bug": ("Core", "Bodyweight", I, REPS),
}

# Done after every workout. (name, sets, target, note)
FINISHER = [
    ("Farmer Walk", 5, "~45 s", "20 kg each hand, ~60 s rest. Suitcase carry on 1-2 days/week (optional)"),
    ("Floor Crunch", 1, "20", "Slow: 3 s up, 3 s down. Hold a plate when easy"),
    ("Superman", 1, "12-15", "Face down, hold 1-2 s at the top"),
    ("Side Heel Touch", 1, "20", "Or a 30-45 s plank / dead bugs on 2-3 days a week"),
]
FINISHER_NOTE = "Finish with 5 min stretching: cat-cow and full-body yoga stretch."

INCLINE = "Bench at about 30° (15-30° is fine). Steeper shifts the work to the front delts"

# (position, name, focus, kind, [(exercise, sets, target, note)])
ROUTINES = [
    (1, "Push", "Chest priority", "split", [
        ("Incline Dumbbell Press", 3, "8-12", INCLINE),
        ("Machine Chest Press", 3, "8-12", None),
        ("Shoulder Press", 3, "8-12", None),
        ("Low-to-High Cable Fly", 3, "12-15", None),
        ("Cable Lateral Raise", 3, "12-20", None),
        ("Triceps Pushdown", 3, "10-15", None),
        ("Overhead Cable Triceps Extension", 3, "10-15", None),
    ]),
    (2, "Pull", "Lats priority", "split", [
        ("Lat Pulldown", 3, "8-12", None),
        ("Chest-supported T-bar Row", 3, "8-12", None),
        ("Single-arm Cable Lat Pulldown", 3, "10-12", None),
        ("Straight-arm Cable Pullover", 2, "12-15", None),
        ("Reverse Pec Deck", 3, "12-15", None),
        ("Dumbbell Curl", 3, "8-12", None),
        ("Hammer Curl", 3, "10-12", None),
    ]),
    (3, "Legs", "Quad focus", "split", [
        ("Barbell Squat", 3, "6-10", None),
        ("Leg Press", 3, "10-12", "One foot position, straight sets"),
        ("Leg Extension", 3, "12-15", None),
        ("Leg Curl", 3, "10-12", None),
        ("Calf Raise", 4, "10-15", "Standing"),
    ]),
    (4, "Upper Body", "Chest + back", "split", [
        ("Flat Dumbbell Press", 3, "8-12", "Start around 15-17.5 kg per dumbbell"),
        ("Seated Cable Row", 3, "8-12", None),
        ("Single-arm Cable Lat Pulldown", 3, "10-12", None),
        ("High-to-Low Cable Fly", 3, "12-15", None),
        ("Cable Lateral Raise", 3, "12-20", None),
        ("Reverse Pec Deck", 2, "12-15", None),
    ]),
    (5, "Shoulders + Arms", "Delts, biceps, triceps", "split", [
        ("Shoulder Press", 3, "8-12", None),
        ("Cable Lateral Raise", 4, "12-20", None),
        ("Rear Delt Fly", 3, "12-15", None),
        ("Overhead Cable Triceps Extension", 3, "10-15", "Can alternate with biceps sets, 60 s rest per pair"),
        ("Triceps Pushdown", 3, "10-15", None),
        ("Single-arm Preacher Curl", 3, "10-12", None),
        ("Dumbbell Curl", 3, "8-12", None),
    ]),
    (6, "Legs + Core", "Hamstrings / glutes focus", "split", [
        ("Romanian Deadlift", 3, "8-10", "Start light, focus on the hip hinge"),
        ("Hack Squat", 3, "8-12", "Or Bulgarian split squat"),
        ("Hip Thrust", 3, "8-12", None),
        ("Leg Curl", 3, "10-12", None),
        ("Calf Raise", 4, "10-15", "Standing"),
        ("Hanging Leg Raise", 3, "max", None),
    ]),
    (7, "Full Body", "Catch-up after missing 2+ days", "backup", [
        ("Barbell Squat", 3, "6-10", None),
        ("Romanian Deadlift", 2, "8-10", None),
        ("Incline Dumbbell Press", 3, "8-12", INCLINE),
        ("Lat Pulldown", 3, "8-12", None),
        ("Seated Cable Row", 2, "10-12", None),
        ("Cable Lateral Raise", 2, "12-20", None),
        ("Dumbbell Curl", 2, "10-12", "Alternate with triceps pushdown"),
        ("Triceps Pushdown", 2, "10-12", None),
    ]),
]
