"""ApplicationRecord dataclass tracking each job application sent."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from shared.models.exceptions import DeserializationError

logger = logging.getLogger(__name__)

AppStatusType = Literal["sent", "replied", "interview_scheduled", "rejected", "ghosted"]
_VALID_STATUSES = {"sent", "replied", "interview_scheduled", "rejected", "ghosted"}


@dataclass
class ApplicationRecord:
    """Mutable record tracking a single job application.

    Args:
        application_id: Unique UUID for this application.
        user_id: Identifier of the applicant.
        job_id: UUID of the job applied to.
        resume_variant_id: UUID of the resume variant used.
        cover_letter_id: Optional UUID of the cover letter used.
        status: Current application status.
        sent_at: Timestamp when the application was sent.
        last_activity_at: Timestamp of the most recent activity.
        thread_id: Email thread identifier for tracking replies.
        email_subject: Subject line of the application email.
        reply_count: Number of replies received.
        notes: Optional free-text notes.

    Raises:
        DeserializationError: If from_dict() receives invalid data.
    """

    application_id: uuid.UUID
    user_id: str
    job_id: uuid.UUID
    resume_variant_id: uuid.UUID
    cover_letter_id: Optional[uuid.UUID] = None
    status: AppStatusType = "sent"
    sent_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity_at: Optional[datetime] = None
    thread_id: Optional[str] = None
    email_subject: Optional[str] = None
    reply_count: int = 0
    notes: Optional[str] = None

    def get_days_since_sent(self) -> int:
        """Calculate the number of days since the application was sent.

        Returns:
            Integer number of days from sent_at to now (UTC).
        """
        now = datetime.now(timezone.utc)
        sent = self.sent_at
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=timezone.utc)
        return (now - sent).days

    def validate(self) -> None:
        """Validate field constraints.

        Raises:
            ValueError: If any field violates its constraint.
        """
        for field_name, value in (
            ("application_id", self.application_id),
            ("job_id", self.job_id),
            ("resume_variant_id", self.resume_variant_id),
        ):
            if not isinstance(value, uuid.UUID):
                raise ValueError(f"{field_name} must be a UUID, got {type(value)}")
        if not self.user_id:
            raise ValueError("user_id must be a non-empty string")
        if self.status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {_VALID_STATUSES}, got {self.status!r}"
            )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields; UUIDs and datetimes as strings.
        """
        sent_at = self.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        return {
            "application_id": str(self.application_id),
            "user_id": self.user_id,
            "job_id": str(self.job_id),
            "resume_variant_id": str(self.resume_variant_id),
            "cover_letter_id": str(self.cover_letter_id) if self.cover_letter_id else None,
            "status": self.status,
            "sent_at": sent_at.isoformat(),
            "last_activity_at": (
                self.last_activity_at.isoformat() if self.last_activity_at else None
            ),
            "thread_id": self.thread_id,
            "email_subject": self.email_subject,
            "reply_count": self.reply_count,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ApplicationRecord":
        """Deserialize from a dictionary.

        Args:
            data: Dictionary containing application record fields.

        Returns:
            A new ApplicationRecord instance.

        Raises:
            DeserializationError: If required fields are missing or invalid.
        """
        required = ("application_id", "user_id", "job_id", "resume_variant_id")
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

        def _to_optional_uuid(key: str) -> Optional[uuid.UUID]:
            val = data.get(key)
            if val is None:
                return None
            try:
                return uuid.UUID(str(val))
            except (ValueError, AttributeError) as exc:
                raise DeserializationError(
                    f"Invalid {key}: {val!r}", {"error": str(exc)}
                ) from exc

        def _parse_dt(val: Optional[str]) -> Optional[datetime]:
            if val is None:
                return None
            return datetime.fromisoformat(val)

        try:
            sent_raw = data.get("sent_at")
            sent_at = _parse_dt(sent_raw) if sent_raw else datetime.now(timezone.utc)
            return cls(
                application_id=_to_uuid("application_id"),
                user_id=data["user_id"],
                job_id=_to_uuid("job_id"),
                resume_variant_id=_to_uuid("resume_variant_id"),
                cover_letter_id=_to_optional_uuid("cover_letter_id"),
                status=data.get("status", "sent"),
                sent_at=sent_at,
                last_activity_at=_parse_dt(data.get("last_activity_at")),
                thread_id=data.get("thread_id"),
                email_subject=data.get("email_subject"),
                reply_count=data.get("reply_count", 0),
                notes=data.get("notes"),
            )
        except DeserializationError:
            raise
        except Exception as exc:
            raise DeserializationError(
                f"Failed to construct ApplicationRecord: {exc}", {"data": data}
            ) from exc
