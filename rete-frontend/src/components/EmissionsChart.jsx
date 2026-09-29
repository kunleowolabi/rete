import { useMemo } from "react";
import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, BarElement, LinearScale, CategoryScale, Tooltip } from "chart.js";

ChartJS.register(BarElement, LinearScale, CategoryScale, Tooltip);

const EMISSION_FACTORS = {
  gas: 0.49,
  gas_steam: 0.40,
  steam: 0.65,
  hydro: 0.024,
  solar: 0.041,
};
const DEFAULT_FACTOR = 0.5;

export default function EmissionsChart({ fuelMix, loading }) {
  const { labels, data } = useMemo(() => {
    const rows = [...(fuelMix || [])].sort(
      (a, b) =>
        Number(b.installed_mw) * (EMISSION_FACTORS[b.fuel_type] ?? DEFAULT_FACTOR) -
        Number(a.installed_mw) * (EMISSION_FACTORS[a.fuel_type] ?? DEFAULT_FACTOR)
    );
    return {
      labels: rows.map((r) => r.fuel_type.replace("_", "/")),
      data: rows.map((r) => Number(r.installed_mw) * (EMISSION_FACTORS[r.fuel_type] ?? DEFAULT_FACTOR)),
    };
  }, [fuelMix]);

  if (loading) return <p className="text-sm text-white/40">Loading…</p>;
  if (!data.length) return <p className="text-xs text-white/40 italic">No data available.</p>;

  return (
    <div>
      <div style={{ height: 140 }}>
        <Bar
          data={{
            labels,
            datasets: [{ data, backgroundColor: "#ffcc4d", borderRadius: 2, barThickness: 16 }],
          }}
          options={{
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: { ticks: { color: "#8c8c8c", font: { size: 13 } }, grid: { color: "rgba(255,255,255,0.06)" } },
              y: { ticks: { color: "#8c8c8c", font: { size: 13 } }, grid: { display: false } },
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "#0a0a0a",
                titleColor: "#fff",
                bodyColor: "#fff",
                titleFont: { size: 13 },
                bodyFont: { size: 13 },
                callbacks: { label: (ctx) => `${ctx.parsed.x.toFixed(0)} tCO2/h` },
              },
            },
          }}
        />
      </div>
      <p className="text-xs text-white/40 italic" style={{ marginTop: 8 }}>
        Estimated tCO2/h if each fuel type ran at full installed capacity, using standard published
        emission factors. Illustrative, not a measured figure.
      </p>
    </div>
  );
}