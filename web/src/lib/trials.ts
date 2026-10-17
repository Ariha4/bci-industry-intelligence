// Pure data logic for the dashboard: filtering, sorting, and counting.
// Kept free of React so it is easy to unit test (see trials.test.ts).

import type { SortState, SponsorType, Trial, TrialFilters } from "../types";

// Statuses that mean the trial is still running or about to start.
export const ACTIVE_STATUSES = new Set([
  "RECRUITING",
  "NOT_YET_RECRUITING",
  "ENROLLING_BY_INVITATION",
  "ACTIVE_NOT_RECRUITING",
]);

export const DEFAULT_FILTERS: TrialFilters = {
  searchText: "",
  status: "ALL",
  sponsorType: "ALL",
  activeOnly: false,
  breakthroughOnly: false,
};

// ClinicalTrials.gov sponsor classes grouped into three readable buckets.
export function sponsorTypeOf(sponsorClass: string): Exclude<SponsorType, "ALL"> {
  if (sponsorClass === "INDUSTRY") return "INDUSTRY";
  if (sponsorClass === "FED" || sponsorClass === "OTHER_GOV" || sponsorClass === "NIH") return "GOVERNMENT";
  return "ACADEMIC";
}

// "ACTIVE_NOT_RECRUITING" -> "Active, not recruiting"; "PHASE1,PHASE2" -> "Phase 1/2"
export function formatStatus(status: string): string {
  const special: Record<string, string> = {
    ACTIVE_NOT_RECRUITING: "Active, not recruiting",
    NOT_YET_RECRUITING: "Not yet recruiting",
    ENROLLING_BY_INVITATION: "Enrolling by invitation",
  };
  if (special[status]) return special[status];
  const lower = status.toLowerCase().replace(/_/g, " ");
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

export function formatPhase(phase: string): string {
  if (phase === "NA") return "N/A";
  if (phase === "EARLY_PHASE1") return "Early Phase 1";
  const phaseNumbers: string[] = [];
  for (const part of phase.split(",")) {
    phaseNumbers.push(part.replace("PHASE", ""));
  }
  return "Phase " + phaseNumbers.join("/");
}

function matchesSearch(trial: Trial, searchText: string): boolean {
  const query = searchText.trim().toLowerCase();
  if (query === "") return true;
  const searchableFields = [trial.brief_title, trial.lead_sponsor, trial.nct_id, ...trial.conditions, ...trial.interventions];
  for (const field of searchableFields) {
    if (field.toLowerCase().includes(query)) return true;
  }
  return false;
}

export function filterTrials(trials: Trial[], filters: TrialFilters): Trial[] {
  const matchingTrials: Trial[] = [];
  for (const trial of trials) {
    if (!matchesSearch(trial, filters.searchText)) continue;
    if (filters.status !== "ALL" && trial.overall_status !== filters.status) continue;
    if (filters.sponsorType !== "ALL" && sponsorTypeOf(trial.lead_sponsor_class) !== filters.sponsorType) continue;
    if (filters.activeOnly && !ACTIVE_STATUSES.has(trial.overall_status)) continue;
    if (filters.breakthroughOnly && trial.breakthrough_designations.length === 0) continue;
    matchingTrials.push(trial);
  }
  return matchingTrials;
}

export function sortTrials(trials: Trial[], sort: SortState): Trial[] {
  const sorted = [...trials];
  const directionMultiplier = sort.direction === "asc" ? 1 : -1;
  sorted.sort((first, second) => {
    const firstValue = first[sort.column];
    const secondValue = second[sort.column];
    // Missing values (e.g. no start year) always sort to the bottom.
    if (firstValue === null && secondValue === null) return 0;
    if (firstValue === null) return 1;
    if (secondValue === null) return -1;
    if (typeof firstValue === "number" && typeof secondValue === "number") {
      return (firstValue - secondValue) * directionMultiplier;
    }
    return String(firstValue).localeCompare(String(secondValue)) * directionMultiplier;
  });
  return sorted;
}

export interface CountRow {
  label: string;
  count: number;
}

// Top sponsors by trial count, largest first.
export function countBySponsor(trials: Trial[], limit: number): CountRow[] {
  const countsBySponsor = new Map<string, number>();
  for (const trial of trials) {
    countsBySponsor.set(trial.lead_sponsor, (countsBySponsor.get(trial.lead_sponsor) ?? 0) + 1);
  }
  const rows: CountRow[] = [];
  for (const [label, count] of countsBySponsor) {
    rows.push({ label, count });
  }
  rows.sort((first, second) => second.count - first.count || first.label.localeCompare(second.label));
  return rows.slice(0, limit);
}

// Trials started per year, oldest first, with empty years filled in as 0
// so the chart shows real gaps instead of skipping them.
export function countByStartYear(trials: Trial[]): CountRow[] {
  const countsByYear = new Map<number, number>();
  for (const trial of trials) {
    if (trial.start_year === null) continue;
    countsByYear.set(trial.start_year, (countsByYear.get(trial.start_year) ?? 0) + 1);
  }
  if (countsByYear.size === 0) return [];
  const years = [...countsByYear.keys()];
  const firstYear = Math.min(...years);
  const lastYear = Math.max(...years);
  const rows: CountRow[] = [];
  for (let year = firstYear; year <= lastYear; year += 1) {
    rows.push({ label: String(year), count: countsByYear.get(year) ?? 0 });
  }
  return rows;
}

export interface Summary {
  totalTrials: number;
  activeTrials: number;
  distinctSponsors: number;
  breakthroughSponsors: number;
}

export function summarize(trials: Trial[]): Summary {
  let activeTrials = 0;
  const sponsors = new Set<string>();
  const breakthroughSponsors = new Set<string>();
  for (const trial of trials) {
    if (ACTIVE_STATUSES.has(trial.overall_status)) activeTrials += 1;
    sponsors.add(trial.lead_sponsor);
    if (trial.breakthrough_designations.length > 0) {
      // Count companies, not legal entities: "Synchron, Inc." and
      // "Synchron Australia Pty Ltd." are both Synchron.
      breakthroughSponsors.add(trial.breakthrough_designations[0].company);
    }
  }
  return {
    totalTrials: trials.length,
    activeTrials,
    distinctSponsors: sponsors.size,
    breakthroughSponsors: breakthroughSponsors.size,
  };
}

export function uniqueStatuses(trials: Trial[]): string[] {
  const statuses = new Set<string>();
  for (const trial of trials) statuses.add(trial.overall_status);
  return [...statuses].sort();
}
