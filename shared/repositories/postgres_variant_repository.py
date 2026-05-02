"""PostgreSQL stub for VariantRegistry — Phase 0+ implementation placeholder."""

# TODO: import sqlalchemy ORM components when implementing Phase 0+
# from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from typing import List, Optional

from shared.models.variant_record import VariantRecord
from shared.registries.base import VariantRegistryBase


class PostgresVariantRepository(VariantRegistryBase):
    """PostgreSQL-backed variant repository (Phase 0+ stub).

    All methods raise NotImplementedError. Implement using SQLAlchemy
    async ORM in Phase 0+ once the database schema is migrated.
    """

    async def save(self, variant: VariantRecord) -> None:
        """Insert a new variant row into PostgreSQL.

        Args:
            variant: VariantRecord to persist.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.save — implement in Phase 0+"
        )

    async def get(self, variant_id: uuid.UUID) -> VariantRecord:
        """Retrieve a variant by primary key.

        Args:
            variant_id: UUID primary key.

        Returns:
            The matching VariantRecord.

        Raises:
            VariantNotFoundError: If no row with that variant_id exists.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.get — implement in Phase 0+"
        )

    async def get_for_job(self, job_id: uuid.UUID) -> List[VariantRecord]:
        """Return all variants for a given job_id.

        Args:
            job_id: UUID of the job.

        Returns:
            List of VariantRecord instances.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.get_for_job — implement in Phase 0+"
        )

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
        raise NotImplementedError(
            "PostgresVariantRepository.get_approved_for_job — implement in Phase 0+"
        )

    async def get_for_user(self, user_id: str) -> List[VariantRecord]:
        """Return all variants for a given user_id.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of VariantRecord instances.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.get_for_user — implement in Phase 0+"
        )

    async def get_pending_for_user(self, user_id: str) -> List[VariantRecord]:
        """Return variants with approval_status = 'pending' for a user.

        Args:
            user_id: Identifier of the user.

        Returns:
            List of pending VariantRecord instances.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.get_pending_for_user — implement in Phase 0+"
        )

    async def update_approval_status(self, variant_id: uuid.UUID, status: str) -> None:
        """UPDATE variants SET approval_status = :status WHERE variant_id = :id.

        Args:
            variant_id: UUID of the variant.
            status: New approval status.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.update_approval_status — implement in Phase 0+"
        )

    async def update_approval_token(self, variant_id: uuid.UUID, token: str) -> None:
        """UPDATE variants SET approval_token = :token WHERE variant_id = :id.

        Args:
            variant_id: UUID of the variant.
            token: 64-character hex approval token.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.update_approval_token — implement in Phase 0+"
        )

    async def exists(self, variant_id: uuid.UUID) -> bool:
        """Check existence via a COUNT query.

        Args:
            variant_id: UUID to check.

        Returns:
            True if a row exists.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.exists — implement in Phase 0+"
        )

    async def count_by_user(self, user_id: str) -> int:
        """Return COUNT(*) WHERE user_id = :user_id.

        Args:
            user_id: Identifier of the user.

        Returns:
            Integer count.
        """
        raise NotImplementedError(
            "PostgresVariantRepository.count_by_user — implement in Phase 0+"
        )
