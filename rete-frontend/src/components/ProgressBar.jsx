export default function ProgressBar({ value, max, color = "var(--color-accent)", showLabel = true }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2 w-full">
      <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {showLabel && <span className="text-xs text-white/50 w-10 text-right">{pct.toFixed(0)}%</span>}
    </div>
  );
}