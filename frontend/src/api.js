const BASE = "/api";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  basilEvents: () => request("/basil-events"),
  loadedEvents: () => request("/events"),
  registerEvent: (basilEventId) =>
    request("/events", {
      method: "POST",
      body: JSON.stringify({ basil_event_id: basilEventId }),
    }),
  articles: (eventId) => request(`/events/${eventId}/articles`),
  entities: (eventId) => request(`/events/${eventId}/entities`),
  sentiment: (eventId) => request(`/events/${eventId}/sentiment`),
  framing: (eventId) => request(`/events/${eventId}/framing`),
  omission: (eventId) => request(`/events/${eventId}/omission`),
  bias: (eventId) => request(`/events/${eventId}/bias`),
  clusters: (eventId) => request(`/events/${eventId}/clusters`),
};
