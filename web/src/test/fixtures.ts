import type { Trial, TrialDataset } from "../types";

export function makeTrial(overrides: Partial<Trial>): Trial {
  return {
    nct_id: "NCT00000000",
    brief_title: "Sample trial",
    overall_status: "RECRUITING",
    phase: "NA",
    study_type: "INTERVENTIONAL",
    conditions: ["ALS"],
    lead_sponsor: "University of Michigan",
    lead_sponsor_class: "OTHER",
    collaborators: [],
    interventions: ["Implant"],
    start_date: "2024-01",
    start_year: 2024,
    countries: ["United States"],
    breakthrough_designations: [],
    ...overrides,
  };
}

export const neuralinkTrial = makeTrial({
  nct_id: "NCT11111111",
  brief_title: "PRIME Study of the N1 Implant",
  lead_sponsor: "Neuralink Corp",
  lead_sponsor_class: "INDUSTRY",
  conditions: ["Quadriplegia", "ALS"],
  start_year: 2023,
  breakthrough_designations: [
    { company: "Neuralink", device: "N1 Implant", designation_year: 2020, source_url: "https://example.com/n1" },
  ],
});

export const strokeTrial = makeTrial({
  nct_id: "NCT22222222",
  brief_title: "BCI Robotic Mirror Therapy After Stroke",
  lead_sponsor: "Beijing Tiantan Hospital",
  conditions: ["Ischemic Stroke"],
  overall_status: "COMPLETED",
  start_year: 2021,
});

export const nihTrial = makeTrial({
  nct_id: "NCT33333333",
  brief_title: "Speech Neuroprosthesis Feasibility",
  lead_sponsor: "National Institute of Neurological Disorders and Stroke",
  lead_sponsor_class: "NIH",
  phase: "PHASE1",
  start_year: null,
  start_date: null,
});

export const sampleDataset: TrialDataset = {
  generated_at: "2026-10-12T09:05:00+00:00",
  trial_count: 3,
  trials: [neuralinkTrial, strokeTrial, nihTrial],
  fda_breakthrough_devices: neuralinkTrial.breakthrough_designations,
};
