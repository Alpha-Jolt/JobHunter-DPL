"""Tests for JobRegistryBase abstract class."""

import inspect

import pytest

from shared.registries.base import JobRegistryBase


def test_job_registry_base_is_abstract():
    with pytest.raises(TypeError):
        JobRegistryBase()  # type: ignore[abstract]


def test_job_registry_base_defines_save():
    assert hasattr(JobRegistryBase, "save")
    assert getattr(JobRegistryBase.save, "__isabstractmethod__", False)


def test_job_registry_base_defines_get():
    assert hasattr(JobRegistryBase, "get")
    assert getattr(JobRegistryBase.get, "__isabstractmethod__", False)


def test_job_registry_base_defines_get_many():
    assert hasattr(JobRegistryBase, "get_many")
    assert getattr(JobRegistryBase.get_many, "__isabstractmethod__", False)


def test_job_registry_base_defines_get_all_with_email():
    assert hasattr(JobRegistryBase, "get_all_with_email")
    assert getattr(JobRegistryBase.get_all_with_email, "__isabstractmethod__", False)


def test_job_registry_base_defines_get_by_source():
    assert hasattr(JobRegistryBase, "get_by_source")
    assert getattr(JobRegistryBase.get_by_source, "__isabstractmethod__", False)


def test_job_registry_base_defines_get_by_status():
    assert hasattr(JobRegistryBase, "get_by_status")
    assert getattr(JobRegistryBase.get_by_status, "__isabstractmethod__", False)


def test_job_registry_base_defines_exists():
    assert hasattr(JobRegistryBase, "exists")
    assert getattr(JobRegistryBase.exists, "__isabstractmethod__", False)


def test_job_registry_base_defines_count():
    assert hasattr(JobRegistryBase, "count")
    assert getattr(JobRegistryBase.count, "__isabstractmethod__", False)


def test_job_registry_base_defines_delete_by_source():
    assert hasattr(JobRegistryBase, "delete_by_source")
    assert getattr(JobRegistryBase.delete_by_source, "__isabstractmethod__", False)


def test_job_registry_base_methods_are_async():
    for method_name in (
        "save", "get", "get_many", "get_all_with_email",
        "get_by_source", "get_by_status", "exists", "count", "delete_by_source",
    ):
        method = getattr(JobRegistryBase, method_name)
        assert inspect.iscoroutinefunction(method), (
            f"{method_name} must be an async method"
        )
