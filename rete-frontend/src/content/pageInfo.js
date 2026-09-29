// Notes shown in the "i" card beside a page title. Edit here during the
// frontend accuracy pass; keep the rows in step with the figures the page shows.

export const OVERVIEW_INFO = {
  title: "Overview",
  items: [
    {
      figure: "Generating now",
      note: "The total shown on niggrid's dashboard for the latest hour, as reported by the GenCos.",
    },
    {
      figure: "Modelled ceiling and live gap",
      note: "From the demand model's latest fitted quarter (Q1 2026). It covers the connected network only, not total national demand.",
    },
    {
      figure: "Record peak",
      note: "The highest output ever delivered to the grid, on 4 March 2025, per TCN.",
    },
    {
      figure: "Installed capacity",
      note: "NERC's Q1 2026 report, covering 28 grid-connected plants. Other publications quote 14,147 MW and 15,193 MW under different definitions of what counts.",
    },
    {
      figure: "Available capacity",
      note: "NERC's August 2026 factsheet: the average capacity available for dispatch that month. GenCos declare this figure to the System Operator; it is not independently tested.",
    },
    {
      figure: "Wheeling capacity",
      note: "As reported by TCN. It depends on DisCos being ready to take the load.",
    },
    {
      figure: "Delivered to DISCOs",
      note: "The load niggrid shows allocated to the DISCOs. It is an allocation figure, not metered consumption.",
    },
    {
      figure: "Delivered per person",
      note: "The DISCO allocation divided by the UN's 2026 population estimate (World Population Prospects 2024, medium variant). Population is modelled, since Nigeria's last census was in 2006, and it includes people with no grid connection.",
    },
  ],
};