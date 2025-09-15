"""Core module for generic function used across the scripts."""
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader, Template
from loguru import logger
from mypy_boto3_s3 import S3Client
from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError
from sqlalchemy_utils import create_database as create_db
from sqlalchemy_utils import drop_database

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext


def delete_database(conn_str: str) -> None:
    """Delete a database based on the connection string."""
    logger.debug(f"Deleting database for tenant {conn_str.split('/')[-1]}")
    try:
        drop_database(conn_str)
    except ProgrammingError as err:
        if "DatabaseDoesNotExist" in str(err):
            logger.debug("Database does not exist")
        else:
            raise err
    logger.success("Database deleted")


def create_database(conn_str: str) -> None:
    """Create a database based on the connection string."""
    logger.debug(f"Creating database for tenant {conn_str.split('/')[-1]}")
    try:
        create_db(conn_str)
    except ProgrammingError as err:
        if "DuplicateDatabase" in str(err):
            logger.debug("Database already exists. Deleting and creating again.")
            drop_database(conn_str)
            create_db(conn_str)
        else:
            raise err
    finally:
        logger.success("Database created")


def build_database_url(
    database: str,
    user: str,
    password: str,
    host: str = "localhost",
    port: int = 5432,
    driver: str = "postgresql",
) -> str:
    """Build a database url based on the parameters."""
    logger.debug(f"Building database URL for tenant {database}")
    return f"{driver}://{user}:{password}@{host}:{port}/{database}"


def create_s3_bucket(
    tenant: str, endpoint_url: str, aws_access_key_id: str, aws_secret_access_key: str
) -> None:
    """Create a S3 bucket based on the parameters."""
    s3: S3Client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    logger.debug(f"Creating S3 bucket for tenant {tenant}")
    try:
        s3.create_bucket(Bucket=tenant)
    except ClientError as err:
        if err.response["Error"]["Code"] == "BucketAlreadyExists":
            logger.debug("Bucket already exists. Deleting and creating again.")
            s3.delete_bucket(Bucket=tenant)
            s3.create_bucket(Bucket=tenant)
        else:
            raise err
    finally:
        logger.success(f"S3 bucket created for tenant {tenant}")

    return


def delete_s3_bucket(
    tenant: str, endpoint_url: str, aws_access_key_id: str, aws_secret_access_key: str
) -> None:
    """Delete a S3 bucket based on the parameters."""
    s3: S3Client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    logger.debug(f"Deleting S3 bucket for tenant {tenant}")
    try:
        s3.delete_bucket(Bucket=tenant)
    except ClientError as err:
        if err.response["Error"]["Code"] == "NoSuchBucket":
            logger.debug("Bucket does not exist")
        else:
            raise err
    finally:
        logger.success(f"S3 bucket deleted for tenant {tenant}")

    return


def _write_files_in_disk(alembic_ini_template: Template, env_py_template: Template) -> None:
    """Write alembic templates in disk."""
    logger.debug("Writing alembic templates to disk")
    alembic_ini_file = open("alembic/alembic.ini", "w")
    alembic_ini_file.write(alembic_ini_template)
    alembic_ini_file.close()
    env_py_file = open("alembic/env.py", "w")
    env_py_file.write(env_py_template)
    env_py_file.close()
    logger.debug("Alembic templates written in disk")


def _remove_files_from_disk():
    """Remove alembic templates from disk."""
    logger.debug("Removing alembic templates from disk")
    os.remove("alembic/alembic.ini")
    os.remove("alembic/env.py")
    logger.debug("Alembic templates removed from disk")


def run_alembic_migration(conn_str: str, alembic_parent_path: str) -> None:
    """Run alembic migrations for a given database."""
    logger.debug("Loading alembic templates")
    jinja_env = Environment(loader=FileSystemLoader("templates"))
    alembic_ini_template = jinja_env.get_template("alembic.ini.jinja").render(conn_str=conn_str)
    env_py_template = jinja_env.get_template("env.py.jinja").render()

    cwd = os.getcwd()
    logger.debug(f"Bumping directory from {os.getcwd()} to {alembic_parent_path}")
    os.chdir(alembic_parent_path)

    _write_files_in_disk(alembic_ini_template, env_py_template)

    logger.debug(f"Running alembic migrations for tenant {conn_str.split('/')[-1]}")
    engine = create_engine(conn_str)
    conn = engine.connect()
    MigrationContext.configure(conn)
    alembic_config = Config("alembic/alembic.ini")
    command.upgrade(alembic_config, "head")

    _remove_files_from_disk()

    target_dir = Path(cwd)
    logger.debug(f"Bumping from directory {os.getcwd()} to {str(target_dir)}")
    os.chdir(target_dir)
    logger.success("Alembic migrations completed")
