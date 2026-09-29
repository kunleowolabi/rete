const BASE_URL = "https://d22cq6dlw6uxlc.cloudfront.net/";

async function fetchJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed: ${res.status}`);
  }
  return res.json();
}

// --- Overview ---
export const getSummary = () => fetchJSON("summary");
export const getGenerationCurrent = () => fetchJSON("generation/current");
export const getGenerationHistory = (range = "24h") =>
  fetchJSON(`generation/history?range=${range}`);

// --- DISCOs ---
export const getDiscos = () => fetchJSON("discos");
export const getDiscoLiveAllocation = () => fetchJSON("discos/live-allocation");
export const getDiscoDetail = (discoId) => fetchJSON(`discos/${discoId}`);
export const getDiscoTimeseries = (discoId) => fetchJSON(`discos/${discoId}/timeseries`);
export const getDiscoLoadHistory = (discoId, range = "24h") =>
  fetchJSON(`discos/${discoId}/load-history?range=${range}`);
export const getDiscoNercTrends = (discoId) => fetchJSON(`discos/${discoId}/nerc-trends`);

// --- Infrastructure ---
export const getInfrastructureSummary = () => fetchJSON("infrastructure/summary");
export const getPlants = () => fetchJSON("plants");
export const getSubstations = () => fetchJSON("substations");
export const getLines = () => fetchJSON("lines");
export const getMinigrids = () => fetchJSON("minigrids");

// --- Boundaries ---
export const getDiscoBoundaries = () => fetchJSON("boundaries/discos");
export const getStateBoundaries = () => fetchJSON("boundaries/states");
export const getCountryBoundary = () => fetchJSON("boundaries/country");

// --- Live Data ---
export const getDiscoAllocationHistory = (range = "24h") =>
  fetchJSON(`discos/allocation-history?range=${range}`);
export const getGencoCurrent = () => fetchJSON("genco/current");
export const getDiscosRanked = () => fetchJSON("discos/ranked");
export const getGencoUtilization = () => fetchJSON("genco/utilization");