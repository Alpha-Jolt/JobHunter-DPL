"""Tests for ApplicationLogBase abstract class."""

import inspect

import pytest

from shared.registries.base import ApplicationLogBase


def test_application_log_base_is_abstract():
    with pytest.raises(TypeError):
        ApplicationLogBase()  # type: ignore[abstract]


def test_application_log_base_defines_record_send():
    assert hasattr(ApplicationLogBase, "record_send")
    assert getattr(ApplicationLogBase.record_send, "__isabstractmethod__", False)


def test_application_log_base_defines_get():
    assert hasattr(ApplicationLogBase, "get")
    assert getattr(ApplicationLogBase.get, "__isabstractmethod__", False)


def test_application_log_base_defines_get_by_user():
    assert hasattr(ApplicationLogBase, "get_by_user")
    assert getattr(ApplicationLogBase.get_by_user, "__isabstractmethod__", False)


def test_application_log_base_defines_get_by_job():
    assert hasattr(ApplicationLogBase, "get_by_job")
    assert getattr(ApplicationLogBase.get_by_job, "__isabstractmethod__", False)


def test_application_log_base_defines_has_user_applied_to_job():
    assert hasattr(ApplicationLogBase, "has_user_applied_to_job")
    assert getattr(
        ApplicationLogBase.has_user_applied_to_job, "__isabstractmethod__", False
    )


def test_application_log_base_defines_get_applications_sent_today():
    assert hasattr(ApplicationLogBase, "get_applications_sent_today")
    assert getattr(
        ApplicationLogBase.get_applications_sent_today, "__isabstractmethod__", False
    )


def test_application_log_base_defines_update_status():
    assert hasattr(ApplicationLogBase, "update_status")
    assert getattr(ApplicationLogBase.update_status, "__isabstractmethod__", False)


def test_application_log_base_defines_update_reply_count():
    assert hasattr(ApplicationLogBase, "update_reply_count")
    assert getattr(ApplicationLogBase.update_reply_count, "__isabstractmethod__", False)


def test_application_log_base_defines_count_by_user():
    assert hasattr(ApplicationLogBase, "count_by_user")
    assert getattr(ApplicationLogBase.count_by_user, "__isabstractmethod__", False)


def test_application_log_base_methods_are_async():
    for method_name in (
        "record_send", "get", "get_by_user", "get_by_job",
        "has_user_applied_to_job", "get_applications_sent_today",
        "update_status", "update_reply_count", "count_by_user",
    ):
        method = getattr(ApplicationLogBase, method_name)
        assert inspect.iscoroutinefunction(method), (
            f"{method_name} must be an async method"
        )
