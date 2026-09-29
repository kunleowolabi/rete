const VARIANT_CLASS = {
  ok: "badge-ok",
  warn: "badge-warn",
  bad: "badge-bad",
  accent: "badge-accent",
  line: "badge-line",
};

export default function Badge({ children, variant = "accent" }) {
  return <span className={`badge ${VARIANT_CLASS[variant] || VARIANT_CLASS.accent}`}>{children}</span>;
}