"""Core module for testing the groups helpers."""
import pytest
from fastapi import HTTPException, status

from api.routers.groups.helpers import (
    ListGroupsSortFieldChecker,
    ListRolesByGroupsSortFieldChecker,
    ListUsersByGroupSortFieldChecker,
    sort_field_exception,
)


def test_sort_field_exception__check_if_422_is_raised():
    """Test if the sort field exception raises a 422 error."""
    assert isinstance(sort_field_exception, HTTPException)
    assert sort_field_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.parametrize(
    "checker_class",
    [ListRolesByGroupsSortFieldChecker, ListUsersByGroupSortFieldChecker, ListGroupsSortFieldChecker],
)
def test_field_checker__check_if_available_fields_are_from_the_checker_model(checker_class):
    """Test if the field checker returns the available fields from the checker model."""
    checker = checker_class()

    assert checker.available_fields() == list(checker._model.__fields__.keys())


@pytest.mark.parametrize(
    "checker_class",
    [ListRolesByGroupsSortFieldChecker, ListUsersByGroupSortFieldChecker, ListGroupsSortFieldChecker],
)
def test_field_checker__check_if_available_fields_are_returned_when_called(checker_class):
    """Test if the field checker returns the available fields when called."""
    checker = checker_class()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


@pytest.mark.parametrize(
    "checker_class",
    [ListRolesByGroupsSortFieldChecker, ListUsersByGroupSortFieldChecker, ListGroupsSortFieldChecker],
)
def test_field_checker__check_if_none_sort_field_returns_none(checker_class):
    """Test if the field checker returns None when None is passed."""
    checker = checker_class()

    assert checker(None) is None


@pytest.mark.parametrize(
    "checker_class",
    [ListRolesByGroupsSortFieldChecker, ListUsersByGroupSortFieldChecker, ListGroupsSortFieldChecker],
)
def test_field_checker__check_if_no_available_field_raises_error_when_called(checker_class):
    """Test if the field checker raises an error when a non-available field is passed."""
    checker = checker_class()

    dummy_field = "the_lakers_are_awesome_and_seahawks_arent"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)
