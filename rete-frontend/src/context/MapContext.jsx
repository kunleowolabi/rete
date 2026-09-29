import { createContext, useContext, useState, useEffect } from "react";

const MapContext = createContext(null);

const DEFAULT_CONFIG = {
  discoBoundaries: null,
  stateBoundaries: null,
  plants: null,
  substations: null,
  lines: null,
  minigrids: null,
};

const DEFAULT_LAYER_VISIBILITY = {
  discoBoundaries: true,
  stateBoundaries: false,
  plants: false,
  substations: false,
  lines: false,
  minigrids: false,
};

export function MapConfigProvider({ children }) {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [selectedDiscoId, setSelectedDiscoId] = useState(null);
  const [activeLayers, setActiveLayers] = useState(DEFAULT_LAYER_VISIBILITY);

  return (
    <MapContext.Provider
      value={{ config, setConfig, selectedDiscoId, setSelectedDiscoId, activeLayers, setActiveLayers }}
    >
      {children}
    </MapContext.Provider>
  );
}

// Pages call this with the data they have and their default layer visibility.
export function useMapConfig(config, defaultLayers) {
  const ctx = useContext(MapContext);
  if (!ctx) throw new Error("useMapConfig must be used within MapConfigProvider");
  const { setConfig, setActiveLayers } = ctx;

  useEffect(() => {
    setConfig({ ...DEFAULT_CONFIG, ...config });
    if (defaultLayers) setActiveLayers({ ...DEFAULT_LAYER_VISIBILITY, ...defaultLayers });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(config)]);
}

export function useSharedMapConfig() {
  const ctx = useContext(MapContext);
  if (!ctx) throw new Error("useSharedMapConfig must be used within MapConfigProvider");
  return ctx.config;
}

export function useSelectedDisco() {
  const ctx = useContext(MapContext);
  if (!ctx) throw new Error("useSelectedDisco must be used within MapConfigProvider");
  return [ctx.selectedDiscoId, ctx.setSelectedDiscoId];
}

export function useMapLayers() {
  const ctx = useContext(MapContext);
  if (!ctx) throw new Error("useMapLayers must be used within MapConfigProvider");
  return [ctx.activeLayers, ctx.setActiveLayers];
}