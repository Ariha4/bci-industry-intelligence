// Mirrors the JSON written by src/export_json.py in the Python pipeline.

export interface BreakthroughDesignation {
  company: string;
  device: string;
  designation_year: number;
  source_url: string;
}

export interface Trial {
  nct_id: string;
  brief_title: string;
  overall_status: string;
  phase: string;
  study_type: string | null;
  conditions: string[];
  lead_sponsor: string;
  lead_sponsor_class: string;
  collaborators: string[];
  interventions: string[];
  start_date: string | null;
  start_year: number | null;
  countries: string[];
  breakthrough_designations: BreakthroughDesignation[];
}

export interface TrialDataset {
  generated_at: string;
  trial_count: number;
  trials: Trial[];
  fda_breakthrough_devices: BreakthroughDesignation[];
}

export type SponsorType = "ALL" | "INDUSTRY" | "ACADEMIC" | "GOVERNMENT";

export interface TrialFilters {
  searchText: string;
  status: string; // "ALL" or an overall_status value
  sponsorType: SponsorType;
  activeOnly: boolean;
  breakthroughOnly: boolean;
}

export type SortColumn = "brief_title" | "lead_sponsor" | "overall_status" | "phase" | "start_year";

export interface SortState {
  column: SortColumn;
  direction: "asc" | "desc";
}
