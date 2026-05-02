"""PostgreSQL stub for JobRegistry — Phase 0+ implementation placeholder."""

# TODO: import sqlalchemy ORM components when implementing Phase 0+
# from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from typing import List

from shared.models.job_record import JobRecord
from shared.registries.base import JobRegistryBase


class PostgresJobRepository(JobRegistryBase):
    """PostgreSQL-backed job repository (Phase 0+ stub).

    All methods raise NotImplementedError. Implement using SQLAlchemy
    async ORM in Phase 0+ once the database schema is migrated.
    """

    async def save(self, jobs: List[JobRecord]) -> None:
        """Persist a list of job records to PostgreSQL.

        Args:
            jobs: List of JobRecord instances to upsert.
        """
        raise NotImplementedError("PostgresJobRepository.save — implement in Phase 0+")

    async def get(self, job_id: uuid.UUID) -> JobRecord:
        """Retrieve a job by primary key from PostgreSQL.

        Args:
            job_id: UUID primary key.

        Returns:
            The matching JobRecord.

        Raises:
            JobNotFoundError: If no row with that job_id exists.
        """
        raise NotImplementedError("PostgresJobRepository.get — implement in Phase 0+")

    async def get_many(self, job_ids: List[uuid.UUID]) -> List[JobRecord]:
        """Retrieve multiple jobs by primary keys.

        Args:
            job_ids: List of UUIDs.

        Returns:
            List of matching JobRecord instances.
        """
        raise NotImplementedError("PostgresJobRepository.get_many — implement in Phase 0+")

    async def get_all_with_email(self) -> List[JobRecord]:
        """Return all rows where apply_email IS NOT NULL.

        Returns:
            List of JobRecord instances.
        """
        raise NotImplementedError(
            "PostgresJobRepository.get_all_with_email — implement in Phase 0+"
        )

    async def get_by_source(self, source: str) -> List[JobRecord]:
        """Return all rows matching the given source column value.

        Args:
            source: One of "linkedin", "naukri", "indeed".

        Returns:
            List of matching JobRecord instances.
        """
        raise NotImplementedError(
            "PostgresJobRepository.get_by_source — implement in Phase 0+"
        )

    async def get_by_status(self, status: str) -> List[JobRecord]:
        """Return all rows matching the given status column value.

        Args:
            status: One of "raw", "reviewed", "applied", "closed".

        Returns:
            List of matching JobRecord instances.
        """
        raise NotImplementedError(
            "PostgresJobRepository.get_by_status — implement in Phase 0+"
        )

    async def exists(self, job_id: uuid.UUID) -> bool:
        """Check existence via a COUNT query.

        Args:
            job_id: UUID to check.

        Returns:
            True if a row exists.
        """
        raise NotImplementedError("PostgresJobRepository.exists — implement in Phase 0+")

    async def count(self) -> int:
        """Return total row count from the jobs table.

        Returns:
            Integer count.
        """
        raise NotImplementedError("PostgresJobRepository.count — implement in Phase 0+")

    async def delete_by_source(self, source: str) -> int:
        """Delete all rows matching the given source and return the count.

        Args:
            source: One of "linkedin", "naukri", "indeed".

        Returns:
            Number of rows deleted.
        """
        raise NotImplementedError(
            "PostgresJobRepository.delete_by_source — implement in Phase 0+"
        )
