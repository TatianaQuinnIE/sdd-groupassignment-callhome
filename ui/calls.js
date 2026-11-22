// "Log a call": a panel under a contact's row to record a call now and see recent calls.

let openCallsId = null; // the contact whose call panel is open, if any

function formatCallTime(value) {
  return new Intl.DateTimeFormat([], { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function toggleCalls(contact) {
  openCallsId = openCallsId === contact.id ? null : contact.id;
  renderContacts(); // redraws the table, with or without the panel
}

// Builds the panel row that renderContacts puts under the open contact.
function callsPanel(contact, columnCount) {
  const row = document.createElement("tr");
  row.className = "calls-row";
  const td = document.createElement("td");
  td.colSpan = columnCount;

  const form = document.createElement("form");
  form.className = "call-form";
  form.innerHTML = `
    <strong>Called just now?</strong>
    <label>Minutes <input name="minutes" type="number" min="1" max="600" placeholder="optional"></label>
    <label>Note <input name="note" maxlength="500" placeholder="optional"></label>
    <button type="submit">Save call</button>`;
  form.addEventListener("submit", (event) => logCall(event, contact));

  const list = document.createElement("ul");
  list.className = "call-list";
  list.textContent = "Loading calls…";

  td.append(form, list);
  row.append(td);
  loadCalls(contact, list);
  return row;
}

async function loadCalls(contact, list) {
  try {
    const calls = await callService("contacts", "/contacts/" + contact.id + "/calls");
    list.replaceChildren();
    if (calls.length === 0) {
      list.textContent = "No calls logged yet.";
      return;
    }
    for (const call of calls.slice(0, 5)) {
      const item = document.createElement("li");
      const parts = [formatCallTime(call.called_at)];
      if (call.minutes) parts.push(call.minutes + " min");
      if (call.note) parts.push(call.note);
      item.textContent = parts.join(" · ") + " ";
      const remove = button("✕", () => deleteCall(contact, call));
      remove.className = "icon";
      remove.title = "Remove this call";
      item.append(remove);
      list.append(item);
    }
  } catch (error) {
    list.textContent = "Calls could not be loaded.";
    showError(error.message);
  }
}

async function logCall(event, contact) {
  event.preventDefault();
  const f = event.target.elements;
  const body = {}; // called_at is left out: the service uses "now"
  if (f.minutes.value) body.minutes = Number(f.minutes.value);
  if (f.note.value.trim()) body.note = f.note.value.trim();
  try {
    await callService("contacts", "/contacts/" + contact.id + "/calls", { method: "POST", body });
    hideError();
    await loadContacts(); // "Last called" changes, and the panel reloads its list
  } catch (error) {
    showError(error.message);
  }
}

async function deleteCall(contact, call) {
  if (!confirm("Remove the call from " + formatCallTime(call.called_at) + "?")) return;
  try {
    await callService("contacts", "/contacts/" + contact.id + "/calls/" + call.id, { method: "DELETE" });
    await loadContacts();
  } catch (error) {
    showError(error.message);
  }
}
