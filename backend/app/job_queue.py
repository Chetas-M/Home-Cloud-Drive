"""
Home Cloud Drive - Background Job Queue
=======================================
A lightweight, durable background job queue built on asyncio.

Design goals:
- Zero extra dependencies for local/simple deployments.
- Persistent job state written to a JSON store so jobs survive
  process restarts (configurable; in-memory only when disabled).
- Per-job-type configurable retry policies with exponential back-off.
- Observable job status and per-type failure counters.
- Thread-safe helper to enqueue from sync or async code.

Job types defined here
----------------------
``thumbnail``       – Generate an image thumbnail after upload.
``search_index``    – Extract and store searchable text content.
``email``           – Send a transactional email via Resend.
``trash_cleanup``   – Purge files that have expired from the trash.
``log_cleanup``     – Prune old activity log rows.

Each job type maps to a registered *handler* function.  Handlers are
async callables that receive a single ``dict`` payload and return
``None`` on success or raise an exception on failure.  Transient
failures are retried automatically; permanent failures are recorded
in ``job_failure_counters``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    RETRYING = "retrying"


# ---------------------------------------------------------------------------
# Job record
# ---------------------------------------------------------------------------


@dataclass
class Job:
    id: str
    job_type: str
    payload: Dict[str, Any]
    status: str = JobStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    run_after: float = field(default_factory=time.time)  # Unix timestamp
    error: Optional[str] = None
    result: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

# Default back-off: 30 s, 5 min, 30 min
_DEFAULT_BACKOFF_SECONDS = [30, 300, 1800]

JOB_RETRY_POLICY: Dict[str, list] = {
    "thumbnail":    [10, 60, 300],
    "search_index": [15, 120, 600],
    "email":        [60, 300, 1800],
    "trash_cleanup": [],          # no retries for maintenance jobs
    "log_cleanup":   [],
}


def _backoff_seconds(job_type: str, attempt: int) -> float:
    """Return seconds to wait before the next attempt."""
    schedule = JOB_RETRY_POLICY.get(job_type, _DEFAULT_BACKOFF_SECONDS)
    if not schedule:
        return 0.0
    idx = min(max(0, attempt - 1), len(schedule) - 1)
    return float(schedule[idx])


# ---------------------------------------------------------------------------
# Failure counters (in-memory; reset on restart)
# ---------------------------------------------------------------------------

job_failure_counters: Dict[str, int] = {}   # job_type -> total failure count
job_success_counters: Dict[str, int] = {}   # job_type -> total success count

# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------

HandlerFn = Callable[[Dict[str, Any]], Awaitable[None]]
_handlers: Dict[str, HandlerFn] = {}


def register_handler(job_type: str, fn: HandlerFn) -> None:
    """Register an async handler for a job type."""
    _handlers[job_type] = fn


# ---------------------------------------------------------------------------
# Persistent store (JSON file, optional)
# ---------------------------------------------------------------------------

_store_path: Optional[str] = None
_store_lock = asyncio.Lock()


def configure_store(path: str) -> None:
    """Call once at startup to enable persistence."""
    global _store_path
    _store_path = path
    os.makedirs(os.path.dirname(path), exist_ok=True)


async def _load_pending_jobs() -> list[Job]:
    """Load jobs that were not finished when the process last exited."""
    if _store_path is None or not os.path.exists(_store_path):
        return []
    try:
        async with _store_lock:
            with open(_store_path, "r", encoding="utf-8") as fh:
                raw: list[dict] = json.load(fh)
        jobs = []
        for d in raw:
            try:
                j = Job.from_dict(d)
                # Treat anything that was RUNNING as RETRYING (process crashed)
                if j.status == JobStatus.RUNNING:
                    j.status = JobStatus.RETRYING
                    j.run_after = time.time()
                if j.status in (JobStatus.PENDING, JobStatus.RETRYING):
                    jobs.append(j)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("job_queue: skipping corrupt job record: %s", exc)
        logger.info("job_queue: reloaded %d pending jobs from %s", len(jobs), _store_path)
        return jobs
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("job_queue: could not load job store: %s", exc)
        return []


async def _persist_jobs(jobs: list[Job]) -> None:
    if _store_path is None:
        return
    try:
        async with _store_lock:
            tmp = _store_path + ".tmp"
            data = [j.to_dict() for j in jobs if j.status in (JobStatus.PENDING, JobStatus.RETRYING, JobStatus.RUNNING)]
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            os.replace(tmp, _store_path)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("job_queue: failed to persist jobs: %s", exc)


# ---------------------------------------------------------------------------
# The Queue
# ---------------------------------------------------------------------------


class BackgroundJobQueue:
    """
    Asyncio-native background job queue.

    Usage::

        queue = BackgroundJobQueue(concurrency=4)
        await queue.start()
        job_id = await queue.enqueue("thumbnail", {"file_id": "...", ...})
        ...
        await queue.shutdown()
    """

    def __init__(self, concurrency: int = 3) -> None:
        self._concurrency = concurrency
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: Dict[str, Job] = {}         # id -> Job
        self._jobs_lock = asyncio.Lock()
        self._workers: list[asyncio.Task] = []
        self._running = False

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Start worker tasks.  Call once at application startup."""
        if self._running:
            return
        self._running = True

        # Reload persisted jobs
        old_jobs = await _load_pending_jobs()
        for job in old_jobs:
            async with self._jobs_lock:
                self._jobs[job.id] = job
            await self._queue.put(job)

        for i in range(self._concurrency):
            task = asyncio.create_task(self._worker(i), name=f"job_worker_{i}")
            self._workers.append(task)

        logger.info(
            "job_queue: started with %d worker(s); %d reloaded job(s)",
            self._concurrency,
            len(old_jobs),
        )

    async def shutdown(self, timeout: float = 10.0) -> None:
        """Signal workers to stop and wait for them to finish."""
        self._running = False
        # Wake workers so they can check the flag
        for _ in self._workers:
            try:
                self._queue.put_nowait(_SENTINEL_JOB)
            except asyncio.QueueFull:
                pass
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            for t in self._workers:
                t.cancel()
        logger.info("job_queue: shut down")

    async def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
        run_after: Optional[float] = None,
    ) -> str:
        """Enqueue a new job.  Returns the job id."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=job_type,
            payload=payload,
            max_attempts=max(1, max_attempts),
            run_after=run_after or time.time(),
        )
        async with self._jobs_lock:
            self._jobs[job.id] = job
        await self._persist_snapshot()
        await self._queue.put(job)
        logger.debug("job_queue: enqueued %s[%s]", job_type, job.id)
        return job.id

    async def get_status(self, job_id: str) -> Optional[dict]:
        """Return a JSON-serialisable status dict for the job, or None."""
        async with self._jobs_lock:
            job = self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "id": job.id,
            "job_type": job.job_type,
            "status": job.status,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "error": job.error,
            "result": job.result,
            "created_at": datetime.fromtimestamp(job.created_at, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(job.updated_at, tz=timezone.utc).isoformat(),
        }

    async def stats(self) -> dict:
        """Return aggregate queue statistics."""
        counts: Dict[str, int] = {}
        async with self._jobs_lock:
            jobs = list(self._jobs.values())
        for job in jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        return {
            "queue_size": self._queue.qsize(),
            "total_tracked": len(jobs),
            "by_status": counts,
            "failures_by_type": dict(job_failure_counters),
            "successes_by_type": dict(job_success_counters),
        }

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    async def _worker(self, worker_id: int) -> None:
        logger.debug("job_queue: worker %d started", worker_id)
        while self._running:
            try:
                job: Job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if job is _SENTINEL_JOB:
                self._queue.task_done()
                break

            # Respect run_after (simple delay)
            delay = job.run_after - time.time()
            if delay > 0:
                await asyncio.sleep(delay)

            await self._execute(job, worker_id)
            self._queue.task_done()

        logger.debug("job_queue: worker %d stopped", worker_id)

    async def _execute(self, job: Job, worker_id: int) -> None:
        handler = _handlers.get(job.job_type)
        if handler is None:
            logger.error(
                "job_queue: no handler registered for job type '%s' (job %s)",
                job.job_type, job.id,
            )
            async with self._jobs_lock:
                job.status = JobStatus.FAILED
                job.error = f"No handler for job type '{job.job_type}'"
                job.updated_at = time.time()
            job_failure_counters[job.job_type] = job_failure_counters.get(job.job_type, 0) + 1
            await self._persist_snapshot()
            return

        async with self._jobs_lock:
            job.status = JobStatus.RUNNING
            job.attempts += 1
            job.updated_at = time.time()
        await self._persist_snapshot()

        try:
            await handler(job.payload)
            async with self._jobs_lock:
                job.status = JobStatus.DONE
                job.error = None
                job.updated_at = time.time()
            job_success_counters[job.job_type] = job_success_counters.get(job.job_type, 0) + 1
            logger.debug(
                "job_queue: worker %d completed %s[%s] (attempt %d)",
                worker_id, job.job_type, job.id, job.attempts,
            )
        except Exception as exc:  # pylint: disable=broad-except
            async with self._jobs_lock:
                job.error = str(exc)
                job.updated_at = time.time()

            if job.attempts < job.max_attempts:
                backoff = _backoff_seconds(job.job_type, job.attempts)
                async with self._jobs_lock:
                    job.status = JobStatus.RETRYING
                    job.run_after = time.time() + backoff
                logger.warning(
                    "job_queue: %s[%s] failed (attempt %d/%d), retrying in %.0fs: %s",
                    job.job_type, job.id, job.attempts, job.max_attempts, backoff, exc,
                )
                await self._queue.put(job)
            else:
                async with self._jobs_lock:
                    job.status = JobStatus.FAILED
                job_failure_counters[job.job_type] = job_failure_counters.get(job.job_type, 0) + 1
                logger.error(
                    "job_queue: %s[%s] permanently failed after %d attempt(s): %s",
                    job.job_type, job.id, job.attempts, exc,
                )

        await self._persist_snapshot()

    async def _persist_snapshot(self) -> None:
        async with self._jobs_lock:
            jobs = list(self._jobs.values())
        await _persist_jobs(jobs)


# ---------------------------------------------------------------------------
# Sentinel (used to wake workers during shutdown)
# ---------------------------------------------------------------------------

_SENTINEL_JOB = Job(id="__sentinel__", job_type="__sentinel__", payload={})

# ---------------------------------------------------------------------------
# Module-level singleton (configured in main.py)
# ---------------------------------------------------------------------------

job_queue: BackgroundJobQueue = BackgroundJobQueue(concurrency=3)
