import type { SponsorType, TrialFilters } from "../types";
import { DEFAULT_FILTERS, formatStatus } from "../lib/trials";

interface FilterBarProps {
  filters: TrialFilters;
  statuses: string[];
  onChange: (filters: TrialFilters) => void;
}

export default function FilterBar({ filters, statuses, onChange }: FilterBarProps) {
  // Each control updates one field and keeps the rest of the filters as they were.
  function update<Key extends keyof TrialFilters>(key: Key, value: TrialFilters[Key]) {
    onChange({ ...filters, [key]: value });
  }

  return (
    <section className="filter-bar" aria-label="Filters">
      <label className="field search-field">
        <span>Search</span>
        <input
          type="search"
          placeholder="Title, sponsor, condition, or NCT ID"
          value={filters.searchText}
          onChange={(event) => update("searchText", event.target.value)}
        />
      </label>

      <label className="field">
        <span>Status</span>
        <select value={filters.status} onChange={(event) => update("status", event.target.value)}>
          <option value="ALL">All statuses</option>
          {statuses.map((status) => (
            <option key={status} value={status}>
              {formatStatus(status)}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Sponsor type</span>
        <select value={filters.sponsorType} onChange={(event) => update("sponsorType", event.target.value as SponsorType)}>
          <option value="ALL">All sponsors</option>
          <option value="INDUSTRY">Industry</option>
          <option value="ACADEMIC">Academic and other</option>
          <option value="GOVERNMENT">Government</option>
        </select>
      </label>

      <label className="checkbox">
        <input type="checkbox" checked={filters.activeOnly} onChange={(event) => update("activeOnly", event.target.checked)} />
        Active only
      </label>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={filters.breakthroughOnly}
          onChange={(event) => update("breakthroughOnly", event.target.checked)}
        />
        FDA Breakthrough sponsors
      </label>

      <button type="button" className="reset-button" onClick={() => onChange(DEFAULT_FILTERS)}>
        Reset
      </button>
    </section>
  );
}
