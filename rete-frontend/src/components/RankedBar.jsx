export default function RankedBar({ label, value, max, color = "var(--color-line)" }) {
  const v = Number(value);
  const pct = max > 0 ? Math.min((v / max) * 100, 100) : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="flex justify-between text-xs" style={{ marginBottom: 4 }}>
        <span className="text-white/70">{label}</span>
        <span className="text-white font-semibold">{Number.isFinite(v) ? v.toFixed(1) : "—"}%</span>
      </div>
      <div style={{ height: 8, background: "rgba(255,255,255,0.1)", borderRadius: 2 }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
}