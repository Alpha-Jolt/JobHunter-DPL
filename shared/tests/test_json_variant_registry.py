"""Integration tests for JSON-backed VariantRegistry."""

import uuid

import pytest

from shared.models.exceptions import RegistryError, VariantNotFoundError


async def test_save_creates_variant_with_created_at(variant_registry, variant_factory):
    variant = variant_factory(created_at=None)
    await variant_registry.save(variant)
    retrieved = await variant_registry.get(variant.variant_id)
    assert retrieved.created_at is not None


async def test_get_retrieves_by_variant_id(variant_registry, variant_factory):
    variant = variant_factory()
    await variant_registry.save(variant)
    retrieved = await variant_registry.get(variant.variant_id)
    assert retrieved.variant_id == variant.variant_id


async def test_get_raises_variant_not_found_error(variant_registry):
    with pytest.raises(VariantNotFoundError):
        await variant_registry.get(uuid.uuid4())


async def test_get_for_job_returns_all_variants_for_job(variant_registry, variant_factory):
    job_id = uuid.uuid4()
    v1 = variant_factory(job_id=job_id, user_id="user-a")
    v2 = variant_factory(job_id=job_id, user_id="user-b")
    v3 = variant_factory()  # different job
    await variant_registry.save(v1)
    await variant_registry.save(v2)
    await variant_registry.save(v3)
    result = await variant_registry.get_for_job(job_id)
    assert len(result) == 2


async def test_get_approved_for_job_returns_approved_variant(
    variant_registry, variant_factory
):
    job_id = uuid.uuid4()
    user_id = "user-x"
    variant = variant_factory(job_id=job_id, user_id=user_id, approval_status="pending")
    await variant_registry.save(variant)
    await variant_registry.update_approval_status(variant.variant_id, "approved")
    result = await variant_registry.get_approved_for_job(job_id, user_id)
    assert result is not None
    assert result.variant_id == variant.variant_id


async def test_get_approved_for_job_returns_none_when_no_approved(
    variant_registry, variant_factory
):
    job_id = uuid.uuid4()
    variant = variant_factory(job_id=job_id, approval_status="pending")
    await variant_registry.save(variant)
    result = await variant_registry.get_approved_for_job(job_id, variant.user_id)
    assert result is None


async def test_get_for_user_returns_all_user_variants(variant_registry, variant_factory):
    user_id = "user-multi"
    job_ids = [uuid.uuid4(), uuid.uuid4()]
    for jid in job_ids:
        await variant_registry.save(variant_factory(user_id=user_id, job_id=jid))
    result = await variant_registry.get_for_user(user_id)
    assert len(result) == 2


async def test_get_pending_for_user_returns_only_pending(variant_registry, variant_factory):
    user_id = "user-pending"
    job_id_1 = uuid.uuid4()
    job_id_2 = uuid.uuid4()
    pending = variant_factory(user_id=user_id, job_id=job_id_1, approval_status="pending")
    approved = variant_factory(user_id=user_id, job_id=job_id_2, approval_status="pending")
    await variant_registry.save(pending)
    await variant_registry.save(approved)
    await variant_registry.update_approval_status(approved.variant_id, "approved")
    result = await variant_registry.get_pending_for_user(user_id)
    assert len(result) == 1
    assert result[0].variant_id == pending.variant_id


async def test_update_approval_status_changes_and_persists(
    variant_registry, variant_factory
):
    variant = variant_factory(approval_status="pending")
    await variant_registry.save(variant)
    await variant_registry.update_approval_status(variant.variant_id, "approved")
    retrieved = await variant_registry.get(variant.variant_id)
    assert retrieved.approval_status == "approved"
    assert retrieved.approved_at is not None


async def test_update_approval_status_raises_for_missing_variant(variant_registry):
    with pytest.raises(VariantNotFoundError):
        await variant_registry.update_approval_status(uuid.uuid4(), "approved")


async def test_update_approval_token_stores_token(variant_registry, variant_factory):
    variant = variant_factory()
    await variant_registry.save(variant)
    token = "a" * 64
    await variant_registry.update_approval_token(variant.variant_id, token)
    retrieved = await variant_registry.get(variant.variant_id)
    assert retrieved.approval_token == token


async def test_update_approval_token_raises_for_missing_variant(variant_registry):
    with pytest.raises(VariantNotFoundError):
        await variant_registry.update_approval_token(uuid.uuid4(), "a" * 64)


async def test_exists_returns_true_for_saved_variant(variant_registry, variant_factory):
    variant = variant_factory()
    await variant_registry.save(variant)
    assert await variant_registry.exists(variant.variant_id) is True


async def test_exists_returns_false_for_missing_variant(variant_registry):
    assert await variant_registry.exists(uuid.uuid4()) is False


async def test_count_by_user_returns_correct_count(variant_registry, variant_factory):
    user_id = "user-count"
    for jid in [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]:
        await variant_registry.save(variant_factory(user_id=user_id, job_id=jid))
    assert await variant_registry.count_by_user(user_id) == 3


async def test_duplicate_user_job_pair_raises_registry_error(
    variant_registry, variant_factory
):
    job_id = uuid.uuid4()
    user_id = "user-dup"
    v1 = variant_factory(user_id=user_id, job_id=job_id)
    v2 = variant_factory(user_id=user_id, job_id=job_id)
    await variant_registry.save(v1)
    with pytest.raises(RegistryError):
        await variant_registry.save(v2)
