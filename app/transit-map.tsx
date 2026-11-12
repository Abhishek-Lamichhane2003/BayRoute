"use client";

import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { LiveVehicle } from "./types";

export function TransitMap({ vehicles }: { vehicles: LiveVehicle[] }) {
  const mapContainer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let disposed = false;
    let map: import("maplibre-gl").Map | undefined;

    async function mountMap() {
      if (!mapContainer.current) return;
      const maplibre = await import("maplibre-gl");
      if (disposed || !mapContainer.current) return;

      map = new maplibre.Map({
        container: mapContainer.current,
        center: [-121.887, 37.351],
        zoom: 11.1,
        attributionControl: false,
        style: {
          version: 8,
          sources: {
            openstreetmap: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [{ id: "osm", type: "raster", source: "openstreetmap" }],
        },
      });
      map.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      map.addControl(new maplibre.AttributionControl({ compact: true }), "bottom-right");

      vehicles.forEach((vehicle) => {
        const marker = document.createElement("button");
        marker.className = "vehicle-marker";
        marker.style.setProperty("--route-color", vehicle.route_color);
        marker.type = "button";
        marker.setAttribute(
          "aria-label",
          `Route ${vehicle.route_name}, ${Math.round(vehicle.delay_seconds / 60)} minutes late near ${vehicle.stop_name}`,
        );
        marker.textContent = vehicle.route_name;

        const popupNode = document.createElement("div");
        popupNode.className = "map-popup";
        const title = document.createElement("strong");
        title.textContent = `Route ${vehicle.route_name}`;
        const detail = document.createElement("span");
        detail.textContent = `${vehicle.stop_name} · ${(vehicle.delay_seconds / 60).toFixed(1)} min delay`;
        popupNode.append(title, detail);
        const popup = new maplibre.Popup({ offset: 16 }).setDOMContent(popupNode);

        new maplibre.Marker({ element: marker })
          .setLngLat([vehicle.longitude, vehicle.latitude])
          .setPopup(popup)
          .addTo(map!);
      });
    }

    void mountMap();
    return () => {
      disposed = true;
      map?.remove();
    };
  }, [vehicles]);

  return <div ref={mapContainer} className="transit-map" aria-label="Live vehicle map" />;
}
