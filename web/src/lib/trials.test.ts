import { describe, expect, it } from "vitest";
import {
  DEFAULT_FILTERS,
  countBySponsor,
  countByStartYear,
  filterTrials,
  formatPhase,
  formatStatus,
  sortTrials,
  sponsorTypeOf,
  summarize,
} from "./trials";
import { makeTrial, neuralinkTrial, nihTrial, strokeTrial } from "../test/fixtures";

const allTrials = [neuralinkTrial, strokeTrial, nihTrial];

describe("filterTrials", () => {
  it("returns everything with default filters", () => {
    expect(filterTrials(allTrials, DEFAULT_FILTERS)).toHaveLength(3);
  });

  it("searches titles, sponsors, conditions, and NCT IDs case-insensitively", () => {
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, searchText: "stroke" }).map((t) => t.nct_id)).toEqual([
      "NCT22222222",
      "NCT33333333", // matches the sponsor name "...Disorders and Stroke"
    ]);
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, searchText: "nct111" })).toEqual([neuralinkTrial]);
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, searchText: "quadriplegia" })).toEqual([neuralinkTrial]);
  });

  it("filters by sponsor type, active status, and FDA designation", () => {
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, sponsorType: "INDUSTRY" })).toEqual([neuralinkTrial]);
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, sponsorType: "GOVERNMENT" })).toEqual([nihTrial]);
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, activeOnly: true })).not.toContain(strokeTrial);
    expect(filterTrials(allTrials, { ...DEFAULT_FILTERS, breakthroughOnly: true })).toEqual([neuralinkTrial]);
  });

  it("combines filters with AND logic", () => {
    const result = filterTrials(allTrials, { ...DEFAULT_FILTERS, sponsorType: "INDUSTRY", status: "COMPLETED" });
    expect(result).toEqual([]);
  });
});

describe("sortTrials", () => {
  it("sorts numbers and keeps missing years at the bottom in both directions", () => {
    const ascending = sortTrials(allTrials, { column: "start_year", direction: "asc" });
    expect(ascending.map((t) => t.start_year)).toEqual([2021, 2023, null]);
    const descending = sortTrials(allTrials, { column: "start_year", direction: "desc" });
    expect(descending.map((t) => t.start_year)).toEqual([2023, 2021, null]);
  });

  it("sorts text alphabetically without mutating the input", () => {
    const original = [...allTrials];
    const sorted = sortTrials(allTrials, { column: "lead_sponsor", direction: "asc" });
    expect(sorted[0].lead_sponsor).toBe("Beijing Tiantan Hospital");
    expect(allTrials).toEqual(original);
  });
});

describe("counting helpers", () => {
  it("ranks sponsors by trial count and respects the limit", () => {
    const trials = [
      makeTrial({ nct_id: "A", lead_sponsor: "NeuroPace" }),
      makeTrial({ nct_id: "B", lead_sponsor: "NeuroPace" }),
      makeTrial({ nct_id: "C", lead_sponsor: "Synchron, Inc." }),
    ];
    expect(countBySponsor(trials, 1)).toEqual([{ label: "NeuroPace", count: 2 }]);
  });

  it("fills empty years with zero so gaps show on the chart", () => {
    const rows = countByStartYear([makeTrial({ start_year: 2020 }), makeTrial({ start_year: 2022 })]);
    expect(rows).toEqual([
      { label: "2020", count: 1 },
      { label: "2021", count: 0 },
      { label: "2022", count: 1 },
    ]);
  });

  it("counts FDA Breakthrough companies once even across legal entities", () => {
    const designation = { company: "Synchron", device: "Stentrode", designation_year: 2020, source_url: "x" };
    const trials = [
      makeTrial({ nct_id: "A", lead_sponsor: "Synchron, Inc.", breakthrough_designations: [designation] }),
      makeTrial({ nct_id: "B", lead_sponsor: "Synchron Australia Pty Ltd.", breakthrough_designations: [designation] }),
    ];
    expect(summarize(trials)).toMatchObject({ distinctSponsors: 2, breakthroughSponsors: 1 });
  });
});

describe("formatting", () => {
  it("labels statuses, phases, and sponsor types", () => {
    expect(formatStatus("ACTIVE_NOT_RECRUITING")).toBe("Active, not recruiting");
    expect(formatStatus("RECRUITING")).toBe("Recruiting");
    expect(formatPhase("PHASE1,PHASE2")).toBe("Phase 1/2");
    expect(formatPhase("NA")).toBe("N/A");
    expect(sponsorTypeOf("FED")).toBe("GOVERNMENT");
    expect(sponsorTypeOf("OTHER")).toBe("ACADEMIC");
  });
});
