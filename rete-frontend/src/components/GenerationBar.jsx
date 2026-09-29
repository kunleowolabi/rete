import Skeleton from "./Skeleton";

const TRACK = "#5c5c5c";
const CORNER = 2;

const fmt = (n) => Number(n).toLocaleString("en-GB", { maximumFractionDigits: 0 });

export default function GenerationBar({ generation, peak, ceiling, asAt, loading }) {
  const gen = Number(generation);
  const pk = Number(peak);
  const ceil = Number(ceiling);
  const ready = !loading && [gen, pk, ceil].every((n) => Number.isFinite(n) && n > 0);
  const scaleMax = ready ? Math.max(gen, pk, ceil) : 1;
  const pct = (n) => `${(n / scaleMax) * 100}%`;

  return (
    <div
      className="bg-black/85 border border-white/15 rounded-lg"
      style={{ padding: "24px 24px 22px 24px" }}
    >
      <p className="text-xs font-semibold text-white/50">Generation against modelled demand</p>

      {loading ? (
        <>
          <div style={{ marginTop: 14 }}>
            <Skeleton width="30%" height={26} />
          </div>
          <div style={{ marginTop: 22 }}>
            <Skeleton width="100%" height={14} radius={3} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", columnGap: 16, marginTop: 24 }}>
            <Skeleton height={32} />
            <Skeleton height={32} />
            <Skeleton height={32} />
          </div>
        </>
      ) : (
        <>
          <div className="flex items-baseline" style={{ gap: 8, marginTop: 14 }}>
            <span className="text-stat-value text-white">{fmt(gen)}</span>
            <span className="text-xs text-white/40 font-medium">MW generating now</span>
          </div>

          <div style={{ position: "relative", height: 14, marginTop: 22 }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: TRACK,
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: pct(pk),
                  background: "#ffffff",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: pct(gen),
                  background: "var(--color-line)",
                }}
              />
            </div>

            <div
              style={{
                position: "absolute",
                left: pct(ceil),
                top: "50%",
                width: 18,
                height: 18,
                transform: "translate(-50%, -50%)",
                borderRadius: CORNER,
                background: TRACK,
                border: "3px solid #ffffff",
              }}
            />
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              columnGap: 16,
              marginTop: 24,
            }}
          >
            <LegendItem swatch={<Swatch background="var(--color-line)" />} label="Generating now" value={`${fmt(gen)} MW`} />
            <LegendItem swatch={<Swatch background="#ffffff" />} label="Record peak" value={`${fmt(pk)} MW`} />
            <LegendItem
              swatch={<Swatch background={TRACK} border="2px solid #ffffff" />}
              label="Modelled ceiling"
              value={`${fmt(ceil)} MW`}
            />
          </div>
        </>
      )}

      {asAt && !loading && (
        <p className="text-xs text-white/40" style={{ marginTop: 18 }}>
          As at {String(asAt).slice(0, 16)}
        </p>
      )}
    </div>
  );
}

function Swatch({ background, border }) {
  return (
    <span
      style={{
        display: "block",
        width: 12,
        height: 12,
        flexShrink: 0,
        background,
        border,
        borderRadius: CORNER,
      }}
    />
  );
}

function LegendItem({ swatch, label, value }) {
  return (
    <div>
      <div className="flex items-center" style={{ gap: 8 }}>
        {swatch}
        <span className="text-xs text-white/50">{label}</span>
      </div>
      <p className="text-sm font-semibold text-white" style={{ marginTop: 4 }}>
        {value}
      </p>
    </div>
  );
}