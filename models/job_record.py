"""JobRecord dataclass representing a single scraped job listing."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from shared.models.exceptions import DeserializationError

logger = logging.getLogger(__name__)

SourceType = Literal["linkedin", "naukri", "indeed"]
RemoteType = Literal["onsite", "hybrid", "remote"]
JobType = Literal["fulltime", "parttime", "contract", "internship"]
StatusType = Literal["raw", "reviewed", "applied", "closed"]
EmailTrustType = Literal["unknown", "verified", "low"]

_VALID_SOURCES = {"linkedin", "naukri", "indeed"}
_VALID_REMOTE_TYPES = {"onsite", "hybrid", "remote", None}
_VALID_JOB_TYPES = {"fulltime", "parttime", "contract", "internship"}
_VALID_STATUSES = {"raw", "reviewed", "applied", "closed"}
_VALID_EMAIL_TRUST = {"unknown", "verified", "low"}


@dataclass(frozen=True)
class JobRecord:
    """Immutable representation of a scraped job listing.

    Args:
        job_id: Unique UUID for this job record.
        source: Platform the job was scraped from.
        external_id: ID assigned by the source platform.
        title: Job title.
        company_name: Name of the hiring company.
        company_domain: Company website domain.
        location: Job location string.
        remote_type: Work arrangement type.
        salary_min: Minimum salary offered.
        salary_max: Maximum salary offered.
        experience_min: Minimum years of experience required.
        experience_max: Maximum years of experience required.
        description: Full job description text.
        skills_required: List of required skill strings.
        job_type: Employment type.
        apply_email: Email address to send applications to.
        email_trust: Trust level of the apply_email address.
        apply_url: Direct application URL.
        posted_at: When the job was posted.
        scraped_at: When the job was scraped.
        last_seen_at: When the job was last observed active.
        status: Current processing status of this record.

    Raises:
        DeserializationError: If from_dict() receives invalid data.
    """

    job_id: uuid.UUID
    source: SourceType
    external_id: str
    title: str
    company_name: str
    company_domain: Optional[str]
    location: Optional[str]
    remote_type: Optional[RemoteType]
    salary_min: Optional[float]
    salary_max: Optional[float]
    experience_min: Optional[int]
    experience_max: Optional[int]
    description: str
    skills_required: list = field(default_factory=list)
    job_type: JobType = "fulltime"
    apply_email: Optional[str] = None
    email_trust: EmailTrustType = "unknown"
    apply_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    status: StatusType = "raw"

    def validate(self) -> None:
        """Validate field constraints.

        Raises:
            ValueError: If any field violates its constraint.
        """
        if not isinstance(self.job_id, uuid.UUID):
            raise ValueError(f"job_id must be a UUID, got {type(self.job_id)}")
        if self.source not in _VALID_SOURCES:
            raise ValueError(f"source must be one of {_VALID_SOURCES}, got {self.source!r}")
        if self.remote_type not in _VALID_REMOTE_TYPES:
            raise ValueError(
                f"remote_type must be one of {_VALID_REMOTE_TYPES}, got {self.remote_type!r}"
            )
        if self.job_type not in _VALID_JOB_TYPES:
            raise ValueError(
                f"job_type must be one of {_VALID_JOB_TYPES}, got {self.job_type!r}"
            )
        if self.status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {_VALID_STATUSES}, got {self.status!r}"
            )
        if self.email_trust not in _VALID_EMAIL_TRUST:
            raise ValueError(
                f"email_trust must be one of {_VALID_EMAIL_TRUST}, got {self.email_trust!r}"
            )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields; UUIDs and datetimes as strings.
        """
        return {
            "job_id": str(self.job_id),
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "location": self.location,
            "remote_type": self.remote_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "experience_min": self.experience_min,
            "experience_max": self.experience_max,
            "description": self.description,
            "skills_required": list(self.skills_required),
            "job_type": self.job_type,
            "apply_email": self.apply_email,
            "email_trust": self.email_trust,
            "apply_url": self.apply_url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobRecord":
        """Deserialize from a dictionary.

        Args:
            data: Dictionary containing job record fields.

        Returns:
            A new JobRecord instance.

        Raises:
            DeserializationError: If required fields are missing or invalid.
        """
        required = ("job_id", "source", "external_id", "title", "company_name", "description")
        missing = [k for k in required if k not in data or data[k] is None]
        if missing:
            raise DeserializationError(
                f"Missing required fields: {missing}", {"data": data}
            )
        try:
            job_id = uuid.UUID(str(data["job_id"]))
        except (ValueError, AttributeError) as exc:
            raise DeserializationError(
                f"Invalid job_id: {data.get('job_id')!r}", {"error": str(exc)}
            ) from exc

        if data["source"] not in _VALID_SOURCES:
            raise DeserializationError(
                f"Invalid source: {data['source']!r}",
                {"valid": list(_VALID_SOURCES)},
            )

        def _parse_dt(val: Optional[str]) -> Optional[datetime]:
            if val is None:
                return None
            return datetime.fromisoformat(val)

        try:
            return cls(
                job_id=job_id,
                source=data["source"],
                external_id=data["external_id"],
                title=data["title"],
                company_name=data["company_name"],
                company_domain=data.get("company_domain"),
                location=data.get("location"),
                remote_type=data.get("remote_type"),
                salary_min=data.get("salary_min"),
                salary_max=data.get("salary_max"),
                experience_min=data.get("experience_min"),
                experience_max=data.get("experience_max"),
                description=data["description"],
                skills_required=list(data.get("skills_required") or []),
                job_type=data.get("job_type", "fulltime"),
                apply_email=data.get("apply_email"),
                email_trust=data.get("email_trust", "unknown"),
                apply_url=data.get("apply_url"),
                posted_at=_parse_dt(data.get("posted_at")),
                scraped_at=_parse_dt(data.get("scraped_at")),
                last_seen_at=_parse_dt(data.get("last_seen_at")),
                status=data.get("status", "raw"),
            )
        except Exception as exc:
            raise DeserializationError(
                f"Failed to construct JobRecord: {exc}", {"data": data}
            ) from exc
