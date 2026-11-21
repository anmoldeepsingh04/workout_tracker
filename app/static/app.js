"use strict";

const state = {
  routines: [],
  exercises: [],
  finisherNote: "",
  nextUpId: null,
  routineId: null,
  dirty: false,
};

// ------------------------------------------------------------------ utils
const $ = (sel) => document.querySelector(sel);

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function isoToday() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function fmtDate(iso, opts = { weekday: "short", day: "numeric", month: "short" }) {
  return new Date(iso + "T12:00:00").toLocaleDateString(undefined, opts);
}

const fmtNum = (n) => (Number.isInteger(n) ? String(n) : String(+n.toFixed(2)));
function fmtSet(s, unit = "reps") {
  const amount = unit === "seconds" ? `${s.reps}s` : String(s.reps);
  return s.weight ? `${fmtNum(s.weight)}×${amount}` : amount;
}
const fmtSets = (sets, unit) => sets.map((s) => fmtSet(s, unit)).join(" · ");
const fmtTarget = (t) => (t ?? "").replace("-", "–");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 401) {
    location.href = "/login";
    throw new Error("Logged out");
  }
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((d) => d.msg).join(", ");
    } catch (_) { /* ignore */ }
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("error", isError);
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

function confirmDiscard() {
  return !state.dirty || confirm("You have unsaved changes. Discard them?");
}

// ------------------------------------------------------------------ log view
function routineLabel(r) {
  const prefix = r.kind === "split" ? `Day ${r.position} · ` : "";
  const next = r.id === state.nextUpId ? "  (next up)" : "";
  return `${prefix}${r.name}${r.focus ? ` — ${r.focus}` : ""}${next}`;
}

function renderRoutineSelect() {
  const option = (r) => el("option", { value: r.id }, routineLabel(r));
  const split = state.routines.filter((r) => r.kind === "split");
  const backup = state.routines.filter((r) => r.kind !== "split");
  $("#routine").replaceChildren(
    el("option", { value: "" }, "Select a workout…"),
    el("optgroup", { label: "Split (do in order)" }, ...split.map(option)),
    backup.length ? el("optgroup", { label: "Backup" }, ...backup.map(option)) : null,
  );
  syncRoutineSelect();
}

// Next split day after the most recent split workout (rotation, not weekday).
async function computeNextUp() {
  const split = state.routines.filter((r) => r.kind === "split");
  const recent = await api("/api/workouts?limit=30");
  const lastSplit = recent.find((w) => split.some((r) => r.id === w.routine_id));
  if (!lastSplit) { state.nextUpId = split[0]?.id ?? null; return; }
  const i = split.findIndex((r) => r.id === lastSplit.routine_id);
  state.nextUpId = split[(i + 1) % split.length].id;
}

function syncRoutineSelect() {
  const sel = $("#routine");
  sel.value = state.routineId ?? "";
  sel.classList.toggle("unset", state.routineId === null);
}

// If a workout is already saved for this date, select its routine.
async function routineSavedOn(date) {
  const saved = await api(`/api/workouts?${new URLSearchParams({ date })}`);
  return saved.length ? saved[0].routine_id : null;
}

function setRow(tbody, values = {}, placeholder = {}, opts = {}) {
  const n = tbody.children.length + 1;
  const weightPh = placeholder.weight ? fmtNum(placeholder.weight) : (opts.bodyweight ? "BW" : "kg");
  const weight = el("input", {
    type: "number", inputmode: "decimal", step: "any", min: "0",
    placeholder: weightPh, "aria-label": `Set ${n} weight`,
  });
  const reps = el("input", {
    type: "number", inputmode: "numeric", step: "1", min: "1",
    placeholder: placeholder.reps ?? opts.repsHint ?? (opts.seconds ? "sec" : "reps"),
    "aria-label": `Set ${n} ${opts.seconds ? "seconds" : "reps"}`,
  });
  if (values.weight !== undefined) weight.value = fmtNum(values.weight);
  if (values.reps !== undefined) reps.value = values.reps;
  const row = el("tr", {},
    el("td", { class: "num" }, n),
    el("td", {}, weight),
    el("td", {}, reps),
    el("td", { class: "rm" }, el("button", {
      class: "icon-btn", type: "button", title: "Remove set", "aria-label": "Remove set",
      onclick: () => { row.remove(); renumber(tbody); state.dirty = true; },
    }, "×")),
  );
  tbody.append(row);
  return row;
}

