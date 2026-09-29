import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMapConfig, useSelectedDisco } from "../context/MapContext";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import GroupedBarChart from "../components/GroupedBarChart";
import QuarterPager from "../components/QuarterPager";
import Skeleton from "../components/Skeleton";
import ErrorState from "../components/ErrorState";
import {
  getDiscos,
  getDiscoDetail,
  getDiscoTimeseries,
  getDiscoNercTrends,
} from "../api/client";

const quarterLabel = (iso) => {
  if (!iso) return "";
  const [year, month] = String(iso).slice(0, 7).split("-").map(Number);
  return `Q${Math.floor((month - 1) / 3) + 1} '${String(year).slice(2)}`;
};

const MODEL_START = "2022-10-01";
const WINDOW = 4;

function windowFor(rows, page) {
  if (!rows.length) return [];
  const end = rows.length - page * WINDOW;
  const start = Math.max(end - WINDOW, 0);
  return rows.slice(start, Math.max(end, 0));
}

function rangeLabel(rows) {
  if (!rows.length) return "";
  const first = quarterLabel(rows[0].period_start);
  const last = quarterLabel(rows[rows.length - 1].period_start);
  return first === last ? first : `${first} – ${last}`;
}

export default function Trend({ onCollapse }) {
  const [selectedDiscoId, setSelectedDiscoId] = useSelectedDisco();
  const [demandPage, setDemandPage] = useState(0);
  const [nercPage, setNercPage] = useState(0);

  const { data: discos } = useQuery({ queryKey: ["discos"], queryFn: getDiscos });

  const activeDiscoId = selectedDiscoId || discos?.[0]?.disco_id;

  const { data: detail } = useQuery({
    queryKey: ["disco-detail", activeDiscoId],
    queryFn: () => getDiscoDetail(activeDiscoId),
    enabled: !!activeDiscoId,
  });

  const {
    data: timeseriesRaw,
    isLoading: tsLoading,
    isError: tsError,
    refetch: refetchTs,
  } = useQuery({
    queryKey: ["disco-timeseries", activeDiscoId],
    queryFn: () => getDiscoTimeseries(activeDiscoId),
    enabled: !!activeDiscoId,
  });

  const timeseries = useMemo(
    () => (timeseriesRaw || []).filter((r) => r.period_start >= MODEL_START),
    [timeseriesRaw]
  );

  const {
    data: nercTrends,
    isLoading: nercLoading,
    isError: nercError,
    refetch: refetchNerc,
  } = useQuery({
    queryKey: ["disco-nerc-trends", activeDiscoId],
    queryFn: () => getDiscoNercTrends(activeDiscoId),
    enabled: !!activeDiscoId,
  });

  const nercPoints = nercTrends?.points || [];

  const resetPaging = (id) => {
    setSelectedDiscoId(id);
    setDemandPage(0);
    setNercPage(0);
  };

  const discoBoundaryFC = useMemo(() => {
    if (!detail?.boundary_geojson) return null;
    try {
      const geom = JSON.parse(detail.boundary_geojson);
      return {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: { disco_id: detail.disco_id, name: detail.name, is_approximate: detail.is_approximate },
            geometry: geom,
          },
        ],
      };
    } catch {
      return null;
    }
  }, [detail]);

  useMapConfig(
    { discoBoundaries: discoBoundaryFC },
    { discoBoundaries: true }
  );

  const demandWindow = windowFor(timeseries, demandPage);
  const demandMaxPage = Math.max(Math.ceil(timeseries.length / WINDOW) - 1, 0);
  const demandSeries = [
    { label: "Offtake", color: "#ffcc4d", data: demandWindow.map((r) => Number(r.energy_offtake_mwh_per_h)) },
    { label: "Modelled demand", color: "#ffffff", data: demandWindow.map((r) => Number(r.fitted_demand_mwh_per_h)) },
  ];

  const nercWindow = windowFor(nercPoints, nercPage);
  const nercMaxPage = Math.max(Math.ceil(nercPoints.length / WINDOW) - 1, 0);
  const nercSeries = [
    { label: "ATC&C loss (%)", color: "#ffcc4d", data: nercWindow.map((r) => Number(r.actual_atcc_pct)) },
    { label: "Billing efficiency (%)", color: "#1d9bf0", data: nercWindow.map((r) => Number(r.billing_efficiency_pct)) },
    { label: "Metering rate (%)", color: "#0d5c8f", data: nercWindow.map((r) => Number(r.metering_rate_pct)) },
  ];

  return (
    <div>
      <PageHeader title="Trend" subtitle="Historical performance by DISCO" onCollapse={onCollapse} />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        <select
          className="w-full text-sm bg-black/85 border border-white/15 rounded-lg text-white"
          style={{ padding: "12px 14px" }}
          value={activeDiscoId || ""}
          onChange={(e) => resetPaging(e.target.value)}
        >
          {discos?.map((d) => (
            <option key={d.disco_id} value={d.disco_id} className="text-black">
              {d.name}
            </option>
          ))}
        </select>

        <Card title="Offtake vs modelled demand">
          {tsError ? (
            <ErrorState message="Couldn't load this DISCO's history." onRetry={refetchTs} />
          ) : (
            <>
              <QuarterPager
                label={rangeLabel(demandWindow)}
                onPrev={() => setDemandPage((p) => Math.min(p + 1, demandMaxPage))}
                onNext={() => setDemandPage((p) => Math.max(p - 1, 0))}
                canPrev={demandPage < demandMaxPage}
                canNext={demandPage > 0}
              />
              {tsLoading ? (
                <Skeleton width="100%" height={220} radius={8} />
              ) : (
                <GroupedBarChart labels={demandWindow.map((r) => quarterLabel(r.period_start))} series={demandSeries} />
              )}
              <div className="flex" style={{ gap: 16, marginTop: 12 }}>
                {demandSeries.map((s) => (
                  <LegendDot key={s.label} color={s.color} label={s.label} />
                ))}
              </div>
              <p className="text-xs text-white/40" style={{ marginTop: 8 }}>
                {timeseries.length} quarters available since the model's start (2022Q4), in MWh/h.
              </p>
            </>
          )}
        </Card>

        <Card title="NERC performance metrics">
          {nercError ? (
            <ErrorState message="Couldn't load NERC metrics." onRetry={refetchNerc} />
          ) : (
            <>
              <QuarterPager
                label={rangeLabel(nercWindow)}
                onPrev={() => setNercPage((p) => Math.min(p + 1, nercMaxPage))}
                onNext={() => setNercPage((p) => Math.max(p - 1, 0))}
                canPrev={nercPage < nercMaxPage}
                canNext={nercPage > 0}
              />
              {nercLoading ? (
                <Skeleton width="100%" height={220} radius={8} />
              ) : (
                <GroupedBarChart labels={nercWindow.map((r) => quarterLabel(r.period_start))} series={nercSeries} />
              )}
              <div className="flex" style={{ gap: 16, marginTop: 12 }}>
                {nercSeries.map((s) => (
                  <LegendDot key={s.label} color={s.color} label={s.label} />
                ))}
              </div>
            </>
          )}
        </Card>

        {detail?.is_approximate && (
          <p className="text-xs text-[var(--color-line)] italic">
            We don't yet have this DISCO's exact service area, so the map shows the entire
            state(s) it operates in instead. The real boundary is smaller.
          </p>
        )}
      </div>
    </div>
  );
}

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center" style={{ gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      <span className="text-xs text-white/50">{label}</span>
    </div>
  );
}