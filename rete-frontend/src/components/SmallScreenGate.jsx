import { useEffect, useState } from "react";

// Rete's layout needs a sidebar plus a 40%-width panel beside the map,
// so below this width it breaks. Adjust if you find a better cut-off.
const SMALL_SCREEN = "(max-width: 899px)";
const SKIP_KEY = "rete:continue-on-small-screen";

function readSkip() {
  try {
    return sessionStorage.getItem(SKIP_KEY) === "1";
  } catch {
    return false;
  }
}

function writeSkip() {
  try {
    sessionStorage.setItem(SKIP_KEY, "1");
  } catch {
    // Storage blocked (private mode etc.): continuing still works for this page view.
  }
}

// Spacing uses inline styles because index.css resets margin and padding on every
// element outside a cascade layer, which overrides Tailwind's spacing utilities.
export default function SmallScreenGate({ children }) {
  const [isSmall, setIsSmall] = useState(
    () => typeof window !== "undefined" && window.matchMedia(SMALL_SCREEN).matches
  );
  const [skipped, setSkipped] = useState(readSkip);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia(SMALL_SCREEN);
    // Only ever release the gate (e.g. phone rotated to landscape on a large tablet).
    // Never re-gate a running app when a desktop window is narrowed.
    const onChange = (e) => {
      if (!e.matches) setIsSmall(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  if (!isSmall || skipped) return children;

  const continueAnyway = () => {
    writeSkip();
    setSkipped(true);
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText("https://explorerete.com");
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <main className="min-h-screen w-full bg-[var(--color-bg-page)] text-white flex flex-col justify-center"
      style={{ padding: "40px 24px" }}>
      <div className="w-full" style={{ maxWidth: 448, margin: "0 auto" }}>
        <h1 className="text-3xl font-semibold">Rete</h1>
        <p className="text-white/60" style={{ marginTop: 4 }}>State of the grid, with nuance</p>

        <img
          src="/og-image.png"
          alt="Rete's map of Nigeria's electricity grid."
          className="w-full border border-white/15"
          style={{ marginTop: 32 }}
        />

        <p className="text-lg leading-relaxed" style={{ marginTop: 32 }}>
          Rete is built for larger screens. Open it on a laptop or desktop for the full map and data.
        </p>

        <div className="flex flex-col" style={{ marginTop: 32, gap: 12 }}>
          <button
            onClick={copyLink}
            className="w-full bg-white text-black text-sm font-medium"
            style={{ padding: "12px 0" }}
          >
            {copied ? "Link copied" : "Copy link for later"}
          </button>
          <button
            onClick={continueAnyway}
            className="w-full border border-white/25 text-white/80 text-sm"
            style={{ padding: "12px 0" }}
          >
            Continue anyway
          </button>
        </div>
      </div>
    </main>
  );
}
