// "My week": the user's time zone, sleep hours and weekly busy times (overlap-service /me).
// Suggestions avoid these, so every change reloads "This week".

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function showWeekError(message) {
  const el = document.getElementById("myweek-error");
  el.textContent = message;
  el.hidden = !message;
}

function renderMyWeek(week) {
  const settings = document.getElementById("settings-form").elements;
  settings.time_zone.value = week.time_zone;
  settings.sleep_start.value = week.sleep_start.slice(0, 5); // "23:00:00" -> "23:00"
  settings.sleep_end.value = week.sleep_end.slice(0, 5);

  const list = document.getElementById("busy-list");
  list.replaceChildren();
  if (week.busy.length === 0) {
    list.append(el("li", "muted", "No busy times yet. Add classes, work or anything else that repeats every week."));
  }
  for (const block of week.busy) {
    const item = el("li", "busy-item");
    item.append(
      el("strong", "", DAYS[block.weekday].slice(0, 3)),
      " " + block.start.slice(0, 5) + "–" + block.end.slice(0, 5) + (block.label ? " · " + block.label : "") + " ",
    );
    const remove = button("✕", () => deleteBusy(block));
    remove.className = "icon";
    remove.title = "Remove this busy time";
    item.append(remove);
    list.append(item);
  }
}

async function loadMyWeek() {
  const content = document.getElementById("myweek-content");
  const unavailable = document.getElementById("myweek-unavailable");
  try {
    renderMyWeek(await callService("overlap", "/me"));
    content.hidden = false;
    unavailable.hidden = true;
  } catch (error) {
    content.hidden = true;
    unavailable.hidden = false;
    document.getElementById("myweek-unavailable-text").textContent = error.message;
  }
}

// Every change: show errors in this card, then reload both "My week" and "This week".
async function changeMyWeek(path, options) {
  try {
    await callService("overlap", path, options);
    showWeekError("");
    await loadMyWeek();
    loadSuggestions();
    return true;
  } catch (error) {
    showWeekError(error.message);
    return false;
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const f = event.target.elements;
  await changeMyWeek("/me", {
    method: "PUT",
    body: { time_zone: f.time_zone.value, sleep_start: f.sleep_start.value, sleep_end: f.sleep_end.value },
  });
}

async function addBusy(event) {
  event.preventDefault();
  const form = event.target;
  const f = form.elements;
  if (f.end.value <= f.start.value) {
    // Same rule as the service, checked here too so the user gets an instant answer.
    showWeekError("The end time must be after the start time.");
    return;
  }
  const body = { weekday: Number(f.weekday.value), start: f.start.value, end: f.end.value };
  if (f.label.value.trim()) body.label = f.label.value.trim();
  if (await changeMyWeek("/me/busy", { method: "POST", body })) {
    f.label.value = "";
  }
}

async function deleteBusy(block) {
  const text = DAYS[block.weekday] + " " + block.start.slice(0, 5) + "–" + block.end.slice(0, 5);
  if (!confirm("Remove your busy time on " + text + "?")) return;
  await changeMyWeek("/me/busy/" + block.id, { method: "DELETE" });
}

function setUpMyWeek() {
  const day = document.getElementById("busy-form").elements.weekday;
  DAYS.forEach((name, index) => day.append(new Option(name, index)));
  document.getElementById("settings-form").addEventListener("submit", saveSettings);
  document.getElementById("busy-form").addEventListener("submit", addBusy);
  document.getElementById("myweek-retry").addEventListener("click", loadMyWeek);
  loadMyWeek();
}
