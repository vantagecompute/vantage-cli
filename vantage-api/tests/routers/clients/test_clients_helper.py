"""Core module for testing the clients helpers."""
import pytest
from fastapi import HTTPException, status

from api.body.output import ClientModel
from api.routers.clients.helpers import (
    _DEFAULT_CLIENTS_LIST_BY_CLIENT_ID,
    ListClientsSortFieldChecker,
    clean_clients,
    sort_field_exception,
)


def test_sort_field_exception__check_if_422_is_raised():
    """Test if the sort field exception raises a 422 error."""
    assert isinstance(sort_field_exception, HTTPException)
    assert sort_field_exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_clients_field_checker__check_if_available_fields_are_from_the_checker_model():
    """Test if the field checker returns the available fields from the checker model."""
    checker = ListClientsSortFieldChecker()

    assert checker.available_fields() == list(checker._model.__fields__.keys())


def test_clients_field_checker__check_if_available_fields_are_returned_when_called():
    """Test if the field checker returns the available fields when called."""
    checker = ListClientsSortFieldChecker()

    for sort_field in checker.available_fields():
        assert checker(sort_field) == sort_field


def test_clients_field_checker__check_if_none_sort_field_returns_none():
    """Test if the field checker returns None when None is passed."""
    checker = ListClientsSortFieldChecker()

    assert checker(None) is None


def test_clients_field_checker__check_if_no_available_field_raises_error_when_called():
    """Test if the field checker raises an error when a non-available field is passed."""
    checker = ListClientsSortFieldChecker()

    dummy_field = "back_to_the_court_magic_johnson"

    assert dummy_field not in checker.available_fields()

    with pytest.raises(HTTPException):
        checker(dummy_field)


def test_default_clients_list():
    """Test if the default clients list is the expected one."""
    assert _DEFAULT_CLIENTS_LIST_BY_CLIENT_ID == [
        "account",
        "account-console",
        "admin-cli",
        "admin-ops",
        "broker",
        "default",
        "realm-management",
        "security-admin-console",
    ]


def test_clean_clients__check_if_returns_allowed_client():
    """Test if the clean_clients function returns the allowed clients."""
    client = {
        "name": "blablabla",
        "description": "dummy description",
        "id": "abcdefghijklmn",
        "clientId": "dummy",
    }

    cleaned_clients = clean_clients(clients_list=[ClientModel(**client)])

    assert cleaned_clients == [ClientModel(**client)]


def test_clean_clients__check_if_returns_allowed_client_and_clean_not_allowed_client():
    """Test if the clean_clients function cleans the clients that are not allowed."""
    clients = [
        {
            "name": "blablabla",
            "description": "dummy description",
            "id": "abcdefghijklmn",
            "clientId": "dummy",
        },
        {"name": "default", "description": "dummy", "id": "abcdefghijklmn", "clientId": "default"},
    ]

    cleaned_clients = clean_clients(clients_list=[ClientModel(**client) for client in clients])

    assert cleaned_clients == [ClientModel(**clients[0])]
