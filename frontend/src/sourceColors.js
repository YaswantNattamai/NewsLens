const PALETTE = ["#2b4570", "#a63d40", "#57684a", "#8a6d3b", "#5b4a72"];

/**
 * Stable color per source, based on alphabetical order so the same source
 * always gets the same color across reloads and across every panel on the
 * page (the stamp tag is the page's one recurring signature element).
 */
export function assignSourceColors(sources) {
  const sorted = [...sources].sort();
  const map = {};
  sorted.forEach((source, i) => {
    map[source] = PALETTE[i % PALETTE.length];
  });
  return map;
}
