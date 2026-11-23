# Workout Tracker: Ideas & Roadmap

Ideas for making the app nicer to use at the gym and more useful between sessions. Nothing here is built yet. Effort: **S** = an hour or two, **M** = a session, **L** = several sessions.

## Where the app is today

The app logs workouts by routine, shows last time's sets, follows the frozen plan (with the finisher), keeps a history, and backs itself up to GitHub. What's missing or rough:

| Pain point | Effect |
|---|---|
| The free Render server sleeps after 15 min, and waking it takes about a minute | The first open at the gym means waiting |
| Every number is typed with the keyboard | Slow and fiddly between sets, especially with sweaty hands |
| Nothing is saved until "Save workout" | Closing the tab or losing signal mid-workout loses everything |
| You can log data but not see progress | The main finding from the Nov review (most exercises flat for 8 weeks) isn't visible in the app |
| The app doesn't tell you when to add weight | The progression rule from the plan has to be remembered |
| Changing the plan means editing code | Swapping an exercise needs a code change |
| Changing the database structure needed a full rebuild last time | Risky now that real data lives in Neon |

The ideas below address these first, then add the "more value" features.

## 1. Look and feel

**Design direction:**
- **Dark theme by default** (with light as an option). Easier to read in a gym, and saves battery.
- **Big, high-contrast numbers** for weights and reps, and less small grey text.
- **A colour for each muscle group** (chest red, back blue, shoulders orange, and so on), used everywhere: tags, charts, the calendar.
- **A bottom tab bar**, which is easier to reach one-handed than the current top tabs: **Today · Log · Progress · History · Settings**.
- Short animations when a set is ticked off or a record is broken, plus a phone vibration where supported.

| Idea | Why it helps | Effort |
|---|---|---|
| **Install as a real app (PWA)**: icon, splash screen, opens full-screen without browser bars | Feels like an app on the home screen, not a website | S |
| **Dark mode**, following the phone's setting | Readable in the gym, looks modern | S |
| **Tap buttons instead of typing**: `−` / `+` buttons for weight (one equipment step) and reps (±1) | Logging a set becomes one or two taps | M |
| **Tick off sets** (✓): tapping ✓ on an empty set fills it from last time or the target | Logging an "as last time" set is one tap, and you can see where you are | M |
| **Workout progress bar** ("12 / 21 sets"), with finished exercises collapsing | Clear sense of progress, and less scrolling | S |
| **Focus mode**: one exercise full-screen, swipe to the next | Less clutter mid-workout | M |
| **Rest timer** that starts automatically after ✓: 2–3 min for compounds, 60–90 s for isolations (from the plan), with a vibration or sound when rest ends | Keeps rest consistent, and no separate timer app | M |
| **Superset view** for the Shoulders + Arms day (alternating triceps and biceps cards) | Matches how you actually train that day | M |
| **Swipe left on a set to delete it**, with an undo bar | Faster, and mistakes are recoverable | S |
| **"Waking up…" screen** instead of a blank page while the server starts | The one-minute wait doesn't look broken | S |
| **Loading placeholders and smooth transitions** between tabs | Feels faster | S |

### Sketch: logging screen

```
┌──────────────────────────────────┐
│ Day 4 · Upper Body     12/17 ▓▓▓░ │
├──────────────────────────────────┤
│ Flat Dumbbell Press     C  Chest │
│ 3 × 8–12 · last: 15×12 15×10 15×9 │
│ ↑ Try 17.5 kg today              │
│                                  │
│  1  [−] 17.5 [+]  [−] 10 [+]  ✓  │
│  2  [−] 17.5 [+]  [−]  9 [+]  ✓  │
│  3  [−] 17.5 [+]  [−] __ [+]  ○  │
│                                  │
│        ⏱ Rest 1:42 / 2:30        │
├──────────────────────────────────┤
│ Today  Log  Progress  History  ⚙ │
└──────────────────────────────────┘
```

## 2. Reliability at the gym

