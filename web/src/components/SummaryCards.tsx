import type { Summary } from "../lib/trials";

interface SummaryCardsProps {
  summary: Summary;
}

export default function SummaryCards({ summary }: SummaryCardsProps) {
  const cards = [
    { label: "Trials shown", value: summary.totalTrials },
    { label: "Active or recruiting", value: summary.activeTrials },
    { label: "Distinct sponsors", value: summary.distinctSponsors },
    { label: "Sponsors with FDA Breakthrough", value: summary.breakthroughSponsors },
  ];
  return (
    <section className="summary-cards" aria-label="Summary">
      {cards.map((card) => (
        <div className="card" key={card.label}>
          <div className="card-value">{card.value}</div>
          <div className="card-label">{card.label}</div>
        </div>
      ))}
    </section>
  );
}
