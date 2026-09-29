export default function PulseDot({ color = "var(--color-line)" }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
        animation: "pulse-ring 1.6s ease-out infinite",
        boxShadow: `0 0 0 0 ${color}`,
      }}
    />
  );
}