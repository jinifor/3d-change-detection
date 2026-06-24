from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, PositiveFloat


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class UploadTarget(BaseModel):
    object_key: str
    url: str
    method: Literal["PUT"] = "PUT"


class ProjectRead(BaseModel):
    id: str
    name: str
    crs_epsg: int | None
    origin_x: float | None
    origin_y: float | None
    registration_rmse: float | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUploadRead(BaseModel):
    project: ProjectRead
    uploads: dict[Literal["t1", "t2"], UploadTarget]


class ProjectAssetsRead(BaseModel):
    t1_copc_url: str
    t2_aligned_copc_url: str
    change_copc_url: str
    change_geojson_url: str


class MultipartUploadCreate(BaseModel):
    object_name: Literal["t1", "t2"]
    part_count: int = Field(ge=1, le=10000)


class MultipartPartTarget(BaseModel):
    part_number: int
    url: str
    method: Literal["PUT"] = "PUT"


class MultipartUploadRead(BaseModel):
    object_key: str
    upload_id: str
    parts: list[MultipartPartTarget]


class MultipartPartComplete(BaseModel):
    part_number: int = Field(ge=1)
    etag: str = Field(min_length=1)


class MultipartUploadComplete(BaseModel):
    object_key: str
    upload_id: str
    parts: list[MultipartPartComplete]


class ProcessingParameters(BaseModel):
    voxel_size_m: PositiveFloat
    m3c2_scale_m: PositiveFloat
    normal_radius_m: PositiveFloat
    distance_threshold_m: PositiveFloat
    cluster_size_m: PositiveFloat = Field(description="DBSCAN eps in meters")
    cluster_min_samples: int = Field(ge=1)
    registration_rmse_threshold_m: PositiveFloat


class JobRead(BaseModel):
    id: str
    project_id: str
    status: str
    progress: int
    parameters: dict
    registration_matrix: list[list[float]] | None
    registration_decision: str | None
    failure_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistrationDecisionRequest(BaseModel):
    decision: Literal["continue", "abort"]


class CandidateRead(BaseModel):
    id: str
    project_id: str
    tile_id: str | None
    bbox: dict
    area: float
    point_count: int
    distance_mean: float
    distance_max: float
    volume: float | None
    height: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
