"""CompanyRecord dataclass representing a discovered and enriched company."""

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from shared.models.exceptions import DeserializationError

logger = logging.getLogger(__name__)

_VALID_EMAIL_TRUST = {"unverified", "low_trust"}
_VALID_ATS_PLATFORMS = {
    "greenhouse", "lever", "ashby", "workday", "smartrecruiters",
    "bamboohr", "teamtailor", "recruitee", "jazzhr", "workable",
    "custom", "none",
}
_VALID_CRAWL_STATUSES = {
    "pending", "enriched", "failed", "robots_blocked", "access_denied", "name_only",
}
_VALID_SOURCES = {
    "bootstrap_dataset", "govt_registry", "vc_portfolio", "github_org",
    "directory", "search_discovery", "recursive",
}

_LEGAL_SUFFIX_RE = re.compile(
    r"\b(pvt\.?\s*ltd\.?|private\s+limited|inc\.?|ltd\.?|llc|llp|corp\.?|"
    r"corporation|limited|technologies|technology|tech|solutions|solution|"
    r"systems|system|software|services|service|consulting|consultancy|"
    r"group|india|global)\b",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str:
    """Lowercase, strip legal suffixes, remove non-alphanumeric characters.

    Args:
        name: Raw company name string.

    Returns:
        Normalised name suitable for deduplication fingerprint.
    """
    lowered = name.lower()
    stripped = _LEGAL_SUFFIX_RE.sub("", lowered)
    return re.sub(r"[^a-z0-9]", "", stripped)


def build_dedup_fingerprint(normalized_name: str, apex_domain: str) -> str:
    """Build MD5-based deduplication fingerprint.

    Args:
        normalized_name: Output of normalize_company_name().
        apex_domain: Canonical apex domain string.

    Returns:
        32-character MD5 hex digest.
    """
    raw = (normalized_name + apex_domain).encode("utf-8")
    return hashlib.md5(raw).hexdigest()


@dataclass(frozen=True)
class CompanyRecord:
    """Immutable representation of a discovered and enriched company.

    Args:
        company_id: Unique UUID for this company.
        apex_domain: Canonical deduplication key (e.g. ``acme.com``).
        source: Discovery source channel.
        dedup_fingerprint: MD5 of normalized_name + apex_domain.
        company_name: Raw extracted company name.
        normalized_name: Name after legal suffix stripping for dedup.
        subdomains: All discovered subdomains of this company.
        career_page_url: Resolved career section URL.
        career_emails: Emails classified as HR/career-related.
        contact_emails: All other extracted emails.
        email_trust: Trust level of extracted emails.
        ats_platform: Detected applicant tracking system.
        industry: Industry if extractable from structured data.
        hq_location: HQ location if extractable.
        company_size: Size if published.
        source_detail: Specific directory name or search query.
        robots_txt_allowed: Whether enrichment scraping was permitted.
        discovery_date: When first added to companies table.
        last_enriched_at: Last time full enrichment ran.
        email_last_crawled_at: Last time email extraction ran.
        crawl_status: Current enrichment state.
        related_company_id: UUID of related company (multi-domain same company).

    Raises:
        DeserializationError: If from_dict() receives invalid data.
    """

    company_id: uuid.UUID
    apex_domain: str
    source: str
    dedup_fingerprint: str
    company_name: Optional[str] = None
    normalized_name: Optional[str] = None
    subdomains: List[str] = field(default_factory=list)
    career_page_url: Optional[str] = None
    career_emails: List[str] = field(default_factory=list)
    contact_emails: List[str] = field(default_factory=list)
    email_trust: str = "unverified"
    ats_platform: str = "none"
    industry: Optional[str] = None
    hq_location: Optional[str] = None
    company_size: Optional[str] = None
    source_detail: Optional[str] = None
    robots_txt_allowed: Optional[bool] = None
    discovery_date: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_enriched_at: Optional[datetime] = None
    email_last_crawled_at: Optional[datetime] = None
    crawl_status: str = "pending"
    related_company_id: Optional[uuid.UUID] = None

    def __post_init__(self) -> None:
        if self.email_trust not in _VALID_EMAIL_TRUST:
            raise ValueError(
                f"Invalid email_trust '{self.email_trust}'. "
                f"Must be one of {sorted(_VALID_EMAIL_TRUST)}."
            )
        if self.ats_platform not in _VALID_ATS_PLATFORMS:
            raise ValueError(
                f"Invalid ats_platform '{self.ats_platform}'. "
                f"Must be one of {sorted(_VALID_ATS_PLATFORMS)}."
            )
        if self.crawl_status not in _VALID_CRAWL_STATUSES:
            raise ValueError(
                f"Invalid crawl_status '{self.crawl_status}'. "
                f"Must be one of {sorted(_VALID_CRAWL_STATUSES)}."
            )
        if self.source not in _VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{self.source}'. "
                f"Must be one of {sorted(_VALID_SOURCES)}."
            )

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields serialised to primitive types.
        """
        return {
            "company_id": str(self.company_id),
            "apex_domain": self.apex_domain,
            "source": self.source,
            "dedup_fingerprint": self.dedup_fingerprint,
            "company_name": self.company_name,
            "normalized_name": self.normalized_name,
            "subdomains": list(self.subdomains),
            "career_page_url": self.career_page_url,
            "career_emails": list(self.career_emails),
            "contact_emails": list(self.contact_emails),
            "email_trust": self.email_trust,
            "ats_platform": self.ats_platform,
            "industry": self.industry,
            "hq_location": self.hq_location,
            "company_size": self.company_size,
            "source_detail": self.source_detail,
            "robots_txt_allowed": self.robots_txt_allowed,
            "discovery_date": self.discovery_date.isoformat() if self.discovery_date else None,
            "last_enriched_at": self.last_enriched_at.isoformat() if self.last_enriched_at else None,
            "email_last_crawled_at": (
                self.email_last_crawled_at.isoformat() if self.email_last_crawled_at else None
            ),
            "crawl_status": self.crawl_status,
            "related_company_id": str(self.related_company_id) if self.related_company_id else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CompanyRecord":
        """Deserialise from a dictionary.

        Args:
            data: Dictionary previously produced by to_dict().

        Returns:
            CompanyRecord instance.

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
                company_id=uuid.UUID(data["company_id"]),
                apex_domain=data["apex_domain"],
                source=data["source"],
                dedup_fingerprint=data["dedup_fingerprint"],
                company_name=data.get("company_name"),
                normalized_name=data.get("normalized_name"),
                subdomains=list(data.get("subdomains") or []),
                career_page_url=data.get("career_page_url"),
                career_emails=list(data.get("career_emails") or []),
                contact_emails=list(data.get("contact_emails") or []),
                email_trust=data.get("email_trust", "unverified"),
                ats_platform=data.get("ats_platform", "none"),
                industry=data.get("industry"),
                hq_location=data.get("hq_location"),
                company_size=data.get("company_size"),
                source_detail=data.get("source_detail"),
                robots_txt_allowed=data.get("robots_txt_allowed"),
                discovery_date=_parse_dt(data.get("discovery_date")) or datetime.now(timezone.utc),
                last_enriched_at=_parse_dt(data.get("last_enriched_at")),
                email_last_crawled_at=_parse_dt(data.get("email_last_crawled_at")),
                crawl_status=data.get("crawl_status", "pending"),
                related_company_id=(
                    uuid.UUID(data["related_company_id"])
                    if data.get("related_company_id")
                    else None
                ),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise DeserializationError(
                f"Failed to deserialise CompanyRecord: {exc}", {"data": data}
            ) from exc
