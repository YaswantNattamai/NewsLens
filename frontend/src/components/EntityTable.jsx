const TYPE_ORDER = ["PERSON", "ORG", "GPE"];

function groupEntities(rows) {
  // rows: [{source, canonical_entity, entity_type, mention_count}]
  const byType = {};
  for (const r of rows) {
    const type = r.entity_type || "OTHER";
    byType[type] ??= {};
    byType[type][r.canonical_entity] ??= { totals: {}, sum: 0 };
    const count = Number(r.mention_count);
    byType[type][r.canonical_entity].totals[r.source] = count;
    byType[type][r.canonical_entity].sum += count;
  }
  return byType;
}

export default function EntityTable({ rows, sources, sourceColors }) {
  if (!rows.length) return <p className="empty-state">No entities extracted for this event.</p>;

  const byType = groupEntities(rows);
  const types = Object.keys(byType).sort(
    (a, b) => TYPE_ORDER.indexOf(a) - TYPE_ORDER.indexOf(b) || a.localeCompare(b)
  );
  const maxCount = Math.max(1, ...rows.map((r) => Number(r.mention_count)));

  return (
    <table className="entity-table">
      <thead>
        <tr>
          <th>Entity</th>
          {sources.map((s) => (
            <th key={s} style={{ color: sourceColors[s] }}>
              {s}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {types.map((type) => {
          const entities = Object.entries(byType[type]).sort((a, b) => b[1].sum - a[1].sum);
          return (
            <>
              <tr className="entity-type-row" key={`${type}-head`}>
                <td colSpan={sources.length + 1}>{type}</td>
              </tr>
              {entities.map(([entity, data]) => (
                <tr key={`${type}-${entity}`}>
                  <td>{entity}</td>
                  {sources.map((s) => {
                    const count = data.totals[s] || 0;
                    return (
                      <td key={s}>
                        {count > 0 ? (
                          <>
                            <span className="count-bar-track">
                              <span
                                className="count-bar-fill"
                                style={{
                                  width: `${(count / maxCount) * 100}%`,
                                  background: sourceColors[s],
                                }}
                              />
                            </span>
                            {count}
                          </>
                        ) : (
                          <span style={{ color: "var(--rule-strong)" }}>—</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </>
          );
        })}
      </tbody>
    </table>
  );
}
