import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { sampleDataset } from "./test/fixtures";

function mockFetch(response: { ok: boolean; status?: number; body?: unknown }) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status ?? 200,
      json: () => Promise.resolve(response.body),
    }),
  );
}

describe("App", () => {
  beforeEach(() => mockFetch({ ok: true, body: sampleDataset }));
  afterEach(() => vi.unstubAllGlobals());

  it("loads the dataset and shows every trial with summary counts", async () => {
    render(<App dataUrl="/data/trials.json" />);
    expect(await screen.findByText("PRIME Study of the N1 Implant")).toBeInTheDocument();
    expect(screen.getByText("Last refresh: October 12, 2026.", { exact: false })).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "Summary" });
    expect(within(summary).getByText("Trials shown").previousSibling).toHaveTextContent("3");
    expect(screen.getAllByText("FDA Breakthrough").length).toBeGreaterThan(0);
  });

  it("narrows the table as the user types a search", async () => {
    const user = userEvent.setup();
    render(<App dataUrl="/data/trials.json" />);
    await screen.findByText("PRIME Study of the N1 Implant");

    await user.type(screen.getByRole("searchbox"), "mirror");
    expect(screen.getByText("BCI Robotic Mirror Therapy After Stroke")).toBeInTheDocument();
    expect(screen.queryByText("PRIME Study of the N1 Implant")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(screen.getByText("PRIME Study of the N1 Implant")).toBeInTheDocument();
  });

  it("sorts by a column when its header is clicked", async () => {
    const user = userEvent.setup();
    render(<App dataUrl="/data/trials.json" />);
    await screen.findByText("PRIME Study of the N1 Implant");

    await user.click(screen.getByRole("button", { name: /Sponsor/ }));
    const rows = screen.getAllByRole("row");
    expect(within(rows[1]).getByText("Beijing Tiantan Hospital")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Sponsor/ })).toHaveAttribute("aria-sort", "ascending");
  });

  it("opens trial details with the FDA designation and closes with Escape", async () => {
    const user = userEvent.setup();
    render(<App dataUrl="/data/trials.json" />);
    await user.click(await screen.findByRole("button", { name: "PRIME Study of the N1 Implant" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("N1 Implant (2020)", { exact: false })).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: "View on ClinicalTrials.gov" })).toHaveAttribute(
      "href",
      "https://clinicaltrials.gov/study/NCT11111111",
    );

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("pages long result lists with a Show more button", async () => {
    const user = userEvent.setup();
    const manyTrials = [];
    for (let index = 0; index < 30; index += 1) {
      manyTrials.push({ ...sampleDataset.trials[1], nct_id: `NCT9${index}`, brief_title: `Trial number ${index}` });
    }
    mockFetch({ ok: true, body: { ...sampleDataset, trials: manyTrials, trial_count: 30 } });
    render(<App dataUrl="/data/trials.json" />);
    await screen.findByText("Showing 25 of 30 trials");
    expect(screen.getAllByRole("row")).toHaveLength(26); // header + 25

    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(screen.getAllByRole("row")).toHaveLength(31);
    expect(screen.queryByRole("button", { name: "Show more" })).not.toBeInTheDocument();
  });

  it("shows an error message when the data file fails to load", async () => {
    mockFetch({ ok: false, status: 404 });
    render(<App dataUrl="/data/trials.json" />);
    expect(await screen.findByText("Could not load trial data (HTTP 404)")).toBeInTheDocument();
  });
});
