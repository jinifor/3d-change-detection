from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_api_key, require_sse_token
from app.db.models import Job
from app.schemas import JobRead, RegistrationDecisionRequest
from app.services.events import event_stream
from app.services.jobs import set_registration_decision

router = APIRouter()


@router.get("/{job_id}", response_model=JobRead, dependencies=[Depends(require_api_key)])
def read_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job


@router.get("/{job_id}/events", dependencies=[Depends(require_sse_token)])
def stream_job_events(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return StreamingResponse(event_stream(job_id), media_type="text/event-stream")


@router.post(
    "/{job_id}/registration-decision",
    response_model=JobRead,
    dependencies=[Depends(require_api_key)],
)
def decide_registration_quality(
    job_id: str,
    payload: RegistrationDecisionRequest,
    db: Session = Depends(get_db),
) -> Job:
    job = set_registration_decision(db, job_id, payload.decision)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job