function renumber(tbody) {
  [...tbody.children].forEach((tr, i) => { tr.firstChild.textContent = i + 1; });
}

function exerciseCard(ex, saved, last) {
  const { name, muscle_group, kind, unit, equipment, sets, target, note } = ex;
  const seconds = unit === "seconds";
  const bodyweight = equipment === "Bodyweight";
  const repsHint = target && /^\d/.test(target) && !seconds ? fmtTarget(target) : null;
  const opts = { seconds, bodyweight, repsHint };

  const tbody = el("tbody");
  const lastSets = last?.sets ?? [];
  const placeholderFor = (i) => lastSets[i] ?? lastSets[lastSets.length - 1] ?? {};
  const addRow = (vals, i) => setRow(tbody, vals, placeholderFor(i), opts);

  if (saved?.length) {
    saved.forEach((s, i) => addRow(s, i));
  } else {
    const n = sets ?? Math.max(lastSets.length, 3);
    for (let i = 0; i < n; i++) addRow({}, i);
  }

  const copyLast = () => {
    tbody.replaceChildren();
    lastSets.forEach((s, i) => addRow(s, i));
    state.dirty = true;
  };

  const planBits = [
    sets && target ? `${sets} × ${fmtTarget(target)}` : null,
    kind ? kind[0].toUpperCase() + kind.slice(1) : null,
  ].filter(Boolean);

  const card = el("div", {
    class: "card exercise", "data-name": name, "data-bw": bodyweight ? "1" : "",
  },
    el("div", { class: "card-head" },
      el("h2", {}, name),
      kind ? el("span", { class: `kind ${kind}`, title: kind }, kind === "compound" ? "C" : "I") : null,
      muscle_group ? el("span", { class: "tag" }, muscle_group) : null,
      el("button", {
        class: "icon-btn", type: "button", title: "Remove exercise from this workout",
        "aria-label": `Remove ${name}`,
        onclick: () => { card.remove(); state.dirty = true; },
      }, "×"),
    ),
    planBits.length || note
      ? el("div", { class: "plan" },
          planBits.length ? el("strong", {}, planBits.join(" · ")) : null,
          note ? el("span", {}, note) : null)
      : null,
    last
      ? el("div", { class: "last" },
          el("span", {}, `Last (${fmtDate(last.date, { day: "numeric", month: "short" })}): ${fmtSets(lastSets, unit)}`),
          el("button", { class: "btn link", type: "button", onclick: copyLast }, "Copy"))
      : el("div", { class: "last" }, el("span", {}, "No previous sets")),
    el("table", { class: "sets" },
      el("thead", {}, el("tr", {}, el("th"),
        el("th", {}, bodyweight ? "Weight (kg, blank = BW)" : seconds ? "Weight (kg/hand)" : "Weight (kg)"),
        el("th", {}, seconds ? "Seconds" : "Reps"), el("th"))),
      tbody),
    el("button", {
      class: "btn link add-set", type: "button",
      onclick: () => {
        const prev = tbody.lastElementChild?.querySelectorAll("input");
        const vals = prev && prev[1].value
          ? { weight: prev[0].value === "" ? undefined : +prev[0].value, reps: +prev[1].value } : {};
        const row = addRow(vals, tbody.children.length);
        row.querySelector("input").focus();
        state.dirty = true;
      },
    }, "+ Add set"),
  );
  card.addEventListener("input", () => { state.dirty = true; });
  return card;
}

function finisherHeader() {
  return el("div", { class: "section-head" },
    el("h3", {}, "Finisher"),
    state.finisherNote ? el("p", {}, state.finisherNote) : null);
}

