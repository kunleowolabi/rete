import PageHeader from "../components/PageHeader";
import Card from "../components/Card";

const RESEARCH_PAPERS = [
  {
    title: "Cross-Country Satellite-Based Allocation",
    description:
      "Tests whether VIIRS nighttime radiance and population predict electricity consumption shares across well-supplied regions (US, France, Spain, UK, Italy, Turkey), and how reliably that model transfers between them.",
    status: "Preprint — under SSRN review",
    github: "#",
    ssrn: null,
    usedFor: "Allocation methodology reference; not currently applied to Nigerian state-level figures.",
  },
  {
    title: "Estimating Suppressed Electricity Demand in a Rationed Grid: A Disequilibrium Approach for Nigeria",
    description:
      "A Fair-Jaffee/Maddala-Nelson disequilibrium model fitted on 154 DISCO-quarters (2022Q4–2026Q1), recovering a modelled demand ceiling for Nigeria's connected electricity network from NERC's own commercial filings.",
    status: "Preprint — under SSRN review",
    github: "#",
    ssrn: null,
    usedFor: "Powers every demand and gap figure shown on the Overview, Live, and Trend pages.",
  },
];

const PUBLIC_DATASETS = [
  {
    name: "GRID3 Nigeria Administrative Boundaries",
    publisher: "GRID3",
    use: "State and LGA spatial boundaries — the spine every other layer joins to.",
    note: null,
    url: "https://grid3.org",
  },
  {
    name: "NERC Quarterly Reports",
    publisher: "Nigerian Electricity Regulatory Commission",
    use: "Per-DISCO energy offtake, billing efficiency, ATC&C loss, metering rate — 2017Q3 to present.",
    note: null,
    url: "https://nerc.gov.ng",
  },
  {
    name: "niggrid.org 24hr Grid Dashboard",
    publisher: "Nigerian Independent System Operator (NISO)",
    use: "Live per-plant generation and per-DISCO load allocation, scraped hourly.",
    note: null,
    url: "https://niggrid.org",
  },
  {
    name: "OpenStreetMap Power Infrastructure",
    publisher: "OpenStreetMap contributors, via Geofabrik",
    use: "Plant locations, substations, and transmission lines.",
    note: "HV (330/132kV) coverage is strong. MV (33kV) and LV (11kV) coverage is sparse — most distribution-tier lines are not mapped.",
    url: "https://www.openstreetmap.org",
  },
  {
    name: "Nigeria Mini-Grid Site Inventory",
    publisher: "Nigeria SE4ALL",
    use: "66 documented mini-grid sites with location, capacity, and status.",
    note: "Last updated in 2020. REA reports 900+ mini-grids under construction nationally as of 2025 — this dataset does not reflect that.",
    url: "https://www.nigeriase4all.gov.ng/mini-grids",
  },
];

const CUSTOM_DATASETS = [
  {
    name: "Plant & DISCO Reference Crosswalk",
    scope: "33 power plants (niggrid), 28 NERC-matched, 12 DISCOs, alias mappings across 4 independent sources.",
    description:
      "Reconciles the different plant universes reported by niggrid, NERC, and OpenStreetMap into one consistent reference.",
    access: "Available on request.",
  },
  {
    name: "DISCO Demand Estimation Panel",
    scope: "154 DISCO-quarters, 2022Q4–2026Q1, 11 DISCOs.",
    description:
      "The fitted disequilibrium model output — observed offtake, modelled demand ceiling, regime probability, and suppressed gap per DISCO per quarter.",
    access: "Available on request.",
  },
  {
    name: "OSM-Derived Infrastructure Layer",
    scope: "196 plant geometries (23 matched to reference), 389 substations, 895 transmission line segments.",
    description:
      "Cleaned, simplified, and geocoded power infrastructure extracted from OpenStreetMap for Nigeria.",
    access: "Available on request.",
  },
];

export default function DataPage({ onCollapse }) {
  return (
    <div>
      <PageHeader title="Data & Methodology" subtitle="Every figure traces back to a source" onCollapse={onCollapse} />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        <Card title="Research papers">
          {RESEARCH_PAPERS.map((paper, i) => (
            <div
              key={paper.title}
              className="border-b border-white/10 last:border-0"
              style={{ padding: i === 0 ? "0 0 16px 0" : "16px 0" }}
            >
              <h3 className="text-sm font-semibold text-white">{paper.title}</h3>
              <p className="text-xs text-[var(--color-line)]" style={{ marginTop: 4 }}>{paper.status}</p>
              <p className="text-xs text-white/60" style={{ marginTop: 8, lineHeight: 1.6 }}>{paper.description}</p>
              <p className="text-xs text-white/40 italic" style={{ marginTop: 8, lineHeight: 1.6 }}>{paper.usedFor}</p>
              <div className="flex" style={{ gap: 16, marginTop: 10 }}>
                {paper.github && (
                  <a href={paper.github} className="text-xs text-[var(--color-accent)] hover:underline">
                    GitHub →
                  </a>
                )}
                {paper.ssrn && (
                  <a href={paper.ssrn} className="text-xs text-[var(--color-accent)] hover:underline">
                    SSRN →
                  </a>
                )}
              </div>
            </div>
          ))}
        </Card>

        <Card title="Public datasets">
          {PUBLIC_DATASETS.map((ds, i) => (
            <div
              key={ds.name}
              className="border-b border-white/10 last:border-0"
              style={{ padding: i === 0 ? "0 0 14px 0" : "14px 0" }}
            >
              <div className="flex items-baseline justify-between" style={{ gap: 12 }}>
                <h3 className="text-sm font-medium text-white">{ds.name}</h3>
                {ds.url && (
                  <a href={ds.url} className="text-xs text-[var(--color-accent)] hover:underline whitespace-nowrap">
                    Source →
                  </a>
                )}
              </div>
              <p className="text-xs text-white/40" style={{ marginTop: 2 }}>{ds.publisher}</p>
              <p className="text-xs text-white/60" style={{ marginTop: 6, lineHeight: 1.6 }}>{ds.use}</p>
              {ds.note && (
                <p className="text-xs text-[var(--color-line)] italic" style={{ marginTop: 6, lineHeight: 1.6 }}>
                  {ds.note}
                </p>
              )}
            </div>
          ))}
        </Card>

        <Card title="Custom datasets">
          {CUSTOM_DATASETS.map((ds, i) => (
            <div
              key={ds.name}
              className="border-b border-white/10 last:border-0"
              style={{ padding: i === 0 ? "0 0 14px 0" : "14px 0" }}
            >
              <h3 className="text-sm font-medium text-white">{ds.name}</h3>
              <p className="text-xs text-white/40" style={{ marginTop: 2 }}>{ds.scope}</p>
              <p className="text-xs text-white/60" style={{ marginTop: 6, lineHeight: 1.6 }}>{ds.description}</p>
              <p className="text-xs text-[var(--color-accent)]" style={{ marginTop: 6 }}>{ds.access}</p>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}