from sqlalchemy.orm import Session

from app.db.models import Candidate, Project
from app.processing.storage_keys import StorageKeys
from app.schemas import (
    MultipartPartTarget,
    MultipartUploadComplete,
    MultipartUploadCreate,
    MultipartUploadRead,
    ProjectAssetsRead,
    ProjectCreate,
    ProjectUploadRead,
    UploadTarget,
)
from app.services.storage import get_storage_client


def create_project_with_upload_urls(db: Session, payload: ProjectCreate) -> ProjectUploadRead:
    project = Project(name=payload.name, status="UPLOADED")
    db.add(project)
    db.commit()
    db.refresh(project)

    storage = get_storage_client()
    t1_key = StorageKeys.raw_t1(project.id)
    t2_key = StorageKeys.raw_t2(project.id)
    return ProjectUploadRead(
        project=project,
        uploads={
            "t1": UploadTarget(object_key=t1_key, url=storage.presigned_put_url(t1_key)),
            "t2": UploadTarget(object_key=t2_key, url=storage.presigned_put_url(t2_key)),
        },
    )


def list_project_candidates(db: Session, project_id: str) -> list[Candidate]:
    return (
        db.query(Candidate)
        .filter(Candidate.project_id == project_id)
        .order_by(Candidate.created_at.asc())
        .all()
    )


def get_project_assets(project_id: str) -> ProjectAssetsRead:
    storage = get_storage_client()
    return ProjectAssetsRead(
        t1_copc_url=storage.presigned_get_url(StorageKeys.copc_t1(project_id)),
        t2_aligned_copc_url=storage.presigned_get_url(StorageKeys.copc_t2_aligned(project_id)),
        change_copc_url=storage.presigned_get_url(StorageKeys.result_change_copc(project_id)),
        change_geojson_url=storage.presigned_get_url(StorageKeys.result_change_geojson(project_id)),
    )


def create_multipart_upload(
    project_id: str,
    payload: MultipartUploadCreate,
) -> MultipartUploadRead:
    object_key = _raw_object_key(project_id, payload.object_name)
    storage = get_storage_client()
    upload_id = storage.create_multipart_upload(object_key)
    return MultipartUploadRead(
        object_key=object_key,
        upload_id=upload_id,
        parts=[
            MultipartPartTarget(
                part_number=part_number,
                url=storage.presigned_upload_part_url(object_key, upload_id, part_number),
            )
            for part_number in range(1, payload.part_count + 1)
        ],
    )


def complete_multipart_upload(payload: MultipartUploadComplete) -> None:
    storage = get_storage_client()
    storage.complete_multipart_upload(
        object_key=payload.object_key,
        upload_id=payload.upload_id,
        parts=[part.model_dump() for part in payload.parts],
    )


def _raw_object_key(project_id: str, object_name: str) -> str:
    if object_name == "t1":
        return StorageKeys.raw_t1(project_id)
    return StorageKeys.raw_t2(project_id)
