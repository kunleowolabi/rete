import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import SmallScreenGate from "./components/SmallScreenGate";
import { MapConfigProvider } from "./context/MapContext";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false } },
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <SmallScreenGate>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <MapConfigProvider>
            <App />
          </MapConfigProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </SmallScreenGate>
  </React.StrictMode>
);
