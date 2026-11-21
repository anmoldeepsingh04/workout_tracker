"use strict";

const DAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const state = {
  routines: [],
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

function weekdayIndex(iso) {           // 0 = Monday
  const d = new Date(iso + "T12:00:00");
  return (d.getDay() + 6) % 7;
}

function fmtDate(iso, opts = { weekday: "short", day: "numeric", month: "short" }) {
  return new Date(iso + "T12:00:00").toLocaleDateString(undefined, opts);
}

const fmtNum = (n) => (Number.isInteger(n) ? String(n) : String(+n.toFixed(2)));
const fmtSets = (sets) => sets.map((s) => `${fmtNum(s.weight)}×${s.reps}`).join(" · ");

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
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
function renderDays() {
  const box = $("#days");
  box.replaceChildren(
    ...state.routines.map((r) =>
      el("button", {
        class: "day" + (r.id === state.routineId ? " active" : ""),
        type: "button",
        onclick: () => {
          if (r.id === state.routineId || !confirmDiscard()) return;
          state.routineId = r.id;
          loadLog();
        },
      }, el("small", {}, DAY_SHORT[r.day_of_week]), r.name)
    )
  );
}

function setRow(tbody, values = {}, placeholder = {}) {
  const n = tbody.children.length + 1;
  const weight = el("input", {
    type: "number", inputmode: "decimal", step: "any", min: "0",
    placeholder: placeholder.weight ?? "kg", "aria-label": `Set ${n} weight`,
  });
  const reps = el("input", {
    type: "number", inputmode: "numeric", step: "1", min: "1",
    placeholder: placeholder.reps ?? "reps", "aria-label": `Set ${n} reps`,
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

function exerciseCard({ name, muscle_group }, saved, last) {
  const tbody = el("tbody");
  const lastSets = last?.sets ?? [];
  const placeholderFor = (i) => lastSets[i] ?? lastSets[lastSets.length - 1] ?? {};

  if (saved?.length) {
    saved.forEach((s, i) => setRow(tbody, s, placeholderFor(i)));
  } else {
    const n = Math.max(lastSets.length, 3);
    for (let i = 0; i < n; i++) setRow(tbody, {}, placeholderFor(i));
  }

  const copyLast = () => {
    tbody.replaceChildren();
    lastSets.forEach((s, i) => setRow(tbody, s, placeholderFor(i)));
    state.dirty = true;
  };

  const card = el("div", { class: "card exercise", "data-name": name },
    el("div", { class: "card-head" },
      el("h2", {}, name),
      muscle_group ? el("span", { class: "tag" }, muscle_group) : null,
      el("button", {
        class: "icon-btn", type: "button", title: "Remove exercise from this workout",
        "aria-label": `Remove ${name}`,
        onclick: () => { card.remove(); state.dirty = true; },
      }, "×"),
    ),
    last
      ? el("div", { class: "last" },
          el("span", {}, `Last (${fmtDate(last.date, { day: "numeric", month: "short" })}): ${fmtSets(lastSets)}`),
          el("button", { class: "btn link", type: "button", onclick: copyLast }, "Copy"))
      : el("div", { class: "last" }, el("span", {}, "No previous sets")),
    el("table", { class: "sets" },
      el("thead", {}, el("tr", {}, el("th"), el("th", {}, "Weight (kg)"), el("th", {}, "Reps"), el("th"))),
      tbody),
    el("button", {
      class: "btn link add-set", type: "button",
      onclick: () => {
        const prev = tbody.lastElementChild?.querySelectorAll("input");
        const vals = prev && prev[0].value && prev[1].value
          ? { weight: +prev[0].value, reps: +prev[1].value } : {};
        const row = setRow(tbody, vals, placeholderFor(tbody.children.length));
        row.querySelector("input").focus();
        state.dirty = true;
      },
    }, "+ Add set"),
  );
  card.addEventListener("input", () => { state.dirty = true; });
  return card;
}

async function loadLog() {
  renderDays();
  const date = $("#date").value;
  const box = $("#exercises");
  const status = $("#status");
  status.className = "status";

  const routine = state.routines.find((r) => r.id === state.routineId);
  if (!routine) {
    box.replaceChildren(el("p", { class: "empty" }, "Rest day? Pick a routine above to log a workout."));
    status.textContent = "";
    $("#notes").value = "";
    state.dirty = false;
    return;
  }

  box.replaceChildren(el("p", { class: "empty" }, "Loading…"));
  const params = new URLSearchParams({ date, routine_id: routine.id });
  const saved = await api(`/api/workouts/find?${params}`);

  // exercises: what was saved for this day (if any) + the routine's template
  const list = [];
  const seen = new Set();
  const push = (e) => {
    const key = e.name.toLowerCase();
    if (!seen.has(key)) { seen.add(key); list.push(e); }
  };
  (saved?.exercises ?? []).forEach(push);
  if (!saved) routine.exercises.forEach(push);

  const lastParams = new URLSearchParams({ before: date });
  list.forEach((e) => lastParams.append("names", e.name));
  const last = list.length ? await api(`/api/last?${lastParams}`) : {};

  box.replaceChildren(...list.map((e) => exerciseCard(e, e.sets, last[e.name])));
  $("#notes").value = saved?.notes ?? "";
  status.textContent = saved
    ? `Saved workout for ${fmtDate(date)} — edit and save again to update it.`
    : `New ${routine.name} workout for ${fmtDate(date)}. Grey numbers are last time's sets.`;
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
  if (!$("#exercises .exercise")) $("#exercises").replaceChildren();
  $("#exercises").append(card);
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
      const weight = parseFloat(w.value);
      const reps = parseInt(r.value, 10);
      const wOk = w.value !== "" && weight >= 0;
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
          el("div", { class: "h-ex" }, el("b", {}, e.name), el("span", {}, fmtSets(e.sets)))),
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

function routineForDate(iso) {
  return state.routines.find((r) => r.day_of_week === weekdayIndex(iso))?.id ?? null;
}

async function init() {
  [state.routines, state.exercises] = await Promise.all([api("/api/routines"), api("/api/exercises")]);
  $("#exercise-list").replaceChildren(...state.exercises.map((e) => el("option", { value: e.name })));

  const dateInput = $("#date");
  dateInput.value = isoToday();
  let lastDate = dateInput.value;
  state.routineId = routineForDate(dateInput.value);

  dateInput.addEventListener("change", () => {
    if (!dateInput.value) { dateInput.value = lastDate; return; }
    if (!confirmDiscard()) { dateInput.value = lastDate; return; }
    lastDate = dateInput.value;
    state.routineId = routineForDate(dateInput.value) ?? state.routineId;
    loadLog().catch((e) => toast(e.message, true));
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
