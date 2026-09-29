import { useQuery } from "@tanstack/react-query";
import { getDiscoDetail, getDiscoNercTrends } from "../api/client";
import Skeleton from "./Skeleton";

const num = (v, digits = 0) => {
  if (v == null || v === "" || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits });
};

const quarterLabel = (iso) => {
  if (!iso) return null;
  const [year, month] = String(iso).slice(0, 7).split("-").map(Number);
  return `Q${Math.floor((month - 1) / 3) + 1} ${year}`;
};

export default function DiscoDetailCard({ discoId, onClose, topOffset = 16, leftOffset }) {
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["disco-detail", discoId],
    queryFn: () => getDiscoDetail(discoId),
    enabled: !!discoId,
  });

  const { data: nerc, isLoading: nercLoading } = useQuery({
    queryKey: ["disco-nerc-trends", discoId],
    queryFn: () => getDiscoNercTrends(discoId),
    enabled: !!discoId,
  });

  const loading = detailLoading || nercLoading;
  const latestNerc = nerc?.points?.[nerc.points.length - 1];
  const quarter = quarterLabel(detail?.period_start);

  const rows = [
    { label: "Average offtake", value: num(detail?.energy_offtake_mwh_per_h), unit: "MWh/h" },
    { label: "Modelled demand", value: num(detail?.fitted_demand_mwh_per_h), unit: "MWh/h" },
    { label: "Suppressed gap", value: num(detail?.suppressed_gap_mwh_per_h), unit: "MWh/h", highlight: true },
    { label: "ATC&C loss", value: num(detail?.actual_atcc_pct, 1), unit: "%" },
    { label: "Billing efficiency", value: num(detail?.billing_efficiency_pct, 1), unit: "%" },
    { label: "Metering rate", value: num(latestNerc?.metering_rate_pct, 1), unit: "%" },
    { label: "Customers metered", value: num(latestNerc?.customers_metered) },
  ];

  return (
    <div
      className="content-scale absolute w-80 bg-black/85 border border-white/15 rounded-xl shadow-2xl overflow-hidden z-30 text-white flex flex-col"
      style={{ top: topOffset, left: leftOffset, maxHeight: `calc(100vh - ${topOffset}px - 24px)` }}
    >
      <div
        className="flex items-start justify-between border-b border-white/15"
        style={{ padding: "20px 22px" }}
      >
        <div style={{ minWidth: 0 }}>
          <p className="text-xs text-white/50">DISCO</p>
          {detailLoading ? (
            <div style={{ marginTop: 6 }}>
              <Skeleton width={140} height={14} />
            </div>
          ) : (
            <p className="text-sm font-semibold text-white" style={{ marginTop: 4 }}>{detail?.name}</p>
          )}
          <p className="text-xs text-white/50" style={{ marginTop: 4, lineHeight: 1.5 }}>
            {detailLoading ? "" : detail?.states_served}
          </p>
        </div>
        <button
          onClick={onClose}
          title="Hide"
          className="text-white/60 hover:text-white"
          style={{ background: "none", border: "none", cursor: "pointer", padding: 4, marginTop: 2 }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="3" />
          </svg>
        </button>
      </div>

      <div style={{ padding: "6px 22px 18px 22px", overflow: "auto", flex: 1, minHeight: 0 }}>
        {loading ? (
          <div style={{ paddingTop: 14 }}>
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="flex justify-between border-b border-white/10 last:border-0" style={{ padding: "14px 0" }}>
                <Skeleton width="45%" height={11} />
                <Skeleton width="20%" height={13} />
              </div>
            ))}
          </div>
        ) : (
          <>
            {quarter && (
              <p className="text-xs text-white/40" style={{ padding: "12px 0 4px 0" }}>
                {quarter} · NERC quarterly figures
              </p>
            )}
            <div>
              {rows.map((row) => (
                <Row key={row.label} {...row} />
              ))}
            </div>
            {detail?.is_approximate && (
              <p className="text-xs text-[var(--color-line)] italic" style={{ paddingTop: 14, lineHeight: 1.5 }}>
                We don't yet have this DISCO's exact service area, so the map shows the entire
                state(s) it operates in instead. The real boundary is smaller.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Row({ label, value, unit, highlight = false }) {
  const hasValue = value !== "—";
  return (
    <div
      className="flex items-baseline justify-between border-b border-white/10 last:border-0"
      style={{ padding: "14px 0" }}
    >
      <span className="text-xs text-white/50">{label}</span>
      <span>
        <span className={`text-sm font-semibold ${highlight ? "text-[var(--color-line)]" : "text-white"}`}>
          {value}
        </span>
        {unit && hasValue && (
          <span className="text-xs text-white/40" style={{ marginLeft: 4 }}>
            {unit}
          </span>
        )}
      </span>
    </div>
  );
}