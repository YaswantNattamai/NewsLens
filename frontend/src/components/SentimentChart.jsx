import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";

const MAX_ENTITIES = 12;

function pivot(rows, sources) {
  const byEntity = {};
  for (const r of rows) {
    byEntity[r.canonical_entity] ??= { entity: r.canonical_entity, _mentions: 0 };
    byEntity[r.canonical_entity][r.source] = Number(r.sentiment_score);
    byEntity[r.canonical_entity]._mentions += 1;
  }
  return Object.values(byEntity)
    .sort((a, b) => b._mentions - a._mentions || a.entity.localeCompare(b.entity))
    .slice(0, MAX_ENTITIES);
}

export default function SentimentChart({ rows, sources, sourceColors }) {
  if (!rows.length) return <p className="empty-state">No sentiment data for this event.</p>;

  const data = pivot(rows, sources);
  const height = Math.max(220, data.length * 44);

  return (
    <div className="card" style={{ padding: "16px 16px 4px" }}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }}>
          <CartesianGrid horizontal={false} stroke="var(--rule)" />
          <XAxis
            type="number"
            domain={[-1, 1]}
            tick={{ fontFamily: "IBM Plex Mono", fontSize: 10, fill: "var(--ink-soft)" }}
            tickFormatter={(v) => (v > 0 ? `+${v}` : `${v}`)}
          />
          <YAxis
            type="category"
            dataKey="entity"
            width={110}
            tick={{ fontFamily: "IBM Plex Sans", fontSize: 12, fill: "var(--ink)" }}
          />
          <ReferenceLine x={0} stroke="var(--ink)" />
          <Tooltip
            formatter={(value) => (value === undefined ? "not mentioned" : value.toFixed(2))}
            contentStyle={{
              fontFamily: "IBM Plex Mono",
              fontSize: 12,
              border: "1px solid var(--rule-strong)",
              borderRadius: 3,
            }}
          />
          <Legend wrapperStyle={{ fontFamily: "IBM Plex Mono", fontSize: 11 }} />
          {sources.map((s) => (
            <Bar key={s} dataKey={s} name={s} fill={sourceColors[s]} radius={2} maxBarSize={14} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
