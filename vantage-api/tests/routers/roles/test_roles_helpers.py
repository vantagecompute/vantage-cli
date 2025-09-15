"""Core module for testing the roles helpers."""
import pytest
from fastapi import HTTPException, status

from api.routers.roles.helpers import (
    ListRolesSortFieldChecker,
    ListUsersByRoleSortFieldChecker,
    sort_field_exception,
)


def test_sort_field_exception__check_if_422_is_raised():
    """Check if 422 is raised by the sort field exception."""
    assert isinstance(sort_field_exception, HTTPException)
    assert sort_field_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_roles_field_checker__check_if_available_fields_are_from_the_checker_model():
    """Check if available fields are from the checker model."""
    checker = ListRolesSortFieldChecker()

    assert checker.available_fields() == list(checker._model.__fields__.keys())


def test_roles_field_checker__check_if_available_fields_are_returned_when_called():
    """Check if available fields are returned when called."""
    checker = ListRolesSortFieldChecker()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


def test_roles_field_checker__check_if_none_sort_field_returns_none():
    """Check if none sort field returns none."""
    checker = ListRolesSortFieldChecker()

    assert checker(None) is None


def test_roles_field_checker__check_if_no_available_field_raises_error_when_called():
    """Check if no available field raises error when called."""
    checker = ListRolesSortFieldChecker()

    dummy_field = "the_lakers_are_awesome"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)


def test_users_by_role_field_checker__check_if_available_fields_are_from_the_checker_model():
    """Check if available fields are from the checker model."""
    checker = ListUsersByRoleSortFieldChecker()

    assert checker.available_fields() == list(checker._model.__fields__.keys())


def test_users_by_role_field_checker__check_if_available_fields_are_returned_when_called():
    """Check if available fields are returned when called."""
    checker = ListUsersByRoleSortFieldChecker()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


def test_users_by_role_field_checker__check_if_none_sort_field_returns_none():
    """Check if none sort field returns none."""
    checker = ListUsersByRoleSortFieldChecker()

    assert checker(None) is None


def test_users_by_role_field_checker__check_if_no_available_field_raises_error_when_called():
    """Check if no available field raises error when called."""
    checker = ListUsersByRoleSortFieldChecker()

    dummy_field = "the_lakers_are_awesome"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)
