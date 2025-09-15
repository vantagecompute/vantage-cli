"""Pytest configuration file."""
#!/usr/bin/env python3
import asyncio
import os
import re
from collections.abc import Generator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncContextManager, AsyncGenerator, Callable, Collection, Dict, List, Union
from unittest import mock

import aws_cdk.assertions as assertions
import httpx
import pytest
import respx
import sqlalchemy
from asgi_lifespan import LifespanManager
from httpx import AsyncClient, Response
from loguru import logger
from sqlalchemy import delete, insert, inspect, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Delete, Insert, Select
from sqlalchemy_utils import create_database, database_exists
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer

from alembic import command
from alembic.config import Config
from api.graphql_app import types
from api.graphql_app.helpers import cluster_name_to_client_id
from api.graphql_app.types import Context, DecodedToken
from api.identity.management_api import backend_client
from api.settings import SETTINGS
from api.sql_app import models
from api.sql_app.enums import (
    ClusterProviderEnum,
    ClusterStatusEnum,
    SubscriptionTiersNames,
    SubscriptionTypesNames,
)
from api.sql_app.session import create_async_session, keycloak_transaction


@pytest.fixture
async def test_app():
    """Yield the FastAPI application for testing purposes."""
    from api.main import app as test_app

    async with LifespanManager(test_app):
        yield test_app


@pytest.fixture(scope="session")
def organization_id() -> str:
    """Yield a dummy organization ID."""
    return "d4e6b8d6-9f3d-4e5e-9a5c-4c9a1e0f5d5c"


@pytest.fixture
def inviter_id() -> str:
    """Yield a dummy inviter ID."""
    return "b86ccef3-cbe6-4bcd-b8a3-4fe52bb9ace6"


@pytest.fixture
def invitee_id() -> str:
    """Yield a dummy invitee ID."""
    return "d7f8e9d7-9f3d-4e5e-9a5c-4c9a1e0f5d5c"


@pytest.fixture
def invitee_email() -> str:
    """Yield a dummy invitee email."""
    return "peace@ilovetesting.com"


@pytest.fixture(scope="session")
def keycloak_postgresql():
    """Run a postgres container to emulate the keycloak database."""
    with PostgresContainer("postgres:10.20") as postgres:
        user = postgres.POSTGRES_USER
        passwd = postgres.POSTGRES_PASSWORD
        db = postgres.POSTGRES_DB
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        with (
            mock.patch.object(SETTINGS, "KC_DB_HOST", new=host),
            mock.patch.object(SETTINGS, "KC_DB_USERNAME", new=user),
            mock.patch.object(SETTINGS, "KC_DB_PASSWORD", new=passwd),
            mock.patch.object(SETTINGS, "KC_DB_DATABASE", new=db),
            mock.patch.object(SETTINGS, "KC_DB_PORT", new=port),
        ):
            yield postgres


@pytest.fixture(scope="session")
def api_postgres(organization_id: str):
    """Run a postgres container to emulate the API database."""
    with PostgresContainer("postgres:14.1", dbname=organization_id) as postgres:
        user = postgres.POSTGRES_USER
        passwd = postgres.POSTGRES_PASSWORD
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)
        with (
            mock.patch.object(SETTINGS, "DB_HOST", new=host),
            mock.patch.object(SETTINGS, "DB_USERNAME", new=user),
            mock.patch.object(SETTINGS, "DB_PASSWORD", new=passwd),
            mock.patch.object(SETTINGS, "DB_PORT", new=port),
        ):
            yield postgres


