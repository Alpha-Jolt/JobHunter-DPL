"""Shared pytest fixtures for the shared layer test suite."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shared.models.application_record import ApplicationRecord
from shared.models.job_record import JobRecord
from shared.models.variant_record import VariantRecord
from shared.registries.application_log import ApplicationLog
from shared.registries.job_registry import JobRegistry
from shared.registries.variant_registry import VariantRegistry


@pytest.fixture
def tmp_registry_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for registry JSON files."""
    reg_dir = tmp_path / "registries"
    reg_dir.mkdir()
    return reg_dir


@pytest.fixture
def job_registry(tmp_registry_dir: Path) -> JobRegistry:
    """Provide a JobRegistry backed by a temp file."""
    return JobRegistry(file_path=str(tmp_registry_dir / "jobs.json"))


@pytest.fixture
def variant_registry(tmp_registry_dir: Path) -> VariantRegistry:
    """Provide a VariantRegistry backed by a temp file."""
    return VariantRegistry(file_path=str(tmp_registry_dir / "variants.json"))


@pytest.fixture
def application_log(tmp_registry_dir: Path) -> ApplicationLog:
    """Provide an ApplicationLog backed by a temp file."""
    return ApplicationLog(file_path=str(tmp_registry_dir / "applications.json"))


def make_job_record(**overrides) -> JobRecord:
    """Factory for JobRecord with sensible defaults.

    Args:
        **overrides: Field values to override.

    Returns:
        A valid JobRecord instance.
    """
    defaults = {
        "job_id": uuid.uuid4(),
        "source": "linkedin",
        "external_id": f"ext-{uuid.uuid4().hex[:8]}",
        "title": "Software Engineer",
        "company_name": "Acme Corp",
        "company_domain": "acme.com",
        "location": "Bangalore",
        "remote_type": "hybrid",
        "salary_min": 800000.0,
        "salary_max": 1200000.0,
        "experience_min": 1,
        "experience_max": 3,
        "description": "Build and maintain backend services.",
        "skills_required": ["Python", "PostgreSQL"],
        "job_type": "fulltime",
        "apply_email": "hr@acme.com",
        "email_trust": "unknown",
        "apply_url": "https://acme.com/jobs/1",
        "posted_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
        "scraped_at": datetime(2026, 4, 2, tzinfo=timezone.utc),
        "last_seen_at": datetime(2026, 4, 2, tzinfo=timezone.utc),
        "status": "raw",
    }
    defaults.update(overrides)
    return JobRecord(**defaults)


def make_variant_record(**overrides) -> VariantRecord:
    """Factory for VariantRecord with sensible defaults.

    Args:
        **overrides: Field values to override.

    Returns:
        A valid VariantRecord instance.
    """
    defaults = {
        "variant_id": uuid.uuid4(),
        "user_id": f"user-{uuid.uuid4().hex[:8]}",
        "job_id": uuid.uuid4(),
        "master_resume_id": uuid.uuid4(),
        "pdf_key": "s3/resumes/variant.pdf",
        "docx_key": "s3/resumes/variant.docx",
        "curated_json": {"summary": "Experienced engineer"},
        "gaps_identified": ["Kubernetes"],
        "approval_status": "pending",
        "approval_token": None,
        "approved_at": None,
        "user_feedback": None,
        "created_at": datetime(2026, 4, 3, tzinfo=timezone.utc),
        "prompt_version": "v1.0",
    }
    defaults.update(overrides)
    return VariantRecord(**defaults)


def make_application_record(**overrides) -> ApplicationRecord:
    """Factory for ApplicationRecord with sensible defaults.

    Args:
        **overrides: Field values to override.

    Returns:
        A valid ApplicationRecord instance.
    """
    defaults = {
        "application_id": uuid.uuid4(),
        "user_id": f"user-{uuid.uuid4().hex[:8]}",
        "job_id": uuid.uuid4(),
        "resume_variant_id": uuid.uuid4(),
        "cover_letter_id": None,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc),
        "last_activity_at": None,
        "thread_id": None,
        "email_subject": "Application for Software Engineer",
        "reply_count": 0,
        "notes": None,
    }
    defaults.update(overrides)
    return ApplicationRecord(**defaults)


@pytest.fixture
def job_factory():
    """Return the make_job_record factory function."""
    return make_job_record


@pytest.fixture
def variant_factory():
    """Return the make_variant_record factory function."""
    return make_variant_record


@pytest.fixture
def application_factory():
    """Return the make_application_record factory function."""
    return make_application_record
