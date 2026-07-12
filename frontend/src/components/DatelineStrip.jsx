import SourceStamp from "./SourceStamp.jsx";

export default function DatelineStrip({ eventLabel, articles, sourceColors }) {
  return (
    <div className="dateline">
      <span className="dateline-id">EVENT — {eventLabel}</span>
      <div className="dateline-sources">
        {articles.map((a) =>
          a.url ? (
            <a key={a.id} href={a.url} target="_blank" rel="noreferrer">
              <SourceStamp source={a.source} color={sourceColors[a.source]} />
            </a>
          ) : (
            <SourceStamp key={a.id} source={a.source} color={sourceColors[a.source]} />
          )
        )}
      </div>
    </div>
  );
}
