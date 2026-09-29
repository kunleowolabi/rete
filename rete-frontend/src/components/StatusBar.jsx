import { useState, useEffect } from "react";

export default function StatusBar() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const dateStr = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  const timeStr = now.toLocaleTimeString("en-GB", { hour12: false });

  return (
    <div
      className="w-full bg-black/85 border-b border-white/15 shadow-lg flex items-center justify-between"
      style={{ height: 70, paddingLeft: 20, paddingRight: 40 }}
    >
      <img src="/Four.svg" alt="Rete" className="h-[23px] w-auto" />
      <div className="text-sm text-white/50 whitespace-nowrap">
        {dateStr} · <span className="font-mono">{timeStr}</span>
      </div>
    </div>
  );
}