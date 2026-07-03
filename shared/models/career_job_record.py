"""CareerJobRecord dataclass representing a job listing scraped from a company career page."""

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from shared.models.exceptions import DeserializationError

logger = logging.getLogger(__name__)

_VALID_REMOTE_TYPES = {"onsite", "hybrid", "remote", None}
_VALID_JOB_TYPES = {"fulltime", "parttime", "contract", "internship", "freelance", None}
_VALID_EXTRACTION_METHODS = {
    "ats_api", "json_ld", "sitemap", "api_reverse", "html_parse", "playwright_render",
}
_VALID_STATUSES = {"active", "closed", "raw"}

_TRACKING_PARAMS = frozenset([
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "referrer", "gh_src", "lever-source", "source",
])


def normalize_job_url(url: str) -> str:
    """Lowercase URL, strip known tracking parameters, strip trailing slash.

    Args:
        url: Raw job listing URL.

    Returns:
        Normalised URL string suitable for hashing.
    """
    parsed = urlparse(url.lower())
    filtered = {
        k: v for k, v in parse_qs(parsed.query).items()
        if k not in _TRACKING_PARAMS
    }
    clean = parsed._replace(query=urlencode(filtered, doseq=True))
    return urlunparse(clean).rstrip("/")


def compute_url_hash(normalized_url: str) -> str:
    """MD5 of a normalised job URL.

    Args:
        normalized_url: Output of normalize_job_url().

    Returns:
        32-character MD5 hex digest.
    """
    return hashlib.md5(normalized_url.encode("utf-8")).hexdigest()


def compute_content_hash(job_title: str, description: str) -> str:
    """MD5 of normalised job title + description for change detection.

    Args:
        job_title: Job title string.
        description: Full description text.

    Returns:
        32-character MD5 hex digest.
    """
    normalized = (job_title.strip().lower() + " " + (description or "").strip().lower())
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CareerJobRecord:
    """Immutable representation of a job listing scraped from a company career page.

    Args:
        career_job_id: Unique UUID for this record.
        company_id: UUID of the parent company in the companies table.
        job_title: Normalised job title.
        job_url: Direct URL to the job listing page.
        url_hash: MD5 of the normalised job URL — primary dedup key.
        content_hash: MD5 of title + description — change detection key.
        extraction_method: Which extractor produced this record.
        scraped_at: When first collected.
        last_seen_at: Updated on every crawl pass.
        description: Full job description text.
        skills_required: Parsed skill tags.
        location: Normalised location string.
        remote_type: Work arrangement type.
        salary_min: Minimum salary (INR).
        salary_max: Maximum salary (INR).
        experience_min: Minimum years of experience.
        experience_max: Maximum years of experience.
        job_type: Employment type.
        apply_email: Job-specific application email.
        apply_url: Direct apply URL.
        ats_platform: Inherited from the company record.
        posted_at: Posting date if extractable.
        status: Current status of this listing.
        source_channel: Always ``career_page``.

    Raises:
        DeserializationError: If from_dict() receives invalid data.
    """

    career_job_id: uuid.UUID
    company_id: uuid.UUID
    job_title: str
    job_url: str
    url_hash: str
    content_hash: str
    extraction_method: str
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None
    skills_required: List[str] = field(default_factory=list)
    location: Optional[str] = None
    remote_type: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    job_type: Optional[str] = None
    apply_email: Optional[str] = None
    apply_url: Optional[str] = None
    ats_platform: Optional[str] = None
    posted_at: Optional[datetime] = None
    status: str = "raw"
    source_channel: str = "career_page"

    def __post_init__(self) -> None:
        if self.remote_type not in _VALID_REMOTE_TYPES:
            raise ValueError(
                f"Invalid remote_type '{self.remote_type}'. "
                f"Must be one of {sorted(v for v in _VALID_REMOTE_TYPES if v)}."
            )
        if self.job_type not in _VALID_JOB_TYPES:
            raise ValueError(
                f"Invalid job_type '{self.job_type}'. "
                f"Must be one of {sorted(v for v in _VALID_JOB_TYPES if v)}."
            )
        if self.extraction_method not in _VALID_EXTRACTION_METHODS:
            raise ValueError(
                f"Invalid extraction_method '{self.extraction_method}'. "
                f"Must be one of {sorted(_VALID_EXTRACTION_METHODS)}."
            )
        if self.status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of {sorted(_VALID_STATUSES)}."
            )
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError(
                    f"salary_min ({self.salary_min}) cannot exceed salary_max ({self.salary_max})."
                )

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields serialised to primitive types.
        """
        return {
            "career_job_id": str(self.career_job_id),
            "company_id": str(self.company_id),
            "job_title": self.job_title,
            "job_url": self.job_url,
            "url_hash": self.url_hash,
            "content_hash": self.content_hash,
            "extraction_method": self.extraction_method,
            "scraped_at": self.scraped_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "description": self.description,
            "skills_required": list(self.skills_required),
            "location": self.location,
            "remote_type": self.remote_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "experience_min": self.experience_min,
            "experience_max": self.experience_max,
            "job_type": self.job_type,
            "apply_email": self.apply_email,
            "apply_url": self.apply_url,
            "ats_platform": self.ats_platform,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "status": self.status,
            "source_channel": self.source_channel,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CareerJobRecord":
        """Deserialise from a dictionary.

        Args:
            data: Dictionary previously produced by to_dict().

        Returns:
            CareerJobRecord instance.

        Raises:
            DeserializationError: If required fields are missing or malformed.
        """
        try:
            def _parse_dt(v: Optional[str]) -> Optional[datetime]:
                if not v:
                    return None
                dt = datetime.fromisoformat(v)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt

            return cls(
                career_job_id=uuid.UUID(data["career_job_id"]),
                company_id=uuid.UUID(data["company_id"]),
                job_title=data["job_title"],
                job_url=data["job_url"],
                url_hash=data["url_hash"],
                content_hash=data["content_hash"],
                extraction_method=data["extraction_method"],
                scraped_at=_parse_dt(data.get("scraped_at")) or datetime.now(timezone.utc),
                last_seen_at=_parse_dt(data.get("last_seen_at")) or datetime.now(timezone.utc),
                description=data.get("description"),
                skills_required=list(data.get("skills_required") or []),
                location=data.get("location"),
                remote_type=data.get("remote_type"),
                salary_min=data.get("salary_min"),
                salary_max=data.get("salary_max"),
                experience_min=data.get("experience_min"),
                experience_max=data.get("experience_max"),
                job_type=data.get("job_type"),
                apply_email=data.get("apply_email"),
                apply_url=data.get("apply_url"),
                ats_platform=data.get("ats_platform"),
                posted_at=_parse_dt(data.get("posted_at")),
                status=data.get("status", "raw"),
                source_channel=data.get("source_channel", "career_page"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise DeserializationError(
                f"Failed to deserialise CareerJobRecord: {exc}", {"data": data}
            ) from exc
