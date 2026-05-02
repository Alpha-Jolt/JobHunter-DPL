"""VariantRecord dataclass representing an AI-generated resume variant."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from shared.models.exceptions import DeserializationError

logger = logging.getLogger(__name__)

ApprovalStatusType = Literal["pending", "approved", "rejected"]
_VALID_APPROVAL_STATUSES = {"pending", "approved", "rejected"}


@dataclass
class VariantRecord:
    """Mutable representation of an AI-generated resume variant.

    Args:
        variant_id: Unique UUID for this variant.
        user_id: Identifier of the user who owns this variant.
        job_id: UUID of the job this variant was generated for.
        master_resume_id: UUID of the source resume used.
        pdf_key: S3 key for the PDF version.
        docx_key: S3 key for the DOCX version.
        curated_json: AI-curated resume data structure.
        gaps_identified: Skills the user lacks but the job requires.
        approval_status: Current approval state.
        approval_token: 64-char hex token for email-based approval.
        approved_at: Timestamp when the variant was approved.
        user_feedback: Optional feedback from the user.
        created_at: Timestamp when the variant was created.
        prompt_version: Version string of the AI prompt used.

    Raises:
        DeserializationError: If from_dict() receives invalid data.
    """

    variant_id: uuid.UUID
    user_id: str
    job_id: uuid.UUID
    master_resume_id: uuid.UUID
    pdf_key: str
    docx_key: str
    curated_json: dict
    gaps_identified: list = field(default_factory=list)
    approval_status: ApprovalStatusType = "pending"
    approval_token: Optional[str] = None
    approved_at: Optional[datetime] = None
    user_feedback: Optional[str] = None
    created_at: Optional[datetime] = None
    prompt_version: str = ""

    def is_approved(self) -> bool:
        """Return True if this variant has been approved.

        Returns:
            True when approval_status is "approved".
        """
        return self.approval_status == "approved"

    def is_pending(self) -> bool:
        """Return True if this variant is awaiting approval.

        Returns:
            True when approval_status is "pending".
        """
        return self.approval_status == "pending"

    def validate(self) -> None:
        """Validate field constraints.

        Raises:
            ValueError: If any field violates its constraint.
        """
        for field_name, value in (
            ("variant_id", self.variant_id),
            ("job_id", self.job_id),
            ("master_resume_id", self.master_resume_id),
        ):
            if not isinstance(value, uuid.UUID):
                raise ValueError(f"{field_name} must be a UUID, got {type(value)}")
        if not self.user_id:
            raise ValueError("user_id must be a non-empty string")
        if self.approval_status not in _VALID_APPROVAL_STATUSES:
            raise ValueError(
                f"approval_status must be one of {_VALID_APPROVAL_STATUSES}, "
                f"got {self.approval_status!r}"
            )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields; UUIDs and datetimes as strings.
        """
        return {
            "variant_id": str(self.variant_id),
            "user_id": self.user_id,
            "job_id": str(self.job_id),
            "master_resume_id": str(self.master_resume_id),
            "pdf_key": self.pdf_key,
            "docx_key": self.docx_key,
            "curated_json": self.curated_json,
            "gaps_identified": list(self.gaps_identified),
            "approval_status": self.approval_status,
            "approval_token": self.approval_token,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "user_feedback": self.user_feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VariantRecord":
        """Deserialize from a dictionary.

        Args:
            data: Dictionary containing variant record fields.

        Returns:
            A new VariantRecord instance.

        Raises:
            DeserializationError: If required fields are missing or invalid.
        """
        required = ("variant_id", "user_id", "job_id", "master_resume_id")
        missing = [k for k in required if not data.get(k)]
        if missing:
            raise DeserializationError(
                f"Missing required fields: {missing}", {"data": data}
            )

        def _to_uuid(key: str) -> uuid.UUID:
            try:
                return uuid.UUID(str(data[key]))
            except (ValueError, AttributeError) as exc:
                raise DeserializationError(
                    f"Invalid {key}: {data.get(key)!r}", {"error": str(exc)}
                ) from exc

        def _parse_dt(val: Optional[str]) -> Optional[datetime]:
            if val is None:
                return None
            return datetime.fromisoformat(val)

        try:
            return cls(
                variant_id=_to_uuid("variant_id"),
                user_id=data["user_id"],
                job_id=_to_uuid("job_id"),
                master_resume_id=_to_uuid("master_resume_id"),
                pdf_key=data.get("pdf_key", ""),
                docx_key=data.get("docx_key", ""),
                curated_json=data.get("curated_json") or {},
                gaps_identified=list(data.get("gaps_identified") or []),
                approval_status=data.get("approval_status", "pending"),
                approval_token=data.get("approval_token"),
                approved_at=_parse_dt(data.get("approved_at")),
                user_feedback=data.get("user_feedback"),
                created_at=_parse_dt(data.get("created_at")),
                prompt_version=data.get("prompt_version", ""),
            )
        except DeserializationError:
            raise
        except Exception as exc:
            raise DeserializationError(
                f"Failed to construct VariantRecord: {exc}", {"data": data}
            ) from exc
