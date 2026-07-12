export default function ArticleReader({ articles, sourceColors }) {
  if (!articles || !articles.length) {
    return <p className="empty-state">No articles loaded.</p>;
  }

  return (
    <div style={{ 
      display: "grid", 
      gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", 
      gap: 20, 
      marginBottom: 32 
    }}>
      {articles.map((art) => {
        // Split text by newlines to form proper paragraph blocks
        const paragraphs = art.raw_text
          ? art.raw_text.split(/\n\n+/).filter(p => p.trim().length > 0)
          : [];

        return (
          <div 
            className="card" 
            key={art.id} 
            style={{ 
              borderTop: `4px solid ${sourceColors[art.source] || "#ccc"}`,
              padding: "16px 20px" 
            }}
          >
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              marginBottom: 12,
              borderBottom: "1px solid var(--rule)",
              paddingBottom: 8
            }}>
              <span className="source-label" style={{ 
                fontFamily: "var(--font-mono)", 
                fontWeight: 600, 
                textTransform: "uppercase",
                fontSize: 13,
                color: sourceColors[art.source]
              }}>
                {art.source}
              </span>
              {art.url && (
                <a 
                  href={art.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  style={{ fontSize: 12, textDecoration: "none" }}
                >
                  Original Article ↗
                </a>
              )}
            </div>
            
            <div style={{ 
              maxHeight: "350px", 
              overflowY: "auto", 
              paddingRight: 8,
              fontSize: 14,
              lineHeight: 1.6,
              color: "var(--ink)"
            }}>
              {paragraphs.length > 0 ? (
                paragraphs.map((p, i) => (
                  <p key={i} style={{ margin: "0 0 12px 0", textAlign: "justify" }}>
                    {p.trim()}
                  </p>
                ))
              ) : (
                <p style={{ margin: 0, fontStyle: "italic", color: "var(--ink-soft)" }}>
                  {art.raw_text || "No text content available."}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
