from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.schemas.jobs import JobStatus, ToonifyStyle


@dataclass
class ToonifyJob:
    id: str
    image_id: str
    style: ToonifyStyle
    prompt: str | None
    status: JobStatus
    result_path: Path | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, ToonifyJob] = {}

    def create(self, image_id: str, style: ToonifyStyle, prompt: str | None = None) -> ToonifyJob:
        now = datetime.now(UTC)
        job = ToonifyJob(
            id=uuid4().hex,
            image_id=image_id,
            style=style,
            prompt=prompt,
            status=JobStatus.pending,
            result_path=None,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ToonifyJob | None:
        return self._jobs.get(job_id)

    def mark_processing(self, job_id: str) -> ToonifyJob | None:
        job = self.get(job_id)
        if job is None:
            return None

        job.status = JobStatus.processing
        job.updated_at = datetime.now(UTC)
        return job

    def mark_completed(self, job_id: str, result_path: Path) -> ToonifyJob | None:
        job = self.get(job_id)
        if job is None:
            return None

        job.status = JobStatus.completed
        job.result_path = result_path
        job.error_message = None
        job.updated_at = datetime.now(UTC)
        return job

    def mark_failed(self, job_id: str, error_message: str) -> ToonifyJob | None:
        job = self.get(job_id)
        if job is None:
            return None

        job.status = JobStatus.failed
        job.error_message = error_message
        job.updated_at = datetime.now(UTC)
        return job

    def clear(self) -> None:
        self._jobs.clear()


job_store = JobStore()
