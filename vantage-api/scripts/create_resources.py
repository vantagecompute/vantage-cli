"""Core module for defining functions whose purpose is to create all necessary resources for each individual microservice."""  # noqa: E501
import os

from scripts.helpers import build_database_url, create_database, create_s3_bucket, run_alembic_migration


def notifications_api(tenant: str) -> None:
    """Create a PostgreSQL database for the given tenant and run migrations."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("NOTIFICATIONS_API_POSTGRES_USER"),
        password=os.environ.get("NOTIFICATIONS_API_POSTGRES_PASSWORD"),
        host=os.environ.get("NOTIFICATIONS_API_POSTGRES_HOST"),
    )
    create_database(dabatase_url)
    run_alembic_migration(dabatase_url, "notifications-api")  # pre-defined path based on the Dockerfile


def sos_api(tenant: str) -> None:
    """Create a PostgreSQL database and a S3 bucket for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("SOS_API_POSTGRES_USER"),
        password=os.environ.get("SOS_API_POSTGRES_PASSWORD"),
        host=os.environ.get("SOS_API_POSTGRES_HOST"),
    )
    create_database(dabatase_url)
    run_alembic_migration(dabatase_url, "sos-api")  # pre-defined path based on the Dockerfile
    create_s3_bucket(
        tenant=tenant,
        endpoint_url=os.environ.get("SOS_API_S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("SOS_API_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("SOS_API_S3_SECRET_ACCESS_KEY"),
    )


def vantage_api(tenant: str) -> None:
    """Create a PostgreSQL database for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("VANTAGE_API_POSTGRES_USER"),
        password=os.environ.get("VANTAGE_API_POSTGRES_PASSWORD"),
        host=os.environ.get("VANTAGE_API_POSTGRES_HOST"),
    )
    create_database(dabatase_url)
    run_alembic_migration(dabatase_url, "vantage-api")  # pre-defined path based on the Dockerfile


def jobbergate_api(tenant: str) -> None:
    """Create a PostgreSQL database and a S3 bucket for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("JOBBERGATE_API_POSTGRES_USER"),
        password=os.environ.get("JOBBERGATE_API_POSTGRES_PASSWORD"),
        host=os.environ.get("JOBBERGATE_API_POSTGRES_HOST"),
    )
    create_database(dabatase_url)
    run_alembic_migration(dabatase_url, "jobbergate-api")  # pre-defined path based on the Dockerfile
    create_s3_bucket(
        tenant=tenant,
        endpoint_url=os.environ.get("JOBBERGATE_API_S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("JOBBERGATE_API_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("JOBBERGATE_API_S3_SECRET_ACCESS_KEY"),
    )


def lm_api(tenant: str) -> None:
    """Create a PostgreSQL database for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("LM_API_POSTGRES_USER"),
        password=os.environ.get("LM_API_POSTGRES_PASSWORD"),
        host=os.environ.get("LM_API_POSTGRES_HOST"),
    )
    create_database(dabatase_url)
    run_alembic_migration(dabatase_url, "lm-api")  # pre-defined path based on the Dockerfile