@pytest.fixture(scope="session", autouse=True)
def database_migrations(api_postgres: DockerContainer, organization_id: str):
    """Run the database migrations."""
    conn_string = api_postgres.get_connection_url()

    if not database_exists(conn_string):
        create_database(conn_string)

    os.environ["DB_NAME"] = organization_id

    alembic_cfg = Config("alembic/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", conn_string)
    command.upgrade(config=alembic_cfg, revision="head")

    yield


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Create an instance of the event loop for the tests."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def set_up_keycloak_tables(keycloak_postgresql):
    """Set up the tables in the keycloak database."""
    async with keycloak_transaction() as conn:
        await conn.execute(
            """
CREATE TABLE public.invitation (
    id character varying(36) NOT NULL,
    created_at timestamp without time zone,
    email character varying(255),
    inviter_id character varying(255),
    url character varying(255),
    organization_id character varying(36)
);
"""
        )
        await conn.execute(
            """
CREATE TABLE public.user_entity (
    id character varying(36) NOT NULL,
    email character varying(255),
    email_constraint character varying(255),
    email_verified boolean DEFAULT false NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    federation_link character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    realm_id character varying(255),
    username character varying(255),
    created_timestamp bigint,
    service_account_client_link character varying(255),
    not_before integer DEFAULT 0 NOT NULL
);
"""
        )

        await conn.execute(
            """
CREATE TABLE public.org (
    id character varying,
    enabled boolean DEFAULT true NOT NULL,
    realm_id character varying,
    group_id character varying,
    name character varying,
    description character varying,
    alias character varying,
    redirect_url character varying
);
"""
        )
        await conn.execute(
            """
CREATE TABLE public.keycloak_group (
    id character varying(36) NOT NULL,
    name character varying(255),
    realm_id character varying(255),
    description character varying(255),
    type integer
);
"""
        )
        await conn.execute(
            """
CREATE TABLE public.user_group_membership (
    user_id character varying(255),
    group_id character varying(255)
);
"""
        )
        await conn.execute(
            """
CREATE TABLE public.realm (
    id character varying(36) NOT NULL,
    name character varying(255)
);
"""
        )
    yield
    async with keycloak_transaction() as conn:
        await conn.execute("""DROP TABLE invitation;""")
        await conn.execute("""DROP TABLE user_entity;""")
        await conn.execute("""DROP TABLE org;""")
        await conn.execute("""DROP TABLE keycloak_group;""")
        await conn.execute("""DROP TABLE user_group_membership;""")
        await conn.execute("""DROP TABLE realm;""")


@pytest.fixture
async def test_client(test_app):
    """Yield a client that can issue fake requests against fastapi endpoint functions in the backend."""
    # defer import of main to prevent accidentally importing storage too early

    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def enforce_mocked_oidc_provider(mock_openid_server):
    """Force that the OIDC provider used by vantage-security is the mock_openid_server provided as a fixture.

    No actual calls to an OIDC provider will be made.
    """
    yield


@pytest.fixture(autouse=True)
def mock_admin_api_cache_dir(tmp_path):
    """Mock the cache directory used by the admin-api package."""
    _cache_dir = tmp_path / ".cache/admin-api/management-api"
    with mock.patch("api.identity.management_api.CACHE_DIR", new=_cache_dir):
        yield _cache_dir


@pytest.fixture
def respx_mock():
    """Run a test in the respx context (similar to respx decorator, but it's a fixture)."""
    with respx.mock as mock:
        respx.post(f"https://{SETTINGS.ARMASEC_DOMAIN}/protocol/openid-connect/token").mock(
            return_value=httpx.Response(status_code=200, json={"access_token": "dummy-token"})
        )
        yield mock


@pytest.fixture
def requester_email() -> str:
    """Yield a dummy requester email."""
    yield "requester@ilovetesting.com"


@pytest.fixture
def tester_email(requester_email) -> str:
    """Yield a dummy tester email."""
    # yield the same value as the other fixture to keep compatibility after merging the two APIs
    yield requester_email


@pytest.fixture
def requester_organization():
    """Yield a dummy organization name."""
    yield "rats"


@pytest.fixture
def sample_uuid(organization_id: str):
    """Yield a dummy UUID."""
    # yield the same value as the other fixture to keep compatibility after merging the two APIs
    yield organization_id


@pytest.fixture
def sample_datetime():
    """Yield a dummy datetime."""
    yield "2021-01-01T00:00:00.000Z"


@pytest.fixture
def sample_organization_logo():
    """Yield a dummy organization logo URL."""
    yield "https://rats.com/logo.png"


