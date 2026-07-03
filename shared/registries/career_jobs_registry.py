"""JSON-file-backed implementation of CareerJobsRegistryBase."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from shared.models.career_job_record import CareerJobRecord
from shared.registries.base import CareerJobsRegistryBase

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _acquire_lock(fp) -> None:
    try:
        import fcntl
        fcntl.flock(fp, fcntl.LOCK_EX)
    except ImportError:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)


def _release_lock(fp) -> None:
    try:
        import fcntl
        fcntl.flock(fp, fcntl.LOCK_UN)
    except ImportError:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)


def _read_sync(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fp:
        _acquire_lock(fp)
        try:
            content = fp.read()
        finally:
            _release_lock(fp)
    return json.loads(content) if content.strip() else []


def _write_sync(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(path.parent), delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(records, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, str(path))


def _dedup_key(r: dict) -> str:
    return f"{r.get('company_id')}:{r.get('url_hash')}"


class CareerJobsRegistry(CareerJobsRegistryBase):
    """JSON-file-backed registry for CareerJobRecord objects.

    Stores all records in a single JSON file. Dedup key is
    ``(company_id, url_hash)``. Suitable for Phase 0/alpha volumes.

    Args:
        file_path: Path to the JSON storage file.
    """

    def __init__(self, file_path: str = "registries/career_jobs.json") -> None:
        self._path = Path(file_path)
        self._lock = asyncio.Lock()

    async def _read(self) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _read_sync, self._path)

    async def _write(self, records: List[dict]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _write_sync, self._path, records)

    async def save(self, job: CareerJobRecord) -> None:
        """Persist a single career job, upserting on (company_id, url_hash).

        Args:
            job: CareerJobRecord to save.
        """
        async with self._lock:
            records = await self._read()
            index = {_dedup_key(r): r for r in records}
            key = f"{job.company_id}:{job.url_hash}"
            index[key] = job.to_dict()
            await self._write(list(index.values()))
        logger.debug("Saved career job %s", job.url_hash)

    async def save_many(self, jobs: List[CareerJobRecord]) -> None:
        """Persist a list of career jobs, upserting on (company_id, url_hash).

        Args:
            jobs: List of CareerJobRecord instances to save.
        """
        async with self._lock:
            records = await self._read()
            index = {_dedup_key(r): r for r in records}
            for j in jobs:
                index[f"{j.company_id}:{j.url_hash}"] = j.to_dict()
            await self._write(list(index.values()))
        logger.debug("Saved %d career jobs", len(jobs))

    async def get(self, career_job_id: uuid.UUID) -> CareerJobRecord:
        """Retrieve a career job by UUID.

        Args:
            career_job_id: UUID of the career job.

        Returns:
            Matching CareerJobRecord.

        Raises:
            KeyError: If no record with that ID exists.
        """
        target = str(career_job_id)
        records = await self._read()
        for r in records:
            if r.get("career_job_id") == target:
                return CareerJobRecord.from_dict(r)
        raise KeyError(f"CareerJob not found: {career_job_id}")

    async def get_by_company(self, company_id: uuid.UUID) -> List[CareerJobRecord]:
        """Return all career jobs for a given company.

        Args:
            company_id: UUID of the parent company.

        Returns:
            List of CareerJobRecord instances.
        """
        target = str(company_id)
        records = await self._read()
        return [
            CareerJobRecord.from_dict(r)
            for r in records
            if r.get("company_id") == target
        ]

    async def get_active(self, limit: int = 100, offset: int = 0) -> List[CareerJobRecord]:
        """Return active career jobs ordered by last_seen_at DESC.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            List of active CareerJobRecord instances.
        """
        records = await self._read()
        active = [r for r in records if r.get("status") == "active"]
        active.sort(key=lambda r: r.get("last_seen_at", ""), reverse=True)
        return [CareerJobRecord.from_dict(r) for r in active[offset: offset + limit]]

    async def url_hash_exists(self, company_id: uuid.UUID, url_hash: str) -> bool:
        """Check whether (company_id, url_hash) already exists.

        Args:
            company_id: UUID of the parent company.
            url_hash: MD5 of the normalised job URL.

        Returns:
            True if the record exists, False otherwise.
        """
        key = f"{company_id}:{url_hash}"
        records = await self._read()
        return any(_dedup_key(r) == key for r in records)

    async def get_content_hash(
        self, company_id: uuid.UUID, url_hash: str
    ) -> Optional[str]:
        """Return the stored content_hash for a job, or None if not found.

        Args:
            company_id: UUID of the parent company.
            url_hash: MD5 of the normalised job URL.

        Returns:
            Stored content_hash string, or None.
        """
        key = f"{company_id}:{url_hash}"
        records = await self._read()
        for r in records:
            if _dedup_key(r) == key:
                return r.get("content_hash")
        return None

    async def update_last_seen(self, career_job_id: uuid.UUID) -> None:
        """Update last_seen_at to now for an unchanged job.

        Args:
            career_job_id: UUID of the career job.
        """
        target = str(career_job_id)
        now = datetime.now(timezone.utc).isoformat()
        async with self._lock:
            records = await self._read()
            for r in records:
                if r.get("career_job_id") == target:
                    r["last_seen_at"] = now
                    break
            await self._write(records)

    async def update_content(self, career_job_id: uuid.UUID, **fields) -> None:
        """Update content fields on a changed job record.

        Args:
            career_job_id: UUID of the career job.
            **fields: Field name/value pairs to update.
        """
        target = str(career_job_id)
        async with self._lock:
            records = await self._read()
            for r in records:
                if r.get("career_job_id") == target:
                    for k, v in fields.items():
                        r[k] = v
                    r["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                    break
            await self._write(records)

    async def mark_closed(self, career_job_id: uuid.UUID) -> None:
        """Mark a job as closed.

        Args:
            career_job_id: UUID of the career job.
        """
        await self.update_content(career_job_id, status="closed")

    async def mark_missing_jobs_closed(
        self, company_id: uuid.UUID, seen_url_hashes: Set[str]
    ) -> int:
        """Close all jobs for company_id whose url_hash was not seen.

        Args:
            company_id: UUID of the company just crawled.
            seen_url_hashes: url_hash values observed in the latest crawl.

        Returns:
            Number of records marked closed.
        """
        target_company = str(company_id)
        closed_count = 0
        async with self._lock:
            records = await self._read()
            for r in records:
                if (
                    r.get("company_id") == target_company
                    and r.get("status") == "active"
                    and r.get("url_hash") not in seen_url_hashes
                ):
                    r["status"] = "closed"
                    closed_count += 1
            if closed_count:
                await self._write(records)
        logger.debug(
            "Marked %d jobs closed for company %s", closed_count, company_id
        )
        return closed_count

    async def count(self) -> int:
        """Return total number of career job records.

        Returns:
            Integer count.
        """
        return len(await self._read())

    async def count_by_company(self, company_id: uuid.UUID) -> int:
        """Count career jobs for a specific company.

        Args:
            company_id: UUID of the company.

        Returns:
            Integer count.
        """
        target = str(company_id)
        records = await self._read()
        return sum(1 for r in records if r.get("company_id") == target)

    async def count_active_by_company(self) -> Dict[str, int]:
        """Return active job counts keyed by company_id string.

        Returns:
            Dictionary mapping company_id (str) to active job count.
        """
        records = await self._read()
        counts: Dict[str, int] = {}
        for r in records:
            if r.get("status") == "active":
                cid = r.get("company_id", "unknown")
                counts[cid] = counts.get(cid, 0) + 1
        return counts
