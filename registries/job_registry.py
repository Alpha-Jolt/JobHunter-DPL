"""JSON-backed implementation of JobRegistryBase."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from shared.models.exceptions import JobNotFoundError, RegistryError
from shared.models.job_record import JobRecord
from shared.registries.base import JobRegistryBase

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _acquire_lock(fp):
    """Acquire an exclusive file lock (cross-platform)."""
    try:
        import fcntl
        fcntl.flock(fp, fcntl.LOCK_EX)
    except ImportError:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)


def _release_lock(fp):
    """Release a file lock (cross-platform)."""
    try:
        import fcntl
        fcntl.flock(fp, fcntl.LOCK_UN)
    except ImportError:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)


def _read_sync(path: Path) -> List[dict]:
    """Read and parse the JSON file, returning a list of raw dicts."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fp:
        _acquire_lock(fp)
        try:
            content = fp.read()
        finally:
            _release_lock(fp)
    if not content.strip():
        return []
    return json.loads(content)


def _write_sync(path: Path, records: List[dict]) -> None:
    """Atomically write records to the JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dir_path = str(path.parent)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=dir_path, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(records, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, str(path))


class JobRegistry(JobRegistryBase):
    """JSON-file-backed registry for JobRecord objects.

    Stores all records in a single JSON file. Suitable for Phase 0 (<10k jobs).
    All I/O is dispatched to a thread pool to remain non-blocking.
    An asyncio.Lock serialises concurrent writes within the same event loop.

    Args:
        file_path: Path to the JSON storage file.
    """

    def __init__(self, file_path: str = "registries/jobs.json") -> None:
        self._path = Path(file_path)
        self._lock = asyncio.Lock()

    async def _read(self) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _read_sync, self._path)

    async def _write(self, records: List[dict]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _write_sync, self._path, records)

    async def save(self, jobs: List[JobRecord]) -> None:
        """Persist a list of job records, merging with existing data by job_id.

        Args:
            jobs: List of JobRecord instances to save.
        """
        async with self._lock:
            existing = await self._read()
            index = {r["job_id"]: r for r in existing}
            for job in jobs:
                index[str(job.job_id)] = job.to_dict()
            await self._write(list(index.values()))
        logger.debug("Saved %d jobs to %s", len(jobs), self._path)

    async def get(self, job_id: uuid.UUID) -> JobRecord:
        """Retrieve a single job by ID.

        Args:
            job_id: UUID of the job.

        Returns:
            The matching JobRecord.

        Raises:
            JobNotFoundError: If no job with that ID exists.
        """
        records = await self._read()
        target = str(job_id)
        for r in records:
            if r.get("job_id") == target:
                return JobRecord.from_dict(r)
        raise JobNotFoundError(f"Job not found: {job_id}", {"job_id": target})

    async def get_many(self, job_ids: List[uuid.UUID]) -> List[JobRecord]:
        """Retrieve multiple jobs by their IDs.

        Args:
            job_ids: List of UUIDs to retrieve.

        Returns:
            List of matching JobRecord instances.
        """
        targets = {str(jid) for jid in job_ids}
        records = await self._read()
        return [JobRecord.from_dict(r) for r in records if r.get("job_id") in targets]

    async def get_all_with_email(self) -> List[JobRecord]:
        """Return all jobs that have a non-null apply_email.

        Returns:
            List of JobRecord instances with apply_email set.
        """
        records = await self._read()
        return [JobRecord.from_dict(r) for r in records if r.get("apply_email")]

    async def get_by_source(self, source: str) -> List[JobRecord]:
        """Return all jobs from a specific source platform.

        Args:
            source: One of "linkedin", "naukri", "indeed".

        Returns:
            List of matching JobRecord instances.
        """
        records = await self._read()
        return [JobRecord.from_dict(r) for r in records if r.get("source") == source]

    async def get_by_status(self, status: str) -> List[JobRecord]:
        """Return all jobs with a specific status.

        Args:
            status: One of "raw", "reviewed", "applied", "closed".

        Returns:
            List of matching JobRecord instances.
        """
        records = await self._read()
        return [JobRecord.from_dict(r) for r in records if r.get("status") == status]

    async def exists(self, job_id: uuid.UUID) -> bool:
        """Check whether a job exists.

        Args:
            job_id: UUID to check.

        Returns:
            True if the job exists, False otherwise.
        """
        target = str(job_id)
        records = await self._read()
        return any(r.get("job_id") == target for r in records)

    async def count(self) -> int:
        """Return the total number of stored jobs.

        Returns:
            Integer count of all job records.
        """
        records = await self._read()
        return len(records)

    async def delete_by_source(self, source: str) -> int:
        """Delete all jobs from a specific source.

        Args:
            source: One of "linkedin", "naukri", "indeed".

        Returns:
            Number of records deleted.
        """
        records = await self._read()
        kept = [r for r in records if r.get("source") != source]
        deleted = len(records) - len(kept)
        if deleted:
            await self._write(kept)
        logger.debug("Deleted %d jobs from source '%s'", deleted, source)
        return deleted

    async def initialize_from_data(self, raw_jobs: List[dict]) -> None:
        """Load scraper output and save to registry.

        Args:
            raw_jobs: List of raw job dictionaries from scraper output.

        Raises:
            RegistryError: If any record fails to deserialize.
        """
        jobs = []
        for raw in raw_jobs:
            try:
                jobs.append(JobRecord.from_dict(raw))
            except Exception as exc:
                raise RegistryError(
                    f"Failed to deserialize job: {exc}", {"raw": raw}
                ) from exc
        await self.save(jobs)
