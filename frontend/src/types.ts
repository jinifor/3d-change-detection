export type JobStatus =
  | "UPLOADED"
  | "VALIDATING"
  | "REGISTERING"
  | "CONVERTING_COPC"
  | "GENERATING_TILES"
  | "DETECTING_CHANGE"
  | "CLUSTERING"
  | "PUBLISHING"
  | "COMPLETED"
  | "FAILED";

export type UploadName = "t1" | "t2";

export type ApiConfig = {
  baseUrl: string;
  apiKey: string;
  sseToken: string;
};

export type ProjectRead = {
  id: string;
  name: string;
  crs_epsg: number | null;
  origin_x: number | null;
  origin_y: number | null;
  registration_rmse: number | null;
  status: JobStatus | string;
  created_at: string;
  updated_at: string;
};

export type UploadTarget = {
  object_key: string;
  url: string;
  method: "PUT";
};

export type ProjectUploadRead = {
  project: ProjectRead;
  uploads: Record<UploadName, UploadTarget>;
};

export type ProcessingParameters = {
  voxel_size_m: number;
  m3c2_scale_m: number;
  normal_radius_m: number;
  distance_threshold_m: number;
  cluster_size_m: number;
  cluster_min_samples: number;
  registration_rmse_threshold_m: number;
};

export type JobRead = {
  id: string;
  project_id: string;
  status: JobStatus | string;
  progress: number;
  parameters: Record<string, unknown>;
  registration_matrix: number[][] | null;
  registration_decision: "continue" | "abort" | null;
  failure_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ProjectAssetsRead = {
  t1_copc_url: string;
  t2_aligned_copc_url: string;
  change_copc_url: string;
  change_geojson_url: string;
};

export type CandidateRead = {
  id: string;
  project_id: string;
  tile_id: string | null;
  bbox: {
    minx: number;
    miny: number;
    maxx: number;
    maxy: number;
  };
  area: number;
  point_count: number;
  distance_mean: number;
  distance_max: number;
  volume: number | null;
  height: number | null;
  created_at: string;
};

export type JobEvent =
  | {
      type: "job_progress";
      job_id: string;
      progress: number;
      status: JobStatus | string;
    }
  | {
      type: "registration_quality";
      job_id: string;
      rmse: number;
      threshold: number;
      passed: boolean;
    }
  | {
      type: "registration_decision_required";
      job_id: string;
      timeout_seconds: number;
    }
  | {
      type: "registration_decision";
      job_id: string;
      decision: "continue" | "abort";
    }
  | {
      type: "tile_complete";
      job_id?: string;
      tile_id: string;
    }
  | {
      type: "job_complete";
      job_id: string;
    }
  | {
      type: "job_failed";
      job_id: string;
      message: string;
    }
  | Record<string, unknown>;

export type EventLogItem = {
  id: string;
  at: string;
  label: string;
  payload: JobEvent;
};

export type LayerVisibility = {
  t1: boolean;
  t2: boolean;
  change: boolean;
  candidates: boolean;
};
