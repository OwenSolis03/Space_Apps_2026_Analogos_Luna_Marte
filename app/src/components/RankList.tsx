import type { RankedTarget, UnrankedTarget } from "../lib/msi";
import { fmtLat, fmtLon, pct } from "../lib/msi";
import { DIM_LABEL } from "../lib/content";

interface Props {
  ranked: RankedTarget[];
  unranked?: UnrankedTarget[];
  total: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function RankList({ ranked, unranked, total, selectedId, onSelect }: Props) {
  const missingDimensionNames = Array.from(
    new Set((unranked ?? []).flatMap((u) => u.missingDims)),
  ).map((d) => DIM_LABEL[d]?.label.toLowerCase() ?? d);

  return (
    <section aria-labelledby="rank-h" className="flex min-w-0 flex-col rounded-panel border border-line bg-surface">
      <header className="flex items-baseline justify-between gap-2 px-4 pt-3 pb-2">
        <h3 id="rank-h" className="text-base font-semibold">Target ranking</h3>
        <span className="eyebrow num">
          {ranked.length} / {total}
        </span>
      </header>
      {ranked.length === 0 ? (
        <p className="px-4 pb-4 text-sm text-muted">No target reaches that minimum MSI. Lower it to see results.</p>
      ) : (
        <ol className="max-h-[32rem] overflow-auto border-t border-line">
          {ranked.map((r, i) => {
            const on = r.target.id === selectedId;
            return (
              <li key={r.target.id}>
                <button
                  type="button"
                  aria-current={on ? "true" : undefined}
                  onClick={() => onSelect(r.target.id)}
                  className={`grid w-full cursor-pointer grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-x-2 border-b border-line px-3 py-2.5 text-left transition-colors hover:bg-surface-2 active:bg-line ${
                    on ? "bg-surface-2 outline-2 -outline-offset-2 outline-accent" : ""
                  }`}
                >
                  <span className="num text-xs text-faint">{String(i + 1).padStart(2, "0")}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">{r.target.name}</span>
                    <span className="num block text-xs text-muted">
                      {r.target.id} · {fmtLat(r.target.lat)}, {fmtLon(r.target.lon)}
                    </span>
                  </span>
                  <span className="num text-right font-medium">
                    {pct(r.best)}
                    <span className="block text-[0.65rem] font-normal text-faint">MSI</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
      {unranked && unranked.length > 0 && (
        <footer className="border-t border-line bg-surface-2/40 px-4 py-3 text-xs text-muted">
          <p>
            <span className="font-semibold text-fg">{unranked.length} targets</span> are not ranked for this case:
            {" "}
            no {missingDimensionNames.join(", ")} data at these sites (
            {unranked.slice(0, 3).map((u) => u.target.name).join(", ")}
            {unranked.length > 3 ? ", …" : ""}).
          </p>
        </footer>
      )}
    </section>
  );
}
