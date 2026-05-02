"""Tests for VariantRegistryBase abstract class."""

import inspect

import pytest

from shared.registries.base import VariantRegistryBase


def test_variant_registry_base_is_abstract():
    with pytest.raises(TypeError):
        VariantRegistryBase()  # type: ignore[abstract]


def test_variant_registry_base_defines_save():
    assert hasattr(VariantRegistryBase, "save")
    assert getattr(VariantRegistryBase.save, "__isabstractmethod__", False)


def test_variant_registry_base_defines_get():
    assert hasattr(VariantRegistryBase, "get")
    assert getattr(VariantRegistryBase.get, "__isabstractmethod__", False)


def test_variant_registry_base_defines_get_for_job():
    assert hasattr(VariantRegistryBase, "get_for_job")
    assert getattr(VariantRegistryBase.get_for_job, "__isabstractmethod__", False)


def test_variant_registry_base_defines_get_approved_for_job():
    assert hasattr(VariantRegistryBase, "get_approved_for_job")
    assert getattr(VariantRegistryBase.get_approved_for_job, "__isabstractmethod__", False)


def test_variant_registry_base_defines_get_for_user():
    assert hasattr(VariantRegistryBase, "get_for_user")
    assert getattr(VariantRegistryBase.get_for_user, "__isabstractmethod__", False)


def test_variant_registry_base_defines_get_pending_for_user():
    assert hasattr(VariantRegistryBase, "get_pending_for_user")
    assert getattr(VariantRegistryBase.get_pending_for_user, "__isabstractmethod__", False)


def test_variant_registry_base_defines_update_approval_status():
    assert hasattr(VariantRegistryBase, "update_approval_status")
    assert getattr(
        VariantRegistryBase.update_approval_status, "__isabstractmethod__", False
    )


def test_variant_registry_base_defines_update_approval_token():
    assert hasattr(VariantRegistryBase, "update_approval_token")
    assert getattr(
        VariantRegistryBase.update_approval_token, "__isabstractmethod__", False
    )


def test_variant_registry_base_defines_exists():
    assert hasattr(VariantRegistryBase, "exists")
    assert getattr(VariantRegistryBase.exists, "__isabstractmethod__", False)


def test_variant_registry_base_defines_count_by_user():
    assert hasattr(VariantRegistryBase, "count_by_user")
    assert getattr(VariantRegistryBase.count_by_user, "__isabstractmethod__", False)


def test_variant_registry_base_methods_are_async():
    for method_name in (
        "save", "get", "get_for_job", "get_approved_for_job", "get_for_user",
        "get_pending_for_user", "update_approval_status", "update_approval_token",
        "exists", "count_by_user",
    ):
        method = getattr(VariantRegistryBase, method_name)
        assert inspect.iscoroutinefunction(method), (
            f"{method_name} must be an async method"
        )
