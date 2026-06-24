from datetime import datetime, timezone
from time import monotonic, sleep

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Job
from app.db.session import SessionLocal
from app.processing.clustering import cluster_change_points
from app.processing.copc import convert_to_copc
from app.processing.exceptions import ProcessingError
from app.processing.m3c2 import process_tiles_m3c2
from app.processing.paths import WorkPaths
from app.processing.publishing import publish_results
from app.processing.registration import register_t2_to_t1
from app.processing.storage_keys import StorageKeys
from app.processing.tiling import create_tiles
from app.processing.validation import validate_inputs
from app.schemas import ProcessingParameters
from app.services.events import publish_event
from app.services.storage import get_storage_client


class ChangeDetectionPipeline:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def run(self) -> None:
        try:
            with SessionLocal() as db:
                job = self._get_job(db)
                project = job.project
                project_id = project.id
                parameters = ProcessingParameters.model_validate(job.parameters)
                paths = WorkPaths.for_project(project_id)
                paths.ensure()
                job.started_at = datetime.now(timezone.utc)
                db.commit()

            self._download_raw_inputs(project_id, paths)

            self._set_status("VALIDATING", 5)
            with SessionLocal() as db:
                validation = validate_inputs(paths.t1_raw, paths.t2_raw)
                job = self._get_job(db)
                project = job.project
                project.crs_epsg = validation.crs_epsg
                project.origin_x = validation.origin_x
                project.origin_y = validation.origin_y
                db.commit()

            if validation.overlap_ratio < settings.minimum_bbox_overlap_ratio:
                raise ProcessingError(
                    "bbox overlap ratio "
                    f"{validation.overlap_ratio:.4f} is below configured minimum "
                    f"{settings.minimum_bbox_overlap_ratio:.4f}"
                )

            self._set_status("REGISTERING", 20)
            registration = register_t2_to_t1(
                paths=paths,
                parameters=parameters,
                origin_x=validation.origin_x,
                origin_y=validation.origin_y,
            )
            with SessionLocal() as db:
                job = self._get_job(db)
                project = job.project
                project.registration_rmse = registration.rmse
                job.registration_matrix = registration.matrix
                db.commit()

            publish_event(
                self.job_id,
                {
                    "type": "registration_quality",
                    "job_id": self.job_id,
                    "rmse": registration.rmse,
                    "threshold": parameters.registration_rmse_threshold_m,
                    "passed": registration.rmse <= parameters.registration_rmse_threshold_m,
                },
            )
            if registration.rmse > parameters.registration_rmse_threshold_m:
                self._wait_for_registration_decision()

            self._set_status("CONVERTING_COPC", 40)
            convert_to_copc(str(paths.t1_raw), str(paths.t1_copc))
            convert_to_copc(str(paths.t2_aligned), str(paths.t2_aligned_copc))
            self._upload_copc(project_id, paths)

            self._set_status("GENERATING_TILES", 50)
            with SessionLocal() as db:
                create_tiles(
                    db=db,
                    project_id=project_id,
                    bbox=validation.overlap_bbox,
                    tile_size_m=settings.default_tile_size_m,
                )

            self._set_status("DETECTING_CHANGE", 60)
            with SessionLocal() as db:
                for tile, _ in process_tiles_m3c2(
                    db=db,
                    project_id=project_id,
                    origin_x=validation.origin_x,
                    origin_y=validation.origin_y,
                    paths=paths,
                    parameters=parameters,
                ):
                    publish_event(
                        self.job_id,
                        {"type": "tile_complete", "job_id": self.job_id, "tile_id": tile.id},
                    )

            self._set_status("CLUSTERING", 85)
            with SessionLocal() as db:
                cluster_change_points(
                    db=db,
                    project_id=project_id,
                    crs_epsg=validation.crs_epsg,
                    origin_x=validation.origin_x,
                    origin_y=validation.origin_y,
                    paths=paths,
                    parameters=parameters,
                )

            self._set_status("PUBLISHING", 95)
            publish_results(project_id, paths, validation.origin_x, validation.origin_y)

            with SessionLocal() as db:
                job = self._get_job(db)
                project = job.project
                job.status = "COMPLETED"
                job.progress = 100
                job.completed_at = datetime.now(timezone.utc)
                project.status = "COMPLETED"
                db.commit()
            publish_event(self.job_id, {"type": "job_complete", "job_id": self.job_id})
        except Exception as exc:  # noqa: BLE001
            self._fail(str(exc))
            raise

    def _download_raw_inputs(self, project_id: str, paths: WorkPaths) -> None:
        storage = get_storage_client()
        storage.download_file(StorageKeys.raw_t1(project_id), paths.t1_raw)
        storage.download_file(StorageKeys.raw_t2(project_id), paths.t2_raw)

    def _upload_copc(self, project_id: str, paths: WorkPaths) -> None:
        storage = get_storage_client()
        storage.upload_file(paths.t1_copc, StorageKeys.copc_t1(project_id))
        storage.upload_file(paths.t2_aligned_copc, StorageKeys.copc_t2_aligned(project_id))

    def _wait_for_registration_decision(self) -> None:
        deadline = monotonic() + settings.registration_decision_timeout_seconds
        publish_event(
            self.job_id,
            {
                "type": "registration_decision_required",
                "job_id": self.job_id,
                "timeout_seconds": settings.registration_decision_timeout_seconds,
            },
        )
        while True:
            with SessionLocal() as db:
                job = self._get_job(db)
                if job.registration_decision == "continue":
                    publish_event(
                        self.job_id,
                        {"type": "registration_decision", "job_id": self.job_id, "decision": "continue"},
                    )
                    return
                if job.registration_decision == "abort":
                    raise ProcessingError("registration quality rejected by user")
            if monotonic() >= deadline:
                raise ProcessingError("registration quality decision timed out")
            sleep(settings.registration_decision_poll_seconds)

    def _set_status(self, status: str, progress: int) -> None:
        with SessionLocal() as db:
            job = self._get_job(db)
            project = job.project
            job.status = status
            job.progress = progress
            project.status = status
            db.commit()
        publish_event(
            self.job_id,
            {"type": "job_progress", "job_id": self.job_id, "progress": progress, "status": status},
        )

    def _fail(self, message: str) -> None:
        with SessionLocal() as db:
            job = db.get(Job, self.job_id)
            if job is not None:
                job.status = "FAILED"
                job.progress = job.progress or 0
                job.failure_message = message
                job.completed_at = datetime.now(timezone.utc)
                job.project.status = "FAILED"
                db.commit()
        publish_event(self.job_id, {"type": "job_failed", "job_id": self.job_id, "message": message})

    def _get_job(self, db: Session) -> Job:
        job = db.get(Job, self.job_id)
        if job is None:
            raise ProcessingError(f"job not found: {self.job_id}")
        return job
