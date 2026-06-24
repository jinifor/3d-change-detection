from app.processing.pipeline import ChangeDetectionPipeline


def process_job(job_id: str) -> None:
    ChangeDetectionPipeline(job_id).run()
