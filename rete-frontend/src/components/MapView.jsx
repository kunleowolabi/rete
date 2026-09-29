import * as maplibregl from "maplibre-gl";
import MaplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");

import { useState, useMemo, useRef, useEffect } from "react";
import { Map, Source, Layer, Marker, Popup } from "react-map-gl/maplibre";
import MarkerPoint from "./MarkerPoint";

const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/dark";

const NIGERIA_BOUNDS = {
  longitude: 8.6753,
  latitude: 9.082,
  zoom: 5.2,
};

const DISCO_FILL = "#8c8c8c";
const STATE_LINE = "#5a5a5a"; // default grey — internal state boundaries only
const NIGERIA_OUTLINE = "#ffcc4d"; // yellow — national outline only
const DISCO_LINE = "#c8c8c8";

const PLANT_COLOR = "#ffffff";
const LINE_YELLOW = "#ffcc4d";
const MINIGRID_COLOR = "#0d5c8f";

const FUEL_LABELS = {
  gas: "Gas",
  hydro: "Hydro",
  steam: "Steam",
  gas_steam: "Gas/Steam",
  solar: "Solar",
};

export default function MapView({
  discoBoundaries,
  stateBoundaries,
  countryBoundary,
  plants,
  substations,
  lines,
  minigrids,
  onDiscoClick,
  layers = {
    discoBoundaries: true,
    stateBoundaries: false,
    plants: false,
    substations: false,
    lines: false,
    minigrids: false,
  },
}) {
  const mapRef = useRef(null);
  const [hoveredDisco, setHoveredDisco] = useState(null);
  const [selectedPlant, setSelectedPlant] = useState(null);
  const [selectedMinigrid, setSelectedMinigrid] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => mapRef.current?.resize(), 100);
    return () => clearTimeout(timer);
  }, []);

  const substationsGeoJSON = useMemo(() => toFeatureCollection(substations), [substations]);
  const linesGeoJSON = useMemo(() => toFeatureCollection(lines), [lines]);

  const plantPoints = useMemo(() => extractPoints(plants, "osm_id"), [plants]);
  const minigridPoints = useMemo(() => extractPoints(minigrids, "minigrid_id"), [minigrids]);

  const handleDiscoClick = (event) => {
    const feature = event.features?.[0];
    if (feature?.layer?.id === "disco-fill" && onDiscoClick) {
      onDiscoClick(feature.properties.disco_id);
    }
  };

  return (
    <Map
      ref={mapRef}
      initialViewState={NIGERIA_BOUNDS}
      mapStyle={BASEMAP_STYLE}
      style={{ width: "100%", height: "100%" }}
      interactiveLayerIds={["disco-fill"]}
      onClick={handleDiscoClick}
      onMouseMove={(e) => {
        const feature = e.features?.[0];
        setHoveredDisco(feature?.layer?.id === "disco-fill" ? feature.properties.disco_id : null);
      }}
    >
      {/* Internal state boundaries — grey */}
      {stateBoundaries && (
        <Source id="states" type="geojson" data={stateBoundaries}>
          <Layer
            id="state-outline"
            source="states"
            type="line"
            paint={{ "line-color": STATE_LINE, "line-width": 0.6 }}
          />
        </Source>
      )}

      {/* National outline — yellow, drawn from the dissolved country polygon
          so it only traces Nigeria's outer edge, not every state border */}
      {countryBoundary && (
        <Source id="country" type="geojson" data={countryBoundary}>
          <Layer
            id="country-outline"
            source="country"
            type="line"
            paint={{ "line-color": NIGERIA_OUTLINE, "line-width": 0.6 }}
          />
        </Source>
      )}

      {layers.discoBoundaries && discoBoundaries && (
        <Source id="discos" type="geojson" data={discoBoundaries}>
          <Layer
            id="disco-fill"
            source="discos"
            type="fill"
            paint={{
              "fill-color": DISCO_FILL,
              "fill-opacity": ["case", ["==", ["get", "disco_id"], hoveredDisco || ""], 0.55, 0.35],
            }}
          />
          <Layer
            id="disco-outline"
            source="discos"
            type="line"
            paint={{ "line-color": DISCO_LINE, "line-width": 1.4 }}
          />
        </Source>
      )}

      {layers.lines && linesGeoJSON && (
        <Source id="lines-hv" type="geojson" data={linesGeoJSON}>
          <Layer
            id="line-hv"
            source="lines-hv"
            type="line"
            filter={["in", ["get", "voltage_tier"], ["literal", ["330kV", "132kV"]]]}
            paint={{ "line-color": LINE_YELLOW, "line-width": 1.4 }}
          />
        </Source>
      )}

      {layers.lines && linesGeoJSON && (
        <Source id="lines-mv" type="geojson" data={linesGeoJSON}>
          <Layer
            id="line-mv"
            source="lines-mv"
            type="line"
            filter={["in", ["get", "voltage_tier"], ["literal", ["33kV", "11kV", "unknown"]]]}
            paint={{ "line-color": LINE_YELLOW, "line-width": 1.4, "line-dasharray": [3, 2.5] }}
          />
        </Source>
      )}

      {layers.substations && substationsGeoJSON && (
        <Source id="substations" type="geojson" data={substationsGeoJSON}>
          <Layer
            id="substation-points"
            source="substations"
            type="circle"
            paint={{
              "circle-radius": 3,
              "circle-color": "#ffffff",
              "circle-stroke-width": 1,
              "circle-stroke-color": "#4a4a4a",
            }}
          />
        </Source>
      )}

      {layers.plants &&
        plantPoints.map((p) => (
          <Marker key={p.id} longitude={p.lng} latitude={p.lat} anchor="center">
            <MarkerPoint
              color={PLANT_COLOR}
              pulse
              label={FUEL_LABELS[p.fuel_source] || p.fuel_source}
              sublabel={p.name}
              isSelected={selectedPlant === p.id}
              onSelect={() => setSelectedPlant(selectedPlant === p.id ? null : p.id)}
            />
          </Marker>
        ))}

      {layers.minigrids &&
        minigridPoints.map((m) => (
          <Marker key={m.id} longitude={m.lng} latitude={m.lat} anchor="center">
            <MarkerPoint
              color={MINIGRID_COLOR}
              label={m.power_system}
              sublabel={m.community}
              isSelected={selectedMinigrid === m.id}
              onSelect={() => setSelectedMinigrid(selectedMinigrid === m.id ? null : m.id)}
            />
          </Marker>
        ))}

      {selectedPlant &&
        (() => {
          const p = plantPoints.find((pt) => pt.id === selectedPlant);
          if (!p) return null;
          return (
            <Popup
              longitude={p.lng}
              latitude={p.lat}
              anchor="bottom"
              onClose={() => setSelectedPlant(null)}
              closeButton={false}
              offset={16}
            >
              <div style={{ fontSize: 13, minWidth: 140, padding: "4px 2px", fontFamily: "Raleway, sans-serif" }}>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>{p.name}</div>
                <div style={{ color: "#888", fontSize: 11 }}>{FUEL_LABELS[p.fuel_source] || p.fuel_source}</div>
                {p.installed_mw && (
                  <div style={{ fontWeight: 700, fontSize: 15, marginTop: 6 }}>{p.installed_mw} MW</div>
                )}
              </div>
            </Popup>
          );
        })()}

      {selectedMinigrid &&
        (() => {
          const m = minigridPoints.find((pt) => pt.id === selectedMinigrid);
          if (!m) return null;
          return (
            <Popup
              longitude={m.lng}
              latitude={m.lat}
              anchor="bottom"
              onClose={() => setSelectedMinigrid(null)}
              closeButton={false}
              offset={16}
            >
              <div style={{ fontSize: 13, minWidth: 140, padding: "4px 2px", fontFamily: "Raleway, sans-serif" }}>
                <div style={{ fontWeight: 700, marginBottom: 2 }}>{m.community}</div>
                <div style={{ color: "#888", fontSize: 11 }}>
                  {m.power_system} · {m.condition}
                </div>
                {m.capacity_kw && (
                  <div style={{ fontWeight: 700, fontSize: 15, marginTop: 6 }}>{m.capacity_kw} kW</div>
                )}
              </div>
            </Popup>
          );
        })()}
    </Map>
  );
}

function extractPoints(items, idField) {
  if (!items) return [];
  return items
    .map((item, i) => {
      const geom = typeof item.geometry === "string" ? JSON.parse(item.geometry) : item.geometry;
      if (!geom?.coordinates) return null;
      const [lng, lat] = geom.coordinates;
      return { id: item[idField] ?? i, lng, lat, ...item };
    })
    .filter(Boolean);
}

function toFeatureCollection(items, transform = (x) => x) {
  if (!items) return null;
  return {
    type: "FeatureCollection",
    features: items.map((item) => {
      const { geometry, ...properties } = transform(item);
      return {
        type: "Feature",
        properties,
        geometry: typeof geometry === "string" ? JSON.parse(geometry) : geometry,
      };
    }),
  };
}