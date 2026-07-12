import SourceStamp from "./SourceStamp.jsx";

export default function BiasPanel({ rows, sourceColors }) {
  if (!rows.length) {
    return (
      <p className="empty-state">
        No flagged sentences — either the fine-tuned classifier isn't configured
        (BIAS_MODEL_DIR unset on the backend) or it found nothing to flag for this event.
      </p>
    );
  }

  const bySource = {};
  for (const r of rows) {
    bySource[r.source] ??= [];
    bySource[r.source].push(r);
  }

  return (
    <div className="card" style={{ padding: "6px 16px" }}>
      {Object.entries(bySource).map(([source, sentences]) => (
        <div key={source} style={{ padding: "12px 0", borderBottom: "1px solid var(--rule)" }}>
          <div style={{ marginBottom: 8 }}>
            <SourceStamp source={source} color={sourceColors[source]} />
          </div>
          {sentences.slice(0, 10).map((s, i) => (
            <div className="bias-row" key={i}>
              <span className="bias-prob">{Math.round(s.probability * 100)}%</span>
              <span>{s.sentence}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
