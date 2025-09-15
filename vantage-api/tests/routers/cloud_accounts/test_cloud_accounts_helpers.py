"""Core module for testing cloud_accounts helper functions."""
import pytest
from fastapi import HTTPException, status

from api.routers.cloud_accounts.helpers import ListCloudAccountsFieldChecker, sort_field_exception


def test_sort_field_exception__check_if_422_is_raised():
    """Check if 422 is raised by the sort field exception."""
    assert isinstance(sort_field_exception, HTTPException)
    assert sort_field_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize("checker_class", [ListCloudAccountsFieldChecker])
def test_field_checker__check_if_available_fields_are_from_the_checker_model(checker_class):
    """Check if available fields are from the checker model."""
    checker = checker_class()

    all_fields = list(checker._model.__fields__.keys())
    available_fields = [field for field in all_fields if field not in checker.not_available_fields()]

    assert checker.available_fields() == available_fields


@pytest.mark.parametrize("checker_class", [ListCloudAccountsFieldChecker])
def test_field_checker__check_if_available_fields_are_returned_when_called(checker_class):
    """Check if available fields are returned when called."""
    checker = checker_class()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


@pytest.mark.parametrize("checker_class", [ListCloudAccountsFieldChecker])
def test_field_checker__check_if_none_sort_field_returns_none(checker_class):
    """Check if none sort field returns none."""
    checker = checker_class()

    assert checker(None) is None


@pytest.mark.parametrize("checker_class", [ListCloudAccountsFieldChecker])
def test_field_checker__check_if_no_available_field_raises_error_when_called(checker_class):
    """Check if no available field raises error when called."""
    checker = checker_class()

    dummy_field = "the_lakers_are_awesome_and_seahawks_arent"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)
