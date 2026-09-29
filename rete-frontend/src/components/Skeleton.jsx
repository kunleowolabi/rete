export default function Skeleton({ width = "100%", height = 14, radius = 4, style = {} }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: radius,
        background:
          "linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.14) 37%, rgba(255,255,255,0.06) 63%)",
        backgroundSize: "400% 100%",
        animation: "skeleton-sweep 1.6s ease-in-out infinite",
        ...style,
      }}
    />
  );
}