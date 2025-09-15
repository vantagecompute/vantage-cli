"""Test the helper functions in the scripts module."""
from unittest import mock

import boto3
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber
from mypy_boto3_s3 import S3Client
from sqlalchemy.exc import ProgrammingError

from alembic.config import Config
from scripts.helpers import (
    _remove_files_from_disk,
    _write_files_in_disk,
    build_database_url,
    create_database,
    create_s3_bucket,
    delete_database,
    delete_s3_bucket,
    run_alembic_migration,
)


@mock.patch("scripts.helpers.drop_database")
def test_delete_database__successful_deletion(
    mocked_drop_database: mock.MagicMock, caplog: pytest.LogCaptureFixture
):
    """Test that the function deletes the database successfully."""
    conn_str = "dummy_conn_str"
    delete_database(conn_str)
    assert f"Deleting database for tenant {conn_str.split('/')[-1]}" in caplog.text
    assert "Database deleted" in caplog.text
    mocked_drop_database.assert_called_once_with(conn_str)


@mock.patch("scripts.helpers.drop_database")
def test_delete_database__database_does_not_exist(
    mocked_drop_database: mock.MagicMock, caplog: pytest.LogCaptureFixture
):
    """Test that the function logs and raises an error when the database does not exist."""
    conn_str = "dummy_conn_str"
    mocked_drop_database.side_effect = ProgrammingError(
        "DatabaseDoesNotExist",
        params=mock.MagicMock(),
        orig=BaseException(),
    )
    delete_database(conn_str)
    assert f"Deleting database for tenant {conn_str.split('/')[-1]}" in caplog.text
    assert "Database does not exist" in caplog.text
    mocked_drop_database.assert_called_once_with(conn_str)