@pytest.fixture
def organization_owner_id():
    """Yield a dummy organization owner ID."""
    yield "c3e8a8f4-1b3c-4f6e-9c2a-4f2b1e0f5d5c"


@pytest.fixture
def organization_payload_in_token(
    requester_organization, sample_uuid, sample_datetime, sample_organization_logo, organization_owner_id
):
    """Build the organization payload expected in the access token."""
    yield {
            requester_organization: {
            "name": requester_organization,
            "id": sample_uuid,
            "created_at": [sample_datetime],
            "logo": [sample_organization_logo],
            "owner": [organization_owner_id],
        }
    }


@pytest.fixture
def enforce_strawberry_context_authentication(
    organization_payload_in_token: Dict[str, Dict[str, Union[str, Dict[str, List[str]]]]], tester_email: str
) -> None:
    """Enforce that the strawberry context is authenticated."""
    decoded_token_instance = DecodedToken(
        email=tester_email,
        permissions=[
            "compute:cluster:read",
            "compute:ssh-keys:read",
            "compute:cluster:create",
            "compute:cluster:update",
            "compute:cluster:delete",
            "compute:slurm-info:upsert",
            "storage:file-system:read",
            "storage:file-system:create",
            "storage:file-system:update",
            "storage:file-system:delete",
            "storage:mount:create",
            "storage:mount:delete",
            "compute:queue-action:read",
            "compute:queue-action:create",
            "compute:queue-action:delete",
            "notebook:server:read",
            "notebook:server:create",
            "notebook:server:delete",
        ],
        organization=organization_payload_in_token[next(iter(organization_payload_in_token))].get("id")
    )

    @property
    async def mock_context_async_decoded_token(self: Context) -> DecodedToken:
        """Mock the asynchronous property method to decode the access token from the request.

        This mock is needed because there is no request in the context when testing the
        GraphQL schema.
        """
        setattr(self, "_token_data", decoded_token_instance)
        return decoded_token_instance

    @property
    def mock_context_sync_decoded_token(self: Context) -> DecodedToken:
        """Mock the synchronous property method to return the access token decoded from the request.

        This mock is needed because there is no request in the context when testing the
        GraphQL schema.
        """
        return decoded_token_instance

    with mock.patch.object(Context, "decoded_token", new=mock_context_async_decoded_token):
        with mock.patch.object(Context, "token_data", new=mock_context_sync_decoded_token):
            yield


@pytest.fixture
async def inject_security_header(
    test_client, build_rs256_token, requester_email, organization_payload_in_token
):
    """Provide a helper method that will inject a security token into the requests for a test client.

    If no permisions are provided, the security token will still be valid but will not
    carry any permissions. Uses the `build_rs256_token()` fixture from the armasec package.
    """

    def _helper(owner_id: str, *permissions: List[str]):
        token = build_rs256_token(
            claim_overrides={
                "sub": owner_id,
                "permissions": permissions,
                "azp": "rats",
                "email": requester_email,
                "organization": organization_payload_in_token,
            }
        )
        test_client.headers.update({"Authorization": f"Bearer {token}"})

    return _helper


