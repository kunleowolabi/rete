const TRACK = "#5c5c5c";
const fmt = (n) => Number(n).toLocaleString("en-GB", { maximumFractionDigits: 0 });

export default function DiscoLiveBar({ name, live, ceiling }) {
  const liveN = Number(live);
  const ceilN = Number(ceiling);
  const ready = Number.isFinite(liveN) && Number.isFinite(ceilN) && ceilN > 0;
  const scaleMax = ready ? Math.max(liveN, ceilN) : 1;
  const pct = (n) => `${(n / scaleMax) * 100}%`;

  return (
    <div style={{ marginBottom: 16 }}>
      <div className="flex justify-between text-xs" style={{ marginBottom: 6 }}>
        <span className="text-white/70">{name}</span>
        <span className="text-white font-semibold">
          {ready ? `${fmt(liveN)} / ${fmt(ceilN)} MW` : "—"}
        </span>
      </div>
      <div style={{ position: "relative", height: 10 }}>
        <div style={{ position: "absolute", inset: 0, background: TRACK, borderRadius: 2, overflow: "hidden" }}>
          {ready && (
            <div
              style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: pct(liveN), background: "var(--color-line)" }}
            />
          )}
        </div>
        {ready && (
          <div
            style={{
              position: "absolute",
              left: pct(ceilN),
              top: "50%",
              width: 12,
              height: 12,
              transform: "translate(-50%, -50%)",
              background: TRACK,
              border: "2px solid #ffffff",
            }}
          />
        )}
      </div>
    </div>
  );
}