// "This week": who to call and when, from overlap-service GET /suggestions.
// The service sends UTC times; they are shown in the user's time zone (and the contact's).

function timeIn(value, timeZone) {
  return new Intl.DateTimeFormat([], { timeZone, hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

// "2026-11-22": the calendar day of a moment in a time zone, used to put windows in columns.
function dayKey(value, timeZone) {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date(value));
}

function dayLabel(value, timeZone) {
  return new Intl.DateTimeFormat([], { timeZone, weekday: "short", day: "numeric" }).format(new Date(value));
}

// A holiday's "2026-11-26" is a plain day in the contact's country: format it in UTC so it
// never shifts to the day before or after.
function holidayDay(date) {
  return new Intl.DateTimeFormat([], { timeZone: "UTC", weekday: "short", day: "numeric", month: "short" })
    .format(new Date(date + "T00:00:00Z"));
}

function holidayText(holiday) {
  return holiday.local_name && holiday.local_name !== holiday.name
    ? holiday.name + " (" + holiday.local_name + ")"
    : holiday.name;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderSpotlight(data) {
  const box = document.getElementById("spotlight");
  box.replaceChildren(el("p", "spotlight-kicker", "Calling home…"));
  // Most overdue first, so the first due contact with a free window is the one to call.
  const next = data.suggestions.find((s) => s.overdue.is_due && s.windows.length > 0);
  if (!next) {
    box.append(el("p", "spotlight-name", "You're all caught up"));
    return;
  }
  const w = next.windows[0];
  const you = data.user_time_zone;
  const when =
    (dayKey(w.start, you) === dayKey(data.generated_at, you) ? "Today" : dayLabel(w.start, you)) +
    " " + timeIn(w.start, you) + "–" + timeIn(w.end, you) + " your time · " +
    timeIn(w.start, next.time_zone) + "–" + timeIn(w.end, next.time_zone) + " in " + next.city;
  const since = next.overdue.days_since === null ? "Never called yet" : "Last call " + Math.floor(next.overdue.days_since) + " days ago";
  box.append(el("p", "spotlight-name", next.name), el("p", "spotlight-when", when), el("p", "spotlight-since", since));
  if (w.holiday) {
    box.append(el("p", "spotlight-holiday", "It's a public holiday in " + next.city + ": " + holidayText(w.holiday)));
  }
}

function renderWeek(data) {
  const you = data.user_time_zone;
  const start = new Date(data.generated_at);
  const days = [];
  for (let i = 0; i < data.days; i++) {
    const moment = new Date(start.getTime() + i * 86400000);
    days.push({ key: dayKey(moment, you), label: i === 0 ? "Today" : dayLabel(moment, you) });
  }

  const head = document.getElementById("week-head");
  head.replaceChildren(el("th", "", "Who"), ...days.map((d) => el("th", "", d.label)));

  const body = document.getElementById("week-body");
  body.replaceChildren();
  for (const s of data.suggestions) {
    const row = document.createElement("tr");
    const who = el("td", "who", s.name + " ");
    if (s.overdue.is_due) who.append(el("span", "tag", "due"));
    row.append(who);
    for (const day of days) {
      const cell = el("td", "slots");
      for (const w of s.windows.filter((w) => dayKey(w.start, you) === day.key)) {
        const slot = el("span", "slot", timeIn(w.start, you) + "–" + timeIn(w.end, you));
        if (w.holiday) {
          slot.classList.add("holiday");
          slot.title = "Public holiday in " + s.city + ": " + holidayText(w.holiday);
          slot.append(" 🎉");
        }
        cell.append(slot);
      }
      row.append(cell);
    }
    body.append(row);
  }
  document.getElementById("week-zone").textContent = "Times in your time zone (" + you + ").";
  renderHolidays(data);
}

// Holidays in each contact's country this week, from Nager.Date via overlap-service.
function renderHolidays(data) {
  const items = [];
  for (const s of data.suggestions) {
    for (const h of s.holidays || []) {
      items.push({ date: h.date, text: holidayDay(h.date) + " · " + holidayText(h) + " · " + s.name + " (" + s.city + ")" });
    }
  }
  items.sort((a, b) => a.date.localeCompare(b.date));
  document.getElementById("week-holiday-list").replaceChildren(...items.map((i) => el("li", "", i.text)));
  document.getElementById("week-holidays").hidden = items.length === 0;
  // Nager.Date down: the windows are still right, only the holiday flags are missing.
  document.getElementById("week-holidays-off").hidden = data.holidays_available !== false;
}

async function loadSuggestions() {
  const unavailable = document.getElementById("week-unavailable");
  const content = document.getElementById("week-content");
  try {
    const data = await callService("overlap", "/suggestions");
    unavailable.hidden = true;
    if (data.suggestions.length === 0) {
      content.hidden = true;
      return; // nothing to plan yet; "Your people" shows the empty state
    }
    renderSpotlight(data);
    renderWeek(data);
    content.hidden = false;
  } catch (error) {
    // Designed failure: contacts keep working, this card says what happened.
    content.hidden = true;
    unavailable.hidden = false;
    document.getElementById("week-error").textContent = error.message;
  }
}

// The first load happens after contacts load (see loadContacts in contacts.js).
function setUpSuggestions() {
  document.getElementById("week-retry").addEventListener("click", loadSuggestions);
}
