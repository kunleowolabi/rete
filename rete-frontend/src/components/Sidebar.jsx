import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Overview" },
  { path: "/live", label: "Live" },
  { path: "/infrastructure", label: "Infrastructure" },
  { path: "/trend", label: "Trend" },
  { path: "/offgrid", label: "Mini-Grids" },
  { path: "/data", label: "Data" },
];

export default function Sidebar({ onNavigate, width }) {
  return (
    <nav
      className="bg-black/85 border border-white/15 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.7)] flex flex-col overflow-hidden"
      style={{ width }}
    >
      <div className="flex flex-col gap-2 px-4 py-5">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            onClick={onNavigate}
            style={{ display: "block", padding: "14px 18px" }}
            className={({ isActive }) =>
              `text-sm transition-colors ${
                isActive
                  ? "bg-white/5 text-white font-bold"
                  : "text-white/60 font-semibold hover:bg-white/5 hover:text-white"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}