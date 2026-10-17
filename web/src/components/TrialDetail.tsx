import { useEffect } from "react";
import type { Trial } from "../types";
import { formatPhase, formatStatus } from "../lib/trials";

interface TrialDetailProps {
  trial: Trial;
  onClose: () => void;
}

function ListOrNone({ items }: { items: string[] }) {
  if (items.length === 0) return <span className="muted">None listed</span>;
  return (
    <ul className="plain-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function TrialDetail({ trial, onClose }: TrialDetailProps) {
  // Close the panel with the Escape key.
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <aside
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" className="close-button" onClick={onClose} aria-label="Close details">
          ×
        </button>
        <p className="muted">{trial.nct_id}</p>
        <h2 id="detail-title">{trial.brief_title}</h2>

        <dl className="detail-grid">
          <dt>Sponsor</dt>
          <dd>{trial.lead_sponsor}</dd>
          <dt>Status</dt>
          <dd>{formatStatus(trial.overall_status)}</dd>
          <dt>Phase</dt>
          <dd>{formatPhase(trial.phase)}</dd>
          <dt>Start date</dt>
          <dd>{trial.start_date ?? "Not listed"}</dd>
        </dl>

        {trial.breakthrough_designations.length > 0 && (
          <section className="fda-box">
            <h3>FDA Breakthrough Device Designation</h3>
            <ul className="plain-list">
              {trial.breakthrough_designations.map((designation) => (
                <li key={designation.device}>
                  {designation.device} ({designation.designation_year}){" "}
                  <a href={designation.source_url} target="_blank" rel="noreferrer">
                    source
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}

        <h3>Conditions</h3>
        <ListOrNone items={trial.conditions} />
        <h3>Interventions</h3>
        <ListOrNone items={trial.interventions} />
        <h3>Collaborators</h3>
        <ListOrNone items={trial.collaborators} />
        <h3>Countries</h3>
        <ListOrNone items={trial.countries} />

        <a className="external-link" href={`https://clinicaltrials.gov/study/${trial.nct_id}`} target="_blank" rel="noreferrer">
          View on ClinicalTrials.gov
        </a>
      </aside>
    </div>
  );
}
