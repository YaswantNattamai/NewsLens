import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function EventPicker({ onEventReady }) {
  const [basilIds, setBasilIds] = useState([]);
  const [loadedEvents, setLoadedEvents] = useState([]);
  const [selectedBasilId, setSelectedBasilId] = useState("");
  const [selectedLoadedId, setSelectedLoadedId] = useState("");
  const [liveQuery, setLiveQuery] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | live | error
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    api
      .basilEvents()
      .then((res) => setBasilIds(res.event_ids || []))
      .catch(() => setBasilIds([]));
    api
      .loadedEvents()
      .then((res) => setLoadedEvents(res || []))
      .catch(() => setLoadedEvents([]));
  }, []);

  async function handleLoadNew() {
    if (!selectedBasilId) return;
    setStatus("loading");
    setErrorMsg("");
    try {
      const result = await api.registerEvent(selectedBasilId);
      const refreshed = await api.loadedEvents();
      setLoadedEvents(refreshed || []);
      setStatus("idle");
      onEventReady(result.event_id);
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }

  function handleOpenExisting() {
    if (!selectedLoadedId) return;
    onEventReady(Number(selectedLoadedId));
  }

  async function handleLiveSearch(e) {
    e?.preventDefault();
    const q = liveQuery.trim();
    if (!q) return;
    setStatus("live");
    setErrorMsg("");
    try {
      const result = await api.liveEvent(q);
      const refreshed = await api.loadedEvents();
      setLoadedEvents(refreshed || []);
      setStatus("idle");
      onEventReady(result.event_id);
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }

  return (
    <div>
      <form className="picker live-picker" onSubmit={handleLiveSearch}>
        <input
          type="text"
          className="live-search"
          placeholder="Analyze a live topic — e.g. “interest rate decision”"
          value={liveQuery}
          onChange={(e) => setLiveQuery(e.target.value)}
          disabled={status === "live"}
        />
        <button type="submit" disabled={!liveQuery.trim() || status === "live"}>
          {status === "live" ? "Gathering coverage…" : "Analyze live"}
        </button>
      </form>

      <div className="picker">
        <select
          value={selectedLoadedId}
          onChange={(e) => setSelectedLoadedId(e.target.value)}
          disabled={loadedEvents.length === 0}
        >
          <option value="">
            {loadedEvents.length ? "Already analyzed…" : "No events analyzed yet"}
          </option>
          {loadedEvents.map((e) => (
            <option key={e.id} value={e.id}>
              {e.topic}
            </option>
          ))}
        </select>
        <button onClick={handleOpenExisting} disabled={!selectedLoadedId}>
          Open
        </button>

        <span style={{ color: "var(--ink-soft)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
          or
        </span>

        <select value={selectedBasilId} onChange={(e) => setSelectedBasilId(e.target.value)}>
          <option value="">
            {basilIds.length ? "Select a BASIL event…" : "No BASIL events found on disk"}
          </option>
          {basilIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <button onClick={handleLoadNew} disabled={!selectedBasilId || status === "loading"}>
          {status === "loading" ? "Analyzing…" : "Load + analyze"}
        </button>
      </div>

      {status === "loading" && (
        <p className="picker-note">
          Running NER, sentiment, framing alignment, and omission scoring — first run for an
          event can take a minute or two while models load.
        </p>
      )}
      {status === "live" && (
        <p className="picker-note">
          Searching recent coverage via GDELT, fetching each outlet's article, then running the
          full analysis — this can take 30–60s. Wire-copy duplicates are removed automatically.
        </p>
      )}
      {status === "error" && <p className="picker-note error-state">{errorMsg}</p>}
      {basilIds.length === 0 && (
        <p className="picker-note">
          No BASIL events found — check BASIL_DIR on the backend points at your downloaded
          dataset (see README).
        </p>
      )}
    </div>
  );
}
