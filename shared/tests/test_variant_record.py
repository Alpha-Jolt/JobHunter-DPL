"""Unit tests for VariantRecord dataclass."""

import uuid
from datetime import datetime, timezone

import pytest

from shared.models.exceptions import DeserializationError
from shared.models.variant_record import VariantRecord
from shared.tests.conftest import make_variant_record


def test_variant_record_creates_valid_instance():
    record = make_variant_record()
    assert isinstance(record.variant_id, uuid.UUID)
    assert record.approval_status == "pending"


def test_variant_record_is_not_frozen():
    record = make_variant_record()
    record.approval_status = "approved"
    assert record.approval_status == "approved"


def test_from_dict_returns_variant_record():
    original = make_variant_record()
    restored = VariantRecord.from_dict(original.to_dict())
    assert restored.variant_id == original.variant_id
    assert restored.user_id == original.user_id
    assert restored.job_id == original.job_id


def test_from_dict_raises_for_missing_required_fields():
    with pytest.raises(DeserializationError):
        VariantRecord.from_dict({"user_id": "u1"})


def test_to_dict_round_trips_all_fields():
    record = make_variant_record()
    d = record.to_dict()
    assert d["variant_id"] == str(record.variant_id)
    assert d["gaps_identified"] == record.gaps_identified
    assert d["curated_json"] == record.curated_json


def test_is_approved_returns_true_when_approved():
    record = make_variant_record(approval_status="approved")
    assert record.is_approved() is True


def test_is_approved_returns_false_when_pending():
    record = make_variant_record(approval_status="pending")
    assert record.is_approved() is False


def test_is_pending_returns_true_when_pending():
    record = make_variant_record(approval_status="pending")
    assert record.is_pending() is True


def test_is_pending_returns_false_when_approved():
    record = make_variant_record(approval_status="approved")
    assert record.is_pending() is False


def test_validate_passes_for_valid_record():
    record = make_variant_record()
    record.validate()


def test_validate_raises_for_non_uuid_variant_id():
    record = make_variant_record()
    record.variant_id = "not-a-uuid"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_non_uuid_job_id():
    record = make_variant_record()
    record.job_id = "not-a-uuid"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_empty_user_id():
    record = make_variant_record()
    record.user_id = ""
    with pytest.raises(ValueError):
        record.validate()


def test_validate_raises_for_invalid_approval_status():
    record = make_variant_record()
    record.approval_status = "maybe"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        record.validate()


def test_approved_at_serialized_as_iso():
    ts = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    record = make_variant_record(approval_status="approved", approved_at=ts)
    d = record.to_dict()
    assert "2026-05-01" in d["approved_at"]


def test_none_optional_fields_serialize_as_none():
    record = make_variant_record(approval_token=None, user_feedback=None)
    d = record.to_dict()
    assert d["approval_token"] is None
    assert d["user_feedback"] is None
