export default function QuarterPager({ label, onPrev, onNext, canPrev, canNext }) {
  return (
    <div className="flex items-center justify-between" style={{ marginBottom: 10 }}>
      <button
        onClick={onPrev}
        disabled={!canPrev}
        className="text-white/60 hover:text-white disabled:opacity-20 disabled:hover:text-white/60"
        style={{ background: "none", border: "none", cursor: canPrev ? "pointer" : "default", padding: 4 }}
        title="Earlier quarters"
      >
        ←
      </button>
      <span className="text-xs text-white/40">{label}</span>
      <button
        onClick={onNext}
        disabled={!canNext}
        className="text-white/60 hover:text-white disabled:opacity-20 disabled:hover:text-white/60"
        style={{ background: "none", border: "none", cursor: canNext ? "pointer" : "default", padding: 4 }}
        title="Later quarters"
      >
        →
      </button>
    </div>
  );
}