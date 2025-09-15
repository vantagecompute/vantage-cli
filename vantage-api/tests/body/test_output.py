"""Core module for testing output pydantic models."""
import pytest
from pydantic import ValidationError

from api.body.output import IdPModel


def test_idp_model_validation_logic__client_id_as_str():
    """Test if the IdPModel is created correctly when the config is a string."""
    payload = {
        "internalId": "test_id",
        "config": "test",
        "providerId": "test_provider_id",
    }
    model = IdPModel(**payload)

    assert model.id == "test_id"
    assert model.client_id == "test"
    assert model.provider_id == "test_provider_id"


def test_idp_model_validation_logic__client_id_as_dict():
    """Test if the IdPModel is created correctly when the config is a dict."""
    payload = {
        "internalId": "test_id",
        "config": {"clientId": "test"},
        "providerId": "test_provider_id",
    }
    model = IdPModel(**payload)

    assert model.id == "test_id"
    assert model.client_id == "test"
    assert model.provider_id == "test_provider_id"


def test_idp_model_validation_logic__check_validation_error():
    """Test if the IdPModel raises a validation error when the config is not a string or a dict."""
    payload = {
        "internalId": "test_id",
        "config": [],
        "providerId": "test_provider_id",
    }

    with pytest.raises(ValidationError):
        IdPModel(**payload)
