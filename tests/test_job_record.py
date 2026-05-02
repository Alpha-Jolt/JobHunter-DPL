"""Unit tests for JobRecord dataclass."""

import uuid
from datetime import datetime, timezone

import pytest

from shared.models.exceptions import DeserializationError
from shared.models.job_record import JobRecord
from shared.tests.conftest import make_job_record


def test_job_record_creates_valid_instance():
    record = make_job_record()
    assert isinstance(record.job_id, uuid.UUID)
    assert record.source == "linkedin"
    assert record.status == "raw"


def test_job_record_is_frozen():
    record = make_job_record()
    with pytest.raises((AttributeError, TypeError)):
        record.title = "Changed"  # type: ignore[misc]


def test_from_dict_returns_job_record():
    original = make_job_record()
    restored = JobRecord.from_dict(original.to_dict())
    assert restored.job_id == original.job_id
    assert restored.title == original.title
    assert restored.source == original.source


def test_from_dict_raises_for_missing_required_fields():
    with pytest.raises(DeserializationError):
        JobRecord.from_dict({"source": "linkedin"})


def test_from_dict_raises_for_invalid_source():
    data = make_job_record().to_dict()
    data["source"] = "monster"
    with pytest.raises(DeserializationError):
        JobRecord.from_dict(data)


def test_from_dict_raises_for_invalid_job_id():
    data = make_job_record().to_dict()
    data["job_id"] = "not-a-uuid"
    with pytest.raises(DeserializationError):
        JobRecord.from_dict(data)


def test_to_dict_round_trips_all_fields():
    record = make_job_record()
    d = record.to_dict()
    assert d["job_id"] == str(record.job_id)
    assert d["skills_required"] == record.skills_required
    assert d["posted_at"] == record.posted_at.isoformat()


def test_validate_passes_for_valid_record():
    record = make_job_record()
    record.validate()  # should not raise


def test_validate_raises_for_non_uuid_job_id():
    record = make_job_record()
    bad = JobRecord(
        job_id="not-a-uuid",  # type: ignore[arg-type]
        source=record.source,
        external_id=record.external_id,
        title=record.title,
        company_name=record.company_name,
        company_domain=record.company_domain,
        location=record.location,
        remote_type=record.remote_type,
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        experience_min=record.experience_min,
        experience_max=record.experience_max,
        description=record.description,
    )
    with pytest.raises(ValueError):
        bad.validate()


def test_validate_raises_for_invalid_status():
    data = make_job_record().to_dict()
    data["status"] = "raw"
    record = JobRecord.from_dict(data)
    bad = JobRecord(
        job_id=record.job_id,
        source=record.source,
        external_id=record.external_id,
        title=record.title,
        company_name=record.company_name,
        company_domain=record.company_domain,
        location=record.location,
        remote_type=record.remote_type,
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        experience_min=record.experience_min,
        experience_max=record.experience_max,
        description=record.description,
        status="invalid_status",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError):
        bad.validate()


def test_validate_raises_for_invalid_remote_type():
    record = make_job_record()
    bad = JobRecord(
        job_id=record.job_id,
        source=record.source,
        external_id=record.external_id,
        title=record.title,
        company_name=record.company_name,
        company_domain=record.company_domain,
        location=record.location,
        remote_type="flying",  # type: ignore[arg-type]
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        experience_min=record.experience_min,
        experience_max=record.experience_max,
        description=record.description,
    )
    with pytest.raises(ValueError):
        bad.validate()


def test_validate_raises_for_invalid_job_type():
    record = make_job_record()
    bad = JobRecord(
        job_id=record.job_id,
        source=record.source,
        external_id=record.external_id,
        title=record.title,
        company_name=record.company_name,
        company_domain=record.company_domain,
        location=record.location,
        remote_type=record.remote_type,
        salary_min=record.salary_min,
        salary_max=record.salary_max,
        experience_min=record.experience_min,
        experience_max=record.experience_max,
        description=record.description,
        job_type="gig",  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError):
        bad.validate()


def test_datetime_fields_serialized_as_iso():
    record = make_job_record(scraped_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc))
    d = record.to_dict()
    assert "2026-01-15" in d["scraped_at"]


def test_none_optional_fields_serialize_as_none():
    record = make_job_record(apply_email=None, apply_url=None)
    d = record.to_dict()
    assert d["apply_email"] is None
    assert d["apply_url"] is None
