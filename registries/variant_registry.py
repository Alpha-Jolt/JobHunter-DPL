"""JSON-backed implementation of VariantRegistryBase."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from shared.models.exceptions import RegistryError, VariantNotFoundError
from shared.models.variant_record import VariantRecord
from shared.registries.base import VariantRegistryBase

logger = logging.getLogger(__name__)

MAX_VARIANTS_PER_SESSION = 50

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


class VariantRegistry(VariantRegistryBase):
    """JSON-file-backed registry for VariantRecord objects.

    Args:
        file_path: Path to the JSON storage file.
    """

    def __init__(self, file_path: str = "registries/variants.json") -> None:
        self._path = Path(file_path)

    async def _read(self) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _read_sync, self._path)

    async def _write(self, records: List[dict]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _write_sync, self._path, records)

    async def save(self, variant: VariantRecord) -> None:
        """Persist a new variant record.

        Enforces budget (MAX_VARIANTS_PER_SESSION) and deduplication
        per (user_id, job_id) pair.

        Args:
            variant: VariantRecord to save.

        Raises:
            RegistryError: If budget or deduplication constraints are violated.
        """
        records = await self._read()
        user_count = sum(1 for r in records if r.get("user_id") == variant.user_id)

        if user_count >= MAX_VARIANTS_PER_SESSION:
            raise RegistryError(
                f"User {variant.user_id!r} has reached the variant budget "
                f"({MAX_VARIANTS_PER_SESSION})",
                {"user_id": variant.user_id},
            )

        duplicate = any(
            r.get("user_id") == variant.user_id
            and r.get("job_id") == str(variant.job_id)
            for r in records
        )
        if duplicate:
            raise RegistryError(
                f"Variant already exists for user {variant.user_id!r} "
                f"and job {variant.job_id}",
                {"user_id": variant.user_id, "job_id": str(variant.job_id)},
            )

        if variant.created_at is None:
            variant.created_at = datetime.now(timezone.utc)

        records.append(variant.to_dict())
        await self._write(records)
        logger.debug("Saved variant %s for user %s", variant.variant_id, variant.user_id)

    async def get(self, variant_id: uuid.UUID) -> VariantRecord:
        """Retrieve a single variant by ID.

        Args:
            variant_id: UUID of the variant.

        Returns:
            The matching VariantRecord.

        Raises:
            VariantNotFoundError: If no variant with that ID exists.
        """
        target = str(variant_id)
        for r in await self._read():
            if r.get("variant_id") == target:
                return VariantRecord.from_dict(r)
        raise VariantNotFoundError(
            f"Variant not found: {variant_id}", {"variant_id": target}
        )

    async def get_for_job(self, job_id: uuid.UUID) -> List[VariantRecord]:
        """Return all variants for a specific job.

        Args:
            job_id: UUID of the job.

        Returns:
            List of VariantRecord instances.
        """
        target = str(job_id)
        return [
            VariantRecord.from_dict(r)
            for r in await self._read()
            if r.get("job_id") == target
        ]

    async def get_approved_for_job(
        self, job_id: uuid.UUID, user_id: str
    ) -> Optional[VariantRecord]:
        """Return the approved variant for a user+job pair.

        Args:
            job_id: UUID of the job.
            user_id: Identifier of the user.

        Returns:
            The approved VariantRecord, or None.
        """
        target_job = str(job_id)
        for r in await self._read():
            if (
                r.get("job_id") == target_job
                and r.get("user_id") == user_id
                and r.get("approval_status") == "approved"
            ):
                return VariantRecord.from_dict(r)
        return None

    async def get_for_user(self, user_id: str) -> List[VariantRecord]:
        """Return all variants generated by a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of VariantRecord instances.
        """
        return [
            VariantRecord.from_dict(r)
            for r in await self._read()
            if r.get("user_id") == user_id
        ]

    async def get_pending_for_user(self, user_id: str) -> List[VariantRecord]:
        """Return only pending variants for a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of pending VariantRecord instances.
        """
        return [
            VariantRecord.from_dict(r)
            for r in await self._read()
            if r.get("user_id") == user_id and r.get("approval_status") == "pending"
        ]

    async def update_approval_status(self, variant_id: uuid.UUID, status: str) -> None:
        """Update the approval status of a variant.

        Args:
            variant_id: UUID of the variant.
            status: New status — "approved", "rejected", or "pending".

        Raises:
            VariantNotFoundError: If the variant does not exist.
        """
        target = str(variant_id)
        records = await self._read()
        for r in records:
            if r.get("variant_id") == target:
                r["approval_status"] = status
                if status == "approved":
                    r["approved_at"] = datetime.now(timezone.utc).isoformat()
                await self._write(records)
                return
        raise VariantNotFoundError(
            f"Variant not found: {variant_id}", {"variant_id": target}
        )

    async def update_approval_token(self, variant_id: uuid.UUID, token: str) -> None:
        """Store the email approval token for a variant.

        Args:
            variant_id: UUID of the variant.
            token: 64-character hex approval token.

        Raises:
            VariantNotFoundError: If the variant does not exist.
        """
        target = str(variant_id)
        records = await self._read()
        for r in records:
            if r.get("variant_id") == target:
                r["approval_token"] = token
                await self._write(records)
                return
        raise VariantNotFoundError(
            f"Variant not found: {variant_id}", {"variant_id": target}
        )

    async def exists(self, variant_id: uuid.UUID) -> bool:
        """Check whether a variant exists.

        Args:
            variant_id: UUID to check.

        Returns:
            True if the variant exists, False otherwise.
        """
        target = str(variant_id)
        return any(r.get("variant_id") == target for r in await self._read())

    async def count_by_user(self, user_id: str) -> int:
        """Count variants generated by a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            Integer count.
        """
        return sum(1 for r in await self._read() if r.get("user_id") == user_id)
