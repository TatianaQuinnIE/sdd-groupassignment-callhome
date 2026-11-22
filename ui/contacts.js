// "Your people": list, add, edit and delete contacts (contacts-service CRUD).
// Everything shown comes from the API and is inserted with textContent, never as HTML.

let contacts = [];
let editingId = null; // null = the form adds a new contact

const DEFAULTS = {
  sleep_start: "23:00",
  sleep_end: "07:00",
  call_minutes: 30,
  call_every_days: 7,
};

function localTimeIn(timeZone) {
  return new Intl.DateTimeFormat([], { timeZone, hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function lastCalledText(value) {
  if (!value) return "never";
  const days = Math.floor((Date.now() - new Date(value)) / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  return days + " days ago";
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function button(label, onClick) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  b.addEventListener("click", onClick);
  return b;
}

function renderContacts() {
  const body = document.getElementById("contacts-body");
  body.replaceChildren();
  document.getElementById("contacts-empty").hidden = contacts.length > 0;
  document.getElementById("contacts-table").hidden = contacts.length === 0;

  for (const c of contacts) {
    const row = document.createElement("tr");
    row.append(
      cell(c.name),
      cell(c.city + " (" + c.country_code + ")"),
      cell(localTimeIn(c.time_zone)),
      cell("every " + c.call_every_days + (c.call_every_days === 1 ? " day" : " days")),
      cell(lastCalledText(c.last_called)),
    );
    const actions = document.createElement("td");
    actions.className = "actions";
    actions.append(
      button(openCallsId === c.id ? "Close" : "Log a call", () => toggleCalls(c)),
      button("Edit", () => startEdit(c)),
      button("Delete", () => deleteContact(c)),
    );
    row.append(actions);
    body.append(row);
    if (openCallsId === c.id) body.append(callsPanel(c, row.cells.length)); // see calls.js
  }
}

async function loadContacts() {
  const status = document.getElementById("contacts-loading");
  status.hidden = false;
  try {
    contacts = await callService("contacts", "/contacts");
    renderContacts();
  } catch (error) {
    showError(error.message);
  } finally {
    status.hidden = true;
    loadSuggestions(); // any change to people or calls changes "This week" (suggestions.js)
  }
}

function fillForm(values) {
  const form = document.getElementById("contact-form");
  for (const [name, value] of Object.entries(values)) {
    if (!form.elements[name]) continue;
    // The API sends times as "23:00:00"; the time input wants "23:00".
    form.elements[name].value = name.startsWith("sleep") ? String(value).slice(0, 5) : value;
  }
}

function resetForm() {
  editingId = null;
  document.getElementById("contact-form").reset();
  fillForm(DEFAULTS);
  document.getElementById("form-title").textContent = "Add someone";
  document.getElementById("form-submit").textContent = "Add";
  document.getElementById("form-cancel").hidden = true;
}

function startEdit(contact) {
  editingId = contact.id;
  fillForm(contact);
  document.getElementById("form-title").textContent = "Edit " + contact.name;
  document.getElementById("form-submit").textContent = "Save";
  document.getElementById("form-cancel").hidden = false;
  document.getElementById("contact-form").scrollIntoView({ behavior: "smooth" });
}

async function saveContact(event) {
  event.preventDefault();
  const f = event.target.elements;
  const body = {
    name: f.name.value,
    city: f.city.value,
    time_zone: f.time_zone.value,
    country_code: f.country_code.value,
    sleep_start: f.sleep_start.value,
    sleep_end: f.sleep_end.value,
    call_minutes: Number(f.call_minutes.value),
    call_every_days: Number(f.call_every_days.value),
  };
  const submit = document.getElementById("form-submit");
  submit.disabled = true;
  try {
    if (editingId === null) {
      await callService("contacts", "/contacts", { method: "POST", body });
    } else {
      await callService("contacts", "/contacts/" + editingId, { method: "PUT", body });
    }
    hideError();
    resetForm();
    await loadContacts();
  } catch (error) {
    showError(error.message);
  } finally {
    submit.disabled = false;
  }
}

async function deleteContact(contact) {
  if (!confirm("Delete " + contact.name + " and their call log?")) return;
  try {
    await callService("contacts", "/contacts/" + contact.id, { method: "DELETE" });
    if (editingId === contact.id) resetForm();
    await loadContacts();
  } catch (error) {
    showError(error.message);
  }
}

function setUpContacts() {
  // Suggest real IANA time zones while typing (the API rejects unknown ones).
  const list = document.getElementById("time-zones");
  for (const zone of Intl.supportedValuesOf("timeZone")) {
    const option = document.createElement("option");
    option.value = zone;
    list.append(option);
  }
  document.getElementById("contact-form").addEventListener("submit", saveContact);
  document.getElementById("form-cancel").addEventListener("click", resetForm);
  resetForm();
  loadContacts();
}
