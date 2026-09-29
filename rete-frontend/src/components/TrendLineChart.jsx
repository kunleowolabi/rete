import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
} from "chart.js";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip);

export default function TrendLineChart({ labels, series, loading, height = 220 }) {
  if (loading) return <p className="text-sm text-white/40">Loading…</p>;
  if (!labels?.length) return <p className="text-xs text-white/40 italic">No data available.</p>;

  return (
    <div style={{ height }}>
      <Line
        data={{
          labels,
          datasets: series.map((s) => ({
            label: s.label,
            data: s.data,
            borderColor: s.color,
            backgroundColor: s.color,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            spanGaps: true,
          })),
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          scales: {
            x: { ticks: { color: "#8c8c8c", maxTicksLimit: 8 }, grid: { color: "rgba(255,255,255,0.06)" } },
            y: { ticks: { color: "#8c8c8c" }, grid: { color: "rgba(255,255,255,0.06)" } },
          },
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: "#0a0a0a", titleColor: "#fff", bodyColor: "#fff" },
          },
        }}
      />
    </div>
  );
}