from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "3D Change Detection API"
    api_prefix: str = "/api"
    api_key: str = "dev-api-key"
    sse_token: str | None = "dev-api-key"

    database_url: str = "postgresql+psycopg://change:change@postgis:5432/change_detection"
    redis_url: str = "redis://redis:6379/0"
    rq_queue_name: str = "default"
    rq_job_timeout_seconds: int = 60 * 60 * 12

    minio_endpoint: str = "http://minio:9000"
    minio_external_endpoint: str | None = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "point-cloud-projects"
    minio_secure: bool = False
    upload_presign_expires_seconds: int = 60 * 60

    local_data_dir: Path = Path("/data")
    default_tile_size_m: float = 100.0
    minimum_bbox_overlap_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    registration_decision_poll_seconds: float = 2.0
    registration_decision_timeout_seconds: float = 1800.0
    event_history_limit: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
