import { useEffect, useState } from "react";
import { api } from "./api.js";
import { assignSourceColors } from "./sourceColors.js";
import EventPicker from "./components/EventPicker.jsx";
import DatelineStrip from "./components/DatelineStrip.jsx";
import EntityTable from "./components/EntityTable.jsx";
import SentimentChart from "./components/SentimentChart.jsx";
import FramingPanel from "./components/FramingPanel.jsx";
import OmissionPanel from "./components/OmissionPanel.jsx";
import BiasPanel from "./components/BiasPanel.jsx";
import ClusterPanel from "./components/ClusterPanel.jsx";
import ArticleReader from "./components/ArticleReader.jsx";

function Section({ title, description, children }) {
  return (
    <section className="section">
      <div className="section-head">
        <h2>{title}</h2>
        <p className="section-desc">{description}</p>
      </div>
      {children}
    </section>
  );
}

export default function App() {
  const [eventId, setEventId] = useState(null);
  const [eventLabel, setEventLabel] = useState("");
  const [data, setData] = useState(null); // { articles, entities, sentiment, framing, omission, bias }
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (eventId === null) return;
    setStatus("loading");
    setErrorMsg("");

    Promise.all([
      api.articles(eventId),
      api.entities(eventId),
      api.sentiment(eventId),
      api.framing(eventId),
      api.omission(eventId),
      api.bias(eventId),
      api.clusters(eventId),
    ])
      .then(([articles, entities, sentiment, framing, omission, bias, clusters]) => {
        setData({ articles, entities, sentiment, framing, omission, bias, clusters });
        setEventLabel(articles[0]?.event_topic ?? String(eventId));
        setStatus("idle");
      })
      .catch((err) => {
        setStatus("error");
        setErrorMsg(err.message);
      });
  }, [eventId]);

  const sources = data ? [...new Set(data.articles.map((a) => a.source))] : [];
  const sourceColors = assignSourceColors(sources);

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <span className="eyebrow">Narrative Bias Desk</span>
          <h1>NewsLens</h1>
        </div>
        <EventPicker onEventReady={setEventId} />
      </header>

      {status === "loading" && <p className="loading-state">Fetching analysis…</p>}
      {status === "error" && <p className="error-state">{errorMsg}</p>}

      {data && status === "idle" && (
        <>
          <DatelineStrip
            eventLabel={eventLabel}
            articles={data.articles}
            sourceColors={sourceColors}
          />

          <Section
            title="Raw Articles"
            description="The original news text reported by the three sources side-by-side."
          >
            <ArticleReader articles={data.articles} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Entities"
            description="Canonicalized mentions, grouped by type, by source."
          >
            <EntityTable rows={data.entities} sources={sources} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Sentiment"
            description="Average tone toward each entity, per source. Diverges from 0 at center."
          >
            <SentimentChart rows={data.sentiment} sources={sources} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Framing"
            description="How differently each pair describes the same details — a lower bound, not a full measure. Click a pair."
          >
            <FramingPanel rows={data.framing} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Omission"
            description="Share of event-wide entity importance each source leaves out. Click a source."
          >
            <OmissionPanel rows={data.omission} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Narrative clusters"
            description="Groups event sentences into thematic threads using KMeans to expose selective framing."
          >
            <ClusterPanel rows={data.clusters} sourceColors={sourceColors} />
          </Section>

          <Section
            title="Bias signal"
            description="Sentences the fine-tuned classifier flagged as biased, if one is configured."
          >
            <BiasPanel rows={data.bias} sourceColors={sourceColors} />
          </Section>
        </>
      )}

      {!data && status === "idle" && (
        <p className="empty-state">
          Pick a BASIL event above to load and analyze it, or open one you've already run.
        </p>
      )}
    </div>
  );
}