async function loadLog() {
  syncRoutineSelect();
  const date = $("#date").value;
  const box = $("#exercises");
  const status = $("#status");
  status.className = "status";

  const routine = state.routines.find((r) => r.id === state.routineId);
  if (!routine) {
    box.replaceChildren(el("p", { class: "empty" }, "Choose what you\u2019re hitting today to load its exercises."));
    status.textContent = "";
    $("#notes").value = "";
    state.dirty = false;
    return;
  }

  box.replaceChildren(el("p", { class: "empty" }, "Loading…"));
  const params = new URLSearchParams({ date, routine_id: routine.id });
  const saved = await api(`/api/workouts/find?${params}`);

  // exercises: what was saved for this day, or the routine's plan. Plan info (sets x reps,
  // notes, finisher section) is attached to saved exercises too.
  const planByName = new Map(routine.exercises.map((e) => [e.name.toLowerCase(), e]));
  const catalog = new Map(state.exercises.map((e) => [e.name.toLowerCase(), e]));
  const source = saved ? saved.exercises : routine.exercises;
  const list = [];
  const seen = new Set();
  for (const e of source) {
    const key = e.name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    list.push({ ...catalog.get(key), ...planByName.get(key), ...e, sets: saved ? undefined : e.sets,
                savedSets: saved ? e.sets : null, section: planByName.get(key)?.section ?? "main" });
  }
  list.sort((a, b) => (a.section === "finisher") - (b.section === "finisher"));

  const lastParams = new URLSearchParams({ before: date });
  list.forEach((e) => lastParams.append("names", e.name));
  const last = list.length ? await api(`/api/last?${lastParams}`) : {};

  const cards = [];
  list.forEach((e, i) => {
    if (e.section === "finisher" && list[i - 1]?.section !== "finisher") cards.push(finisherHeader());
    cards.push(exerciseCard(e, e.savedSets, last[e.name]));
  });
  box.replaceChildren(...cards);
  $("#notes").value = saved?.notes ?? "";
  status.textContent = saved
    ? `Saved workout for ${fmtDate(date)} — edit and save again to update it.`
    : `New ${routine.name} workout for ${fmtDate(date)}. Grey numbers are last time's sets; C = compound, I = isolation.`;
  if (saved) status.classList.add("saved");
  state.dirty = false;
}

async function addExercise() {
  const input = $("#new-exercise");
  const name = input.value.trim();
  if (!name) return;
  const exists = [...document.querySelectorAll(".exercise")]
    .some((c) => c.dataset.name.toLowerCase() === name.toLowerCase());
  if (exists) { toast("Already in this workout"); return; }

  const known = state.exercises.find((e) => e.name.toLowerCase() === name.toLowerCase());
  const params = new URLSearchParams({ before: $("#date").value });
  params.append("names", known?.name ?? name);
  const last = await api(`/api/last?${params}`);
  const ex = known ?? { name, muscle_group: null };
  const card = exerciseCard(ex, null, last[ex.name]);
  const box = $("#exercises");
  if (!box.querySelector(".exercise")) box.replaceChildren();
  const finisher = box.querySelector(".section-head");
  if (finisher) box.insertBefore(card, finisher); else box.append(card);
  input.value = "";
  state.dirty = true;
  card.querySelector("input").focus();
}

function collect() {
  let valid = true;
  const exercises = [];
  document.querySelectorAll(".exercise").forEach((card) => {
    const sets = [];
    card.querySelectorAll("tbody tr").forEach((tr) => {
      const [w, r] = tr.querySelectorAll("input");
      w.classList.remove("invalid");
      r.classList.remove("invalid");
      if (!w.value && !r.value) return;              // untouched row
      const bw = card.dataset.bw === "1";
      const weight = w.value === "" && bw ? 0 : parseFloat(w.value);
      const reps = parseInt(r.value, 10);
      const wOk = (w.value !== "" || bw) && weight >= 0;
      const rOk = r.value !== "" && reps >= 1;
      if (!wOk) w.classList.add("invalid");
      if (!rOk) r.classList.add("invalid");
      if (wOk && rOk) sets.push({ weight, reps });
      else valid = false;
    });
    if (sets.length) exercises.push({ name: card.dataset.name, sets });
  });
  return { valid, exercises };
}

async function save() {
  const { valid, exercises } = collect();
  if (!valid) { toast("Fill in both weight and reps (or clear the row)", true); return; }
  if (!exercises.length) { toast("Nothing to save yet", true); return; }

  const btn = $("#save");
  btn.disabled = true;
  try {
    await api("/api/workouts", {
      method: "PUT",
      body: JSON.stringify({
        date: $("#date").value,
        routine_id: state.routineId,
        notes: $("#notes").value.trim() || null,
        exercises,
      }),
    });
    const sets = exercises.reduce((n, e) => n + e.sets.length, 0);
    toast(`Saved ✓ ${exercises.length} exercises, ${sets} sets`);
    state.dirty = false;
    await computeNextUp();
    renderRoutineSelect();
    await loadLog();
  } catch (err) {
    toast(err.message, true);
  } finally {
    btn.disabled = false;
  }
}

