"""Core module for defining functions whose purpose is to delete all necessary resources for each individual microservice."""  # noqa: E501
import os

from scripts.helpers import build_database_url, delete_database, delete_s3_bucket


def notifications_api(tenant: str) -> None:
    """Delete a PostgreSQL database for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("NOTIFICATIONS_API_POSTGRES_USER"),
        password=os.environ.get("NOTIFICATIONS_API_POSTGRES_PASSWORD"),
        host=os.environ.get("NOTIFICATIONS_API_POSTGRES_HOST"),
    )
    delete_database(dabatase_url)
    return


def sos_api(tenant: str) -> None:
    """Delete a PostgreSQL database and a S3 bucket for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("SOS_API_POSTGRES_USER"),
        password=os.environ.get("SOS_API_POSTGRES_PASSWORD"),
        host=os.environ.get("SOS_API_POSTGRES_HOST"),
    )
    delete_database(dabatase_url)
    delete_s3_bucket(
        tenant=tenant,
        endpoint_url=os.environ.get("SOS_API_S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("SOS_API_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("SOS_API_S3_SECRET_ACCESS_KEY"),
    )
    return


def vantage_api(tenant: str) -> None:
    """Delete a PostgreSQL database for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("VANTAGE_API_POSTGRES_USER"),
        password=os.environ.get("VANTAGE_API_POSTGRES_PASSWORD"),
        host=os.environ.get("VANTAGE_API_POSTGRES_HOST"),
    )
    delete_database(dabatase_url)
    return


def jobbergate_api(tenant: str) -> None:
    """Delete a PostgreSQL database and a S3 bucket for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("JOBBERGATE_API_POSTGRES_USER"),
        password=os.environ.get("JOBBERGATE_API_POSTGRES_PASSWORD"),
        host=os.environ.get("JOBBERGATE_API_POSTGRES_HOST"),
    )
    delete_database(dabatase_url)
    delete_s3_bucket(
        tenant=tenant,
        endpoint_url=os.environ.get("JOBBERGATE_API_S3_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("JOBBERGATE_API_S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("JOBBERGATE_API_S3_SECRET_ACCESS_KEY"),
    )
    return


def lm_api(tenant: str) -> None:
    """Delete a PostgreSQL database for the given tenant."""
    dabatase_url = build_database_url(
        database=tenant,
        user=os.environ.get("LM_API_POSTGRES_USER"),
        password=os.environ.get("LM_API_POSTGRES_PASSWORD"),
        host=os.environ.get("LM_API_POSTGRES_HOST"),
    )
    delete_database(dabatase_url)
    return
