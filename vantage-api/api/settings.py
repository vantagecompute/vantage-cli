"""Core module for storing application settings."""
from pathlib import Path
from typing import Annotated, Literal, Optional

import toml
from armasec import Armasec
from pydantic import (
    AnyUrl,
    BaseSettings,
    EmailStr,
    Field,
    HttpUrl,
    confloat,
    conint,
    root_validator,
    validator,
)

from api.utils.logging import logger


class Settings(BaseSettings):

    """Core class for storing application settings."""

    # CI purposes
    TEST_ENV: bool = False

    # Sentry
    SENTRY_DSN: Optional[HttpUrl] = None
    SENTRY_TRACES_SAMPLE_RATE: Annotated[float, confloat(gt=0, le=1.0)] = 0.01
    SENTRY_SAMPLE_RATE: Annotated[float, confloat(gt=0.0, le=1.0)] = 0.25
    SENTRY_PROFILING_SAMPLE_RATE: Annotated[float, confloat(gt=0.0, le=1.0)] = 0.01

    # authentication
    ARMASEC_DOMAIN: str
    ARMASEC_LOGGER: str | None = None
    GUARD: Armasec
    MANAGEMENT_CLIENT_ID: str
    MANAGEMENT_CLIENT_SECRET: str
    MANAGEMENT_ENDPOINT: AnyUrl

    # API database
    DB_USERNAME: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_HOST_READ_REPLICA: Optional[str] = None
    DB_PORT: int = 5432
    DB_POOL_SIZE: int = 32
    DB_MAX_OVERFLOW: int = 10
    DB_JIT: Literal["off", "on"] = "on"

    # Optional parameter for local usage only
    AWS_ENDPOINT_URL: str | None = None

    # AWS Marketplace Metering
    AWS_ROLE_NAME_MKT: str = Field(
        "arn:aws:iam::471112618457:role/BasicMarketplaceUsage",
        description="The role name to assume for AWS Marketplace Metering operations.",
    )
    VANTAGE_PRODUCT_CODE: str = Field(
        "ej0j89gonlyhiw8rs6ccyykzd", description="The product code for Vantage on the AWS Marketplace"
    )

    # AWS Marketplace Listener
    AWS_MKT_SUBSCRIPTION_TOPIC: str = Field(
        description="The subscription topic to listen for AWS Marketplace subscription events"
    )
    SQS_MAX_NUMBER_OF_MESSAGES: int = Field(
        description="Max number of messages to get from sqs at once", default=1
    )

    # Keycloak database
    KC_DB_HOST: str
    KC_DB_USERNAME: str
    KC_DB_PASSWORD: str
    KC_DB_DATABASE: str
    KC_DB_PORT: int = 5432

    # RabbitMQ
    MQ_HOST: str
    MQ_USERNAME: str
    MQ_PASSWORD: str
    MQ_VIRTUAL_HOST: str
    MQ_EXCHANGE: str
    MQ_PUBLISH_TIMEOUT: int = 10

    # Upstream policy required by Vantage
    VANTAGE_INTEGRATION_POLICY_URL: str = (
        "https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json"
    )

    # email
    SOURCE_EMAIL: EmailStr = "info@omnivector.solutions"
    CONFIGURATION_SET: str = "Default"
    INVITE_TEMPLATE_NAME: str = "VantageInviteEmailTemplate-{}".format(
        toml.load("pyproject.toml")["tool"]["poetry"]["version"].replace(".", "_")
    )
    DELETE_ORG_TEMPLATE_NAME: str = "VantageDeleteOrgEmailTemplate-{}".format(
        toml.load("pyproject.toml")["tool"]["poetry"]["version"].replace(".", "_")
    )
    REPLY_TO: Optional[EmailStr] = None

    APP_DOMAIN: str = "vantagecompute.ai"

    # general configuration
    CACHE_DIR = Path.home() / ".cache/vantage-api"
    MONITOR_AWS_CLUSTER_STATUS_INTERVAL: Annotated[int, conint(ge=1, le=30)] = 5

    STAGE: str = "staging"

    class Config:
        """Configuration class for the settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"

    @root_validator(pre=True)
    def pre_validator(cls, values):  # noqa: N805
        """Pre validator to set default values."""
        if not values.get("GUARD"):
            values.update(
                GUARD=Armasec(
                    domain=values.get("ARMASEC_DOMAIN"),
                    debug_logger=getattr(logger, values.get("ARMASEC_LOGGER") or "", None),
                ),
            )

        return values

    @validator("AWS_ENDPOINT_URL")
    def validate_aws_endpoint_url(cls, v):  # noqa: N805
        """Validate the AWS_ENDPOINT_URL."""
        if v == "":
            return None
        return v


SETTINGS = Settings()
logger.info("##### Initializing `SETTINGS` successfully")
