export default function PageHeader({ title, subtitle, badge, onCollapse, onInfo, infoActive = false }) {
  return (
    <div
      className="flex items-start justify-between"
      style={{ padding: "28px 28px 0 28px" }}
    >
      <div>
        <div className="flex items-center" style={{ gap: 12 }}>
          <h1 className="text-white font-bold" style={{ fontSize: "20.4px", lineHeight: 1.3 }}>
            {title}
          </h1>

          {onInfo && (
            <button
              onClick={onInfo}
              title="About these figures"
              className={infoActive ? "text-[var(--color-line)]" : "text-white/50 hover:text-white"}
              style={{ background: "none", border: "none", cursor: "pointer", padding: 2, display: "flex" }}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="9" cy="9" r="7.5" stroke="currentColor" strokeWidth="1.5" />
                <line x1="9" y1="8" x2="9" y2="12.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <circle cx="9" cy="5.4" r="0.9" fill="currentColor" />
              </svg>
            </button>
          )}

          {badge}
        </div>
        {subtitle && (
          <p className="text-xs text-white/40" style={{ marginTop: 6 }}>
            {subtitle}
          </p>
        )}
      </div>

      {onCollapse && (
        <button
          onClick={onCollapse}
          title="Hide panel"
          className="text-white/60 hover:text-white"
          style={{ background: "none", border: "none", cursor: "pointer", padding: 4, marginTop: 2 }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="3" />
          </svg>
        </button>
      )}
    </div>
  );
}