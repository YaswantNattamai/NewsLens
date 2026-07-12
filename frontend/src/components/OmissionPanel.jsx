import { useState } from "react";
import SourceStamp from "./SourceStamp.jsx";

function perSource(rows) {
  // omission/topic-overlap scores are computed once per source (relative to
  // the whole event) but stored on every pairwise row that source appears
  // in — collapse back down to one entry per source.
  const map = {};
  for (const r of rows) {
    map[r.source_a] ??= {
      omission: r.omission_score_a,
      topicOverlap: r.topic_overlap_score_a,
      missing: r.missing_entities_a || [],
    };
    map[r.source_b] ??= {
      omission: r.omission_score_b,
      topicOverlap: r.topic_overlap_score_b,
      missing: r.missing_entities_b || [],
    };
  }
  return map;
}

export default function OmissionPanel({ rows, sourceColors }) {
  const [openSource, setOpenSource] = useState(null);

  if (!rows.length) return <p className="empty-state">No omission data for this event.</p>;

  const bySource = perSource(rows);
  const sources = Object.keys(bySource).sort(
    (a, b) => (bySource[b].omission ?? 0) - (bySource[a].omission ?? 0)
  );

  return (
    <div className="card" style={{ padding: "6px 16px" }}>
      {sources.map((source) => {
        const data = bySource[source];
        const pct = data.omission !== null ? Math.round(data.omission * 100) : null;
        const isOpen = openSource === source;

        return (
          <div key={source}>
            <button
              className="pair-card-head"
              style={{ padding: "10px 0" }}
              onClick={() => setOpenSource(isOpen ? null : source)}
            >
              <SourceStamp source={source} color={sourceColors[source]} />
              <div style={{ flex: 1, margin: "0 16px" }} className="progress-row">
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-soft)" }}>
                  entities
                </span>
                <span className="progress-track">
                  <span className="progress-fill" style={{ width: `${pct ?? 0}%` }} />
                </span>
                <span className="progress-value">{pct !== null ? `${pct}%` : "—"}</span>
              </div>
            </button>
            {isOpen && (
              <div className="chip-row">
                {data.missing.length ? (
                  data.missing
                    .slice(0, 20)
                    .map((m) => (
                      <span className="chip" key={m.entity}>
                        {m.entity}
                      </span>
                    ))
                ) : (
                  <span className="empty-state" style={{ padding: 0 }}>
                    Nothing notable missing.
                  </span>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
