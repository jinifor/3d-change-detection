import { useEffect, useMemo, useRef, useState } from "react";
import { GeoJsonLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { LidarControl } from "maplibre-gl-lidar";
import maplibregl, { Map } from "maplibre-gl";
import { AlertTriangle, Eye, EyeOff, LocateFixed } from "lucide-react";
import { defaultMapStyle } from "../config";
import { useAppStore } from "../store/appStore";
import { bboxCenter, candidatesToFeatureCollection } from "../utils/geo";

type LidarControlHandle = InstanceType<typeof LidarControl>;

export function ViewerPanel() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const lidarRef = useRef<LidarControlHandle | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const loadedSignatureRef = useRef("");
  const assetSignatureRef = useRef("");
  const [lidarState, setLidarState] = useState("idle");
  const [lidarError, setLidarError] = useState<string | null>(null);

  const project = useAppStore((state) => state.project);
  const assets = useAppStore((state) => state.assets);
  const candidates = useAppStore((state) => state.candidates);
  const visibility = useAppStore((state) => state.layerVisibility);
  const toggleLayer = useAppStore((state) => state.toggleLayer);
  const selectedCandidateId = useAppStore((state) => state.selectedCandidateId);
  const setSelectedCandidateId = useAppStore((state) => state.setSelectedCandidateId);

  const candidateGeoJson = useMemo(
    () => candidatesToFeatureCollection(candidates, project?.crs_epsg ?? null),
    [candidates, project?.crs_epsg],
  );

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: defaultMapStyle,
      center: [127.03, 37.49],
      zoom: 14,
      pitch: 62,
      bearing: -18,
      maxPitch: 85,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

    map.on("load", () => {
      const lidar = new LidarControl({
        title: "Point Clouds",
        collapsed: true,
        pointSize: 2,
        opacity: 0.95,
        colorScheme: "elevation",
        pickable: true,
        autoZoom: false,
        theme: "light",
        copcLoadingMode: "dynamic",
        streamingPointBudget: 5_000_000,
      });

      lidar.on("loadstart", () => setLidarState("loading"));
      lidar.on("load", () => setLidarState("loaded"));
      lidar.on("loaderror", (event: unknown) => {
        setLidarState("error");
        setLidarError(event instanceof Error ? event.message : "point cloud load failed");
      });
      lidar.on("streamingstart", () => setLidarState("streaming"));
      lidar.on("streamingstop", () => setLidarState("loaded"));

      map.addControl(lidar, "top-right");
      lidarRef.current = lidar;

      const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
      map.addControl(overlay);
      overlayRef.current = overlay;
    });

    mapRef.current = map;
    return () => {
      loadedSignatureRef.current = "";
      assetSignatureRef.current = "";
      overlayRef.current?.finalize();
      overlayRef.current = null;
      lidarRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!overlayRef.current) return;

    overlayRef.current.setProps({
      layers: visibility.candidates
        ? [
            new GeoJsonLayer<Record<string, unknown>>({
              id: "candidate-bbox-layer",
              data: candidateGeoJson,
              pickable: true,
              stroked: true,
              filled: true,
              getFillColor: (feature) =>
                feature.id === selectedCandidateId ? [236, 151, 31, 90] : [13, 148, 136, 50],
              getLineColor: (feature) =>
                feature.id === selectedCandidateId ? [192, 86, 33, 240] : [9, 92, 87, 230],
              getLineWidth: (feature) => (feature.id === selectedCandidateId ? 3 : 2),
              lineWidthMinPixels: 2,
              onClick: (info) => {
                const id = info.object?.id ?? info.object?.properties?.id;
                if (typeof id === "string") setSelectedCandidateId(id);
              },
              updateTriggers: {
                getFillColor: [selectedCandidateId],
                getLineColor: [selectedCandidateId],
                getLineWidth: [selectedCandidateId],
              },
            }),
          ]
        : [],
    });
  }, [candidateGeoJson, selectedCandidateId, setSelectedCandidateId, visibility.candidates]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedCandidateId) return;

    const candidate = candidates.find((item) => item.id === selectedCandidateId);
    if (!candidate) return;

    const center = bboxCenter(candidate, project?.crs_epsg ?? null);
    if (center) {
      map.flyTo({ center, zoom: Math.max(map.getZoom(), 17), pitch: 65, duration: 800 });
    }
  }, [candidates, project?.crs_epsg, selectedCandidateId]);

  useEffect(() => {
    const lidar = lidarRef.current;
    if (!lidar || !assets) return;
    const lidarControl = lidar;
    const assetSignature = [
      assets.t1_copc_url,
      assets.t2_aligned_copc_url,
      assets.change_copc_url,
    ].join("|");
    const shouldFitOnLoad = assetSignature !== assetSignatureRef.current;
    assetSignatureRef.current = assetSignature;

    const sources = [
      visibility.t1 ? assets.t1_copc_url : "",
      visibility.t2 ? assets.t2_aligned_copc_url : "",
      visibility.change ? assets.change_copc_url : "",
    ].filter(Boolean);
    const signature = sources.join("|");
    if (signature === loadedSignatureRef.current) return;

    loadedSignatureRef.current = signature;
    setLidarError(null);

    async function reload() {
      try {
        setLidarState(sources.length > 0 ? "loading" : "idle");
        lidarControl.unloadPointCloud();
        for (const source of sources) {
          await lidarControl.loadPointCloud(source, { loadingMode: "dynamic" });
        }
        if (sources.length > 0 && shouldFitOnLoad) {
          lidarControl.flyToPointCloud();
        }
      } catch (error) {
        setLidarState("error");
        setLidarError(error instanceof Error ? error.message : "point cloud load failed");
      }
    }

    void reload();
  }, [assets, visibility.change, visibility.t1, visibility.t2]);

  return (
    <div className="viewer-shell">
      <div ref={containerRef} className="map-container" />

      <div className="viewer-toolbar">
        <LayerButton active={visibility.t1} label="T1" onClick={() => toggleLayer("t1")} />
        <LayerButton active={visibility.t2} label="T2" onClick={() => toggleLayer("t2")} />
        <LayerButton
          active={visibility.change}
          label="Change"
          onClick={() => toggleLayer("change")}
        />
        <LayerButton
          active={visibility.candidates}
          label="Candidates"
          onClick={() => toggleLayer("candidates")}
        />
        <button
          className="icon-button"
          type="button"
          title="Fit point clouds"
          onClick={() => lidarRef.current?.flyToPointCloud()}
        >
          <LocateFixed size={16} />
        </button>
      </div>

      <div className="viewer-status">
        <span>{lidarState}</span>
        {lidarError && (
          <span className="status-error">
            <AlertTriangle size={14} />
            {lidarError}
          </span>
        )}
      </div>
    </div>
  );
}

function LayerButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={active ? "tool-button active" : "tool-button"} type="button" onClick={onClick}>
      {active ? <Eye size={15} /> : <EyeOff size={15} />}
      <span>{label}</span>
    </button>
  );
}
