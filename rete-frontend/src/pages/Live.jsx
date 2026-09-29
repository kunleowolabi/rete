import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMapConfig } from "../context/MapContext";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import LoadProfileChart from "../components/LoadProfileChart";
import DiscoLiveBar from "../components/DiscoLiveBar";
import PulseDot from "../components/PulseDot";
import Skeleton from "../components/Skeleton";
import ErrorState from "../components/ErrorState";
import {
  getGenerationCurrent,
  getGenerationHistory,
  getDiscoLiveAllocation,
  getDiscoAllocationHistory,
  getDiscos,
  getGencoCurrent,
  getDiscoBoundaries,
  getPlants,
  getSubstations,
  getLines,
  getMinigrids,
} from "../api/client";

const num = (v, digits = 0) => {
  if (v == null || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits });
};

export default function Live({ onCollapse }) {
  const {
    data: current,
    isLoading: currentLoading,
    isError: currentError,
    refetch: refetchCurrent,
  } = useQuery({
    queryKey: ["generation-current"],
    queryFn: getGenerationCurrent,
    refetchInterval: 60_000,
  });

  const {
    data: genHistory,
    isLoading: genHistoryLoading,
    isError: genHistoryError,
    refetch: refetchGenHistory,
  } = useQuery({
    queryKey: ["generation-history", "24h"],
    queryFn: () => getGenerationHistory("24h"),
    refetchInterval: 60_000,
  });

  const { data: allocHistory, isError: allocHistoryError } = useQuery({
    queryKey: ["allocation-history", "24h"],
    queryFn: () => getDiscoAllocationHistory("24h"),
    refetchInterval: 60_000,
  });

  const {
    data: allocation,
    isLoading: allocationLoading,
    isError: allocationError,
    refetch: refetchAllocation,
  } = useQuery({
    queryKey: ["disco-live-allocation"],
    queryFn: getDiscoLiveAllocation,
    refetchInterval: 60_000,
  });

  const { data: discos } = useQuery({ queryKey: ["discos"], queryFn: getDiscos });

  const {
    data: gencos,
    isLoading: gencoLoading,
    isError: gencoError,
    refetch: refetchGencos,
  } = useQuery({
    queryKey: ["genco-current"],
    queryFn: getGencoCurrent,
    refetchInterval: 60_000,
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

  const { peak, low, avg } = useMemo(() => {
    const values = (genHistory?.points || []).map((p) => Number(p.dashboard_total_mw)).filter(Number.isFinite);
    if (!values.length) return {};
    return {
      peak: Math.max(...values),
      low: Math.min(...values),
      avg: values.reduce((a, b) => a + b, 0) / values.length,
    };
  }, [genHistory]);

  const ceilingByDisco = useMemo(() => {
    const map = new Map();
    (discos || []).forEach((d) => map.set(d.disco_id, d.fitted_demand_mwh_per_h));
    return map;
  }, [discos]);

  const rankedDiscos = useMemo(() => {
    return (allocation || [])
      .map((a) => ({ ...a, ceiling: ceilingByDisco.get(a.disco_id) }))
      .filter((a) => a.ceiling != null)
      .sort((a, b) => Number(b.allocation_mw) / Number(b.ceiling) - Number(a.allocation_mw) / Number(a.ceiling));
  }, [allocation, ceilingByDisco]);

  const top8 = (gencos?.gencos || []).slice(0, 8);
  const othersMw = (gencos?.gencos || []).slice(8).reduce((s, g) => s + Number(g.mw || 0), 0);
  const topMw = top8[0]?.mw || 1;

  const chartError = genHistoryError && allocHistoryError;

  return (
    <div>
      <PageHeader
        title="Live"
        badge={<PulseDot />}
        subtitle={`As at ${current?.observed_hour ?? "—"} · updates every 60 seconds`}
        onCollapse={onCollapse}
      />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 31%)",
            justifyContent: "space-between",
            rowGap: 20,
          }}
        >
          <StatCard label="24h peak" value={num(peak)} unit="MW" loading={genHistoryLoading} error={genHistoryError} />
          <StatCard label="24h low" value={num(low)} unit="MW" loading={genHistoryLoading} error={genHistoryError} />
          <StatCard label="24h average" value={num(avg)} unit="MW" loading={genHistoryLoading} error={genHistoryError} />
        </div>

        <Card title="Load profile — last 24 hours">
          {chartError ? (
            <ErrorState message="Couldn't load the load profile." onRetry={refetchGenHistory} />
          ) : (
            <>
              <div style={{ height: 220 }}>
                {!genHistory && !allocHistory ? (
                  <Skeleton width="100%" height="100%" radius={8} />
                ) : (
                  <LoadProfileChart generationPoints={genHistory?.points} allocationPoints={allocHistory?.points} />
                )}
              </div>
              <div className="flex" style={{ gap: 16, marginTop: 12 }}>
                <LegendDot color="#ffcc4d" label="Generation" />
                <LegendDot color="#ffffff" label="DISCO allocation" />
              </div>
            </>
          )}
        </Card>

        <Card title="Delivered by GenCo, now">
          {gencoError ? (
            <ErrorState message="Couldn't load GenCo output." onRetry={refetchGencos} />
          ) : gencoLoading ? (
            <RowSkeletons rows={5} />
          ) : (
            <>
              <p className="text-xs text-white/40" style={{ marginBottom: 14 }}>
                {gencos?.reporting_count ?? "—"} of {gencos?.universe_count ?? "—"} GenCos reporting
              </p>
              {top8.map((g) => (
                <div key={g.genco_id} style={{ marginBottom: 12 }}>
                  <div className="flex justify-between text-xs" style={{ marginBottom: 4 }}>
                    <span className="text-white/70">{g.name}</span>
                    <span className="text-white font-semibold">{num(g.mw)} MW</span>
                  </div>
                  <div style={{ height: 8, background: "rgba(255,255,255,0.1)", borderRadius: 2 }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${(Number(g.mw) / Number(topMw)) * 100}%`,
                        background: "var(--color-accent)",
                        borderRadius: 2,
                      }}
                    />
                  </div>
                </div>
              ))}
              {othersMw > 0 && (
                <div className="flex justify-between text-xs text-white/40" style={{ marginTop: 8 }}>
                  <span>Others</span>
                  <span>{num(othersMw)} MW</span>
                </div>
              )}
            </>
          )}
        </Card>

        <Card title="DISCO allocation vs modelled ceiling">
          {allocationError ? (
            <ErrorState message="Couldn't load DISCO allocation." onRetry={refetchAllocation} />
          ) : allocationLoading ? (
            <RowSkeletons rows={6} />
          ) : (
            rankedDiscos.map((d) => (
              <DiscoLiveBar key={d.disco_id} name={d.name} live={d.allocation_mw} ceiling={d.ceiling} />
            ))
          )}
        </Card>

        <p className="text-xs text-white/40">
          Gap is measured against a modelled demand ceiling for the connected network, not total
          national demand — see the Data page for methodology.
        </p>
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

function LegendDot({ color, label }) {
  return (
    <div className="flex items-center" style={{ gap: 6 }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      <span className="text-xs text-white/50">{label}</span>
    </div>
  );
}