"""JSON-backed implementation of ApplicationLogBase."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from shared.models.application_record import ApplicationRecord
from shared.models.exceptions import ApplicationNotFoundError, RegistryError
from shared.registries.base import ApplicationLogBase

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


def _acquire_lock(fp):
    try:
        import fcntl
        fcntl.flock(fp, fcntl.LOCK_EX)
    except ImportError:
        import msvcrt
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)


def _release_lock(fp):
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
    if not content.strip():
        return []
    return json.loads(content)


def _write_sync(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(path.parent), delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(records, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, str(path))


class ApplicationLog(ApplicationLogBase):
    """JSON-file-backed log for ApplicationRecord objects.

    Args:
        file_path: Path to the JSON storage file.
    """

    def __init__(self, file_path: str = "registries/applications.json") -> None:
        self._path = Path(file_path)

    async def _read(self) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _read_sync, self._path)

    async def _write(self, records: List[dict]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _write_sync, self._path, records)

    async def record_send(self, record: ApplicationRecord) -> None:
        """Log a new application send.

        Prevents duplicate applications for the same (user_id, job_id) pair.

        Args:
            record: ApplicationRecord to persist.

        Raises:
            RegistryError: If the user has already applied to this job.
        """
        if await self.has_user_applied_to_job(record.user_id, record.job_id):
            raise RegistryError(
                f"User {record.user_id!r} has already applied to job {record.job_id}",
                {"user_id": record.user_id, "job_id": str(record.job_id)},
            )
        records = await self._read()
        records.append(record.to_dict())
        await self._write(records)
        logger.debug(
            "Recorded application %s for user %s", record.application_id, record.user_id
        )

    async def get(self, application_id: uuid.UUID) -> ApplicationRecord:
        """Retrieve an application by ID.

        Args:
            application_id: UUID of the application.

        Returns:
            The matching ApplicationRecord.

        Raises:
            ApplicationNotFoundError: If no application with that ID exists.
        """
        target = str(application_id)
        for r in await self._read():
            if r.get("application_id") == target:
                return ApplicationRecord.from_dict(r)
        raise ApplicationNotFoundError(
            f"Application not found: {application_id}", {"application_id": target}
        )

    async def get_by_user(self, user_id: str) -> List[ApplicationRecord]:
        """Return all applications submitted by a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of ApplicationRecord instances.
        """
        return [
            ApplicationRecord.from_dict(r)
            for r in await self._read()
            if r.get("user_id") == user_id
        ]

    async def get_by_job(self, job_id: uuid.UUID) -> List[ApplicationRecord]:
        """Return all applications to a specific job.

        Args:
            job_id: UUID of the job.

        Returns:
            List of ApplicationRecord instances.
        """
        target = str(job_id)
        return [
            ApplicationRecord.from_dict(r)
            for r in await self._read()
            if r.get("job_id") == target
        ]

    async def has_user_applied_to_job(self, user_id: str, job_id: uuid.UUID) -> bool:
        """Check whether a user has already applied to a job.

        Args:
            user_id: Identifier of the user.
            job_id: UUID of the job.

        Returns:
            True if an application already exists for this user+job pair.
        """
        target = str(job_id)
        return any(
            r.get("user_id") == user_id and r.get("job_id") == target
            for r in await self._read()
        )

    async def get_applications_sent_today(self, user_id: str) -> List[ApplicationRecord]:
        """Return applications sent by a user in the last 24 hours.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of ApplicationRecord instances sent within the last 24 hours.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = []
        for r in await self._read():
            if r.get("user_id") != user_id:
                continue
            sent_raw = r.get("sent_at")
            if not sent_raw:
                continue
            sent = datetime.fromisoformat(sent_raw)
            if sent.tzinfo is None:
                sent = sent.replace(tzinfo=timezone.utc)
            if sent >= cutoff:
                result.append(ApplicationRecord.from_dict(r))
        return result

    async def update_status(self, application_id: uuid.UUID, new_status: str) -> None:
        """Update the status of an application.

        Args:
            application_id: UUID of the application.
            new_status: New status string.

        Raises:
            ApplicationNotFoundError: If the application does not exist.
        """
        target = str(application_id)
        records = await self._read()
        for r in records:
            if r.get("application_id") == target:
                r["status"] = new_status
                r["last_activity_at"] = datetime.now(timezone.utc).isoformat()
                await self._write(records)
                return
        raise ApplicationNotFoundError(
            f"Application not found: {application_id}", {"application_id": target}
        )

    async def update_reply_count(self, application_id: uuid.UUID, count: int) -> None:
        """Set the reply count for an application.

        Args:
            application_id: UUID of the application.
            count: New reply count value.

        Raises:
            ApplicationNotFoundError: If the application does not exist.
        """
        target = str(application_id)
        records = await self._read()
        for r in records:
            if r.get("application_id") == target:
                r["reply_count"] = count
                await self._write(records)
                return
        raise ApplicationNotFoundError(
            f"Application not found: {application_id}", {"application_id": target}
        )

    async def count_by_user(self, user_id: str) -> int:
        """Count applications submitted by a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            Integer count.
        """
        return sum(1 for r in await self._read() if r.get("user_id") == user_id)

    async def clear_old_records(self, days: int = 90) -> int:
        """Remove records older than the specified number of days.

        Args:
            days: Age threshold in days (default 90).

        Returns:
            Number of records removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        records = await self._read()
        kept = []
        for r in records:
            sent_raw = r.get("sent_at")
            if not sent_raw:
                kept.append(r)
                continue
            sent = datetime.fromisoformat(sent_raw)
            if sent.tzinfo is None:
                sent = sent.replace(tzinfo=timezone.utc)
            if sent >= cutoff:
                kept.append(r)
        removed = len(records) - len(kept)
        if removed:
            await self._write(kept)
        return removed
