import { useState } from "react";

const DOT = 8;
const RING = 22;

export default function MarkerPoint({
  label,
  sublabel,
  color = "#0a0a0a",
  isSelected = false,
  onSelect,
  pulse = false,
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: "relative", width: DOT, height: DOT, cursor: onSelect ? "pointer" : "default" }}
    >
      {pulse && (
        <div
          style={{
            position: "absolute",
            width: RING,
            height: RING,
            borderRadius: "50%",
            background: `${color}2e`,
            top: "50%",
            left: "50%",
            animation: "pulse-ring 2.4s ease-out infinite",
            pointerEvents: "none",
          }}
        />
      )}

      <div
        style={{
          position: "relative",
          zIndex: 2,
          width: DOT,
          height: DOT,
          borderRadius: "50%",
          background: isSelected ? color : `${color}e6`,
          border: `1.5px solid ${isSelected ? color : `${color}66`}`,
          boxShadow: isSelected
            ? `0 0 0 3px ${color}26, 0 2px 6px rgba(0,0,0,0.3)`
            : "0 1px 3px rgba(0,0,0,0.25)",
          transition: "all 0.15s ease",
        }}
      />

      {hovered && !isSelected && (label || sublabel) && (
        <div
          style={{
            position: "absolute",
            bottom: "18px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(10,10,10,0.9)",
            backdropFilter: "blur(6px)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "7px",
            padding: "6px 10px",
            zIndex: 100,
            pointerEvents: "none",
            whiteSpace: "nowrap",
            fontFamily: "Raleway, sans-serif",
          }}
        >
          {label && (
            <div
              style={{
                fontSize: "9px",
                fontWeight: 600,
                color: "rgba(255,255,255,0.5)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: sublabel ? "2px" : 0,
              }}
            >
              {label}
            </div>
          )}
          {sublabel && <div style={{ fontSize: "12px", fontWeight: 700, color: "#ffffff" }}>{sublabel}</div>}
        </div>
      )}
    </div>
  );
}