"""Integration tests for JSON-backed JobRegistry."""

import asyncio
import uuid
from pathlib import Path

import pytest

from shared.models.exceptions import JobNotFoundError


async def test_save_writes_to_json_file(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    assert Path(job_registry._path).exists()


async def test_get_retrieves_by_job_id(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    retrieved = await job_registry.get(job.job_id)
    assert retrieved.job_id == job.job_id
    assert retrieved.title == job.title


async def test_get_raises_job_not_found_error(job_registry):
    with pytest.raises(JobNotFoundError):
        await job_registry.get(uuid.uuid4())


async def test_get_many_returns_multiple_jobs(job_registry, job_factory):
    jobs = [job_factory() for _ in range(3)]
    await job_registry.save(jobs)
    ids = [j.job_id for j in jobs]
    result = await job_registry.get_many(ids)
    assert len(result) == 3


async def test_get_many_skips_missing_ids(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    result = await job_registry.get_many([job.job_id, uuid.uuid4()])
    assert len(result) == 1


async def test_get_all_with_email_returns_only_jobs_with_email(job_registry, job_factory):
    with_email = job_factory(apply_email="hr@company.com")
    without_email = job_factory(apply_email=None)
    await job_registry.save([with_email, without_email])
    result = await job_registry.get_all_with_email()
    assert len(result) == 1
    assert result[0].job_id == with_email.job_id


async def test_get_by_source_filters_correctly(job_registry, job_factory):
    linkedin_job = job_factory(source="linkedin")
    naukri_job = job_factory(source="naukri")
    await job_registry.save([linkedin_job, naukri_job])
    result = await job_registry.get_by_source("linkedin")
    assert all(j.source == "linkedin" for j in result)
    assert len(result) == 1


async def test_get_by_status_filters_correctly(job_registry, job_factory):
    raw_job = job_factory(status="raw")
    applied_job = job_factory(status="applied")
    await job_registry.save([raw_job, applied_job])
    result = await job_registry.get_by_status("raw")
    assert len(result) == 1
    assert result[0].status == "raw"


async def test_exists_returns_true_for_saved_job(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    assert await job_registry.exists(job.job_id) is True


async def test_exists_returns_false_for_missing_job(job_registry):
    assert await job_registry.exists(uuid.uuid4()) is False


async def test_count_returns_correct_number(job_registry, job_factory):
    jobs = [job_factory() for _ in range(4)]
    await job_registry.save(jobs)
    assert await job_registry.count() == 4


async def test_delete_by_source_removes_jobs_and_returns_count(job_registry, job_factory):
    linkedin_jobs = [job_factory(source="linkedin") for _ in range(2)]
    indeed_job = job_factory(source="indeed")
    await job_registry.save(linkedin_jobs + [indeed_job])
    deleted = await job_registry.delete_by_source("linkedin")
    assert deleted == 2
    assert await job_registry.count() == 1


async def test_delete_by_source_returns_zero_when_none_match(job_registry, job_factory):
    job = job_factory(source="naukri")
    await job_registry.save([job])
    deleted = await job_registry.delete_by_source("indeed")
    assert deleted == 0


async def test_empty_registry_initializes_gracefully(job_registry):
    assert await job_registry.count() == 0


async def test_save_merges_by_job_id(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    await job_registry.save([job])  # save same job again
    assert await job_registry.count() == 1


async def test_concurrent_saves_do_not_corrupt_file(job_registry, job_factory):
    jobs = [job_factory() for _ in range(10)]
    await asyncio.gather(*[job_registry.save([j]) for j in jobs])
    count = await job_registry.count()
    assert count == 10


async def test_atomic_write_produces_valid_json(job_registry, job_factory):
    job = job_factory()
    await job_registry.save([job])
    import json
    with open(job_registry._path, "r") as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) == 1
