export default function SourceStamp({ source, color }) {
  return (
    <span className="stamp" style={{ color }}>
      <span className="dot" />
      {source}
    </span>
  );
}
