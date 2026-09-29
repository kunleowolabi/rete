import Skeleton from "./Skeleton";

export default function StatCard({ label, value, unit, sub, trend, highlight = false, loading = false, error = false }) {
  return (
    <div
      className="bg-black/85 border border-white/15 rounded-lg flex flex-col justify-between"
      style={{ padding: "22px 20px", minHeight: 130 }}
    >
      {error ? (
        <>
          <p className="text-xs font-semibold text-white/50 capitalize">{label}</p>
          <p className="text-sm text-[var(--color-line)]" style={{ marginTop: 16 }}>
            Couldn't load
          </p>
        </>
      ) : loading ? (
        <>
          <Skeleton width="60%" height={12} />
          <div style={{ marginTop: 16 }}>
            <Skeleton width="45%" height={26} />
          </div>
        </>
      ) : (
        <>
          <p className="text-xs font-semibold text-white/50 capitalize">{label}</p>
          <div style={{ marginTop: 16 }}>
            <div className="flex items-baseline" style={{ gap: 6 }}>
              <span className={`text-stat-value ${highlight ? "text-[var(--color-line)]" : "text-white"}`}>
                {value}
              </span>
              {unit && <span className="text-xs text-white/40 font-medium">{unit}</span>}
              {trend != null && <TrendIndicator value={trend} />}
            </div>
            {sub && <p className="text-xs text-white/40" style={{ marginTop: 4 }}>{sub}</p>}
          </div>
        </>
      )}
    </div>
  );
}

function TrendIndicator({ value }) {
  const isUp = value > 0;
  const isFlat = value === 0;
  return (
    <span
      className={`text-xs font-semibold flex items-center gap-0.5 ml-1 ${
        isFlat ? "text-white/40" : isUp ? "text-[var(--color-status-ok)]" : "text-[var(--color-status-bad)]"
      }`}
    >
      {!isFlat && (isUp ? "▲" : "▼")} {Math.abs(value).toFixed(1)}%
    </span>
  );
}