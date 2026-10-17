import type { CountRow } from "../lib/trials";

interface BarChartProps {
  title: string;
  rows: CountRow[];
  orientation: "horizontal" | "vertical";
  emptyMessage?: string;
}

// A small dependency-free bar chart. Bar length is each count as a share of
// the largest count, so the longest bar always fills the available space.
export default function BarChart({ title, rows, orientation, emptyMessage = "No trials match these filters." }: BarChartProps) {
  let largestCount = 0;
  for (const row of rows) {
    if (row.count > largestCount) largestCount = row.count;
  }

  return (
    <figure className="chart">
      <figcaption>{title}</figcaption>
      {rows.length === 0 ? (
        <p className="empty">{emptyMessage}</p>
      ) : orientation === "horizontal" ? (
        <ul className="bars-horizontal">
          {rows.map((row) => (
            <li key={row.label} title={`${row.label}: ${row.count}`}>
              <span className="bar-label">{row.label}</span>
              <span className="bar-track">
                <span className="bar" style={{ width: `${(row.count / largestCount) * 100}%` }} />
              </span>
              <span className="bar-value">{row.count}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="bars-vertical" role="list">
          {rows.map((row) => (
            <div className="column" role="listitem" key={row.label} title={`${row.label}: ${row.count} trials`}>
              <span className="column-value">{row.count > 0 ? row.count : ""}</span>
              <span className="column-track">
                <span className="column-bar" style={{ height: `${(row.count / largestCount) * 100}%` }} />
              </span>
              <span className="column-label">{row.label.slice(2)}</span>
            </div>
          ))}
        </div>
      )}
    </figure>
  );
}
