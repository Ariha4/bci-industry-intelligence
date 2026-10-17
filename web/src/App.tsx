import { useEffect, useMemo, useState } from "react";
import type { SortState, Trial, TrialDataset, TrialFilters } from "./types";
import {
  DEFAULT_FILTERS,
  countBySponsor,
  countByStartYear,
  filterTrials,
  sortTrials,
  summarize,
  uniqueStatuses,
} from "./lib/trials";
import SummaryCards from "./components/SummaryCards";
import FilterBar from "./components/FilterBar";
import BarChart from "./components/BarChart";
import TrialTable from "./components/TrialTable";
import TrialDetail from "./components/TrialDetail";

// The weekly GitHub Actions refresh writes this file (see src/export_json.py).
const DATA_URL = `${import.meta.env.BASE_URL}data/trials.json`;
const REPO_URL = "https://github.com/Ariha4/bci-industry-intelligence";
const PAGE_SIZE = 25;

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; dataset: TrialDataset };

interface AppProps {
  dataUrl?: string;
}

export default function App({ dataUrl = DATA_URL }: AppProps) {
  const [loadState, setLoadState] = useState<LoadState>({ kind: "loading" });
  const [filters, setFilters] = useState<TrialFilters>(DEFAULT_FILTERS);
  const [sort, setSort] = useState<SortState>({ column: "start_year", direction: "desc" });
  const [selectedTrial, setSelectedTrial] = useState<Trial | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  // New filters mean a new result list, so start again from the first page.
  function handleFiltersChange(nextFilters: TrialFilters) {
    setFilters(nextFilters);
    setVisibleCount(PAGE_SIZE);
  }

  useEffect(() => {
    let cancelled = false;
    fetch(dataUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`Could not load trial data (HTTP ${response.status})`);
        return response.json() as Promise<TrialDataset>;
      })
      .then((dataset) => {
        if (!cancelled) setLoadState({ kind: "ready", dataset });
      })
      .catch((error: Error) => {
        if (!cancelled) setLoadState({ kind: "error", message: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [dataUrl]);

  const allTrials = loadState.kind === "ready" ? loadState.dataset.trials : [];

  // Recompute only when the data or the filters/sort change.
  const filteredTrials = useMemo(() => filterTrials(allTrials, filters), [allTrials, filters]);
  const sortedTrials = useMemo(() => sortTrials(filteredTrials, sort), [filteredTrials, sort]);
  const summary = useMemo(() => summarize(filteredTrials), [filteredTrials]);
  const sponsorRows = useMemo(() => countBySponsor(filteredTrials, 10), [filteredTrials]);
  const yearRows = useMemo(() => countByStartYear(filteredTrials), [filteredTrials]);
  const statuses = useMemo(() => uniqueStatuses(allTrials), [allTrials]);

  if (loadState.kind === "loading") {
    return <main className="page"><p className="status-message">Loading trial data…</p></main>;
  }
  if (loadState.kind === "error") {
    return <main className="page"><p className="status-message error">{loadState.message}</p></main>;
  }

  const refreshedOn = new Date(loadState.dataset.generated_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <h1>BCI Trial Tracker</h1>
          <p className="muted">
            Brain-computer interface clinical trials from ClinicalTrials.gov, refreshed weekly. Last refresh: {refreshedOn}.
          </p>
        </div>
        <a href={REPO_URL} target="_blank" rel="noreferrer" className="repo-link">
          Source on GitHub
        </a>
      </header>

      <FilterBar filters={filters} statuses={statuses} onChange={handleFiltersChange} />
      <SummaryCards summary={summary} />

      <section className="charts">
        <BarChart title="Trials started per year" rows={yearRows} orientation="vertical" />
        <BarChart title="Top sponsors by trial count" rows={sponsorRows} orientation="horizontal" />
      </section>

      <TrialTable trials={sortedTrials.slice(0, visibleCount)} sort={sort} onSortChange={setSort} onSelect={setSelectedTrial} />
      {sortedTrials.length > visibleCount && (
        <div className="show-more">
          <span className="muted">
            Showing {visibleCount} of {sortedTrials.length} trials
          </span>
          <button type="button" className="reset-button" onClick={() => setVisibleCount(visibleCount + PAGE_SIZE)}>
            Show more
          </button>
        </div>
      )}

      <footer className="muted footer">
        FDA Breakthrough Device designations are hand-compiled from public reporting; see the repo for sources.
      </footer>

      {selectedTrial && <TrialDetail trial={selectedTrial} onClose={() => setSelectedTrial(null)} />}
    </main>
  );
}
