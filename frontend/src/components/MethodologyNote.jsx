import { useState } from "react";

// Trust banner. NewsLens surfaces computational signals of how sources *differ*
// in covering a story — it does not, and cannot from this data, certify that a
// source is biased, lying, or wrong. This note keeps that distinction in front
// of the reader, and states the one validated number we actually have.
export default function MethodologyNote() {
  const [open, setOpen] = useState(false);

  return (
    <div className="methodology">
      <button className="methodology-head" onClick={() => setOpen(!open)}>
        <span className="methodology-badge">How to read this</span>
        <span className="methodology-tagline">
          These are signals of <strong>difference</strong>, not verdicts of bias.
        </span>
        <span className="methodology-toggle">{open ? "–" : "+"}</span>
      </button>

      {open && (
        <div className="methodology-body">
          <p>
            NewsLens measures how a set of sources <em>differ</em> in covering the same
            story — which entities they name, how they phrase things, what they leave out.
            A high score means the sources <em>diverge</em>, not that any one of them is
            biased, dishonest, or wrong. Treat every panel as a prompt to go read the
            sources yourself, not as a scoreboard.
          </p>
          <ul>
            <li>
              <strong>Framing</strong> is a <em>lower bound</em> on how differently two
              sources phrase even their most similar sentences. Validated against BASIL's
              human bias annotations it shows only a <strong>weak</strong> correlation
              (ROC AUC ≈ 0.56 over 4,300+ aligned pairs) — divergent phrasing leans toward
              human-flagged bias but is close to chance. Read it as "phrasing differs,"
              nothing stronger.
            </li>
            <li>
              <strong>Omission</strong> is measured only <em>relative to the other sources
              shown here</em>. "Missing" means "not mentioned by this source but mentioned
              by others in this set" — not that it was deliberately suppressed.
            </li>
            <li>
              <strong>Sentiment</strong> is an automated model estimate of tone toward an
              entity; it can misread sarcasm, quotes, and context.
            </li>
            <li>
              <strong>Lean labels</strong> (L / C / R) are a coarse orientation aid from a
              curated outlet list — a starting point for grouping, <em>not</em> a
              ground-truth rating of any outlet's politics.
            </li>
            <li>
              <strong>Fewer sources = weaker signal.</strong> With only two outlets there's
              little to triangulate against; confidence grows with more comparable coverage.
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
