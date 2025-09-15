"""Test the create_resources script."""
from unittest import mock

from scripts.create_resources import notifications_api, sos_api, vantage_api


@mock.patch("scripts.create_resources.os")
@mock.patch("scripts.create_resources.run_alembic_migration")
@mock.patch("scripts.create_resources.create_database")
@mock.patch("scripts.create_resources.build_database_url")
def test_create_notifications_api_resources(
    mocked_build_database_url: mock.Mock,
    mocked_create_database: mock.Mock,
    mocked_run_alembic_migration: mock.Mock,
    mocked_os: mock.Mock,
):
    """Test if the notifications-api resources are created correctly."""
    postgres_user = "XXXXXXXXXX"
    postgres_password = "YYYYYYYYYY"
    postgres_host = "ZZZZZZZZZZ"
    tenant = "WWWWWWWWWW"
    postgres_conn_str = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{tenant}"

    mocked_build_database_url.return_value = postgres_conn_str

    mocked_os.environ = {
        "NOTIFICATIONS_API_POSTGRES_USER": postgres_user,
        "NOTIFICATIONS_API_POSTGRES_PASSWORD": postgres_password,
        "NOTIFICATIONS_API_POSTGRES_HOST": postgres_host,
    }

    notifications_api(tenant=tenant)

    mocked_build_database_url.assert_called_once_with(
        database=tenant,
        user=postgres_user,
        password=postgres_password,
        host=postgres_host,
    )
    mocked_create_database.assert_called_once_with(postgres_conn_str)
    mocked_run_alembic_migration.assert_called_once_with(postgres_conn_str, "notifications-api")


@mock.patch("scripts.create_resources.os")
@mock.patch("scripts.create_resources.run_alembic_migration")
@mock.patch("scripts.create_resources.create_database")
@mock.patch("scripts.create_resources.build_database_url")
@mock.patch("scripts.create_resources.create_s3_bucket")
def test_create_sos_api_resources(
    mocked_create_s3_bucket: mock.Mock,
    mocked_build_database_url: mock.Mock,
    mocked_create_database: mock.Mock,
    mocked_run_alembic_migration: mock.Mock,
    mocked_os: mock.Mock,
):
    """Test if the sos-api resources are created correctly."""
    postgres_user = "XXXXXXXXXX"
    postgres_password = "YYYYYYYYYY"
    postgres_host = "ZZZZZZZZZZ"
    tenant = "WWWWWWWWWW"
    s3_endpoint_url = "AAAAAAAAAA"
    aws_access_key_id = "BBBBBBBBBB"
    aws_secret_access_key = "CCCCCCCCCC"

    postgres_conn_str = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{tenant}"

    mocked_build_database_url.return_value = postgres_conn_str

    mocked_os.environ = {
        "SOS_API_POSTGRES_USER": postgres_user,
        "SOS_API_POSTGRES_PASSWORD": postgres_password,
        "SOS_API_POSTGRES_HOST": postgres_host,
        "SOS_API_S3_ENDPOINT_URL": s3_endpoint_url,
        "SOS_API_S3_ACCESS_KEY_ID": aws_access_key_id,
        "SOS_API_S3_SECRET_ACCESS_KEY": aws_secret_access_key,
    }

    sos_api(tenant=tenant)

    mocked_build_database_url.assert_called_once_with(
        database=tenant,
        user=postgres_user,
        password=postgres_password,
        host=postgres_host,
    )
    mocked_create_database.assert_called_once_with(postgres_conn_str)
    mocked_run_alembic_migration.assert_called_once_with(postgres_conn_str, "sos-api")
    mocked_create_s3_bucket.assert_called_once_with(
        tenant=tenant,
        endpoint_url=s3_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


@mock.patch("scripts.create_resources.os")
@mock.patch("scripts.create_resources.run_alembic_migration")
@mock.patch("scripts.create_resources.create_database")
@mock.patch("scripts.create_resources.build_database_url")
def test_create_vantage_api_resources(
    mocked_build_database_url: mock.Mock,
    mocked_create_database: mock.Mock,
    mocked_run_alembic_migration: mock.Mock,
    mocked_os: mock.Mock,
):
    """Test if the vantage-api resources are created correctly."""
    postgres_user = "XXXXXXXXXX"
    postgres_password = "YYYYYYYYYY"
    postgres_host = "ZZZZZZZZZZ"
    tenant = "WWWWWWWWWW"
    postgres_conn_str = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:5432/{tenant}"

    mocked_build_database_url.return_value = postgres_conn_str

    mocked_os.environ = {
        "VANTAGE_API_POSTGRES_USER": postgres_user,
        "VANTAGE_API_POSTGRES_PASSWORD": postgres_password,
        "VANTAGE_API_POSTGRES_HOST": postgres_host,
    }

    vantage_api(tenant=tenant)

    mocked_build_database_url.assert_called_once_with(
        database=tenant,
        user=postgres_user,
        password=postgres_password,
        host=postgres_host,
    )
    mocked_create_database.assert_called_once_with(postgres_conn_str)
    mocked_run_alembic_migration.assert_called_once_with(postgres_conn_str, "vantage-api")