// ------------------------------------------------------------------ history view
async function loadHistory() {
  const box = $("#history");
  box.replaceChildren(el("p", { class: "empty" }, "Loading…"));
  const items = await api("/api/workouts?limit=200");
  if (!items.length) {
    box.replaceChildren(el("p", { class: "empty" }, "No workouts logged yet."));
    return;
  }
  box.replaceChildren(...items.map(historyCard));
}

function historyCard(w) {
  const detail = el("div", { class: "h-detail", hidden: true });
  const card = el("div", { class: "card h-item" },
    el("div", { class: "h-top" },
      el("strong", {}, w.routine_name ?? "Workout"),
      el("span", { class: "h-date" }, fmtDate(w.date, { weekday: "short", day: "numeric", month: "short", year: "numeric" }))),
    el("div", { class: "h-meta" },
      `${w.exercise_count} exercises · ${w.set_count} sets · ${Math.round(w.volume).toLocaleString()} kg volume`),
    detail,
  );
  card.addEventListener("click", async (ev) => {
    if (ev.target.closest(".h-actions")) return;
    if (!detail.hidden) { detail.hidden = true; return; }
    if (!detail.childElementCount) {
      const full = await api(`/api/workouts/${w.id}`);
      detail.append(
        ...full.exercises.map((e) =>
          el("div", { class: "h-ex" }, el("b", {}, e.name), el("span", {}, fmtSets(e.sets, e.unit)))),
        full.notes ? el("p", { class: "h-meta" }, full.notes) : null,
        el("div", { class: "h-actions" },
          el("button", { class: "btn secondary", type: "button", onclick: () => editWorkout(w) }, "Edit"),
          el("button", { class: "btn danger", type: "button", onclick: () => deleteWorkout(w, card) }, "Delete")),
      );
    }
    detail.hidden = false;
  });
  return card;
}

function editWorkout(w) {
  if (!confirmDiscard()) return;
  $("#date").value = w.date;
  state.routineId = w.routine_id;
  showView("log");
  loadLog();
}

async function deleteWorkout(w, card) {
  if (!confirm(`Delete ${w.routine_name ?? "workout"} on ${fmtDate(w.date)}? This can't be undone.`)) return;
  try {
    await api(`/api/workouts/${w.id}`, { method: "DELETE" });
    card.remove();
    toast("Workout deleted");
  } catch (err) {
    toast(err.message, true);
  }
}

// ------------------------------------------------------------------ navigation
function showView(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
  $("#view-log").hidden = name !== "log";
  $("#view-history").hidden = name !== "history";
  $(".savebar").hidden = name !== "log";
  if (name === "history") loadHistory().catch((e) => toast(e.message, true));
}

async function init() {
  let plan;
  [state.routines, state.exercises, plan] = await Promise.all(
    [api("/api/routines"), api("/api/exercises"), api("/api/plan")]);
  state.finisherNote = plan.finisher_note;
  $("#exercise-list").replaceChildren(...state.exercises.map((e) => el("option", { value: e.name })));

  await computeNextUp();
  renderRoutineSelect();

  const dateInput = $("#date");
  dateInput.value = isoToday();
  let lastDate = dateInput.value;
  state.routineId = await routineSavedOn(dateInput.value);

  $("#routine").addEventListener("change", (e) => {
    const id = e.target.value ? Number(e.target.value) : null;
    if (id === state.routineId) return;
    if (!confirmDiscard()) { syncRoutineSelect(); return; }
    state.routineId = id;
    loadLog().catch((err) => toast(err.message, true));
  });

  dateInput.addEventListener("change", async () => {
    if (!dateInput.value) { dateInput.value = lastDate; return; }
    if (!confirmDiscard()) { dateInput.value = lastDate; return; }
    lastDate = dateInput.value;
    try {
      state.routineId = (await routineSavedOn(dateInput.value)) ?? state.routineId;
      await loadLog();
    } catch (e) { toast(e.message, true); }
  });
  document.querySelectorAll(".tab").forEach((t) =>
    t.addEventListener("click", () => showView(t.dataset.view)));
  $("#save").addEventListener("click", save);
  $("#add-exercise-btn").addEventListener("click", () => addExercise().catch((e) => toast(e.message, true)));
  $("#new-exercise").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addExercise().catch((err) => toast(err.message, true)); }
  });
  $("#notes").addEventListener("input", () => { state.dirty = true; });
  window.addEventListener("beforeunload", (e) => { if (state.dirty) e.preventDefault(); });

  await loadLog();
}

init().catch((e) => toast(e.message, true));
