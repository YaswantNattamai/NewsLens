import SourceStamp from "./SourceStamp.jsx";

export default function ClusterPanel({ rows, sourceColors }) {
  if (!rows || !rows.length) {
    return (
      <p className="empty-state">
        No clusters computed for this event yet.
      </p>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
      {rows.map((cluster) => {
        const total = cluster.total_sentences;

        return (
          <div className="card" key={cluster.cluster_id} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span className="source-label" style={{ fontFamily: "var(--font-mono)", fontSize: 11, textTransform: "uppercase" }}>
                  Narrative Thread {cluster.cluster_id + 1}
                </span>
                <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>
                  {total} sentences
                </span>
              </div>
              <blockquote style={{ 
                margin: "0 0 16px 0", 
                fontFamily: "var(--font-display)", 
                fontSize: 16, 
                lineHeight: 1.4,
                fontStyle: "italic",
                color: "var(--ink)"
              }}>
                "{cluster.representative_sentence}"
              </blockquote>
            </div>

            {/* Source Distribution Visualization */}
            <div style={{ marginTop: "auto", borderTop: "1px solid var(--rule)", paddingTop: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8, color: "var(--ink-soft)" }}>
                Source Representation:
              </div>
              
              {/* Stacked Percentage Bar */}
              <div style={{ 
                display: "flex", 
                height: 8, 
                borderRadius: 4, 
                overflow: "hidden", 
                backgroundColor: "var(--rule)",
                marginBottom: 12
              }}>
                {Object.entries(cluster.source_percentages).map(([source, pct]) => (
                  <div 
                    key={source} 
                    style={{ 
                      width: `${pct * 100}%`, 
                      backgroundColor: sourceColors[source] || "#ccc" 
                    }}
                    title={`${source}: ${Math.round(pct * 100)}%`}
                  />
                ))}
              </div>

              {/* Legend with exact numbers */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                {Object.entries(cluster.source_distribution).map(([source, count]) => {
                  const pct = cluster.source_percentages[source] || 0;
                  return (
                    <div key={source} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                      <span 
                        style={{ 
                          width: 8, 
                          height: 8, 
                          borderRadius: "50%", 
                          backgroundColor: sourceColors[source] || "#ccc" 
                        }} 
                      />
                      <span style={{ textTransform: "uppercase", fontWeight: 600 }}>{source}:</span>
                      <span style={{ color: "var(--ink-soft)" }}>{count} ({Math.round(pct * 100)}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
