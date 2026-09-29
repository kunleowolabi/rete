const LAYER_OPTIONS = [
  { key: "discoBoundaries", label: "DISCO areas", color: "#8c8c8c" },
  { key: "lines", label: "HV/MV lines", color: "#ffcc4d" },
  { key: "plants", label: "Power stations", color: "#ffffff" },
  { key: "minigrids", label: "Mini-grids", color: "#0d5c8f" },
];

export default function MapLayerControls({ activeLayers, onToggle, topOffset = 16 }) {
  const toggle = (key) => onToggle((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <>
      <div className="absolute right-4 flex z-10" style={{ top: topOffset, gap: 10 }}>
        {LAYER_OPTIONS.map((opt) => {
          const isActive = activeLayers[opt.key];
          return (
            <button
              key={opt.key}
              onClick={() => toggle(opt.key)}
              className={`bg-black/85 text-white text-xs font-semibold rounded-lg shadow-lg transition-colors border ${
                isActive
                  ? "border-[var(--color-line)]"
                  : "border-white/15 hover:border-white/40"
              }`}
              style={{ padding: "12px 18px", cursor: "pointer" }}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      <div
        className="absolute bottom-4 right-4 bg-black/85 border border-white/15 rounded-xl shadow-lg text-xs z-10"
        style={{ padding: "16px 20px" }}
      >
        <p className="text-section-label text-white/50" style={{ marginBottom: 10 }}>
          Legend
        </p>
        {LAYER_OPTIONS.filter((opt) => activeLayers[opt.key]).map((opt) => (
          <div key={opt.key} className="flex items-center" style={{ gap: 10, padding: "4px 0" }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: opt.color }} />
            <span className="text-white/70">{opt.label}</span>
          </div>
        ))}
        {!Object.values(activeLayers).some(Boolean) && (
          <p className="text-white/40 italic">No layers active</p>
        )}
      </div>
    </>
  );
}