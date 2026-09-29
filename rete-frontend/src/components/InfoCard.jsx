export default function InfoCard({ title, items, onClose, topOffset = 16, leftOffset }) {
  return (
    <div
      className="content-scale absolute w-96 bg-black/85 border border-white/15 rounded-xl shadow-2xl overflow-hidden z-30 text-white"
      style={{ top: topOffset, left: leftOffset }}
    >
      <div
        className="flex items-start justify-between border-b border-white/15"
        style={{ padding: "20px 22px" }}
      >
        <div>
          <p className="text-xs text-white/50">About these figures</p>
          <p className="text-sm font-semibold text-white" style={{ marginTop: 4 }}>
            {title}
          </p>
        </div>
        <button
          onClick={onClose}
          title="Hide"
          className="text-white/60 hover:text-white"
          style={{ background: "none", border: "none", cursor: "pointer", padding: 4, marginTop: 2 }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="3" />
          </svg>
        </button>
      </div>

      <div style={{ padding: "6px 22px 10px 22px", maxHeight: 460, overflow: "auto" }}>
        {items.map((item) => (
          <div
            key={item.figure}
            className="border-b border-white/10 last:border-0"
            style={{ padding: "14px 0" }}
          >
            <p className="text-sm font-semibold text-white">{item.figure}</p>
            <p className="text-xs text-white/60" style={{ marginTop: 4, lineHeight: 1.6 }}>
              {item.note}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}