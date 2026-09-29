import { useMemo } from "react";
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

const LAGOS_TZ = "Africa/Lagos";

const hourLabel = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: LAGOS_TZ,
  });

function buildHourlyGrid(hours = 24) {
  const now = new Date();
  const end = new Date(now);
  end.setMinutes(55, 0, 0);
  if (end > now) end.setHours(end.getHours() - 1);

  const slots = [];
  for (let i = hours - 1; i >= 0; i--) {
    slots.push(new Date(end.getTime() - i * 60 * 60 * 1000));
  }
  return slots;
}

export default function LoadProfileChart({ generationPoints, allocationPoints, loading }) {
  const { labels, genData, allocData } = useMemo(() => {
    const genMap = new Map((generationPoints || []).map((p) => [p.observed_hour, Number(p.dashboard_total_mw)]));
    const allocMap = new Map((allocationPoints || []).map((p) => [p.observed_hour, Number(p.total_mw)]));

    const findNear = (map, slot) => {
      for (const [key, val] of map) {
        if (Math.abs(new Date(key.endsWith("Z") ? key : key + "Z") - slot) < 10 * 60 * 1000) return val;
      }
      return null;
    };

    const slots = buildHourlyGrid(24);
    return {
      labels: slots.map((s) => hourLabel(s.toISOString())),
      genData: slots.map((s) => findNear(genMap, s)),
      allocData: slots.map((s) => findNear(allocMap, s)),
    };
  }, [generationPoints, allocationPoints]);

  if (loading) return <p className="text-sm text-white/40">Loading…</p>;
  if (!generationPoints?.length && !allocationPoints?.length) {
    return <p className="text-xs text-white/40 italic">No data in this window yet.</p>;
  }

  return (
    <Line
      data={{
        labels,
        datasets: [
          {
            label: "Generation",
            data: genData,
            borderColor: "#ffcc4d",
            backgroundColor: "#ffcc4d",
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            spanGaps: true,
          },
          {
            label: "DISCO allocation",
            data: allocData,
            borderColor: "#ffffff",
            backgroundColor: "#ffffff",
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
            spanGaps: true,
          },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { ticks: { color: "#8c8c8c", maxTicksLimit: 8, font: { size: 13 } }, grid: { color: "rgba(255,255,255,0.06)" } },
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
  );
}