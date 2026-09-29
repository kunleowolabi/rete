import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMapConfig } from "../context/MapContext";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import Skeleton from "../components/Skeleton";
import ErrorState from "../components/ErrorState";
import { getMinigrids, getDiscoBoundaries, getPlants, getSubstations, getLines } from "../api/client";

const STATUS_LABEL = {
  Operational: "Active",
  "Non Operational": "Inactive",
};

export default function Offgrid({ onCollapse }) {
  const {
    data: minigrids,
    isLoading,
    isError,
    refetch,
  } = useQuery({ queryKey: ["minigrids"], queryFn: getMinigrids });

  const { data: discoBoundaries } = useQuery({ queryKey: ["disco-boundaries"], queryFn: getDiscoBoundaries });
  const { data: plants } = useQuery({ queryKey: ["plants"], queryFn: getPlants });
  const { data: substations } = useQuery({ queryKey: ["substations"], queryFn: getSubstations });
  const { data: lines } = useQuery({ queryKey: ["lines"], queryFn: getLines });

  useMapConfig(
    { minigrids, discoBoundaries, plants, substations, lines },
    { minigrids: true }
  );

  const totalCapacity = useMemo(
    () => minigrids?.reduce((sum, m) => sum + (Number(m.capacity_kw) || 0), 0),
    [minigrids]
  );
  const activeCount = minigrids?.filter((m) => m.condition === "Operational").length;

  return (
    <div>
      <PageHeader title="Mini-Grids" subtitle="Small-scale and off-grid generation sites" onCollapse={onCollapse} />

      <div style={{ padding: "24px 28px 28px 28px", display: "flex", flexDirection: "column", gap: 20 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 47%)",
            justifyContent: "space-between",
            rowGap: 20,
          }}
        >
          <StatCard label="Total sites" value={minigrids?.length ?? "—"} loading={isLoading} error={isError} />
          <StatCard label="Active" value={activeCount ?? "—"} loading={isLoading} error={isError} />
        </div>

        {!isError && (
          <p className="text-xs text-white/40">
            {minigrids?.length ?? "—"} documented sites, {((totalCapacity ?? 0) / 1000).toFixed(2)} MW total.
            This dataset was last updated in 2020 (Nigeria SE4ALL). REA separately reports 900+
            mini-grids under construction nationally as of 2025 — this page reflects the older
            site-level dataset, not the current national picture.
          </p>
        )}

        <Card title="Sites">
          {isError ? (
            <ErrorState message="Couldn't load mini-grid sites." onRetry={refetch} />
          ) : isLoading ? (
            <TableSkeleton rows={8} />
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10 text-white/40">
                  <th className="text-left font-medium" style={{ padding: "6px 8px 6px 0" }}>Community</th>
                  <th className="text-left font-medium" style={{ padding: "6px 8px" }}>System</th>
                  <th className="text-left font-medium" style={{ padding: "6px 8px" }}>kW</th>
                  <th className="text-left font-medium" style={{ padding: "6px 0 6px 8px" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {minigrids?.map((m) => {
                  const status = STATUS_LABEL[m.condition] ?? m.condition ?? "—";
                  const isActive = status === "Active";
                  return (
                    <tr key={m.minigrid_id} className="border-b border-white/5 last:border-0">
                      <td className="text-white" style={{ padding: "8px 8px 8px 0" }}>{m.community}</td>
                      <td className="text-white/70" style={{ padding: "8px" }}>{m.power_system}</td>
                      <td className="text-white/70" style={{ padding: "8px" }}>{m.capacity_kw ?? "—"}</td>
                      <td className={isActive ? "text-white" : "text-white/40"} style={{ padding: "8px 0 8px 8px" }}>
                        {status}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}

function TableSkeleton({ rows = 8 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex justify-between" style={{ padding: "8px 0" }}>
          <Skeleton width="30%" height={11} />
          <Skeleton width="20%" height={11} />
          <Skeleton width="10%" height={11} />
          <Skeleton width="15%" height={11} />
        </div>
      ))}
    </div>
  );
}