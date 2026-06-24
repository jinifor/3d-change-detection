import type { ApiConfig, ProcessingParameters } from "./types";

export const defaultApiConfig: ApiConfig = {
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? "",
  apiKey: import.meta.env.VITE_API_KEY ?? "dev-api-key",
  sseToken: import.meta.env.VITE_SSE_TOKEN ?? "dev-api-key",
};

export const defaultMapStyle =
  import.meta.env.VITE_MAP_STYLE_URL ??
  "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

export const defaultParameters: ProcessingParameters = {
  voxel_size_m: 0.5,
  m3c2_scale_m: 2.0,
  normal_radius_m: 1.0,
  distance_threshold_m: 0.2,
  cluster_size_m: 1.0,
  cluster_min_samples: 10,
  registration_rmse_threshold_m: 0.2,
};