| Idea | Why it helps | Effort |
|---|---|---|
| **Save as you go**: each ticked set is saved immediately, and a draft is kept on the phone | Closing the tab or losing signal never loses a workout | M |
| **Offline logging**: sets are queued on the phone and sent when signal returns | Basement gyms often have no signal | L |
| **Keep the server awake** with a ping every 14 min (e.g. a free cron service or a GitHub Action), only during your training hours (e.g. 06:00–23:00) | No one-minute wait. Render's 750 free hours a month cover one always-on service, and limiting it to training hours leaves room to spare. Check Render's terms, since some hosts discourage pinging | S |
| **Show "last backup: 2 h ago"** in Settings, read from the GitHub backups branch | Confidence that backups are running, without opening GitHub | S |
| **Monthly backup test**: a GitHub Action restores the latest backup into a fresh database and checks the counts | Proves the backups actually work, before you ever need them | S |
| **Undo delete / trash**: deleted workouts are kept for 30 days | Mistakes are recoverable without restoring a backup | M |

## 3. Get more out of the data (progress and coaching)

This is where most of the extra value is. It turns the review we did in chat into something the app does continuously.

| Idea | What it shows or does | Why it helps | Effort |
|---|---|---|---|
| **Progression hints** | "Try 17.5 kg" when you hit the top of the rep range on every set last time; "Stay at 15 kg, aim for 11–12 reps" otherwise. Uses the right weight step for each equipment type | Applies the plan's double-progression rule for you, which directly fixes the stalled-weights problem | M |
| **Stall alerts** | Flags exercises with no improvement in 3+ sessions, with a suggestion (add a rep, lower the weight and build back, or swap the variation) | Catches plateaus early instead of after 8 weeks | M |
| **Personal records** | Celebrates a new heaviest weight, best estimated one-rep max, or more reps at a weight, right after saving | Motivation, and visible progress | S |
| **Exercise page** | Tap any exercise to see a chart of heaviest set, estimated one-rep max and volume over time, your records, and the full history | Answers "am I getting stronger at this?" instantly | M |
| **Weekly dashboard** | Sessions this week (out of 6), sets per muscle group compared with the plan's targets (chest 15, back 17, …), volume trend | Shows whether the week matched the plan | M |
| **Consistency calendar** | A GitHub-style grid of training days, coloured by routine, with your streak | Consistency was the biggest issue in Sep–Nov | S |
| **Rotation tracker** | "Cycle 3 · Day 4 of 6", which days were skipped, and automatically suggesting **Full Body** after 2+ missed days (the plan's rule) | Keeps the rotation honest without thinking about it | S |
| **Easier-week reminders** | A reminder after 6–8 weeks, plus an "easy week" mode that halves the planned sets | Follows the plan's recovery rule | S |
| **Effort per set (reps in reserve)**, optional | Tap 0 / 1 / 2 / 3+ reps left after a set | Checks the "1–2 reps in reserve" rule, and makes the progression hints smarter | S |
| **Session time** | Start and end time recorded automatically | Spot sessions running long, and compare duration with performance | S |
| **Finisher progress** | Farmer walk weight (20 → 24 → 30 kg per hand), plank time, crunch progression | The finisher's progression plan becomes visible too | S |
| **Monthly report** | One page per month: sessions, records, biggest improvements, stalls, volume per muscle | A quick review, like the one we did in chat | M |

### Later ideas in this area
- **Body tracking:** bodyweight and measurements (waist, arms, chest), so you can compare them with training. Progress photos would need storage beyond the free tiers, so they're probably best kept on the phone.
- **Readiness check:** sleep, energy and soreness (1–5) before a session, compared with performance over time.
- **AI weekly review:** a scheduled job sends the week's data to Claude and returns a short review with suggestions, like our chat analysis. It would need an API key and costs a little per review.

## 4. Plan management

| Idea | Why it helps | Effort |
|---|---|---|
| **Edit the plan in the app**: routines, exercises, order, sets × reps targets, notes | Change the plan without code changes | L |
| **Plan versions** ("Plan v1, frozen 21 Nov 2026"), kept when the plan changes | Progress can be compared across plan changes, and you can see what you were doing when | M |
| **Swap an exercise on the spot**, e.g. when a machine is busy: a list of alternatives for each exercise, saved for that session only | Gym reality without breaking the plan | M |
| **Exercise library**: rename, merge duplicates (e.g. Rear Delt Fly and Reverse Pec Deck are the same machine), hide old exercises | Cleaner data and charts | M |
| ~~**Machine notes**~~ **Done (23 Nov):** the ⚙ line on each exercise card | No more re-figuring settings every session | S |
| **Weight steps for each exercise**: dumbbells in 2.5 kg steps, a cable stack's actual steps (e.g. 3.75 / 6.25 / 8.75), a kg/lb switch | The `−` / `+` buttons and progression hints use real, available weights | S |
| **Form cues and video links** on each exercise card | Useful when starting new exercises (Romanian deadlift, hip thrust) | S |
| **Warm-up sets**, marked as such | Logged, but kept out of the stats | S |

## 5. Foundations (needed before the bigger features)

| Idea | Why | Effort |
|---|---|---|
| **Database migrations** (Alembic) | Lets the database structure change safely without a rebuild. **Needed before any feature that changes the database** (effort per set, plan versions, machine notes, …) | M |
| **Run the tests on every push**, and have Render deploy only when they pass | A broken change never reaches the live app | S |
| **A browser test of the main flow** (open, log a set, save, check History) | The current tests cover only the server, not the page | M |
| **Error tracking** (e.g. Sentry's free tier) | You'd find out about crashes before noticing them at the gym | S |
| **Organise the front-end code** into separate parts (cards, timer, charts), or move to a light framework (Preact or Svelte) once the screens grow | The single `app.js` file will get hard to work with | M–L |
| **Face ID / fingerprint login (passkeys)** instead of a password | Faster and more secure on the phone | M |

## 6. Optional extras

- **Public progress page**, read-only: your data is public on GitHub anyway, so a nice read-only page of your stats could be fun to share. Editing would still need the password.
- **Logging by voice** ("seventeen and a half for ten"), using the browser's built-in speech recognition.
- **Gym reminders** as phone notifications. On iPhone this needs the app installed to the home screen (the PWA idea).
- **Export to Apple Health / Google Fit**, or add sessions to your calendar.

## Suggested order

| Phase | What | Why this order |
|---|---|---|
| **0. Foundations** | Database migrations, tests on every push | Everything after this changes the database, so it has to be safe first |
| **1. Better in the gym** | PWA install, dark mode, `−` / `+` buttons, tick-off sets with automatic saving, rest timer, keep-awake ping | Daily improvement, every session |
| **2. Progress you can see** | Progression hints, records, exercise pages with charts, consistency calendar, rotation tracker | Turns logging into feedback, and attacks the stalled-weights problem |
| **3. Smarter coaching** | Stall alerts, weekly dashboard compared with plan targets, effort per set, easier-week mode, finisher progress, monthly report | Deeper insight once there's a few weeks of richer data |
| **4. Flexibility** | Edit the plan in the app, plan versions, exercise swaps, machine notes, exercise library | Needed once the plan starts changing |
| **5. Extras** | Offline mode, passkeys, AI weekly review, public page, voice, health export | Nice to have |

## Questions to decide before building

1. **iPhone or Android?** It affects home-screen install, notifications and vibration support.
2. **How bad is the signal at your gym?** If it's poor, offline logging moves up to phase 1.
3. **Keep-awake ping, or accept the one-minute wait?** Alternatively, a cheap paid instance removes the wait.
4. **Would you tap "reps left" after each set?** It makes the hints much smarter, but it's one more tap per set.
5. **Dark theme only, or also light?**
6. **Which progress numbers matter most to you:** heaviest set, estimated one-rep max, volume, or bodyweight?
