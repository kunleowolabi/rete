import { useQuery } from "@tanstack/react-query";
import { useMapConfig } from "../context/MapContext";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import DonutChart from "../components/DonutChart";
import EmissionsChart from "../components/EmissionsChart";
import InfoTable from "../components/InfoTable";
import RankedBar from "../components/RankedBar";
import Skeleton from "../components/Skeleton";
import ErrorState from "../components/ErrorState";
import {
  getSummary,
  getInfrastructureSummary,
  getGencoUtilization,
  getDiscosRanked,
  getPlants,
  getSubstations,
  getLines,
  getDiscoBoundaries,
  getMinigrids,
} from "../api/client";

const num = (v, digits = 0) => {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits });
};

export default function Infrastructure({ onCollapse }) {
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
  } = useQuery({ queryKey: ["infrastructure-summary"], queryFn: getInfrastructureSummary });

  const { data: summaryFigures, isError: figuresError } = useQuery({ queryKey: ["summary"], queryFn: getSummary });

  const {
    data: gencoUtil,
    isLoading: gencoUtilLoading,
    isError: gencoUtilError,
    refetch: refetchGencoUtil,
  } = useQuery({ queryKey: ["genco-utilization"], queryFn: getGencoUtilization });

  const {
    data: ranked,
    isLoading: rankedLoading,
    isError: rankedError,
    refetch: refetchRanked,
  } = useQuery({ queryKey: ["discos-ranked"], queryFn: getDiscosRanked });

  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: getPlants });
  const { data: substations } = useQuery({ queryKey: ["substations"], queryFn: getSubstations });
  const { data: lines } = useQuery({ queryKey: ["lines"], queryFn: getLines });
  const { data: discoBoundaries } = useQuery({ queryKey: ["disco-boundaries"], queryFn: getDiscoBoundaries });
  const { data: minigrids } = useQuery({ queryKey: ["minigrids"], queryFn: getMinigrids });

  useMapConfig(
    { discoBoundaries, plants, substations, lines, minigrids },
    { discoBoundaries: true, plants: true, substations: true, lines: true }
  );

  const gencosReporting = (gencoUtil || []).filter((g) => Number(g.current_mw) > 0).length;

  const atccMax = Math.max(...(ranked || []).map((d) => Number(d.actual_atcc_pct || 0)), 1);
  const billingMax = 100;

  const wheeling = summaryFigures?.figures?.wheeling_capacity_mw;
  const peakWheeled = summaryFigures?.figures?.record_peak_generation_mw;

  return (
    <div>
      <PageHeader title="Infrastructure" subtitle="Generation, transmission and distribution" onCollapse={onCollapse} />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 28 }}>
        {/* ── Generation ────────────────────────────────────────────── */}
        <div>
          <p className="text-xs font-semibold text-[var(--color-line)]" style={{ marginBottom: 12 }}>
            Generation
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 47%)",
              justifyContent: "space-between",
              rowGap: 20,
              marginBottom: 20,
            }}
          >
            <StatCard
              label="Installed capacity"
              value={num(summary?.totals?.total_installed_mw)}
              unit="MW"
              loading={summaryLoading}
              error={summaryError}
            />
            <StatCard
              label="Available capacity"
              value={num(summaryFigures?.figures?.available_capacity_mw?.value)}
              unit="MW"
              sub={
                summaryFigures?.figures?.available_capacity_mw
                  ? `as at ${summaryFigures.figures.available_capacity_mw.as_of}`
                  : undefined
              }
              loading={!summaryFigures && !figuresError}
              error={figuresError}
            />
            <StatCard
              label="Active plants"
              value={`${summary?.totals?.active_plants} / ${summary?.totals?.total_plants}`}
              loading={summaryLoading}
              error={summaryError}
            />
            <StatCard
              label="GenCos delivering now"
              value={`${gencosReporting} / ${gencoUtil?.length ?? "—"}`}
              loading={gencoUtilLoading}
              error={gencoUtilError}
            />
          </div>

          <Card title="Energy mix and estimated emissions">
            {summaryError ? (
              <ErrorState message="Couldn't load fuel mix." onRetry={refetchSummary} />
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 24 }}>
                <DonutChart fuelMix={summary?.fuel_mix} loading={summaryLoading} />
                <EmissionsChart fuelMix={summary?.fuel_mix} loading={summaryLoading} />
              </div>
            )}
          </Card>

          <div style={{ marginTop: 20 }}>
            <Card title="GenCo utilization, now"
            hint="Installed capacity is NERC's Q1 2026 reported figure. Some readings can exceed 100% — either a plant briefly running above its rated nameplate capacity, or a difference between the installed-capacity figure on record and the plant's true rating.">
              {gencoUtilError ? (
                <ErrorState message="Couldn't load GenCo utilization." onRetry={refetchGencoUtil} />
              ) : gencoUtilLoading ? (
                <RowSkeletons rows={10} />
              ) : (
                <>
                  {gencoUtil?.map((g) => (
                    <RankedBar
                      key={g.genco_id}
                      label={g.name}
                      value={g.utilization_pct}
                      max={100}
                      color="var(--color-accent)"
                    />
                  ))}
                  <p className="text-xs text-white/40" style={{ marginTop: 8 }}>
                    Current output as a share of installed capacity.
                  </p>
                </>
              )}
            </Card>
          </div>
        </div>

        {/* ── Transmission ──────────────────────────────────────────── */}
        <div>
          <p className="text-xs font-semibold text-[var(--color-line)]" style={{ marginBottom: 12 }}>
            Transmission
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 47%)",
              justifyContent: "space-between",
              rowGap: 20,
              marginBottom: 8,
            }}
          >
            <StatCard label="Wheeling capacity" value={num(wheeling?.value)} unit="MW" loading={!summaryFigures && !figuresError} error={figuresError} />
            <StatCard label="Peak wheeled" value={num(peakWheeled?.value)} unit="MW" loading={!summaryFigures && !figuresError} error={figuresError} />
          </div>

          <p className="text-xs text-white/40 italic" style={{ marginBottom: 20 }}>
            Peak wheeled is based on TCN's reported record peak generation, on{" "}
            {peakWheeled?.as_of ?? "4 March 2025"} — TCN describes this as the highest amount ever
            wheeled to the grid.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 20 }}>
            <Card title="Transmission lines">
              {summaryError ? (
                <ErrorState message="Couldn't load." onRetry={refetchSummary} />
              ) : summary?.lines_by_voltage ? (
                <InfoTable
                  columns={[
                    { key: "voltage_tier", label: "Tier", render: (r) => r.voltage_tier || "Unknown" },
                    { key: "total_length_km", label: "Length", render: (r) => `${r.total_length_km} km` },
                  ]}
                  rows={summary.lines_by_voltage}
                />
              ) : (
                <TableSkeleton rows={4} />
              )}
            </Card>

            <Card title="Substations by type">
              {summaryError ? (
                <ErrorState message="Couldn't load." onRetry={refetchSummary} />
              ) : summary?.substations_by_type ? (
                <InfoTable
                  columns={[
                    { key: "substation_type", label: "Type", render: (r) => <span className="capitalize">{r.substation_type}</span> },
                    { key: "count", label: "Count" },
                  ]}
                  rows={summary.substations_by_type}
                />
              ) : (
                <TableSkeleton rows={4} />
              )}
            </Card>
          </div>

          <p className="text-xs text-white/40 italic" style={{ marginTop: 12 }}>
            {summary?.note}
          </p>
        </div>

        {/* ── Distribution ──────────────────────────────────────────── */}
        <div>
          <p className="text-xs font-semibold text-[var(--color-line)]" style={{ marginBottom: 12 }}>
            Distribution
          </p>

          <Card title="ATC&C loss, ranked (latest quarter)">
            {rankedError ? (
              <ErrorState message="Couldn't load DISCO rankings." onRetry={refetchRanked} />
            ) : rankedLoading ? (
              <RowSkeletons rows={8} />
            ) : (
              ranked?.map((d) => (
                <RankedBar key={d.disco_id} label={d.name} value={d.actual_atcc_pct} max={atccMax} color="var(--color-line)" />
              ))
            )}
          </Card>

          <div style={{ marginTop: 20 }}>
            <Card title="Billing efficiency, ranked (latest quarter)">
              {rankedError ? (
                <ErrorState message="Couldn't load DISCO rankings." onRetry={refetchRanked} />
              ) : rankedLoading ? (
                <RowSkeletons rows={8} />
              ) : (
                [...(ranked || [])]
                  .sort((a, b) => Number(a.billing_efficiency_pct || 0) - Number(b.billing_efficiency_pct || 0))
                  .map((d) => (
                    <RankedBar
                      key={d.disco_id}
                      label={d.name}
                      value={d.billing_efficiency_pct}
                      max={billingMax}
                      color="var(--color-accent)"
                    />
                  ))
              )}
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

function RowSkeletons({ rows = 5 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <div className="flex justify-between" style={{ marginBottom: 6 }}>
            <Skeleton width="40%" height={11} />
            <Skeleton width="15%" height={11} />
          </div>
          <Skeleton width="100%" height={8} radius={2} />
        </div>
      ))}
    </>
  );
}

function TableSkeleton({ rows = 4 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex justify-between" style={{ padding: "8px 0" }}>
          <Skeleton width="45%" height={11} />
          <Skeleton width="20%" height={11} />
        </div>
      ))}
    </div>
  );
}