@pytest.fixture
async def clean_up_database(get_session: AsyncGenerator[AsyncSession, None]) -> None:
    """Clean up the database after the test run."""
    yield
    async with get_session() as sess:
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.MountPointModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.NotebookServerModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.ClusterPartitionsModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.ClusterModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.StorageModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.CloudAccountModel.__tablename__};"""))
        await sess.execute(
            sqlalchemy.text(f"""DELETE FROM {models.CloudAccountApiKeyModel.__tablename__};""")
        )
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.SubscriptionModel.__tablename__};"""))
        await sess.execute(
            sqlalchemy.text(f"""DELETE FROM {models.PendingAwsSubscriptionsModel.__tablename__};""")
        )
        await sess.execute(
            sqlalchemy.text(f"""DELETE FROM {models.OrganizationFreeTrialsModel.__tablename__};""")
        )
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.SlurmClusterConfig.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.AllPartitionInfo.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.AllPartitionInfo.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.PartitionModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.NodeModel.__tablename__};"""))
        await sess.execute(sqlalchemy.text(f"""DELETE FROM {models.AgentHealthCheckModel.__tablename__};"""))
        await sess.commit()


@pytest.fixture
def get_session(organization_id: str) -> Callable[[], AsyncContextManager[AsyncSession]]:
    """Return the async session used to run SQL queries against a database."""

    @asynccontextmanager
    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        """Get the async session to execute queries against the database."""
        session = await create_async_session(organization_id)
        async with session() as sess:
            async with sess.begin():
                try:
                    yield sess
                except Exception as err:
                    await sess.rollback()
                    raise err
                finally:
                    await sess.close()

    return _get_session


@pytest.fixture
def dummy_user_list():
    """Return an example of a user list."""
    return [
        {
            "id": "dc60a026-631a-49f9-a837-45d6287f252f",
            "createdTimestamp": 1650910244544,
            "username": "angry-bull",
            "enabled": True,
            "totp": False,
            "emailVerified": True,
            "firstName": "Angry",
            "lastName": "Bull",
            "picture": "https://avatar.com/angry-bull",
            "email": "angry.bull@omnivector.solutions",
            "disableableCredentialTypes": [],
            "requiredActions": [],
            "notBefore": 0,
            "access": {
                "manageGroupMembership": True,
                "view": True,
                "mapRoles": True,
                "impersonate": False,
                "manage": True,
            },
        },
        {
            "id": "a5f6fd56-8161-4150-a34a-7a62cedb0483",
            "createdTimestamp": 1650455204567,
            "username": "beautiful-shark",
            "enabled": True,
            "totp": False,
            "emailVerified": True,
            "firstName": "Beautiful",
            "lastName": "Shark",
            "email": "beautiful.shark@omnivector.solutions",
            "disableableCredentialTypes": [],
            "requiredActions": [],
            "attributes": {
                "picture": ["https://avatar.com/beautiful-shark"],
            },
            "notBefore": 0,
            "access": {
                "manageGroupMembership": True,
                "view": True,
                "mapRoles": True,
                "impersonate": False,
                "manage": True,
            },
        },
        {
            "id": "a282a8e0-d3b9-4a7d-ade2-7c226806e0d6",
            "createdTimestamp": 1650910244544,
            "username": "happy-bull",
            "enabled": True,
            "totp": False,
            "emailVerified": True,
            "email": "happy.ant@omnivector.solutions",
            "disableableCredentialTypes": [],
            "requiredActions": [],
            "notBefore": 0,
            "picture": "http://avatar.com/happy-bull",
            "attributes": {
                "picture": ["https://avatar.com/happy-bull"],  # takes precedence over the picture key
            },
            "access": {
                "manageGroupMembership": True,
                "view": True,
                "mapRoles": True,
                "impersonate": False,
                "manage": True,
            },
        },
    ]


@pytest.fixture
def default_client():
    """Return an example of a default client."""
    return {
        "id": "bafe4492-44bb-4a29-bace-ce58bb93d546",
        "clientId": "default",
        "name": "default",
        "description": "Default client",
        "surrogateAuthRequired": False,
        "enabled": True,
        "alwaysDisplayInConsole": False,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["*"],
        "webOrigins": [],
        "notBefore": 0,
        "bearerOnly": False,
        "consentRequired": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": True,
        "serviceAccountsEnabled": False,
        "publicClient": True,
        "frontchannelLogout": False,
        "protocol": "openid-connect",
        "attributes": {
            "access.token.lifespan": "86400",
            "saml.multivalued.roles": "False",
            "saml.force.post.binding": "False",
            "oauth2.device.authorization.grant.enabled": "False",
            "use.jwks.url": "False",
            "backchannel.logout.revoke.offline.tokens": "False",
            "saml.server.signature.keyinfo.ext": "False",
            "use.refresh.tokens": "True",
            "jwt.credential.certificate": "abcde12334==",
            "oidc.ciba.grant.enabled": "False",
            "use.jwks.string": "False",
            "backchannel.logout.session.required": "True",
            "client_credentials.use_refresh_token": "False",
            "saml.client.signature": "False",
            "require.pushed.authorization.requests": "False",
            "saml.assertion.signature": "False",
            "id.token.as.detached.signature": "False",
            "saml.encrypt": "False",
            "saml.server.signature": "False",
            "exclude.session.state.from.auth.response": "False",
            "saml.artifact.binding": "False",
            "saml_force_name_id_format": "False",
            "tls.client.certificate.bound.access.tokens": "False",
            "acr.loa.map": "{}",
            "saml.authnstatement": "False",
            "display.on.consent.screen": "False",
            "token.response.type.bearer.lower-case": "False",
            "saml.onetimeuse.condition": "False",
        },
        "authenticationFlowBindingOverrides": {},
        "fullScopeAllowed": False,
        "nodeReRegistrationTimeout": -1,
        "protocolMappers": [
            {
                "id": "6341f9f5-aab7-43a1-9e88-078decebaf21",
                "name": "permissions-in-token",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-client-role-mapper",
                "consentRequired": False,
                "config": {
                    "multivalued": "True",
                    "userinfo.token.claim": "True",
                    "id.token.claim": "True",
                    "access.token.claim": "True",
                    "claim.name": "permissions",
                    "jsonType.label": "String",
                    "usermodel.clientRoleMapping.clientId": "default",
                },
            }
        ],
        "defaultClientScopes": ["web-origins", "profile", "roles", "email"],
        "optionalClientScopes": ["address", "phone", "offline_access", "microprofile-jwt"],
        "access": {"view": True, "configure": True, "manage": True},
    }


@pytest.fixture
def role_list_example():
    """Return an example of a role list."""
    return [
        {
            "id": "ce92b0bd-5e78-4d4a-89ad-c8bc9ed15f4c",
            "name": "jobbergate:job-submissions:edit",
            "description": "Allow to edit job submissions",
            "composite": False,
            "clientRole": True,
            "containerId": "36ede69e-ad7e-464d-bffd-9eb0b07552c5",
        },
        {
            "id": "5402e721-a590-4238-a8c1-ec8d32a80909",
            "name": "cluster:jobs:write",
            "description": "Allow PUT/PATCH operations on jobs",
            "composite": False,
            "clientRole": True,
            "containerId": "36ede69e-ad7e-464d-bffd-9eb0b07552c5",
        },
    ]


@pytest.fixture
def group_example():
    """Return an example of a group."""
    return {
        "id": "ba62e25a-c0e9-491a-8619-d364cc1bd925",
        "name": "Admin",
        "path": "/Admin",
        "attributes": {"description": ["Admin group which has all available roles"]},
        "realmRoles": [],
        "clientRoles": {
            "default": [
                "jobbergate:job-submissions:view",
                "admin:clients:edit",
                "jobbergate:job-scripts:view",
                "admin:connections:view",
                "license-manager:booking:view",
                "admin:invitations:view",
                "jobbergate:applications:edit",
                "license-manager:booking:edit",
                "jobbergate:job-submissions:edit",
                "jobbergate:job-scripts:edit",
                "admin:organizations:view",
                "license-manager:config:view",
                "admin:clients:view",
                "admin:groups:view",
                "license-manager:license:view",
                "jobbergate:applications:view",
                "admin:roles:view",
                "admin:invitations:edit",
                "license-manager:license:edit",
                "admin:users:view",
                "license-manager:config:edit",
                "admin:groups:edit",
                "admin:users:edit",
                "cluster:graphql:edit",
                "cluster:graphql:view",
            ]
        },
    }


@pytest.fixture
def idp_example():
    """Return an example of an identity provider."""
    return {
        "alias": "google",
        "internalId": "25d0649c-7616-413e-93f2-4ab09862def6",
        "providerId": "google",
        "enabled": True,
        "updateProfileFirstLoginMode": "on",
        "trustEmail": False,
        "storeToken": False,
        "addReadTokenRoleOnCreate": False,
        "authenticateByDefault": False,
        "linkOnly": False,
        "firstBrokerLoginFlowAlias": "first broker login",
        "config": {
            "syncMode": "IMPORT",
            "clientSecret": "**********",
            "clientId": "123456789-abcdefghijklm.apps.googleusercontent.com",
            "useJwksUrl": "true",
        },
    }


@pytest.fixture
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
def mock_fetch_default_client(respx_mock, default_client):
    """Mock the GET /admin/realms/vantage/clients endpoint HTTP request."""
    respx_mock.get("/admin/realms/vantage/clients", params={"clientId": "default"}).mock(
        return_value=Response(200, json=[default_client])
    )

    yield


@pytest.fixture
def convert_keys_to_snake_case():
    """Return a helper function to turn all the keys of a list of dictionaries into snake case."""

    def _convert_keys_to_snake_case(dict_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted_list = []

        for dictionary in dict_list:
            converted_dict = {}

            for key, value in dictionary.items():
                snake_case_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
                converted_dict[snake_case_key] = value

            converted_list.append(converted_dict)

        return converted_list

    return _convert_keys_to_snake_case


@pytest.fixture
def caplog(caplog: pytest.LogCaptureFixture):
    """Make loguru to work with pytest.

    [Reference](https://loguru.readthedocs.io/en/stable/resources/migration.html#replacing-caplog-fixture-from-pytest-library)
    """
    handler_id = logger.add(
        caplog.handler,
        format="{message}",
        level=0,
        filter=lambda record: record["level"].no >= caplog.handler.level,
        enqueue=False,  # Set to 'True' if your test is spawning child processes.
    )
    yield caplog
    logger.remove(handler_id)


@dataclass
class SeededData:

    """Dataclass to easily store the data seeded in the database."""

    cluster: types.Cluster
    cluster_without_storage: types.Cluster
    storage: types.Storage
    storage_mounted: types.Storage
    mount_point: types.MountPointModel
    cloud_account: types.CloudAccount
    notebook_server: types.NotebookServer
    partition: types.Partition
    partition_info: types.ClusterPartition


@pytest.fixture
async def seed_database(
    get_session: AsyncGenerator[AsyncSession, None],
    clean_up_database: None,
    organization_id: str,
    tester_email: str,
) -> SeededData:
    """Seed the tickets table with fake data."""
    async with get_session() as sess:
        payload = {
            "name": "Dummy",
            "description": "dummy description",
            "status": ClusterStatusEnum.ready,
            "client_id": cluster_name_to_client_id("Dummy", organization_id),
            "provider": ClusterProviderEnum.aws,
            "creation_parameters": {"jupyterhub_token": "dummy_jupyterhub_token"},
        }
        query = insert(models.ClusterModel).values(**payload).returning(literal_column("*"))
        cluster_name = (await sess.execute(query)).scalars().one()
        query = select(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
        cluster: models.ClusterModel = (await sess.execute(query)).scalars().one()

        cluster_data = cluster.__dict__
        cluster_data.pop("_sa_instance_state")

        payload = {
            "name": "Dummy2",
            "description": "dummy2 description",
            "status": ClusterStatusEnum.ready,
            "client_id": cluster_name_to_client_id("Dummy2", organization_id),
            "provider": ClusterProviderEnum.on_prem,
        }
        query = insert(models.ClusterModel).values(**payload).returning(literal_column("*"))
        cluster_name = (await sess.execute(query)).scalars().one()
        query = select(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
        cluster_without_storage: models.ClusterModel = (await sess.execute(query)).scalars().one()

        cluster_data_without_storage = cluster_without_storage.__dict__
        cluster_data_without_storage.pop("_sa_instance_state")

        payload = {
            "provider": "aws",
            "name": "dummy2",
            "assisted_cloud_account": False,
            "description": "dummy2 description",
            "attributes": {"role_arn": "arn:aws:iam::000000000000:role/test_vantage_api"},
        }
        query = (
            insert(models.CloudAccountModel)
            .values(**payload)
            .returning(
                *[
                    getattr(models.CloudAccountModel, c_attr.key)
                    for c_attr in inspect(models.CloudAccountModel).mapper.column_attrs
                ]
            )
        )
        cloud_account_data = (await sess.execute(query)).one()

        payload = {
            "fs_id": "fs_id",
            "name": "StorageDummy",
            "region": "us-west-2",
            "source": "vantage",
            "owner": tester_email,
            "cloud_account_id": cloud_account_data.id,
        }
        query = (
            insert(models.StorageModel)
            .values(**payload)
            .returning(
                *[
                    getattr(models.StorageModel, c_attr.key)
                    for c_attr in inspect(models.StorageModel).mapper.column_attrs
                ]
            )
        )
        storage_data = (await sess.execute(query)).one()

        payload = {
            "fs_id": "fs_id2",
            "name": "StorageDummy2",
            "region": "us-west-2",
            "source": "vantage",
            "owner": "tester2@omnivector.solutions",
            "cloud_account_id": cloud_account_data.id,
        }
        query = (
            insert(models.StorageModel)
            .values(**payload)
            .returning(
                *[
                    getattr(models.StorageModel, c_attr.key)
                    for c_attr in inspect(models.StorageModel).mapper.column_attrs
                ]
            )
        )
        storage_data_mounted = (await sess.execute(query)).one()

        payload = {
            "cluster_name": cluster_data["name"],
            "client_id": cluster_data["client_id"],
            "mount_point": "/nfs/test",
            "storage_id": storage_data_mounted.id,
            "status": "mounting",
        }
        query = (
            insert(models.MountPointModel)
            .values(**payload)
            .returning(
                *[
                    getattr(models.MountPointModel, c_attr.key)
                    for c_attr in inspect(models.MountPointModel).mapper.column_attrs
                ]
            )
        )
        mount_point_data = (await sess.execute(query)).one()

        payload = {
            "name": "compute",
            "node_type": "t3.medium",
            "max_node_count": 10,
            "is_default": True,
            "cluster_name": cluster_data["name"],
        }
        query = (
            insert(models.ClusterPartitionsModel).values(**payload).returning(models.ClusterPartitionsModel)
        )
        partition_data = (await sess.execute(query)).one()

        payload = {"name": "compute", "cluster_name": cluster_data["name"], "info": {}}
        query = insert(models.PartitionModel).values(**payload).returning(models.PartitionModel)
        partition_info_data = (await sess.execute(query)).one()

        payload = {
            "name": "test-notebook",
            "owner": tester_email,
            "partition": partition_data["name"],
            "cluster_name": cluster_data["name"],
            "server_url": f'{cluster_data["client_id"]}.dev.vantagecompute.ai',
        }
        query = insert(models.NotebookServerModel).values(**payload).returning(models.NotebookServerModel)
        notebook_data = (await sess.execute(query)).one()

        await sess.commit()
    cluster = types.Cluster(**cluster_data)

    yield SeededData(
        cluster=cluster,
        cluster_without_storage=types.Cluster(**cluster_data_without_storage),
        storage=types.Storage(
            **storage_data, mount_points=[], cloud_account=types.CloudAccount(**cloud_account_data)
        ),
        storage_mounted=types.Storage(
            **storage_data_mounted,
            mount_points=[types.MountPointModel(**mount_point_data)],
            cloud_account=types.CloudAccount(**cloud_account_data),
        ),
        mount_point=types.MountPointModel(**mount_point_data),
        cloud_account=types.CloudAccount(**cloud_account_data),
        notebook_server=types.NotebookServer(**notebook_data, cluster=cluster),
        partition=types.Partition(**partition_data),
        partition_info=types.ClusterPartition(**partition_info_data),
    )


@pytest.fixture
def camelify():
    """Return a helper function to turn a string into camel case."""

    def _camelify(word: str):
        return re.sub(r"_(\w)", lambda match: match.group(1).upper(), word)

    return _camelify


@pytest.fixture(scope="session", autouse=True)
def cloud_account_stack() -> Generator[assertions.Template, None, None]:
    """Yield the cloud account stack template."""
    from cloud_account_stack.app import cloud_account_stack

    template = assertions.Template.from_stack(cloud_account_stack)
    yield template


@pytest.fixture
def lambda_function_custom_resource_create_event(
    sample_uuid: str,
) -> Generator[dict[str, Collection[str]], None, None]:
    """Yield the event for the lambda function custom resource on the CREATE event."""
    event = {
        "RequestType": "Create",
        "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:custom-resource",
        "ResponseURL": "http://pre-signed-S3-url-for-response",
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/stack-name/guid",
        "RequestId": "unique id for this create request",
        "ResourceType": "Custom::Resource",
        "LogicalResourceId": "MyCustomResource",
        "ResourceProperties": {
            "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:custom-resource",
            "VantageApiKey": "dummy-api-key",
            "VantageOrganizationId": sample_uuid,
            "StackName": "stack-name",
            "CloudAccountName": "DummyName",
            "CloudAccoutDescription": "DummyDescription",
            "VantageIntegrationRoleArn": "arn:aws:iam::123456789012:role/vantage-integration-role",
            "VantageUrl": "https://dummy-url.omnivector.solutions",
            "VantageIntegrationRoleName": "VantageIntegration-DummyName",
            "VantageIntegrationStackName": "CloudAccountStack",
            "VantageIntegrationRolePolicyName": "VantageIntegrationPolicy-DummyName",
            "VantageIntegrationPolicyUrl": "https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json",
        },
    }
    yield event


@pytest.fixture
def lambda_function_custom_resource_delete_event() -> Generator[dict[str, Collection[str]], None, None]:
    """Yield the event for the lambda function custom resource on the DELETE event."""
    event = {
        "RequestType": "Delete",
        "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:custom-resource",
        "ResponseURL": "http://pre-signed-S3-url-for-response",
        "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/stack-name/guid",
        "RequestId": "unique id for this create request",
        "ResourceType": "Custom::Resource",
        "LogicalResourceId": "MyCustomResource",
        "ResourceProperties": {
            "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:custom-resource",
            "StackName": "stack-name",
            "CloudAccountName": "DummyName",
            "CloudAccoutDescription": "DummyDescription",
            "VantageIntegrationRoleArn": "arn:aws:iam::123456789012:role/vantage-integration-role",
            "VantageUrl": "https://dummy-url.omnivector.solutions",
        },
    }
    yield event


@pytest.fixture
def lambda_function_event_bridge_event() -> Generator[dict[str, str], None, None]:
    """Yield the event for the lambda function from the EventBridge."""
    event = {
        "VantageIntegrationRolePolicyName": "VantageIntegrationPolicy-CloudAccountQA",
        "VantageIntegrationRoleName": "VantageIntegration-CloudAccountQA",
        "VantageIntegrationPolicyUrl": "https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json",
        "CloudAccountName": "CloudAccountQA",
        "VantageIntegrationStackName": "CloudAccountStack",
        "VantageIntegrationRoleLogicalId": "VantageIntegrationRole",
    }
    yield event


@pytest.fixture
async def create_dummy_subscription(
    sample_uuid: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
) -> AsyncGenerator[None, None]:
    """Create a dummy subscription in the database that has the highest tier possible."""
    query: Select | Insert | Delete
    async with get_session() as sess:
        query = select(models.SubscriptionTierModel.id).where(
            models.SubscriptionTierModel.name == SubscriptionTiersNames.enterprise.value
        )
        subscription_tier_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_tier_id is not None

        query = select(models.SubscriptionTypeModel.id).where(
            models.SubscriptionTypeModel.name == SubscriptionTypesNames.cloud.value
        )
        subscription_type_id = (await sess.execute(query)).scalar_one_or_none()
        assert subscription_type_id is not None

        query = (
            insert(models.SubscriptionModel)
            .values(
                organization_id=sample_uuid,
                tier_id=subscription_tier_id,
                type_id=subscription_type_id,
                detail_data={},
                is_free_trial=False,
            )
            .returning(models.SubscriptionModel.id)
        )
        subscription_id: int | None = (await sess.execute(query)).scalar()
        assert subscription_id is not None
        await sess.commit()
    yield
    async with get_session() as sess:
        query = delete(models.SubscriptionModel).where(models.SubscriptionModel.id == subscription_id)
        await sess.execute(query)
        await sess.commit()
