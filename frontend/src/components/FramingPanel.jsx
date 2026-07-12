import { useState } from "react";
import SourceStamp from "./SourceStamp.jsx";

export default function FramingPanel({ rows, sourceColors }) {
  const [openKey, setOpenKey] = useState(null);

  if (!rows.length) return <p className="empty-state">No source pairs to compare yet.</p>;

  return (
    <div className="pair-grid">
      {rows.map((r) => {
        const key = `${r.source_a}-${r.source_b}`;
        const isOpen = openKey === key;
        const hasScore = r.framing_score !== null && r.framing_score !== undefined;
        const pct = hasScore ? Math.round(r.framing_score * 100) : null;

        return (
          <div className="pair-card" key={key}>
            <button className="pair-card-head" onClick={() => setOpenKey(isOpen ? null : key)}>
              <div className="pair-versus">
                <SourceStamp source={r.source_a} color={sourceColors[r.source_a]} />
                <span className="vs">vs</span>
                <SourceStamp source={r.source_b} color={sourceColors[r.source_b]} />
              </div>
              <div style={{ textAlign: "right" }}>
                <span
                  className="score-figure"
                  style={{ color: hasScore && pct >= 45 ? "var(--redline)" : "var(--ink)" }}
                >
                  {hasScore ? `${pct}%` : "—"}
                </span>
                <span className="score-label">
                  {hasScore ? "divergence (lower bound)" : "not comparable"}
                </span>
              </div>
            </button>

            {isOpen && (
              <div className="pair-card-body">
                {r.aligned_pairs && r.aligned_pairs.length ? (
                  r.aligned_pairs.slice(0, 8).map((p, i) => (
                    <div className="aligned-pair" key={i}>
                      <div className="clipping" style={{ color: sourceColors[r.source_a] }}>
                        <p style={{ color: "var(--ink)" }}>{p.sentence_a}</p>
                      </div>
                      <span className="similarity-badge">
                        {Math.round(p.similarity * 100)}% similar
                      </span>
                      <div className="clipping" style={{ color: sourceColors[r.source_b] }}>
                        <p style={{ color: "var(--ink)" }}>{p.sentence_b}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="empty-state">No aligned sentence pairs cleared the similarity floor.</p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
