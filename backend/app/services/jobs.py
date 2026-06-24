from datetime import datetime, timezone

from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Job, Project
from app.schemas import ProcessingParameters
from app.services.events import publish_event


redis_connection = Redis.from_url(settings.redis_url)
queue = Queue(settings.rq_queue_name, connection=redis_connection)


def enqueue_project_job(
    db: Session,
    project_id: str,
    parameters: ProcessingParameters,
) -> Job | None:
    project = db.get(Project, project_id)
    if project is None:
        return None

    job = Job(
        project_id=project.id,
        status="UPLOADED",
        progress=0,
        parameters=parameters.model_dump(),
        started_at=None,
    )
    project.status = "UPLOADED"
    db.add(job)
    db.commit()
    db.refresh(job)

    queue.enqueue(
        "app.worker_tasks.process_job",
        job.id,
        job_timeout=settings.rq_job_timeout_seconds,
    )
    publish_event(
        job.id,
        {"type": "job_progress", "job_id": job.id, "progress": 0, "status": "UPLOADED"},
    )
    return job


def set_registration_decision(db: Session, job_id: str, decision: str) -> Job | None:
    job = db.get(Job, job_id)
    if job is None:
        return None
    job.registration_decision = decision
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    publish_event(
        job.id,
        {"type": "registration_decision", "job_id": job.id, "decision": decision},
    )
    return job
