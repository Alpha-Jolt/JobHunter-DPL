"""JSON-file-backed implementation of CompanyRegistryBase."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from shared.models.company_record import CompanyRecord
from shared.registries.base import CompanyRegistryBase

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


class CompanyRegistry(CompanyRegistryBase):
    """JSON-file-backed registry for CompanyRecord objects.

    Stores all records in a single JSON file. Suitable for Phase 0/alpha
    volumes (<10k companies). All I/O is dispatched to a thread pool to
    remain non-blocking. An asyncio.Lock serialises concurrent writes.

    Args:
        file_path: Path to the JSON storage file.
    """

    def __init__(self, file_path: str = "registries/companies.json") -> None:
        self._path = Path(file_path)
        self._lock = asyncio.Lock()

    async def _read(self) -> List[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _read_sync, self._path)

    async def _write(self, records: List[dict]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, _write_sync, self._path, records)

    async def save(self, company: CompanyRecord) -> None:
        """Persist a single company, upserting on apex_domain.

        Args:
            company: CompanyRecord to save.
        """
        async with self._lock:
            records = await self._read()
            index = {r["apex_domain"]: r for r in records}
            index[company.apex_domain] = company.to_dict()
            await self._write(list(index.values()))
        logger.debug("Saved company %s", company.apex_domain)

    async def save_many(self, companies: List[CompanyRecord]) -> None:
        """Persist a list of companies, upserting on apex_domain.

        Args:
            companies: List of CompanyRecord instances to save.
        """
        async with self._lock:
            records = await self._read()
            index = {r["apex_domain"]: r for r in records}
            for c in companies:
                existing = index.get(c.apex_domain)
                if existing:
                    # Merge: keep record with more populated fields
                    incoming = c.to_dict()
                    merged = _merge_company_dicts(existing, incoming)
                    index[c.apex_domain] = merged
                else:
                    index[c.apex_domain] = c.to_dict()
            await self._write(list(index.values()))
        logger.debug("Saved %d companies", len(companies))

    async def get(self, company_id: uuid.UUID) -> CompanyRecord:
        """Retrieve a company by UUID.

        Args:
            company_id: UUID of the company.

        Returns:
            Matching CompanyRecord.

        Raises:
            KeyError: If no company with that ID exists.
        """
        target = str(company_id)
        records = await self._read()
        for r in records:
            if r.get("company_id") == target:
                return CompanyRecord.from_dict(r)
        raise KeyError(f"Company not found: {company_id}")

    async def get_by_apex_domain(self, apex_domain: str) -> Optional[CompanyRecord]:
        """Return the company for the given apex domain, or None.

        Args:
            apex_domain: Normalised apex domain string.

        Returns:
            CompanyRecord if found, None otherwise.
        """
        records = await self._read()
        for r in records:
            if r.get("apex_domain") == apex_domain:
                return CompanyRecord.from_dict(r)
        return None

    async def get_by_crawl_status(self, status: str) -> List[CompanyRecord]:
        """Return all companies with the given crawl_status.

        Args:
            status: Target crawl_status string.

        Returns:
            List of matching CompanyRecord instances.
        """
        records = await self._read()
        return [
            CompanyRecord.from_dict(r)
            for r in records
            if r.get("crawl_status") == status
        ]

    async def get_pending_email_refresh(self, older_than_days: int = 30) -> List[CompanyRecord]:
        """Return enriched companies whose email data is stale.

        Args:
            older_than_days: Threshold in days.

        Returns:
            List of CompanyRecord instances due for email refresh.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        records = await self._read()
        result = []
        for r in records:
            if r.get("crawl_status") != "enriched":
                continue
            crawled_raw = r.get("email_last_crawled_at")
            if crawled_raw is None:
                result.append(CompanyRecord.from_dict(r))
                continue
            crawled_dt = datetime.fromisoformat(crawled_raw)
            if crawled_dt.tzinfo is None:
                crawled_dt = crawled_dt.replace(tzinfo=timezone.utc)
            if crawled_dt < cutoff:
                result.append(CompanyRecord.from_dict(r))
        return result

    async def apex_domain_exists(self, apex_domain: str) -> bool:
        """Check whether an apex domain is already registered.

        Args:
            apex_domain: Normalised apex domain string.

        Returns:
            True if the domain exists, False otherwise.
        """
        records = await self._read()
        return any(r.get("apex_domain") == apex_domain for r in records)

    async def get_known_domains_set(self) -> Set[str]:
        """Return a set of all known apex domains for in-memory queue dedup.

        Returns:
            Set of apex domain strings.
        """
        records = await self._read()
        return {r["apex_domain"] for r in records if r.get("apex_domain")}

    async def update_crawl_status(self, company_id: uuid.UUID, status: str) -> None:
        """Update the crawl_status of a company.

        Args:
            company_id: UUID of the company.
            status: New crawl_status value.
        """
        target = str(company_id)
        async with self._lock:
            records = await self._read()
            for r in records:
                if r.get("company_id") == target:
                    r["crawl_status"] = status
                    break
            await self._write(records)

    async def update_enrichment(self, company_id: uuid.UUID, **fields) -> None:
        """Partial-update enrichment fields on an existing company record.

        Only non-None values in fields are written; existing data is not
        overwritten with None.

        Args:
            company_id: UUID of the company to update.
            **fields: Field name/value pairs to update.
        """
        target = str(company_id)
        async with self._lock:
            records = await self._read()
            for r in records:
                if r.get("company_id") == target:
                    for k, v in fields.items():
                        if v is not None:
                            r[k] = v
                    break
            await self._write(records)

    async def count(self) -> int:
        """Return total number of stored companies.

        Returns:
            Integer count.
        """
        return len(await self._read())

    async def count_by_crawl_status(self) -> Dict[str, int]:
        """Return company counts grouped by crawl_status.

        Returns:
            Dictionary mapping status string to count.
        """
        records = await self._read()
        counts: Dict[str, int] = {}
        for r in records:
            s = r.get("crawl_status", "pending")
            counts[s] = counts.get(s, 0) + 1
        return counts

    async def count_by_ats_platform(self) -> Dict[str, int]:
        """Return company counts grouped by ats_platform.

        Returns:
            Dictionary mapping ats_platform string to count.
        """
        records = await self._read()
        counts: Dict[str, int] = {}
        for r in records:
            p = r.get("ats_platform", "none")
            counts[p] = counts.get(p, 0) + 1
        return counts


def _merge_company_dicts(existing: dict, incoming: dict) -> dict:
    """Merge two company dicts, keeping the one with more populated fields
    and combining array fields from both.

    Args:
        existing: Currently stored company dict.
        incoming: Newly discovered company dict.

    Returns:
        Merged company dict.
    """
    # Combine array fields
    for array_field in ("career_emails", "contact_emails", "subdomains"):
        combined = list(
            dict.fromkeys(
                (existing.get(array_field) or []) + (incoming.get(array_field) or [])
            )
        )
        existing[array_field] = combined

    # For scalar fields: use incoming value if existing is None/empty
    for key, value in incoming.items():
        if key in ("career_emails", "contact_emails", "subdomains"):
            continue  # already merged above
        if not existing.get(key) and value:
            existing[key] = value

    return existing
