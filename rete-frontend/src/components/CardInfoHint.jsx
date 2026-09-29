import { useState } from "react";

export default function CardInfoHint({ text }) {
  const [open, setOpen] = useState(false);

  return (
    <span style={{ position: "relative", display: "inline-flex" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        title="More about this figure"
        className={open ? "text-[var(--color-line)]" : "text-white/40 hover:text-white/70"}
        style={{ background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex" }}
      >
        <svg width="13" height="13" viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7.5" stroke="currentColor" strokeWidth="1.5" />
          <line x1="9" y1="8" x2="9" y2="12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="9" cy="5.4" r="0.9" fill="currentColor" />
        </svg>
      </button>

      {open && (
        <>
          {/* Click-away catcher */}
          <div
            onClick={() => setOpen(false)}
            style={{ position: "fixed", inset: 0, zIndex: 40 }}
          />
          <div
            className="bg-black border border-white/15 rounded-lg shadow-2xl"
            style={{
              position: "absolute",
              top: "150%",
              left: 0,
              width: 260,
              padding: "12px 14px",
              zIndex: 41,
            }}
          >
            <p className="text-xs text-white/70" style={{ lineHeight: 1.6 }}>{text}</p>
          </div>
        </>
      )}
    </span>
  );
}