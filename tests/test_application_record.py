"""Unit tests for ApplicationRecord dataclass."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.exceptions import DeserializationError
from shared.models.application_record import ApplicationRecord
from shared.tests.conftest import make_application_record


def test_application_record_creates_valid_instance():
    record = make_application_record()
    assert isinstance(record.application_id, uuid.UUID)
    assert record.status == "sent"


def test_application_record_is_not_frozen():
    record = make_application_record()
    record.status = "replied"
    assert record.status == "replied"


def test_sent_at_defaults_to_utc_now():
    record = ApplicationRecord(
        application_id=uuid.uuid4(),
        user_id="u1",
        job_id=uuid.uuid4(),
        resume_variant_id=uuid.uuid4(),
    )
    assert record.sent_at is not None
    assert record.sent_at.tzinfo is not None


def test_reply_count_defaults_to_zero():
    record = ApplicationRecord(
        application_id=uuid.uuid4(),
        user_id="u1",
        job_id=uuid.uuid4(),
        resume_variant_id=uuid.uuid4(),
    )
    assert record.reply_count == 0


def test_from_dict_returns_application_record():
    original = make_application_record()
    restored = ApplicationRecord.from_dict(original.to_dict())
    assert restored.application_id == original.application_id
    assert restored.user_id == original.user_id
    assert restored.job_id == original.job_id


def test_from_dict_raises_for_missing_required_fields():
    with pytest.raises(DeserializationError):
        ApplicationRecord.from_dict({"user_id": "u1"})


def test_to_dict_round_trips_all_fields():
    record = make_application_record()
    d = record.to_dict()
    assert d["application_id"] == str(record.application_id)
    assert d["reply_count"] == 0


def test_get_days_since_sent_returns_correct_days():
    past = datetime.now(timezone.utc) - timedelta(days=5)
    record = make_application_record(sent_at=past)
    assert record.get_days_since_sent() == 5


def test_get_days_since_sent_returns_zero_for_today():
    record = make_application_record(sent_at=datetime.now(timezone.utc))
    assert record.get_days_since_sent() == 0


def test_validate_passes_for_valid_record():
    record = make_application_record()
    record.validate()


def test_validate_raises_for_non_uuid_application_id():
    record = make_application_record()
    record.application_id = "not-a-uuid"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_non_uuid_job_id():
    record = make_application_record()
    record.job_id = "not-a-uuid"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_non_uuid_resume_variant_id():
    record = make_application_record()
    record.resume_variant_id = "not-a-uuid"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_invalid_status():
    record = make_application_record()
    record.status = "pending"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_empty_user_id():
    record = make_application_record()
    record.user_id = ""
    with pytest.raises(ValueError):
        record.validate()


def test_cover_letter_id_serializes_as_string_when_set():
    cid = uuid.uuid4()
    record = make_application_record(cover_letter_id=cid)
    d = record.to_dict()
    assert d["cover_letter_id"] == str(cid)


def test_cover_letter_id_serializes_as_none_when_not_set():
    record = make_application_record(cover_letter_id=None)
    d = record.to_dict()
    assert d["cover_letter_id"] is None