@mock.patch("scripts.helpers.boto3")
@pytest.mark.parametrize(
    "tenant,aws_endpoint_url,aws_access_key_id,aws_secret_access_key",
    [
        ("dummy1", "dummy_url1", "123", "abc"),
        ("dummy2", "dummy_url2", "abc", "123"),
        ("dummy3", "dummy_url3", "321", "cba"),
    ],
)
def test_delete_s3_bucket(
    mocked_boto3: mock.MagicMock,
    tenant: str,
    aws_endpoint_url: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
):
    """Test that the function deletes the S3 bucket successfully."""
    s3: S3Client = boto3.client("s3")

    mocked_boto3.client = mock.Mock(return_value=s3)

    stubber = Stubber(s3)
    stubber.add_response(
        "delete_bucket",
        expected_params={"Bucket": tenant},
        service_response={
            "ResponseMetadata": {"RequestId": "abc123", "HTTPStatusCode": 204, "HostId": "abc123"},
        },
    )

    with stubber:
        delete_s3_bucket(
            tenant=tenant,
            endpoint_url=aws_endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    mocked_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=aws_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


@mock.patch("scripts.helpers.boto3")
@pytest.mark.parametrize(
    "tenant,aws_endpoint_url,aws_access_key_id,aws_secret_access_key",
    [
        ("dummy1", "dummy_url1", "123", "abc"),
        ("dummy2", "dummy_url2", "abc", "123"),
        ("dummy3", "dummy_url3", "321", "cba"),
    ],
)
def test_delete_s3_bucket__no_such_bucket_error(
    mocked_boto3: mock.MagicMock,
    tenant: str,
    aws_endpoint_url: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
):
    """Test that the function handles the NoSuchBucket error."""
    s3: S3Client = boto3.client("s3")

    mocked_boto3.client = mock.Mock(return_value=s3)

    stubber = Stubber(s3)
    stubber.add_response(
        "delete_bucket",
        expected_params={"Bucket": tenant},
        service_response={
            "ResponseMetadata": {"RequestId": "abc123", "HTTPStatusCode": 204, "HostId": "abc123"},
        },
    )

    with stubber:
        delete_s3_bucket(
            tenant=tenant,
            endpoint_url=aws_endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    mocked_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=aws_endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )


@mock.patch("scripts.helpers.os")
def test_remove_files_from_disk(mocked_os: mock.Mock):
    """Test that the function removes the files from disk correctly."""
    mocked_os.remove = mock.Mock()
    _remove_files_from_disk()
    mocked_os.remove.assert_has_calls(calls=[mock.call("alembic/alembic.ini"), mock.call("alembic/env.py")])


@mock.patch("builtins.open")
def test_write_files_in_disk(mocked_open: mock.Mock):
    """Test that the function writes the files in disk correctly."""
    mocked_open_instance = mock.Mock()
    mocked_open_instance.write = mock.Mock()
    mocked_open_instance.write.return_value = None
    mocked_open_instance.close = mock.Mock()
    mocked_open_instance.close.return_value = None

    mocked_open.return_value = mocked_open_instance

    test_file_1 = "test_file_1"
    test_file_2 = "test_file_2"

    _write_files_in_disk(test_file_1, test_file_2)

    mocked_open.assert_has_calls(
        calls=[
            mock.call("alembic/alembic.ini", "w"),
            mock.call().write(test_file_1),
            mock.call().close(),
            mock.call("alembic/env.py", "w"),
            mock.call().write(test_file_2),
            mock.call().close(),
        ]
    )


@mock.patch("scripts.helpers.command")
@mock.patch("scripts.helpers._write_files_in_disk")
@mock.patch("scripts.helpers._remove_files_from_disk")
@mock.patch("scripts.helpers.Environment")
@mock.patch("scripts.helpers.os")
@mock.patch("scripts.helpers.Path")
@mock.patch("scripts.helpers.create_engine")
@mock.patch("scripts.helpers.MigrationContext")
@mock.patch("scripts.helpers.Config")
@pytest.mark.parametrize(
    "conn_str,tenant,alembic_config_path",
    [
        (
            "postgres://user1:password1@omega:5432/8ce1f6e7-68ab-4dd2-bc61-51b8f54d8e9a",
            "8ce1f6e7-68ab-4dd2-bc61-51b8f54d8e9a",
            "rho/alembic.ini",
        ),
        (
            "postgres://alpha:beta@mu:5432/9c34e42b-24a3-47fc-bc8f-eeb67d6b13de",
            "9c34e42b-24a3-47fc-bc8f-eeb67d6b13de",
            "sigma/alembic.ini",
        ),
        (
            "postgres://gamma:delta@omicron:5432/f7d81e5a-8408-4d5d-890d-4b609d0482cf",
            "f7d81e5a-8408-4d5d-890d-4b609d0482cf",
            "tau/alembic.ini",
        ),
        (
            "postgres://psi:epsilon@theta:5432/3d46d4f5-3172-4b57-a3c9-d51832a3b42d",
            "3d46d4f5-3172-4b57-a3c9-d51832a3b42d",
            "chi/alembic.ini",
        ),
        (
            "postgres://pi:tau@chi:5432/b345d3e6-daa9-4a4e-8904-1db7b9c224e8",
            "b345d3e6-daa9-4a4e-8904-1db7b9c224e8",
            "psi/alembic.ini",
        ),
    ],
)
def test_run_alembic_migration(
    mocked_config: mock.Mock,
    mocked_migration_context: mock.Mock,
    mocked_create_engine: mock.Mock,
    mocked_path: mock.Mock,
    mocked_os: mock.Mock,
    mocked_jinja_environment: mock.Mock,
    mocked_remove_files_from_disk: mock.Mock,
    mocked_write_files_in_disk: mock.Mock,
    mocked_command: mock.Mock,
    conn_str: str,
    tenant: str,
    alembic_config_path: str,
    caplog: pytest.LogCaptureFixture,
):
    """Test that the function runs the alembic migrations correctly."""
    mocked_command.upgrade = mock.Mock()

    mocked_jinja_template_render = mock.Mock()
    mocked_jinja_template_render.return_value = "dummy return value"

    mocked_jinja_env_instance = mock.Mock()
    mocked_jinja_env_instance.get_template = mock.Mock()
    mocked_jinja_env_instance.get_template.return_value = mocked_jinja_template_render

    mocked_jinja_environment.return_value = mocked_jinja_env_instance

    cwd = "dummy/directory2"

    mocked_path.return_value = cwd

    mocked_os.getcwd = mock.Mock()
    mocked_os.getcwd.return_value = cwd
    mocked_os.chdir = mock.Mock()

    mocked_connection = mock.Mock()
    mocked_engine = mock.Mock()
    mocked_engine.connect = mock.Mock()
    mocked_engine.connect.return_value = mocked_connection
    mocked_create_engine.return_value = mocked_engine

    mocked_migration_context.configure = mock.Mock(return_value=None)

    alembic_config = Config("alembic/alembic.ini")
    mocked_config.return_value = alembic_config

    run_alembic_migration(conn_str, alembic_config_path)

    mocked_command.upgrade.assert_called_once_with(alembic_config, "head")
    mocked_write_files_in_disk.assert_called_once_with(
        mocked_jinja_environment().get_template().render(), mocked_jinja_environment().get_template().render()
    )
    mocked_remove_files_from_disk.assert_called_once_with()
    mocked_os.chdir.assert_has_calls(calls=[mock.call(alembic_config_path), mock.call(cwd)])
    mocked_path.assert_called_once_with(cwd)
    mocked_create_engine.assert_called_once_with(conn_str)
    mocked_engine.connect.assert_called_once_with()
    mocked_engine.assert_not_called()
    mocked_migration_context.configure.assert_called_once_with(mocked_connection)
    mocked_config.assert_called_once_with("alembic/alembic.ini")
    assert f"Running alembic migrations for tenant {tenant}" in caplog.text


@pytest.mark.parametrize(
    "database,user,password,host,port,driver,expected_database_url",
    [
        (
            "omega",
            "user1",
            "password1",
            "omega",
            5432,
            "postgres",
            "postgres://user1:password1@omega:5432/omega",
        ),
        ("mu", "alpha", "beta", "mu", 5432, "postgresql", "postgresql://alpha:beta@mu:5432/mu"),
        ("omicron", "gamma", "delta", "omicron", 3306, "mysql", "mysql://gamma:delta@omicron:3306/omicron"),
        ("theta", "psi", "epsilon", "delta", 5432, "sqlite", "sqlite://psi:epsilon@delta:5432/theta"),
    ],
)
def test_build_database_url(
    database: str, user: str, password: str, host: str, port: int, driver: str, expected_database_url: str
):
    """Test that the function builds the database URL correctly."""
    result_database_url = build_database_url(
        database=database,
        user=user,
        password=password,
        host=host,
        port=port,
        driver=driver,
    )
    assert result_database_url == expected_database_url


@mock.patch("scripts.helpers.boto3")
@pytest.mark.parametrize("tenant", [("dummy1"), ("dummy2")])
def test_create_s3_bucket__no_error(mocked_boto3: mock.Mock, tenant: str, caplog: pytest.LogCaptureFixture):
    """Test that the function creates a bucket with the given name."""
    endpoit_url = "AAA"
    aws_access_key_id = "BBB"
    aws_secret_access_key = "CCC"

    # mock the S3Client class
    mocked_s3_client = mock.Mock()
    mocked_s3_client.create_bucket = mock.Mock()
    mocked_s3_client.create_bucket.return_value = None

    # mock the Boto3Client class
    mocked_boto3.client = mock.Mock()
    mocked_boto3.client.return_value = mocked_s3_client

    create_s3_bucket(
        tenant=tenant,
        endpoint_url=endpoit_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    mocked_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=endpoit_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    mocked_s3_client.create_bucket.assert_called_once_with(Bucket=tenant)
    assert f"Creating S3 bucket for tenant {tenant}" in caplog.text
    assert f"S3 bucket created for tenant {tenant}" in caplog.text


@mock.patch("scripts.helpers.boto3")
@pytest.mark.parametrize("tenant", [("dummy1"), ("dummy2")])
def test_create_s3_bucket__check_bucket_already_exists_error(
    mocked_boto3: mock.Mock, tenant: str, caplog: pytest.LogCaptureFixture
):
    """Test that the function creates a bucket with the given name."""
    endpoit_url = "AAA"
    aws_access_key_id = "BBB"
    aws_secret_access_key = "CCC"

    # mock the S3Client class
    mocked_s3_client = mock.Mock()
    mocked_s3_client.create_bucket = mock.Mock()
    mocked_s3_client.create_bucket.return_value = None
    mocked_s3_client.create_bucket.side_effect = ClientError(
        error_response={"Error": {"Code": "BucketAlreadyExists"}},
        operation_name="CreateBucket",
    )
    mocked_s3_client.delete_bucket = mock.Mock()
    mocked_s3_client.delete_bucket.return_value = None

    # mock the Boto3Client class
    mocked_boto3.client = mock.Mock()
    mocked_boto3.client.return_value = mocked_s3_client

    with pytest.raises(ClientError) as err:
        create_s3_bucket(
            tenant=tenant,
            endpoint_url=endpoit_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    assert err.value.response["Error"]["Code"] == "BucketAlreadyExists"
    mocked_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=endpoit_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    mocked_s3_client.create_bucket.assert_has_calls(
        calls=[mock.call(Bucket=tenant), mock.call(Bucket=tenant)]
    )
    mocked_s3_client.delete_bucket.assert_called_once_with(Bucket=tenant)
    assert f"Creating S3 bucket for tenant {tenant}" in caplog.text
    assert "Bucket already exists. Deleting and creating again." in caplog.text
    assert f"S3 bucket created for tenant {tenant}" in caplog.text


@mock.patch("scripts.helpers.boto3")
@pytest.mark.parametrize("tenant", [("dummy1"), ("dummy2")])
def test_create_s3_bucket__check_not_mapped_error(
    mocked_boto3: mock.Mock, tenant: str, caplog: pytest.LogCaptureFixture
):
    """Test that the function creates a bucket with the given name."""
    endpoit_url = "AAA"
    aws_access_key_id = "BBB"
    aws_secret_access_key = "CCC"

    # mock the S3Client class
    mocked_s3_client = mock.Mock()
    mocked_s3_client.create_bucket = mock.Mock()
    mocked_s3_client.create_bucket.return_value = None
    mocked_s3_client.create_bucket.side_effect = ClientError(
        error_response={"Error": {"Code": "NotMappedError"}},
        operation_name="CreateBucket",
    )
    mocked_s3_client.delete_bucket = mock.Mock()
    mocked_s3_client.delete_bucket.return_value = None

    # mock the Boto3Client class
    mocked_boto3.client = mock.Mock()
    mocked_boto3.client.return_value = mocked_s3_client

    with pytest.raises(ClientError) as err:
        create_s3_bucket(
            tenant=tenant,
            endpoint_url=endpoit_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

    assert err.value.response["Error"]["Code"] == "NotMappedError"
    mocked_boto3.client.assert_called_once_with(
        "s3",
        endpoint_url=endpoit_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    mocked_s3_client.create_bucket.assert_called_once_with(Bucket=tenant)
    mocked_s3_client.delete_bucket.assert_not_called()
    assert f"Creating S3 bucket for tenant {tenant}" in caplog.text


@mock.patch("scripts.helpers.create_db", return_value=None)
@pytest.mark.parametrize(
    "conn_str",
    [
        ("postgres://user1:password1@omega:5432/8ce1f6e7-68ab-4dd2-bc61-51b8f54d8e9a"),
        ("postgres://alpha:beta@mu:5432/9c34e42b-24a3-47fc-bc8f-eeb67d6b13de"),
        ("postgres://gamma:delta@omicron:5432/f7d81e5a-8408-4d5d-890d-4b609d0482cf"),
        ("postgres://psi:epsilon@theta:5432/3d46d4f5-3172-4b57-a3c9-d51832a3b42d"),
        ("postgres://pi:tau@chi:5432/b345d3e6-daa9-4a4e-8904-1db7b9c224e8"),
    ],
)
def test_create_database__no_error(
    mocked_create_db: mock.Mock, conn_str: str, caplog: pytest.LogCaptureFixture
):
    """Test that the function creates a database with the given name."""
    create_database(conn_str)

    mocked_create_db.assert_called_once_with(conn_str)
    assert f"Creating database for tenant {conn_str.split('/')[-1]}" in caplog.text
    assert "Database created" in caplog.text


@mock.patch("scripts.helpers.create_db", return_value=None)
@mock.patch("scripts.helpers.drop_database", return_value=None)
@pytest.mark.parametrize(
    "conn_str",
    [
        ("postgres://user1:password1@omega:5432/8ce1f6e7-68ab-4dd2-bc61-51b8f54d8e9a"),
        ("postgres://alpha:beta@mu:5432/9c34e42b-24a3-47fc-bc8f-eeb67d6b13de"),
        ("postgres://gamma:delta@omicron:5432/f7d81e5a-8408-4d5d-890d-4b609d0482cf"),
        ("postgres://psi:epsilon@theta:5432/3d46d4f5-3172-4b57-a3c9-d51832a3b42d"),
        ("postgres://pi:tau@chi:5432/b345d3e6-daa9-4a4e-8904-1db7b9c224e8"),
    ],
)
def test_create_database__check_when_database_already_exists(
    mocked_drop_database: mock.Mock,
    mocked_create_db: mock.Mock,
    conn_str: str,
    caplog: pytest.LogCaptureFixture,
):
    """Test that the function creates a database with the given name."""
    mocked_create_db.side_effect = ProgrammingError(
        statement="DuplicateDatabase - Database already exists",
        params=mock.MagicMock(),
        orig=BaseException(),
    )

    with pytest.raises(ProgrammingError):
        create_database(conn_str)

    mocked_create_db.assert_has_calls(calls=[mock.call(conn_str), mock.call(conn_str)])
    mocked_drop_database.assert_called_once_with(conn_str)
    assert f"Creating database for tenant {conn_str.split('/')[-1]}" in caplog.text
    assert "Database already exists. Deleting and creating again." in caplog.text
    assert "Database created" in caplog.text


@mock.patch("scripts.helpers.create_db", return_value=None)
@mock.patch("scripts.helpers.drop_database", return_value=None)
@pytest.mark.parametrize(
    "conn_str",
    [
        ("postgres://user1:password1@omega:5432/8ce1f6e7-68ab-4dd2-bc61-51b8f54d8e9a"),
        ("postgres://alpha:beta@mu:5432/9c34e42b-24a3-47fc-bc8f-eeb67d6b13de"),
        ("postgres://gamma:delta@omicron:5432/f7d81e5a-8408-4d5d-890d-4b609d0482cf"),
        ("postgres://psi:epsilon@theta:5432/3d46d4f5-3172-4b57-a3c9-d51832a3b42d"),
        ("postgres://pi:tau@chi:5432/b345d3e6-daa9-4a4e-8904-1db7b9c224e8"),
    ],
)
def test_create_database__check_not_mapped_error(
    mocked_drop_database: mock.Mock,
    mocked_create_db: mock.Mock,
    conn_str: str,
    caplog: pytest.LogCaptureFixture,
):
    """Test that the function creates a database with the given name."""
    mocked_create_db.side_effect = ProgrammingError(
        statement="NotMappedError - This error is unknown",
        params=mock.MagicMock(),
        orig=BaseException(),
    )

    with pytest.raises(ProgrammingError):
        create_database(conn_str)

    mocked_create_db.assert_called_once_with(conn_str)
    mocked_drop_database.assert_not_called()
    assert f"Creating database for tenant {conn_str.split('/')[-1]}" in caplog.text
