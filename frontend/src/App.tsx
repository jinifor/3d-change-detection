import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Database, Layers3, UploadCloud } from "lucide-react";
import { getCandidates, getProjectAssets } from "./api/client";
import { MonitorPanel } from "./components/MonitorPanel";
import { ProjectPanel } from "./components/ProjectPanel";
import { SetupPanel } from "./components/SetupPanel";
import { TopBar } from "./components/TopBar";
import { ViewerPanel } from "./components/ViewerPanel";
import { InspectorPanel } from "./components/InspectorPanel";
import { useJobEvents } from "./hooks/useJobEvents";
import { useAppStore } from "./store/appStore";

export function App() {
  const config = useAppStore((state) => state.config);
  const project = useAppStore((state) => state.project);
  const job = useAppStore((state) => state.job);
  const setAssets = useAppStore((state) => state.setAssets);
  const setCandidates = useAppStore((state) => state.setCandidates);

  useJobEvents(job?.id ?? null, project?.id ?? null);

  const isComplete = job?.status === "COMPLETED" || project?.status === "COMPLETED";

  const assetsQuery = useQuery({
    queryKey: ["project-assets", project?.id, isComplete],
    queryFn: () => getProjectAssets(config, project!.id),
    enabled: Boolean(project?.id && isComplete),
  });

  const candidatesQuery = useQuery({
    queryKey: ["project-candidates", project?.id, isComplete],
    queryFn: () => getCandidates(config, project!.id),
    enabled: Boolean(project?.id && isComplete),
  });

  useEffect(() => {
    if (assetsQuery.data) setAssets(assetsQuery.data);
  }, [assetsQuery.data, setAssets]);

  useEffect(() => {
    if (candidatesQuery.data) setCandidates(candidatesQuery.data);
  }, [candidatesQuery.data, setCandidates]);

  return (
    <div className="app-shell">
      <TopBar />
      <main className="workspace">
        <aside className="left-rail" aria-label="Workflow">
          <section className="panel">
            <div className="panel-heading">
              <Database size={17} />
              <h2>Projects</h2>
            </div>
            <ProjectPanel />
          </section>
          <section className="panel">
            <div className="panel-heading">
              <UploadCloud size={17} />
              <h2>Upload</h2>
            </div>
            <SetupPanel />
          </section>
          <section className="panel">
            <div className="panel-heading">
              <Activity size={17} />
              <h2>Progress</h2>
            </div>
            <MonitorPanel />
          </section>
        </aside>

        <section className="map-stage" aria-label="3D viewer">
          <div className="stage-title">
            <div>
              <span className="eyebrow">Viewer</span>
              <h1>{project?.name ?? "3D Change Detection"}</h1>
            </div>
            <div className="stage-meta">
              <span>{project?.status ?? "READY"}</span>
              <span>{project?.crs_epsg ? `EPSG:${project.crs_epsg}` : "CRS pending"}</span>
            </div>
          </div>
          <ViewerPanel />
        </section>

        <aside className="right-rail" aria-label="Results">
          <section className="panel grow">
            <div className="panel-heading">
              <Layers3 size={17} />
              <h2>Layers</h2>
            </div>
            <InspectorPanel mode="layers" />
          </section>
          <section className="panel grow">
            <div className="panel-heading">
              <Database size={17} />
              <h2>Candidates</h2>
            </div>
            <InspectorPanel mode="candidates" />
          </section>
        </aside>
      </main>
    </div>
  );
}
