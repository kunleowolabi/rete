import { useQuery } from "@tanstack/react-query";
import { getSummary, getDiscos } from "../api/client";

export default function DataSidePanel() {
  const { data: summary } = useQuery({ queryKey: ["summary"], queryFn: getSummary });
  const { data: discos } = useQuery({ queryKey: ["discos"], queryFn: getDiscos });

  return (
    <div className="p-8 text-[var(--color-surface)]">
      <h2 className="text-sm font-medium text-[var(--color-text-muted)] mb-6">
        Data lineage
      </h2>

      <LineageStep
        label="Raw sources"
        detail="NERC PDFs, niggrid.org, OpenStreetMap, GRID3, REA/SE4ALL"
      />
      <Arrow />
      <LineageStep
        label="Reference & crosswalk"
        detail={`${discos?.length ?? "—"} DISCOs, plant & infrastructure geometry`}
      />
      <Arrow />
      <LineageStep
        label="Modelled estimates"
        detail="Disequilibrium demand model, fitted on 154 DISCO-quarters"
      />
      <Arrow />
      <LineageStep
        label="Served figures"
        detail={
          summary
            ? `${summary.total_demand_gw} GW demand · ${summary.total_observed_gw} GW observed · as of ${summary.period_start}`
            : "Loading…"
        }
        highlight
      />

      <p className="text-xs text-neutral-500 mt-10 leading-relaxed">
        Every number shown on Overview, Live, Infrastructure, and Trend can be traced
        back through this chain to a specific source document and, where modelled,
        a specific model version.
      </p>
    </div>
  );
}

function LineageStep({ label, detail, highlight = false }) {
  return (
    <div
      className={`rounded-lg p-3 mb-1 ${
        highlight ? "bg-[var(--color-accent)]" : "bg-[var(--color-bg-lifted)]"
      }`}
    >
      <p className="text-xs font-medium text-white">{label}</p>
      <p className="text-xs text-neutral-300 mt-0.5">{detail}</p>
    </div>
  );
}

function Arrow() {
  return <div className="text-center text-neutral-600 text-xs py-1">↓</div>;
}