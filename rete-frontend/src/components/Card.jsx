import CardInfoHint from "./CardInfoHint";

export default function Card({ title, hint, children }) {
  return (
    <div
      className="bg-black/85 border border-white/15 rounded-lg"
      style={{ padding: "22px 24px" }}
    >
      {title && (
        <div className="flex items-center" style={{ gap: 6, marginBottom: 16 }}>
          <p className="text-section-label text-white/50">{title}</p>
          {hint && <CardInfoHint text={hint} />}
        </div>
      )}
      {children}
    </div>
  );
}