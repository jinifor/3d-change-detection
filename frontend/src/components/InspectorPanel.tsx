import { ExternalLink, MousePointer2 } from "lucide-react";
import { useAppStore } from "../store/appStore";
import type { LayerVisibility } from "../types";

export function InspectorPanel({ mode }: { mode: "layers" | "candidates" }) {
  if (mode === "layers") return <LayerInspector />;
  return <CandidateInspector />;
}

function LayerInspector() {
  const assets = useAppStore((state) => state.assets);
  const visibility = useAppStore((state) => state.layerVisibility);
  const toggleLayer = useAppStore((state) => state.toggleLayer);

  const layers: Array<{ key: keyof LayerVisibility; label: string; url?: string }> = [
    { key: "t1", label: "T1 COPC", url: assets?.t1_copc_url },
    { key: "t2", label: "T2 Aligned COPC", url: assets?.t2_aligned_copc_url },
    { key: "change", label: "Change COPC", url: assets?.change_copc_url },
    { key: "candidates", label: "Candidate BBox", url: assets?.change_geojson_url },
  ];

  return (
    <div className="layer-list">
      {layers.map((layer) => (
        <div className="layer-row" key={layer.key}>
          <label>
            <input
              checked={visibility[layer.key]}
              type="checkbox"
              onChange={() => toggleLayer(layer.key)}
            />
            <span>{layer.label}</span>
          </label>
          {layer.url && (
            <a href={layer.url} rel="noreferrer" target="_blank" title="Open asset">
              <ExternalLink size={15} />
            </a>
          )}
        </div>
      ))}
      {!assets && <p className="muted">Assets appear after completion.</p>}
    </div>
  );
}

function CandidateInspector() {
  const candidates = useAppStore((state) => state.candidates);
  const selectedCandidateId = useAppStore((state) => state.selectedCandidateId);
  const setSelectedCandidateId = useAppStore((state) => state.setSelectedCandidateId);
  const selected = candidates.find((candidate) => candidate.id === selectedCandidateId);

  return (
    <div className="candidate-panel">
      {selected && (
        <div className="selected-candidate">
          <div className="selected-title">
            <MousePointer2 size={16} />
            <strong>{selected.id.slice(0, 8)}</strong>
          </div>
          <dl>
            <div>
              <dt>Area</dt>
              <dd>{selected.area.toFixed(2)} m2</dd>
            </div>
            <div>
              <dt>Points</dt>
              <dd>{selected.point_count.toLocaleString()}</dd>
            </div>
            <div>
              <dt>Mean</dt>
              <dd>{selected.distance_mean.toFixed(3)} m</dd>
            </div>
            <div>
              <dt>Max</dt>
              <dd>{selected.distance_max.toFixed(3)} m</dd>
            </div>
          </dl>
        </div>
      )}

      <div className="candidate-list">
        {candidates.length === 0 && <p className="muted">No candidates loaded.</p>}
        {candidates.map((candidate) => (
          <button
            className={candidate.id === selectedCandidateId ? "candidate-row selected" : "candidate-row"}
            key={candidate.id}
            type="button"
            onClick={() => setSelectedCandidateId(candidate.id)}
          >
            <span>{candidate.id.slice(0, 8)}</span>
            <strong>{candidate.distance_max.toFixed(2)}m</strong>
          </button>
        ))}
      </div>
    </div>
  );
}
