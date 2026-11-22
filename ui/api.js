// One helper for every call from the browser to a service.
// Service URLs come from config.js (localhost in compose, Azure URLs after deploy).

const TIMEOUT_MS = 10000; // never wait forever for a service

const SERVICE_URLS = {
  contacts: window.APP_CONFIG.contactsUrl,
  overlap: window.APP_CONFIG.overlapUrl,
};

const SERVICE_NAMES = {
  contacts: "Contacts service",
  overlap: "Suggestions service",
};

// Calls `path` on a service and returns the parsed JSON (or null for 204 No Content).
// On any failure it throws an Error whose message can be shown to the user as is.
async function callService(service, path, options = {}) {
  const name = SERVICE_NAMES[service];
  const init = { method: options.method || "GET", signal: AbortSignal.timeout(TIMEOUT_MS) };
  if (options.body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(options.body);
  }

  let response;
  try {
    response = await fetch(SERVICE_URLS[service] + path, init);
  } catch (error) {
    // Timeout, network error or CORS refusal: down, or waking up after being idle.
    throw new Error(name + " is not responding. It may be starting up, try again in a minute.");
  }

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (response.ok) return data;

  if (response.status === 422 && data && Array.isArray(data.detail)) {
    // FastAPI validation errors: "city: Field required; time_zone: unknown time zone"
    const problems = data.detail.map(
      (d) => d.loc[d.loc.length - 1] + ": " + d.msg.replace(/^Value error, /, ""),
    );
    throw new Error("Please check the form. " + problems.join("; "));
  }
  if (data && typeof data.detail === "string") {
    throw new Error(name + ": " + data.detail);
  }
  throw new Error(name + " returned an error (HTTP " + response.status + "). Try again in a minute.");
}
