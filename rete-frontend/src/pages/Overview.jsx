import { useQuery } from "@tanstack/react-query";
import { useMapConfig } from "../context/MapContext";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import GenerationBar from "../components/GenerationBar";
import ErrorState from "../components/ErrorState";
import {
  getSummary,
  getGenerationCurrent,
  getDiscoLiveAllocation,
  getInfrastructureSummary,
  getDiscoBoundaries,
  getPlants,
  getSubstations,
  getLines,
  getMinigrids,
} from "../api/client";

const num = (v, digits = 0) => {
  if (v == null || v === "" || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits });
};

export default function Overview({ onCollapse, onInfo, infoActive }) {
  const {
    data: summary,
    isLoading: summaryLoading,
    isError: summaryError,
    refetch: refetchSummary,
  } = useQuery({ queryKey: ["summary"], queryFn: getSummary });

  const {
    data: current,
    isLoading: currentLoading,
    isError: currentError,
    refetch: refetchCurrent,
  } = useQuery({ queryKey: ["generation-current"], queryFn: getGenerationCurrent });

  const { data: allocation, isLoading: allocationLoading, isError: allocationError } = useQuery({
    queryKey: ["disco-live-allocation"],
    queryFn: getDiscoLiveAllocation,
  });

  const { data: infra, isLoading: infraLoading, isError: infraError } = useQuery({
    queryKey: ["infrastructure-summary"],
    queryFn: getInfrastructureSummary,
  });

  const { data: discoBoundaries } = useQuery({ queryKey: ["disco-boundaries"], queryFn: getDiscoBoundaries });
  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: getPlants });
  const { data: substations } = useQuery({ queryKey: ["substations"], queryFn: getSubstations });
  const { data: lines } = useQuery({ queryKey: ["lines"], queryFn: getLines });
  const { data: minigrids } = useQuery({ queryKey: ["minigrids"], queryFn: getMinigrids });

  useMapConfig(
    { discoBoundaries, plants, substations, lines, minigrids },
    { discoBoundaries: true }
  );

  const figures = summary?.figures;
  const allocationTotal = allocation?.[0]?.total_mw;
  const allocationAsAt = allocation?.[0]?.observed_hour;
  const population = figures?.population?.value;
  const perPerson =
    allocationTotal && population ? (Number(allocationTotal) * 1e6) / Number(population) : null;

  const heroError = currentError || summaryError;

  return (
    <div>
      <PageHeader
        title="Overview"
        subtitle="National headline figures"
        onCollapse={onCollapse}
        onInfo={onInfo}
        infoActive={infoActive}
      />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        {heroError ? (
          <div className="bg-black/85 border border-white/15 rounded-lg" style={{ padding: "24px" }}>
            <ErrorState
              message="Couldn't load generation figures."
              onRetry={() => {
                refetchCurrent();
                refetchSummary();
              }}
            />
          </div>
        ) : (
          <GenerationBar
            generation={current?.dashboard_total_mw}
            peak={figures?.record_peak_generation_mw?.value}
            ceiling={current?.demand_ceiling_mwh_per_h}
            asAt={current?.observed_hour}
            loading={currentLoading || summaryLoading}
          />
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 47%)",
            justifyContent: "space-between",
            rowGap: 20,
          }}
        >
          <StatCard
            label="Installed capacity"
            value={num(infra?.totals?.total_installed_mw)}
            unit="MW"
            loading={infraLoading}
            error={infraError}
          />
          <StatCard
            label="Available capacity"
            value={num(figures?.available_capacity_mw?.value)}
            unit="MW"
            sub={figures?.available_capacity_mw ? `as at ${figures.available_capacity_mw.as_of}` : undefined}
            loading={summaryLoading}
            error={summaryError}
          />
          <StatCard
            label="Wheeling capacity"
            value={num(figures?.wheeling_capacity_mw?.value)}
            unit="MW"
            sub={figures?.wheeling_capacity_mw ? `as at ${figures.wheeling_capacity_mw.as_of}` : undefined}
            loading={summaryLoading}
            error={summaryError}
          />
          <StatCard
            label="Live gap"
            value={num(current?.live_gap_mwh_per_h)}
            unit="MW"
            sub="vs modelled ceiling"
            highlight
            loading={currentLoading}
            error={currentError}
          />
          <StatCard
            label="Delivered to DISCOs"
            value={num(allocationTotal)}
            unit="MW"
            sub={allocationAsAt ? `as at ${String(allocationAsAt).slice(0, 16)}` : undefined}
            loading={allocationLoading}
            error={allocationError}
          />
          <StatCard
            label="Delivered per person"
            value={perPerson == null ? "—" : num(perPerson, 1)}
            unit="W"
            loading={allocationLoading || summaryLoading}
            error={allocationError || summaryError}
          />
        </div>
      </div>
    </div>
  );
}