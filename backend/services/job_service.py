"""In-memory analysis job manager for live processing-stage updates."""
from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class AnalysisJob:
    id: str
    mode: str
    status: str = "queued"
    stage: str = "uploading"
    percent: float = 0.0
    message: str = "Queued"
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    events: "queue.Queue[dict]" = field(default_factory=queue.Queue)

    def emit(self, event: dict) -> None:
        self.updated_at = time.time()
        self.events.put(event)


_jobs: Dict[str, AnalysisJob] = {}
_lock = threading.Lock()


PROCESSING_STAGES = [
    ("uploading", "Uploading"),
    ("processing", "Processing"),
    ("frame_extraction", "Frame extraction"),
    ("face_detection", "Face detection"),
    ("model_inference", "Model inference"),
    ("segment_detection", "Segment detection"),
    ("output_generation", "Output generation"),
    ("completed", "Completed"),
]


def create_job(mode: str) -> AnalysisJob:
    job = AnalysisJob(id=uuid.uuid4().hex, mode=mode)
    with _lock:
        _jobs[job.id] = job
    update_job(job.id, stage="uploading", percent=2, message="Upload received", status="queued")
    return job


def get_job(job_id: str) -> Optional[AnalysisJob]:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, *, stage: str, percent: float, message: str, status: str = "running") -> None:
    job = get_job(job_id)
    if not job:
        return
    job.status = status
    job.stage = stage
    job.percent = float(percent)
    job.message = message
    job.emit(
        {
            "type": "progress",
            "job_id": job_id,
            "status": job.status,
            "stage": stage,
            "percent": job.percent,
            "message": message,
        }
    )


def complete_job(job_id: str, result: dict) -> None:
    job = get_job(job_id)
    if not job:
        return
    job.status = "completed"
    job.stage = "completed"
    job.percent = 100.0
    job.message = "Completed"
    job.result = result
    job.emit({"type": "result", "job_id": job_id, "status": "completed", "result": result})


def fail_job(job_id: str, error: str) -> None:
    job = get_job(job_id)
    if not job:
        return
    job.status = "failed"
    job.error = error
    job.message = error
    job.emit({"type": "error", "job_id": job_id, "status": "failed", "error": error})


def start_background_job(app, job_id: str, runner: Callable[[], dict]) -> None:
    """Run a long analysis in a daemon thread under app context."""

    def _target() -> None:
        with app.app_context():
            try:
                update_job(job_id, stage="processing", percent=5, message="Starting analysis")
                result = runner()
                complete_job(job_id, result)
            except Exception as exc:  # noqa: BLE001 - error must be surfaced to UI
                fail_job(job_id, str(exc))

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()


def cleanup_old_jobs(max_age_seconds: int = 60 * 60) -> None:
    cutoff = time.time() - max_age_seconds
    with _lock:
        old = [jid for jid, job in _jobs.items() if job.updated_at < cutoff]
        for jid in old:
            _jobs.pop(jid, None)
