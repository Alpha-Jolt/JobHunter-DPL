"""PostgreSQL stub for ApplicationLog — Phase 0+ implementation placeholder."""

# TODO: import sqlalchemy ORM components when implementing Phase 0+
# from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from typing import List

from shared.models.application_record import ApplicationRecord
from shared.registries.base import ApplicationLogBase


class PostgresApplicationRepository(ApplicationLogBase):
    """PostgreSQL-backed application log (Phase 0+ stub).

    All methods raise NotImplementedError. Implement using SQLAlchemy
    async ORM in Phase 0+ once the database schema is migrated.
    """

    async def record_send(self, record: ApplicationRecord) -> None:
        """Insert a new application row into PostgreSQL.

        Args:
            record: ApplicationRecord to persist.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.record_send — implement in Phase 0+"
        )

    async def get(self, application_id: uuid.UUID) -> ApplicationRecord:
        """Retrieve an application by primary key.

        Args:
            application_id: UUID primary key.

        Returns:
            The matching ApplicationRecord.

        Raises:
            ApplicationNotFoundError: If no row with that application_id exists.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.get — implement in Phase 0+"
        )

    async def get_by_user(self, user_id: str) -> List[ApplicationRecord]:
        """Return all applications for a given user_id.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of ApplicationRecord instances.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.get_by_user — implement in Phase 0+"
        )

    async def get_by_job(self, job_id: uuid.UUID) -> List[ApplicationRecord]:
        """Return all applications for a given job_id.

        Args:
            job_id: UUID of the job.

        Returns:
            List of ApplicationRecord instances.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.get_by_job — implement in Phase 0+"
        )

    async def has_user_applied_to_job(self, user_id: str, job_id: uuid.UUID) -> bool:
        """Check existence via COUNT WHERE user_id = :uid AND job_id = :jid.

        Args:
            user_id: Identifier of the user.
            job_id: UUID of the job.

        Returns:
            True if a matching row exists.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.has_user_applied_to_job — implement in Phase 0+"
        )

    async def get_applications_sent_today(self, user_id: str) -> List[ApplicationRecord]:
        """Return rows WHERE user_id = :uid AND sent_at >= NOW() - INTERVAL '24 hours'.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of ApplicationRecord instances.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.get_applications_sent_today — implement in Phase 0+"
        )

    async def update_status(self, application_id: uuid.UUID, new_status: str) -> None:
        """UPDATE applications SET status = :status WHERE application_id = :id.

        Args:
            application_id: UUID of the application.
            new_status: New status string.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.update_status — implement in Phase 0+"
        )

    async def update_reply_count(self, application_id: uuid.UUID, count: int) -> None:
        """UPDATE applications SET reply_count = :count WHERE application_id = :id.

        Args:
            application_id: UUID of the application.
            count: New reply count value.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.update_reply_count — implement in Phase 0+"
        )

    async def count_by_user(self, user_id: str) -> int:
        """Return COUNT(*) WHERE user_id = :user_id.

        Args:
            user_id: Identifier of the user.

        Returns:
            Integer count.
        """
        raise NotImplementedError(
            "PostgresApplicationRepository.count_by_user — implement in Phase 0+"
        )
