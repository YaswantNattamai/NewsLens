// Live events carry a coarse political-lean bucket per source; BASIL events
// don't, so `lean` is optional and the badge only renders when present and
// meaningful (not 'unknown').
const LEAN_LABEL = { left: "L", center: "C", right: "R" };

export default function SourceStamp({ source, color, lean }) {
  const showLean = lean && LEAN_LABEL[lean];
  return (
    <span className="stamp" style={{ color }}>
      <span className="dot" />
      {source}
      {showLean && (
        <span className={`lean-badge lean-${lean}`} title={`Leans ${lean}`}>
          {LEAN_LABEL[lean]}
        </span>
      )}
    </span>
  );
}
