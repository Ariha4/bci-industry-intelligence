import type { SortColumn, SortState, Trial } from "../types";
import { formatPhase, formatStatus } from "../lib/trials";

interface TrialTableProps {
  trials: Trial[];
  sort: SortState;
  onSortChange: (sort: SortState) => void;
  onSelect: (trial: Trial) => void;
}

const COLUMNS: { key: SortColumn; label: string }[] = [
  { key: "brief_title", label: "Trial" },
  { key: "lead_sponsor", label: "Sponsor" },
  { key: "overall_status", label: "Status" },
  { key: "phase", label: "Phase" },
  { key: "start_year", label: "Start" },
];

export default function TrialTable({ trials, sort, onSortChange, onSelect }: TrialTableProps) {
  // Clicking the active column flips the direction; clicking a new column sorts it ascending.
  function handleSort(column: SortColumn) {
    if (sort.column === column) {
      onSortChange({ column, direction: sort.direction === "asc" ? "desc" : "asc" });
    } else {
      onSortChange({ column, direction: "asc" });
    }
  }

  if (trials.length === 0) {
    return <p className="empty">No trials match these filters.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              const isSorted = sort.column === column.key;
              const ariaSort = isSorted ? (sort.direction === "asc" ? "ascending" : "descending") : "none";
              return (
                <th key={column.key} aria-sort={ariaSort}>
                  <button type="button" onClick={() => handleSort(column.key)}>
                    {column.label}
                    <span aria-hidden="true">{isSorted ? (sort.direction === "asc" ? " ▲" : " ▼") : ""}</span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {trials.map((trial) => (
            <tr key={trial.nct_id}>
              <td>
                <button type="button" className="link-button" onClick={() => onSelect(trial)}>
                  {trial.brief_title}
                </button>
                <div className="muted">{trial.nct_id}</div>
              </td>
              <td>
                {trial.lead_sponsor}
                {trial.breakthrough_designations.length > 0 && <span className="badge">FDA Breakthrough</span>}
              </td>
              <td>{formatStatus(trial.overall_status)}</td>
              <td>{formatPhase(trial.phase)}</td>
              <td>{trial.start_year ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
