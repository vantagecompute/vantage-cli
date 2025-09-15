"""Core module for testing the functions that delete resources in the RPC server."""
from unittest import mock

import pytest

from scripts.delete_resources import jobbergate_api, lm_api, notifications_api, sos_api, vantage_api
from scripts.helpers import build_database_url


@mock.patch("scripts.delete_resources.os")
@mock.patch("scripts.delete_resources.delete_database")
@pytest.mark.parametrize(
    "db_user,db_passwd,db_host,tenant",
    [
        ("phi", "beta", "gama", "123"),
        ("theta", "epsilon", "alpha", "321"),
        ("coffee", "chocolate", "lambda", "abc91074cba"),
    ],
)
def test_delete_notifications_api_resources(
    mocked_delete_database: mock.MagicMock,
    mocked_os: mock.MagicMock,
    db_user: str,
    db_passwd: str,
    db_host: str,
    tenant: str,
):
    """Test if the Notifications API resources are delete correctly."""
    mocked_os.environ = {
        "NOTIFICATIONS_API_POSTGRES_USER": db_user,
        "NOTIFICATIONS_API_POSTGRES_PASSWORD": db_passwd,
        "NOTIFICATIONS_API_POSTGRES_HOST": db_host,
    }

    database_url = build_database_url(tenant, db_user, db_passwd, db_host)

    notifications_api(tenant)

    mocked_delete_database.assert_called_once_with(database_url)


@mock.patch("scripts.delete_resources.os")
@mock.patch("scripts.delete_resources.delete_database")
@mock.patch("scripts.delete_resources.delete_s3_bucket")
@pytest.mark.parametrize(
    "db_user,db_passwd,db_host,tenant,s3_url,access_key,secret_key",
    [
        ("phi", "beta", "gama", "123", "ethernal.s3.amazonaws.com", "super-secret-key", "not-secure-key"),
        (
            "theta",
            "epsilon",
            "alpha",
            "321",
            "endless.s3.amazonaws.com",
            "mega-secret-key",
            "even-less-secure-key",
        ),
        (
            "coffee",
            "chocolate",
            "lambda",
            "abc91074cba",
            "everlasting.s3.amazonaws.com",
            "outstading-secret-key",
            "shark123",
        ),
    ],
)
def test_delete_sos_api_resources(
    mocked_delete_s3_bucket: mock.MagicMock,
    mocked_delete_database: mock.MagicMock,
    mocked_os: mock.MagicMock,
    db_user: str,
    db_passwd: str,
    db_host: str,
    tenant: str,
    s3_url: str,
    access_key: str,
    secret_key: str,
):
    """Test if the SOS API resources are delete correctly."""
    mocked_os.environ = {
        "SOS_API_POSTGRES_USER": db_user,
        "SOS_API_POSTGRES_PASSWORD": db_passwd,
        "SOS_API_POSTGRES_HOST": db_host,
        "SOS_API_S3_ENDPOINT_URL": s3_url,
        "SOS_API_S3_ACCESS_KEY_ID": access_key,
        "SOS_API_S3_SECRET_ACCESS_KEY": secret_key,
    }

    database_url = build_database_url(tenant, db_user, db_passwd, db_host)

    sos_api(tenant)

    mocked_delete_database.assert_called_once_with(database_url)
    mocked_delete_s3_bucket.assert_called_once_with(
        tenant=tenant,
        endpoint_url=s3_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


@mock.patch("scripts.delete_resources.os")
@mock.patch("scripts.delete_resources.delete_database")
@pytest.mark.parametrize(
    "db_user,db_passwd,db_host,tenant",
    [
        ("phi", "beta", "gama", "123"),
        ("theta", "epsilon", "alpha", "321"),
        ("coffee", "chocolate", "lambda", "abc91074cba"),
    ],
)
def test_delete_vantage_api_resources(
    mocked_delete_database: mock.MagicMock,
    mocked_os: mock.MagicMock,
    db_user: str,
    db_passwd: str,
    db_host: str,
    tenant: str,
):
    """Test if the Vantage API resources are delete correctly."""
    mocked_os.environ = {
        "VANTAGE_API_POSTGRES_USER": db_user,
        "VANTAGE_API_POSTGRES_PASSWORD": db_passwd,
        "VANTAGE_API_POSTGRES_HOST": db_host,
    }

    database_url = build_database_url(tenant, db_user, db_passwd, db_host)

    vantage_api(tenant)

    mocked_delete_database.assert_called_once_with(database_url)


@mock.patch("scripts.delete_resources.os")
@mock.patch("scripts.delete_resources.delete_database")
@mock.patch("scripts.delete_resources.delete_s3_bucket")
@pytest.mark.parametrize(
    "db_user,db_passwd,db_host,tenant,s3_url,access_key,secret_key",
    [
        ("phi", "beta", "gama", "123", "ethernal.s3.amazonaws.com", "super-secret-key", "not-secure-key"),
        (
            "theta",
            "epsilon",
            "alpha",
            "321",
            "endless.s3.amazonaws.com",
            "mega-secret-key",
            "even-less-secure-key",
        ),
        (
            "coffee",
            "chocolate",
            "lambda",
            "abc91074cba",
            "everlasting.s3.amazonaws.com",
            "outstading-secret-key",
            "shark123",
        ),
    ],
)
def test_delete_jobbergate_api_resources(
    mocked_delete_s3_bucket: mock.MagicMock,
    mocked_delete_database: mock.MagicMock,
    mocked_os: mock.MagicMock,
    db_user: str,
    db_passwd: str,
    db_host: str,
    tenant: str,
    s3_url: str,
    access_key: str,
    secret_key: str,
):
    """Test if the Jobbergate API resources are delete correctly."""
    mocked_os.environ = {
        "JOBBERGATE_API_POSTGRES_USER": db_user,
        "JOBBERGATE_API_POSTGRES_PASSWORD": db_passwd,
        "JOBBERGATE_API_POSTGRES_HOST": db_host,
        "JOBBERGATE_API_S3_ENDPOINT_URL": s3_url,
        "JOBBERGATE_API_S3_ACCESS_KEY_ID": access_key,
        "JOBBERGATE_API_S3_SECRET_ACCESS_KEY": secret_key,
    }

    database_url = build_database_url(tenant, db_user, db_passwd, db_host)

    jobbergate_api(tenant)

    mocked_delete_database.assert_called_once_with(database_url)
    mocked_delete_s3_bucket.assert_called_once_with(
        tenant=tenant,
        endpoint_url=s3_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


@mock.patch("scripts.delete_resources.os")
@mock.patch("scripts.delete_resources.delete_database")
@pytest.mark.parametrize(
    "db_user,db_passwd,db_host,tenant",
    [
        ("phi", "beta", "gama", "123"),
        ("theta", "epsilon", "alpha", "321"),
        ("coffee", "chocolate", "lambda", "abc91074cba"),
    ],
)
def test_delete_lm_api_resources(
    mocked_delete_database: mock.MagicMock,
    mocked_os: mock.MagicMock,
    db_user: str,
    db_passwd: str,
    db_host: str,
    tenant: str,
):
    """Test if the License Manager API resources are delete correctly."""
    mocked_os.environ = {
        "LM_API_POSTGRES_USER": db_user,
        "LM_API_POSTGRES_PASSWORD": db_passwd,
        "LM_API_POSTGRES_HOST": db_host,
    }

    database_url = build_database_url(tenant, db_user, db_passwd, db_host)

    lm_api(tenant)

    mocked_delete_database.assert_called_once_with(database_url)
