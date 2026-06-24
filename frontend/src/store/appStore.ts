import { create } from "zustand";
import { defaultApiConfig, defaultParameters } from "../config";
import type {
  ApiConfig,
  CandidateRead,
  EventLogItem,
  JobEvent,
  JobRead,
  LayerVisibility,
  ProcessingParameters,
  ProjectAssetsRead,
  ProjectRead,
  UploadName,
} from "../types";

type UploadProgress = Record<UploadName, number>;

type RegistrationGate = {
  jobId: string;
  rmse: number;
  threshold: number;
} | null;

type AppState = {
  config: ApiConfig;
  parameters: ProcessingParameters;
  project: ProjectRead | null;
  job: JobRead | null;
  assets: ProjectAssetsRead | null;
  candidates: CandidateRead[];
  uploadProgress: UploadProgress;
  events: EventLogItem[];
  registrationGate: RegistrationGate;
  selectedCandidateId: string | null;
  layerVisibility: LayerVisibility;
  setConfig: (config: ApiConfig) => void;
  setParameter: (key: keyof ProcessingParameters, value: number) => void;
  setProject: (project: ProjectRead | null) => void;
  setJob: (job: JobRead | null) => void;
  setAssets: (assets: ProjectAssetsRead | null) => void;
  setCandidates: (candidates: CandidateRead[]) => void;
  setUploadProgress: (targetName: UploadName, percent: number) => void;
  resetUploadProgress: () => void;
  addEvent: (event: JobEvent) => void;
  clearEvents: () => void;
  setRegistrationGate: (gate: RegistrationGate) => void;
  setSelectedCandidateId: (candidateId: string | null) => void;
  toggleLayer: (key: keyof LayerVisibility) => void;
};

function eventLabel(event: JobEvent): string {
  const typed = event as Record<string, unknown>;
  const type = typeof typed.type === "string" ? typed.type : "event";
  if (type === "job_progress") return `${typed.status} ${typed.progress}%`;
  if (type === "registration_quality") {
    const rmse = Number(typed.rmse);
    return typed.passed
      ? `registration RMSE ${rmse.toFixed(3)}m`
      : `registration gate ${rmse.toFixed(3)}m`;
  }
  if (type === "registration_decision_required") return "registration decision required";
  if (type === "registration_decision") return `registration ${typed.decision}`;
  if (type === "tile_complete") return `tile complete ${typed.tile_id}`;
  if (type === "job_complete") return "job complete";
  if (type === "job_failed") return String(typed.message ?? "job failed");
  return String(type);
}

export const useAppStore = create<AppState>((set) => ({
  config: defaultApiConfig,
  parameters: defaultParameters,
  project: null,
  job: null,
  assets: null,
  candidates: [],
  uploadProgress: { t1: 0, t2: 0 },
  events: [],
  registrationGate: null,
  selectedCandidateId: null,
  layerVisibility: {
    t1: true,
    t2: true,
    change: true,
    candidates: true,
  },
  setConfig: (config) => set({ config }),
  setParameter: (key, value) =>
    set((state) => ({
      parameters: {
        ...state.parameters,
        [key]: value,
      },
    })),
  setProject: (project) => set({ project }),
  setJob: (job) => set({ job }),
  setAssets: (assets) => set({ assets }),
  setCandidates: (candidates) => set({ candidates }),
  setUploadProgress: (targetName, percent) =>
    set((state) => ({
      uploadProgress: {
        ...state.uploadProgress,
        [targetName]: percent,
      },
    })),
  resetUploadProgress: () => set({ uploadProgress: { t1: 0, t2: 0 } }),
  addEvent: (event) =>
    set((state) => ({
      events: [
        {
          id: `${Date.now()}-${state.events.length}`,
          at: new Date().toISOString(),
          label: eventLabel(event),
          payload: event,
        },
        ...state.events,
      ].slice(0, 80),
    })),
  clearEvents: () => set({ events: [] }),
  setRegistrationGate: (registrationGate) => set({ registrationGate }),
  setSelectedCandidateId: (selectedCandidateId) => set({ selectedCandidateId }),
  toggleLayer: (key) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [key]: !state.layerVisibility[key],
      },
    })),
}));
