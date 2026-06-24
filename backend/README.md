# Backend / Worker Pipeline

This package implements the MVP backend and worker pipeline described in
`요구사항분석서.md`.

## Local Docker Run

```bash
docker compose up --build
```

API base URL:

```text
http://localhost:8000/api
```

All API routes require:

```text
X-API-Key: dev-api-key
```

## Main Flow

1. `POST /api/projects` creates a project and returns MinIO presigned PUT URLs.
2. Upload `T1.laz` and `T2.laz` to those URLs, or use `POST /api/projects/{project_id}/uploads/multipart` for multipart presigned part URLs.
3. `POST /api/projects/{project_id}/jobs` starts the RQ worker pipeline.
4. `GET /api/jobs/{job_id}/events?token=dev-api-key` streams progress events.
5. `POST /api/jobs/{job_id}/registration-decision` continues or aborts when RMSE exceeds the requested threshold.
6. `GET /api/projects/{project_id}/assets` returns presigned viewer URLs for COPC and GeoJSON outputs.

## Job Parameters

```json
{
  "voxel_size_m": 0.5,
  "m3c2_scale_m": 2.0,
  "normal_radius_m": 1.0,
  "distance_threshold_m": 0.2,
  "cluster_size_m": 1.0,
  "cluster_min_samples": 10,
  "registration_rmse_threshold_m": 0.2
}
```

`cluster_size_m` maps to DBSCAN `eps`. `cluster_min_samples` is explicit because the requirements document defines cluster size as the basis for both DBSCAN `eps` and `min_samples`.

## Fixed MVP Defaults

- `MINIMUM_BBOX_OVERLAP_RATIO=0.5`
- `DEFAULT_TILE_SIZE_M=100.0`
- `REGISTRATION_DECISION_TIMEOUT_SECONDS=1800`
- SSE uses `token` query authentication so browser `EventSource` can connect without custom headers.
- Database schema is managed by Alembic and upgraded on API startup.
