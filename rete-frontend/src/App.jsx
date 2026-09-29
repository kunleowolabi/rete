import { useState, useEffect } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import StatusBar from "./components/StatusBar";
import Sidebar from "./components/Sidebar";
import MapView from "./components/MapView";
import DiscoDetailCard from "./components/DiscoDetailCard";
import InfoCard from "./components/InfoCard";
import MapLayerControls from "./components/MapLayerControls";
import { useSharedMapConfig, useSelectedDisco, useMapLayers } from "./context/MapContext";
import { getStateBoundaries, getCountryBoundary } from "./api/client";
import { OVERVIEW_INFO } from "./content/pageInfo";
import Overview from "./pages/Overview";
import Live from "./pages/Live";
import Infrastructure from "./pages/Infrastructure";
import Trend from "./pages/Trend";
import Offgrid from "./pages/Offgrid";
import DataPage from "./pages/DataPage";

const GAP = 20;
const STATUS_BAR_HEIGHT = 70;
const STATUS_BAR_GAP = 10;
const SIDEBAR_WIDTH = 154;
const BOTTOM_OFFSET = 50;

const CONTENT_TOP = STATUS_BAR_HEIGHT + STATUS_BAR_GAP;

const PAGE_INFO = { "/": OVERVIEW_INFO };

export default function App() {
  const location = useLocation();
  const mapConfig = useSharedMapConfig();
  const [selectedDiscoId, setSelectedDiscoId] = useSelectedDisco();
  const [activeLayers, setActiveLayers] = useMapLayers();
  const [dashboardHidden, setDashboardHidden] = useState(false);
  const [infoOpen, setInfoOpen] = useState(false);
  const pageInfo = PAGE_INFO[location.pathname];

  const { data: stateBoundaries } = useQuery({
    queryKey: ["state-boundaries"],
    queryFn: getStateBoundaries,
  });

  const { data: countryBoundary } = useQuery({
    queryKey: ["country-boundary"],
    queryFn: getCountryBoundary,
  });

  useEffect(() => {
    setInfoOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (selectedDiscoId) setInfoOpen(false);
  }, [selectedDiscoId]);

  const toggleInfo = () => {
    setSelectedDiscoId(null);
    setInfoOpen((open) => !open);
  };

  const dashboardLeft = GAP + SIDEBAR_WIDTH + GAP;
  const cardLeft = dashboardHidden
    ? dashboardLeft
    : `calc(${dashboardLeft}px + 40% + ${GAP}px)`;
  const hideDashboard = () => setDashboardHidden(true);

  return (
    <div className="relative h-screen w-screen bg-[var(--color-bg-page)] overflow-hidden">
      <div className="absolute top-0 left-0 right-0 z-30">
        <StatusBar />
      </div>

      <div className="absolute inset-0" style={{ top: STATUS_BAR_HEIGHT }}>
        <MapView
          {...mapConfig}
          stateBoundaries={stateBoundaries}
          countryBoundary={countryBoundary}
          layers={activeLayers}
          onDiscoClick={setSelectedDiscoId}
        />
      </div>

      <div className="absolute z-20" style={{ top: CONTENT_TOP, left: GAP }}>
        <Sidebar width={SIDEBAR_WIDTH} onNavigate={() => setDashboardHidden(false)} />
      </div>

      {!dashboardHidden && (
        <div
          className="content-scale absolute bg-black/85 border border-white/15 shadow-xl overflow-auto z-10 text-white"
          style={{
            top: CONTENT_TOP,
            bottom: BOTTOM_OFFSET,
            left: dashboardLeft,
            width: "40%",
          }}
        >
          <Routes>
            <Route
              path="/"
              element={<Overview onCollapse={hideDashboard} onInfo={toggleInfo} infoActive={infoOpen} />}
            />
            <Route path="/live" element={<Live onCollapse={hideDashboard} />} />
            <Route path="/infrastructure" element={<Infrastructure onCollapse={hideDashboard} />} />
            <Route path="/trend" element={<Trend onCollapse={hideDashboard} />} />
            <Route path="/offgrid" element={<Offgrid onCollapse={hideDashboard} />} />
            <Route path="/data" element={<DataPage onCollapse={hideDashboard} />} />
          </Routes>
        </div>
      )}

      {dashboardHidden && (
        <button
          onClick={() => setDashboardHidden(false)}
          className="absolute bg-black/85 border border-white/15 shadow-xl text-white/70 hover:text-white z-10 px-3 py-2 text-sm"
          style={{ top: CONTENT_TOP, left: dashboardLeft }}
        >
          + Show panel
        </button>
      )}

      <MapLayerControls activeLayers={activeLayers} onToggle={setActiveLayers} topOffset={CONTENT_TOP} />

      {infoOpen && pageInfo && (
        <InfoCard
          title={pageInfo.title}
          items={pageInfo.items}
          onClose={() => setInfoOpen(false)}
          topOffset={CONTENT_TOP}
          leftOffset={cardLeft}
        />
      )}

      {selectedDiscoId && (
        <DiscoDetailCard
          discoId={selectedDiscoId}
          onClose={() => setSelectedDiscoId(null)}
          topOffset={CONTENT_TOP}
          leftOffset={cardLeft}
        />
      )}
    </div>
  );
}