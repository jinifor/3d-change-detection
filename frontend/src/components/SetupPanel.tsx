import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CircleHelp, Play, Upload } from "lucide-react";
import { createProject, startJob, uploadFile } from "../api/client";
import { useAppStore } from "../store/appStore";
import type { ProcessingParameters, UploadName } from "../types";

const parameterFields: Array<{
  key: keyof ProcessingParameters;
  label: string;
  step: number;
  min: number;
  description: string;
}> = [
  {
    key: "voxel_size_m",
    label: "Voxel Size",
    step: 0.01,
    min: 0.01,
    description: "Downsample spacing in meters for stable-surface registration and M3C2 core points.",
  },
  {
    key: "m3c2_scale_m",
    label: "M3C2 Scale",
    step: 0.01,
    min: 0.01,
    description: "Search radius in meters used by M3C2 to measure distance between T1 and T2 surfaces.",
  },
  {
    key: "normal_radius_m",
    label: "Normal Radius",
    step: 0.01,
    min: 0.01,
    description: "Neighborhood radius in meters used to estimate surface normals for M3C2.",
  },
  {
    key: "distance_threshold_m",
    label: "Distance Threshold",
    step: 0.01,
    min: 0.01,
    description: "Minimum absolute M3C2 distance in meters required to mark a point as changed.",
  },
  {
    key: "cluster_size_m",
    label: "Cluster Size",
    step: 0.01,
    min: 0.01,
    description: "DBSCAN distance in meters used to merge nearby changed points into one candidate.",
  },
  {
    key: "cluster_min_samples",
    label: "Cluster Min Samples",
    step: 1,
    min: 1,
    description: "Minimum number of changed points required to keep a candidate cluster.",
  },
  {
    key: "registration_rmse_threshold_m",
    label: "Registration RMSE",
    step: 0.01,
    min: 0.01,
    description: "Maximum ICP registration RMSE in meters before the pipeline asks whether to continue.",
  },
];

export function SetupPanel() {
  const config = useAppStore((state) => state.config);
  const parameters = useAppStore((state) => state.parameters);
  const uploadProgress = useAppStore((state) => state.uploadProgress);
  const setParameter = useAppStore((state) => state.setParameter);
  const setProject = useAppStore((state) => state.setProject);
  const setJob = useAppStore((state) => state.setJob);
  const setAssets = useAppStore((state) => state.setAssets);
  const setCandidates = useAppStore((state) => state.setCandidates);
  const setUploadProgress = useAppStore((state) => state.setUploadProgress);
  const resetUploadProgress = useAppStore((state) => state.resetUploadProgress);
  const clearEvents = useAppStore((state) => state.clearEvents);
  const addEvent = useAppStore((state) => state.addEvent);

  const [projectName, setProjectName] = useState("Change Detection Project");
  const [files, setFiles] = useState<Record<UploadName, File | null>>({ t1: null, t2: null });

  const ready = useMemo(
    () => projectName.trim().length > 0 && Boolean(files.t1 && files.t2),
    [files.t1, files.t2, projectName],
  );

  const runMutation = useMutation({
    mutationFn: async () => {
      if (!files.t1 || !files.t2) {
        throw new Error("Both T1 and T2 files are required.");
      }

      clearEvents();
      resetUploadProgress();
      setAssets(null);
      setCandidates([]);

      const created = await createProject(config, projectName.trim());
      setProject(created.project);
      addEvent({
        type: "job_progress",
        job_id: created.project.id,
        progress: 0,
        status: "UPLOADED",
      });

      await Promise.all([
        uploadFile("t1", created.uploads.t1.url, files.t1, setUploadProgress),
        uploadFile("t2", created.uploads.t2.url, files.t2, setUploadProgress),
      ]);

      const job = await startJob(config, created.project.id, parameters);
      setJob(job);
      return job;
    },
  });

  function setFile(name: UploadName, event: ChangeEvent<HTMLInputElement>) {
    setFiles((current) => ({
      ...current,
      [name]: event.target.files?.[0] ?? null,
    }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (ready && !runMutation.isPending) runMutation.mutate();
  }

  return (
    <form className="setup-form" onSubmit={submit}>
      <label>
        <span>Project</span>
        <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
      </label>

      <div className="file-grid">
        <label className="file-input">
          <input accept=".las,.laz" type="file" onChange={(event) => setFile("t1", event)} />
          <Upload size={16} />
          <span>{files.t1?.name ?? "T1 LAS/LAZ"}</span>
        </label>
        <label className="file-input">
          <input accept=".las,.laz" type="file" onChange={(event) => setFile("t2", event)} />
          <Upload size={16} />
          <span>{files.t2?.name ?? "T2 LAS/LAZ"}</span>
        </label>
      </div>

      <div className="upload-bars">
        <ProgressBar label="T1" value={uploadProgress.t1} />
        <ProgressBar label="T2" value={uploadProgress.t2} />
      </div>

      <div className="parameter-grid">
        {parameterFields.map((field) => (
          <label key={field.key}>
            <span className="parameter-label">
              <span>{field.label}</span>
              <span
                aria-label={field.description}
                className="help-tooltip"
                tabIndex={0}
                title={field.description}
              >
                <CircleHelp size={13} />
                <span className="tooltip-bubble" role="tooltip">
                  {field.description}
                </span>
              </span>
            </span>
            <input
              inputMode={field.step === 1 ? "numeric" : "decimal"}
              min={field.min}
              step={field.step}
              type="number"
              value={parameters[field.key]}
              onChange={(event) => setParameter(field.key, Number(event.target.value))}
            />
          </label>
        ))}
      </div>

      {runMutation.error && <p className="error-text">{runMutation.error.message}</p>}

      <button className="primary-button full" disabled={!ready || runMutation.isPending} type="submit">
        <Play size={16} />
        {runMutation.isPending ? "Starting" : "Start Job"}
      </button>
    </form>
  );
}

function ProgressBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="progress-row">
      <span>{label}</span>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${value}%` }} />
      </div>
      <strong>{value}%</strong>
    </div>
  );
}
