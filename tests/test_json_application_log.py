"""Integration tests for JSON-backed ApplicationLog."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.exceptions import ApplicationNotFoundError, RegistryError


async def test_record_send_creates_application(application_log, application_factory):
    record = application_factory()
    await application_log.record_send(record)
    retrieved = await application_log.get(record.application_id)
    assert retrieved.application_id == record.application_id


async def test_get_retrieves_by_application_id(application_log, application_factory):
    record = application_factory()
    await application_log.record_send(record)
    retrieved = await application_log.get(record.application_id)
    assert retrieved.user_id == record.user_id
    assert retrieved.job_id == record.job_id


async def test_get_raises_application_not_found_error(application_log):
    with pytest.raises(ApplicationNotFoundError):
        await application_log.get(uuid.uuid4())


async def test_get_by_user_returns_all_user_applications(
    application_log, application_factory
):
    user_id = "user-getbyuser"
    records = [application_factory(user_id=user_id) for _ in range(3)]
    for r in records:
        await application_log.record_send(r)
    result = await application_log.get_by_user(user_id)
    assert len(result) == 3


async def test_get_by_job_returns_all_applications_to_job(
    application_log, application_factory
):
    job_id = uuid.uuid4()
    r1 = application_factory(job_id=job_id, user_id="u1")
    r2 = application_factory(job_id=job_id, user_id="u2")
    r3 = application_factory()  # different job
    await application_log.record_send(r1)
    await application_log.record_send(r2)
    await application_log.record_send(r3)
    result = await application_log.get_by_job(job_id)
    assert len(result) == 2


async def test_has_user_applied_to_job_returns_true_after_send(
    application_log, application_factory
):
    record = application_factory()
    await application_log.record_send(record)
    result = await application_log.has_user_applied_to_job(record.user_id, record.job_id)
    assert result is True


async def test_has_user_applied_to_job_returns_false_before_send(application_log):
    assert await application_log.has_user_applied_to_job("nobody", uuid.uuid4()) is False


async def test_record_send_prevents_duplicate_application(
    application_log, application_factory
):
    record = application_factory()
    await application_log.record_send(record)
    duplicate = application_factory(user_id=record.user_id, job_id=record.job_id)
    with pytest.raises(RegistryError):
        await application_log.record_send(duplicate)


async def test_get_applications_sent_today_returns_recent(
    application_log, application_factory
):
    user_id = "user-today"
    recent = application_factory(
        user_id=user_id, sent_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    old = application_factory(
        user_id=user_id, sent_at=datetime.now(timezone.utc) - timedelta(hours=25)
    )
    await application_log.record_send(recent)
    await application_log.record_send(old)
    result = await application_log.get_applications_sent_today(user_id)
    assert len(result) == 1
    assert result[0].application_id == recent.application_id


async def test_update_status_changes_status_and_persists(
    application_log, application_factory
):
    record = application_factory()
    await application_log.record_send(record)
    await application_log.update_status(record.application_id, "replied")
    retrieved = await application_log.get(record.application_id)
    assert retrieved.status == "replied"


async def test_update_status_raises_for_missing_application(application_log):
    with pytest.raises(ApplicationNotFoundError):
        await application_log.update_status(uuid.uuid4(), "replied")


async def test_update_reply_count_increments_count(application_log, application_factory):
    record = application_factory()
    await application_log.record_send(record)
    await application_log.update_reply_count(record.application_id, 3)
    retrieved = await application_log.get(record.application_id)
    assert retrieved.reply_count == 3


async def test_update_reply_count_raises_for_missing_application(application_log):
    with pytest.raises(ApplicationNotFoundError):
        await application_log.update_reply_count(uuid.uuid4(), 1)


async def test_count_by_user_returns_correct_count(application_log, application_factory):
    user_id = "user-cnt"
    for _ in range(4):
        await application_log.record_send(application_factory(user_id=user_id))
    assert await application_log.count_by_user(user_id) == 4
