import type {
  ApiConfig,
  CandidateRead,
  JobRead,
  ProcessingParameters,
  ProjectAssetsRead,
  ProjectRead,
  ProjectUploadRead,
  UploadName,
} from "../types";

function apiUrl(config: ApiConfig, path: string): string {
  const baseUrl = config.baseUrl.replace(/\/$/, "");
  return `${baseUrl}${path}`;
}

async function apiRequest<T>(
  config: ApiConfig,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", config.apiKey);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(config, path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `${response.status} ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function checkHealth(config: ApiConfig): Promise<{ status: string }> {
  const response = await fetch(apiUrl(config, "/healthz"));
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<{ status: string }>;
}

export function createProject(config: ApiConfig, name: string): Promise<ProjectUploadRead> {
  return apiRequest<ProjectUploadRead>(config, "/api/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function getProject(config: ApiConfig, projectId: string): Promise<ProjectRead> {
  return apiRequest<ProjectRead>(config, `/api/projects/${projectId}`);
}

export function listProjects(config: ApiConfig, status?: string): Promise<ProjectRead[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<ProjectRead[]>(config, `/api/projects${query}`);
}

export function updateProject(
  config: ApiConfig,
  projectId: string,
  name: string,
): Promise<ProjectRead> {
  return apiRequest<ProjectRead>(config, `/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteProject(config: ApiConfig, projectId: string): Promise<void> {
  return apiRequest<void>(config, `/api/projects/${projectId}`, {
    method: "DELETE",
  });
}

export function startJob(
  config: ApiConfig,
  projectId: string,
  parameters: ProcessingParameters,
): Promise<JobRead> {
  return apiRequest<JobRead>(config, `/api/projects/${projectId}/jobs`, {
    method: "POST",
    body: JSON.stringify(parameters),
  });
}

export function getJob(config: ApiConfig, jobId: string): Promise<JobRead> {
  return apiRequest<JobRead>(config, `/api/jobs/${jobId}`);
}

export function getProjectAssets(
  config: ApiConfig,
  projectId: string,
): Promise<ProjectAssetsRead> {
  return apiRequest<ProjectAssetsRead>(config, `/api/projects/${projectId}/assets`);
}

export function getCandidates(config: ApiConfig, projectId: string): Promise<CandidateRead[]> {
  return apiRequest<CandidateRead[]>(config, `/api/projects/${projectId}/candidates`);
}

export function sendRegistrationDecision(
  config: ApiConfig,
  jobId: string,
  decision: "continue" | "abort",
): Promise<JobRead> {
  return apiRequest<JobRead>(config, `/api/jobs/${jobId}/registration-decision`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });
}

export function uploadFile(
  targetName: UploadName,
  url: string,
  file: File,
  onProgress: (targetName: UploadName, percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(targetName, Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress(targetName, 100);
        resolve();
        return;
      }
      reject(new Error(`upload failed: ${xhr.status} ${xhr.statusText}`));
    };

    xhr.onerror = () => reject(new Error("upload failed"));
    xhr.send(file);
  });
}
