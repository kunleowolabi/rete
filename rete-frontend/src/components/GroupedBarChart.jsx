import { Bar } from "react-chartjs-2";
import { Chart as ChartJS, BarElement, LinearScale, CategoryScale, Tooltip } from "chart.js";

ChartJS.register(BarElement, LinearScale, CategoryScale, Tooltip);

export default function GroupedBarChart({ labels, series, loading, height = 220 }) {
  if (loading) return <p className="text-sm text-white/40">Loading…</p>;
  if (!labels?.length) return <p className="text-xs text-white/40 italic">No data available.</p>;

  return (
    <div style={{ height }}>
      <Bar
        data={{
          labels,
          datasets: series.map((s) => ({
            label: s.label,
            data: s.data,
            backgroundColor: s.color,
            borderRadius: 2,
            barPercentage: 0.8,
            categoryPercentage: 0.8,
          })),
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { ticks: { color: "#8c8c8c", maxTicksLimit: 12, font: { size: 13 } }, grid: { display: false } },
            y: { ticks: { color: "#8c8c8c", font: { size: 13 } }, grid: { color: "rgba(255,255,255,0.06)" } },
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#0a0a0a",
              titleColor: "#fff",
              bodyColor: "#fff",
              titleFont: { size: 13 },
              bodyFont: { size: 13 },
            },
          },
        }}
      />
    </div>
  );
}