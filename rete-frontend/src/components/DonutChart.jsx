import { useMemo } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip } from "chart.js";

ChartJS.register(ArcElement, Tooltip);

const FUEL_COLORS = {
  gas: "#ffcc4d",
  hydro: "#1d9bf0",
  steam: "#8c8c8c",
  gas_steam: "#0d5c8f",
  solar: "#e2564f",
};

export default function DonutChart({ fuelMix, loading }) {
  const { labels, data, colors, total } = useMemo(() => {
    const rows = fuelMix || [];
    const total = rows.reduce((s, r) => s + Number(r.installed_mw || 0), 0);
    return {
      labels: rows.map((r) => r.fuel_type),
      data: rows.map((r) => Number(r.installed_mw)),
      colors: rows.map((r) => FUEL_COLORS[r.fuel_type] || "#6b7280"),
      total,
    };
  }, [fuelMix]);

  if (loading) return <p className="text-sm text-white/40">Loading…</p>;
  if (!data.length) return <p className="text-xs text-white/40 italic">No data available.</p>;

  return (
    <div className="flex items-center" style={{ gap: 24 }}>
      <div style={{ width: 140, height: 140, position: "relative", flexShrink: 0 }}>
        <Doughnut
          data={{
            labels,
            datasets: [{ data, backgroundColor: colors, borderWidth: 0 }],
          }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            cutout: "68%",
            plugins: {
              legend: { display: false },
              tooltip: { backgroundColor: "#0a0a0a", titleColor: "#fff", bodyColor: "#fff" },
            },
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span className="text-sm font-semibold text-white">{Math.round(total).toLocaleString()}</span>
          <span className="text-xs text-white/40">MW</span>
        </div>
      </div>

      <div style={{ flex: 1 }}>
        {(fuelMix || []).map((f, i) => (
          <div key={f.fuel_type} className="flex items-center justify-between" style={{ padding: "5px 0" }}>
            <div className="flex items-center" style={{ gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: colors[i] }} />
              <span className="text-xs text-white/70 capitalize">{f.fuel_type.replace("_", "/")}</span>
            </div>
            <span className="text-xs text-white font-semibold">
              {Math.round((Number(f.installed_mw) / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}