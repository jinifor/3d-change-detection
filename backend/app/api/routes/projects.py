from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_api_key
from app.db.models import Candidate, Project
from app.processing.storage_keys import StorageKeys
from app.schemas import (
    CandidateRead,
    JobRead,
    MultipartUploadComplete,
    MultipartUploadCreate,
    MultipartUploadRead,
    ProcessingParameters,
    ProjectAssetsRead,
    ProjectCreate,
    ProjectRead,
    ProjectUploadRead,
)
from app.services.jobs import enqueue_project_job
from app.services.projects import (
    complete_multipart_upload,
    create_project_with_upload_urls,
    create_multipart_upload,
    get_project_assets,
    list_project_candidates,
)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("", response_model=ProjectUploadRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectUploadRead:
    return create_project_with_upload_urls(db, payload)


@router.get("/{project_id}", response_model=ProjectRead)
def read_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.post("/{project_id}/jobs", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def start_project_job(
    project_id: str,
    parameters: ProcessingParameters,
    db: Session = Depends(get_db),
) -> JobRead:
    job = enqueue_project_job(db, project_id, parameters)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return job


@router.get("/{project_id}/candidates", response_model=list[CandidateRead])
def read_project_candidates(project_id: str, db: Session = Depends(get_db)) -> list[Candidate]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return list_project_candidates(db, project_id)


@router.get("/{project_id}/assets", response_model=ProjectAssetsRead)
def read_project_assets(project_id: str, db: Session = Depends(get_db)) -> ProjectAssetsRead:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return get_project_assets(project_id)


@router.post("/{project_id}/uploads/multipart", response_model=MultipartUploadRead)
def start_multipart_upload(
    project_id: str,
    payload: MultipartUploadCreate,
    db: Session = Depends(get_db),
) -> MultipartUploadRead:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return create_multipart_upload(project_id, payload)


@router.post("/{project_id}/uploads/multipart/complete", status_code=status.HTTP_204_NO_CONTENT)
def finish_multipart_upload(
    project_id: str,
    payload: MultipartUploadComplete,
    db: Session = Depends(get_db),
) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    allowed_keys = {StorageKeys.raw_t1(project_id), StorageKeys.raw_t2(project_id)}
    if payload.object_key not in allowed_keys:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid object key")
    complete_multipart_upload(payload)
