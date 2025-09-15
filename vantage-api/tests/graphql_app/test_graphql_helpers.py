"""Tests for the GraphQL helpers."""
import random
import uuid
from datetime import datetime
from typing import AsyncContextManager, Callable
from unittest import mock

import pytest
from httpx import Response
from mypy_boto3_cloudformation.type_defs import StackEventTypeDef
from respx.router import MockRouter
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, Select

from api.graphql_app.helpers import (
    _monitor_aws_cluster_status_task,
    _update_aws_cluster_status,
    _update_aws_cluster_status_details,
    cluster_client_roles_mapping,
    cluster_name_to_client_id,
    is_valid_instance_for_region,
    monitor_aws_cluster_status,
    mount_post_client_request,
    parse_column_and_json_field,
    set_up_cluster_config_on_keycloak,
)
from api.graphql_app.types import ClusterRegion
from api.identity.management_api import backend_client
from api.settings import SETTINGS
from api.sql_app.enums import ClusterStatusEnum
from api.sql_app.models import AwsNodeTypesModel, CloudAccountModel, ClusterModel
from api.sql_app.session import async_session


@pytest.mark.parametrize(
    "cluster_name,organization,expected_client_id",
    [
        (
            "Local Cluster",
            "450AF1DD-1B69-4943-AA34-08685115F174",
            "local-cluster-450AF1DD-1B69-4943-AA34-08685115F174",
        ),
        (
            "Local-Cluster",
            "3A66FBC0-825B-48A5-A83F-C5930A739D25",
            "local-cluster-3A66FBC0-825B-48A5-A83F-C5930A739D25",
        ),
        (
            "!@# Local Cluster !@#$%",
            "683501F2-C6CD-43F8-AC63-65AF0669EC30",
            "local-cluster-683501F2-C6CD-43F8-AC63-65AF0669EC30",
        ),
        (
            "OSL Cluster Staging 1",
            "380B118C-1AD7-450C-BB0D-64DC390B19DC",
            "osl-cluster-staging-1-380B118C-1AD7-450C-BB0D-64DC390B19DC",
        ),
        (
            "OSL Cluster Staging 2",
            "1C5D1782-EA70-4990-AFBF-C3BB8D936C38",
            "osl-cluster-staging-2-1C5D1782-EA70-4990-AFBF-C3BB8D936C38",
        ),
        (
            "Cluster With Space ",
            "204F1CBF-91BB-4762-A125-614EB77032EC",
            "cluster-with-space-204F1CBF-91BB-4762-A125-614EB77032EC",
        ),
        (
            "Cluster Name Ends with Symbol !@#$%",
            "83F39BBB-0CB5-47BF-B86A-2E86B854AF86",
            "cluster-name-ends-with-symbol-83F39BBB-0CB5-47BF-B86A-2E86B854AF86",
        ),
        (
            "Cluster Has SYmbols #&3$ and Letters",
            "AE5FDB4A-9797-4342-9D41-F699619B9CE",
            "cluster-has-symbols-3-and-letters-AE5FDB4A-9797-4342-9D41-F699619B9CE",
        ),
    ],
)
def test_mapping_cluster_name_to_client_id_string(
    cluster_name: str, organization: str, expected_client_id: str
):
    """Check if the cluster name is correctly mapped to the client id."""
    actual_client_id = cluster_name_to_client_id(cluster_name, organization)
    assert actual_client_id == expected_client_id


def test_mount_post_client_request__check_is_mounted_client_payload_is_correct():
    """Check if the mounted client payload is correct."""
    client_uuid = uuid.uuid4()
    client_id = "example"
    client_name = ("Example",)
    client_description = "Example"
    client_secret = "1234567890"

    expected_client_payload = {
        "id": str(client_uuid),
        "clientId": client_id,
        "name": client_name,
        "description": client_description,
        "secret": client_secret,
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["*"],
        "bearerOnly": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
        "publicClient": False,
        "protocol": "openid-connect",
        "fullScopeAllowed": False,
        "protocolMappers": [
            {
                "name": "Permissions",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-client-role-mapper",
                "config": {
                    "multivalued": "true",
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "permissions",
                    "jsonType.label": "String",
                    "usermodel.clientRoleMapping.clientId": client_id,
                },
            },
        ],
        "attributes": {
            "access.token.lifespan": "86400",
            "oauth2.device.authorization.grant.enabled": "true",
            "id.token.signed.response.alg": "RS256",
            "client_credentials.use_refresh_token": "false",
            "access.token.signed.response.alg": "RS256",
            "token.response.type.bearer.lower-case": "false",
        },
    }

    actual_client_payload = mount_post_client_request(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_name,
        client_description=client_description,
        client_secret=client_secret,
    )

    assert actual_client_payload == expected_client_payload


def test_role_mapping():
    """Assert if each role in the mapping has 'description' key not empty and also assert the defined roles.

    This ensures no role is accidentaly deleted and/or added. In other words,
    the role addition/removal will be verified by other people in the team.
    This is a very sensitive operation, the reason why such a thing must be carefully supervisioned.
    """
    expected_roles = [
        "license-manager:feature:read",
        "license-manager:job:delete",
        "license-manager:job:create",
        "license-manager:job:read",
        "license-manager:config:read",
        "license-manager:booking:delete",
        "license-manager:feature:update",
        "jobbergate:job-submissions:update",
        "jobbergate:job-submissions:read",
        "jobbergate:job-scripts:read",
        "jobbergate:clusters:read",
        "jobbergate:clusters:update",
        "compute:slurm-info:upsert",
        "compute:cluster:read",
        "compute:queue-action:read",
        "compute:queue-action:delete",
    ]

    roles = cluster_client_roles_mapping()

    existing_roles = [role.get("name") for role in roles]

    assert existing_roles == expected_roles

    descriptions = [role.get("description") for role in roles]

    assert all(descriptions)


@pytest.mark.parametrize(
    "client_uuid,client_id,client_name,description,client_secret,service_account_id,org_id",
    [
        (
            "dummy-uuid-1",
            "dummy-id-1",
            "dummy-client-name-1",
            "dummy-description-1",
            "dummy-secret-1",
            "dummy-service-account-id-1",
            "dummy-org-1",
        ),
        (
            "dummy-uuid-2",
            "dummy-id-2",
            "dummy-client-name-2",
            "dummy-description-2",
            "dummy-secret-2",
            "dummy-service-account-id-2",
            "dummy-org-2",
        ),
        (
            "dummy-uuid-3",
            "dummy-id-3",
            "dummy-client-name-3",
            "dummy-description-3",
            "dummy-secret-3",
            "dummy-service-account-id-3",
            "dummy-org-3",
        ),
    ],
)
@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
async def test_set_up_cluster_config_on_keycloak__check_successful_client_setup(
    client_uuid: str,
    client_id: str,
    client_name: str,
    description: str,
    client_secret: str,
    service_account_id: str,
    org_id: str,
    respx_mock: MockRouter,
):
    """Check if the client id to act on behalf of the cluster is created successfully."""
    respx_mock.post(
        "/admin/realms/vantage/clients",
        json=mount_post_client_request(
            client_uuid=client_uuid,
            client_id=client_id,
            client_name=client_name,
            client_description=description,
            client_secret=client_secret,
        ),
    ).mock(return_value=Response(201))

    for role in cluster_client_roles_mapping():
        respx_mock.post(f"/admin/realms/vantage/clients/{client_uuid}/roles", json=role).mock(
            return_value=Response(201)
        )

    respx_mock.get(f"/admin/realms/vantage/clients/{client_uuid}/service-account-user").mock(
        return_value=Response(200, json={"id": service_account_id})
    )

    respx_mock.post(
        f"/admin/realms/vantage/organizations/{org_id}/members/",
        content=service_account_id
    ).mock(return_value=Response(204))

    roles = [
        {"name": role.get("name"), "containerId": "dummy-id", "id": "dummy-id"}
        for role in cluster_client_roles_mapping()
    ]
    respx_mock.get(
        f"/admin/realms/vantage/users/{service_account_id}/role-mappings/clients/{client_uuid}/available"
    ).mock(return_value=Response(200, json=roles))

    respx_mock.post(
        f"/admin/realms/vantage/users/{service_account_id}/role-mappings/clients/{client_uuid}", json=roles
    ).mock(return_value=Response(204))

    await set_up_cluster_config_on_keycloak(
        client_uuid=client_uuid,
        client_id=client_id,
        client_name=client_name,
        client_description=description,
        client_secret=client_secret,
        organization_id=org_id,
    )


def test_parse_column_and_json_field__check_successful_parsing():
    """Check if the column and json field are parsed successfully."""
    column, json_field = parse_column_and_json_field("attributes.dummy_field", CloudAccountModel)

    assert column == "attributes"
    assert json_field == "dummy_field"


def test_parse_column_and_json_field__check_unsuccessful_parsing__not_jsonb_column():
    """Check if an error is raised when a non-JSONB column is passed."""
    with pytest.raises(ValueError, match="Column id is not a JSONB field."):
        parse_column_and_json_field("id.dummy_field", CloudAccountModel)


def test_parse_column_and_json_field__check_unsuccessful_parsing__more_than_one_jsonb_field():
    """Check if an error is raised when more than one JSONB field is passed."""
    with pytest.raises(ValueError, match="More than one JSONB field found. Expected only one."):
        parse_column_and_json_field("attributes.dummy_field1.dummy_field2", CloudAccountModel)


def test_parse_column_and_json_field__check_successfull_parsing__no_jsonb_column():
    """Check if the function identifies the passed column isn't a JSONB column."""
    column, json_field = parse_column_and_json_field("id", CloudAccountModel)

    assert column == "id"
    assert json_field is None


class TestIsValidInstanceForRegion:
    """Test cases for the is_valid_instance_for_region function."""

    @pytest.mark.asyncio
    async def test__check_valid_instance(
        self, get_session: Callable[[], AsyncContextManager[AsyncSession]], organization_id: str
    ):
        """Check if the instance is valid for the region."""
        instance_type = str(uuid.uuid4())
        aws_region = random.choice(list(ClusterRegion))
        cpu_manufacturer = str(uuid.uuid4())
        cpu_name = str(uuid.uuid4())
        cpu_arch = str(uuid.uuid4())
        num_cpus = random.randint(1, 100)
        memory = random.randint(1, 100)
        gpu_manufacturer = str(uuid.uuid4())
        gpu_name = str(uuid.uuid4())
        num_gpus = random.randint(1, 100)
        price_per_hour = random.random()

        mocked_info = mock.Mock()
        mocked_info.context.token_data.organization = organization_id
        mocked_info.context.db_session = async_session

        async with get_session() as session:
            query = insert(AwsNodeTypesModel).values(
                instance_type=instance_type,
                aws_region=aws_region.value,
                cpu_manufacturer=cpu_manufacturer,
                cpu_name=cpu_name,
                cpu_arch=cpu_arch,
                num_cpus=num_cpus,
                memory=memory,
                gpu_manufacturer=gpu_manufacturer,
                gpu_name=gpu_name,
                num_gpus=num_gpus,
                price_per_hour=price_per_hour,
            )
            await session.execute(query)
            await session.commit()

        assert await is_valid_instance_for_region(mocked_info, instance_type, aws_region) is True

    @pytest.mark.asyncio
    async def test__check_invalid_instance(self, organization_id: str):
        """Check if the instance is invalid for the region."""
        instance_type = str(uuid.uuid4())
        aws_region = random.choice(list(ClusterRegion))

        mocked_info = mock.Mock()
        mocked_info.context.token_data.organization = organization_id
        mocked_info.context.db_session = async_session

        assert await is_valid_instance_for_region(mocked_info, instance_type, aws_region) is False


@pytest.mark.parametrize(
    "db, region_name, role_arn, stack_name, cluster_name",
    [
        ("alpha", "beta", "gamma", "delta", "epsilon"),
        ("zeta", "eta", "theta", "iota", "kappa"),
        ("lambda", "mu", "nu", "xi", "omicron"),
    ],
)
@mock.patch("api.graphql_app.helpers._monitor_aws_cluster_status_task")
@mock.patch("api.graphql_app.helpers.threading")
def test_monitor_aws_cluster_status__check_successful_task_creation(
    mocked_threading: mock.MagicMock,
    mocked_monitor_aws_cluster_status_task: mock.MagicMock,
    db: str,
    region_name: str,
    role_arn: str,
    stack_name: str,
    cluster_name: str,
):
    """Check if the task is created successfully."""
    mocked_threading.Thread = mock.Mock()
    mocked_threading.Thread.return_value = mock.Mock()
    mocked_threading.Thread.return_value.start = mock.Mock()

    monitor_aws_cluster_status(db, region_name, role_arn, stack_name, cluster_name)

    mocked_threading.Thread.assert_called_once_with(
        target=mocked_monitor_aws_cluster_status_task,
        args=(db, region_name, role_arn, stack_name, cluster_name),
    )
    mocked_threading.Thread.return_value.start.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "original_status, new_status",
    [
        (ClusterStatusEnum.preparing, ClusterStatusEnum.ready),
        (ClusterStatusEnum.preparing, ClusterStatusEnum.deleting),
        (ClusterStatusEnum.preparing, ClusterStatusEnum.failed),
        (ClusterStatusEnum.ready, ClusterStatusEnum.preparing),
        (ClusterStatusEnum.ready, ClusterStatusEnum.deleting),
        (ClusterStatusEnum.ready, ClusterStatusEnum.failed),
        (ClusterStatusEnum.deleting, ClusterStatusEnum.preparing),
        (ClusterStatusEnum.deleting, ClusterStatusEnum.ready),
        (ClusterStatusEnum.deleting, ClusterStatusEnum.failed),
        (ClusterStatusEnum.failed, ClusterStatusEnum.preparing),
        (ClusterStatusEnum.failed, ClusterStatusEnum.ready),
        (ClusterStatusEnum.failed, ClusterStatusEnum.deleting),
    ],
)
async def test__update_cluster_status(
    original_status: ClusterStatusEnum,
    new_status: ClusterStatusEnum,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    tester_email: str,
    organization_id: str,
    clean_up_database: None,
):
    """Check if the status is updated successfully."""
    query: Select | Insert
    cluster_name = "dummy-cluster"

    async with get_session() as session:
        query = insert(ClusterModel).values(
            name=cluster_name,
            status=original_status,
            client_id="dummy-client-id",
            description="dummy-description",
            owner_email=tester_email,
        )
        await session.execute(query)
        await session.commit()

    await _update_aws_cluster_status(organization_id, cluster_name, new_status)

    async with get_session() as session:
        query = select(ClusterModel).where(ClusterModel.name == cluster_name)
        cluster: ClusterModel | None = (await session.execute(query)).scalar_one_or_none()

    assert cluster is not None
    assert cluster.status == new_status


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stack_events, cluster_name",
    [
        (
            [
                StackEventTypeDef(
                    StackId="dummy-alpha",
                    EventId="abc123",
                    StackName="alpha",
                    Timestamp=datetime(2000, 1, 1),
                    LogicalResourceId="gamma",
                    ResourceStatusReason="epsilon",
                )
            ],
            "beta",
        ),
        (
            [
                StackEventTypeDef(
                    StackId="dummy-beta",
                    EventId="321cba",
                    StackName="beta",
                    Timestamp=datetime(2000, 5, 1),
                    LogicalResourceId="gamma",
                    ResourceStatusReason="delta",
                )
            ],
            "omicron",
        ),
    ],
)
async def test__update_aws_cluster_status_details(
    stack_events: list[StackEventTypeDef],
    cluster_name: str,
    get_session: Callable[[], AsyncContextManager[AsyncSession]],
    tester_email: str,
    organization_id: str,
    clean_up_database: None,
):
    """Check if the status is updated successfully."""
    query: Select | Insert
    cluster_name = "dummy-cluster"

    async with get_session() as session:
        query = insert(ClusterModel).values(
            name=cluster_name,
            status=ClusterStatusEnum.ready,
            client_id="dummy-client-id",
            description="dummy-description",
            owner_email=tester_email,
        )
        await session.execute(query)
        await session.commit()

    await _update_aws_cluster_status_details(organization_id, stack_events, cluster_name)

    async with get_session() as session:
        query = select(ClusterModel).where(ClusterModel.name == cluster_name)
        cluster: ClusterModel | None = (await session.execute(query)).scalar_one_or_none()

    assert cluster is not None
    assert cluster.creation_status_details == [
        {
            "logical_resource_id": event["LogicalResourceId"],
            "reason": event["ResourceStatusReason"],
        }
        for event in stack_events
    ]


@pytest.mark.parametrize(
    "db, cluster_name, role_arn, region_name, stack_name, stack_id",
    [
        (
            "db-1",
            "dummy-cluster-1",
            "dummy-role-arn-1",
            "dummy-region-1",
            "dummy-stack-1",
            "dummy-stack-id-1",
        ),
        (
            "db-2",
            "dummy-cluster-2",
            "dummy-role-arn-2",
            "dummy-region-2",
            "dummy-stack-2",
            "dummy-stack-id-2",
        ),
        (
            "db-3",
            "dummy-cluster-3",
            "dummy-role-arn-3",
            "dummy-region-3",
            "dummy-stack-3",
            "dummy-stack-id-3",
        ),
    ],
)
@mock.patch("api.graphql_app.helpers.cfn_ops")
@mock.patch("api.graphql_app.helpers.asyncio")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status_details")
@mock.patch("api.graphql_app.helpers.time")
def test__monitor_aws_cluster_status_task__check_create_complete_status(
    mocked_time: mock.MagicMock,
    mocked__update_aws_cluster_status_details: mock.MagicMock,
    mocked__update_aws_cluster_status: mock.MagicMock,
    mocked_asyncio: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    db: str,
    cluster_name: str,
    role_arn: str,
    region_name: str,
    stack_name: str,
    stack_id: str,
):
    """Verify the behaviour of the _monitor_aws_cluster_status_task upon a CREATE_COMPLETE status."""
    mocked_time.sleep = mock.Mock()

    mocked_cfn_ops.get_stack_id = mock.Mock(return_value=stack_id)
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="CREATE_COMPLETE")
    mocked_cfn_ops.get_create_failed_events = mock.Mock()

    mocked_asyncio.run = mock.Mock()

    mocked__update_aws_cluster_status.return_value = None

    _monitor_aws_cluster_status_task(db, region_name, role_arn, stack_name, cluster_name)

    mocked_time.sleep.assert_not_called()
    mocked__update_aws_cluster_status_details.assert_not_called()
    mocked__update_aws_cluster_status.assert_called_once_with(db, cluster_name, ClusterStatusEnum.ready)
    mocked_cfn_ops.get_create_failed_events.assert_not_called()
    mocked_asyncio.run.assert_called_once_with(mock.ANY)


@pytest.mark.parametrize(
    "db, cluster_name, role_arn, region_name, stack_name, stack_id",
    [
        (
            "db-1",
            "dummy-cluster-1",
            "dummy-role-arn-1",
            "dummy-region-1",
            "dummy-stack-1",
            "dummy-stack-id-1",
        ),
        (
            "db-2",
            "dummy-cluster-2",
            "dummy-role-arn-2",
            "dummy-region-2",
            "dummy-stack-2",
            "dummy-stack-id-2",
        ),
        (
            "db-3",
            "dummy-cluster-3",
            "dummy-role-arn-3",
            "dummy-region-3",
            "dummy-stack-3",
            "dummy-stack-id-3",
        ),
    ],
)
@mock.patch("api.graphql_app.helpers.cfn_ops")
@mock.patch("api.graphql_app.helpers.asyncio")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status_details")
@mock.patch("api.graphql_app.helpers.time")
def test__monitor_aws_cluster_status_task__check_delete_complete_status(
    mocked_time: mock.MagicMock,
    mocked__update_aws_cluster_status_details: mock.MagicMock,
    mocked__update_aws_cluster_status: mock.MagicMock,
    mocked_asyncio: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    db: str,
    cluster_name: str,
    role_arn: str,
    region_name: str,
    stack_name: str,
    stack_id: str,
):
    """Verify the behaviour of the _monitor_aws_cluster_status_task upon a DELETE_COMPLETE status."""
    mocked_time.sleep = mock.Mock()

    mocked_cfn_ops.get_stack_id = mock.Mock(return_value=stack_id)
    mocked_cfn_ops.get_stack_status = mock.Mock(return_value="DELETE_COMPLETE")
    mocked_cfn_ops.get_create_failed_events = mock.Mock()
    mocked_cfn_ops.get_create_failed_events.return_value = "dummy-return-value"

    mocked_asyncio.run = mock.Mock()

    mocked__update_aws_cluster_status.return_value = None

    _monitor_aws_cluster_status_task(db, region_name, role_arn, stack_name, cluster_name)

    mocked_time.sleep.assert_not_called()
    mocked__update_aws_cluster_status_details.assert_called_once_with(db, "dummy-return-value", cluster_name)
    mocked__update_aws_cluster_status.assert_called_once_with(db, cluster_name, ClusterStatusEnum.failed)
    mocked_asyncio.run.assert_has_calls([mock.call(mock.ANY), mock.call(mock.ANY)])


@pytest.mark.parametrize(
    "db, cluster_name, role_arn, region_name, stack_name, stack_id",
    [
        (
            "db-1",
            "dummy-cluster-1",
            "dummy-role-arn-1",
            "dummy-region-1",
            "dummy-stack-1",
            "dummy-stack-id-1",
        ),
        (
            "db-2",
            "dummy-cluster-2",
            "dummy-role-arn-2",
            "dummy-region-2",
            "dummy-stack-2",
            "dummy-stack-id-2",
        ),
        (
            "db-3",
            "dummy-cluster-3",
            "dummy-role-arn-3",
            "dummy-region-3",
            "dummy-stack-3",
            "dummy-stack-id-3",
        ),
    ],
)
@mock.patch("api.graphql_app.helpers.cfn_ops")
@mock.patch("api.graphql_app.helpers.asyncio")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status_details")
@mock.patch("api.graphql_app.helpers.time")
@mock.patch("api.graphql_app.helpers._get_hosted_zone")
def test__monitor_aws_cluster_status_task__check_create_in_progress_status(
    mocked_get_hosted_zone: mock.MagicMock,
    mocked_time: mock.MagicMock,
    mocked__update_aws_cluster_status_details: mock.MagicMock,
    mocked__update_aws_cluster_status: mock.MagicMock,
    mocked_asyncio: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
    db: str,
    cluster_name: str,
    role_arn: str,
    region_name: str,
    stack_name: str,
    stack_id: str,
):
    """Verify the behaviour of the _monitor_aws_cluster_status_task upon a CREATE_IN_PROGRESS status."""
    mocked_time.sleep = mock.Mock()

    mocked_cfn_ops.get_stack_id = mock.Mock(return_value=stack_id)
    # need side effect so the function can exit the loop
    mocked_cfn_ops.get_stack_status.side_effect = ["CREATE_IN_PROGRESS", "CREATE_COMPLETE"]
    mocked_cfn_ops.get_create_failed_events = mock.Mock()
    mocked_get_hosted_zone.return_value = None

    mocked_asyncio.run = mock.Mock()

    mocked__update_aws_cluster_status.return_value = None

    _monitor_aws_cluster_status_task(db, region_name, role_arn, stack_name, cluster_name)

    mocked_time.sleep.assert_called_once_with(SETTINGS.MONITOR_AWS_CLUSTER_STATUS_INTERVAL)
    mocked__update_aws_cluster_status_details.assert_not_called()
    mocked__update_aws_cluster_status.assert_called_once_with(db, cluster_name, ClusterStatusEnum.ready)
    mocked_cfn_ops.get_create_failed_events.assert_not_called()
    mocked_asyncio.run.assert_called_once_with(mock.ANY)


@mock.patch("api.graphql_app.helpers.cfn_ops")
@mock.patch("api.graphql_app.helpers.asyncio")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status_details")
@mock.patch("api.graphql_app.helpers.time")
@mock.patch("api.graphql_app.helpers._get_hosted_zone")
@mock.patch("api.graphql_app.helpers._retrieve_dns_informations")
@mock.patch("api.graphql_app.helpers._check_route53_record_exists")
@mock.patch("api.graphql_app.helpers._create_jupyter_dns_record")
def test__monitor_aws_cluster_status_task__check_when_dns_already_exist(
    mocked_create_jupyter_dns_record: mock.MagicMock,
    mocked_check_route53_record_exists: mock.MagicMock,
    mocked_retrieve_dns_informations: mock.MagicMock,
    mocked_get_hosted_zone: mock.MagicMock,
    mocked_time: mock.MagicMock,
    mocked__update_aws_cluster_status_details: mock.MagicMock,
    mocked__update_aws_cluster_status: mock.MagicMock,
    mocked_asyncio: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
):
    """Verify the behaviour of the dns creation when cluster is in CREATE_IN_PROGRESS status.

    Check when the dns already exist and should not be recreated/updated
    """
    db = "db-1"
    cluster_name = "dummy-cluster-1"
    role_arn = "dummy-role-arn-1"
    region_name = "dummy-region-1"
    stack_name = "dummy-stack-1"
    stack_id = "dummy-stack-id-1"
    hosted_zone_id = "AABBCC0019191"

    mocked_time.sleep = mock.Mock()

    mocked_cfn_ops.get_stack_id = mock.Mock(return_value=stack_id)
    # need side effect so the function can exit the loop
    mocked_cfn_ops.get_stack_status.side_effect = ["CREATE_IN_PROGRESS", "CREATE_COMPLETE"]
    mocked_cfn_ops.get_create_failed_events = mock.Mock()
    mocked_get_hosted_zone.return_value = hosted_zone_id
    mocked_retrieve_dns_informations.return_value = ("190.10.10.10", "https://test.dev.vantagecompute.ai")
    mocked_check_route53_record_exists.return_value = True

    mocked_asyncio.run = mock.Mock()

    mocked__update_aws_cluster_status.return_value = None

    _monitor_aws_cluster_status_task(db, region_name, role_arn, stack_name, cluster_name)

    mocked_create_jupyter_dns_record.assert_not_called()

    mocked_time.sleep.assert_called_once_with(SETTINGS.MONITOR_AWS_CLUSTER_STATUS_INTERVAL)
    mocked__update_aws_cluster_status_details.assert_not_called()
    mocked__update_aws_cluster_status.assert_called_once_with(db, cluster_name, ClusterStatusEnum.ready)
    mocked_cfn_ops.get_create_failed_events.assert_not_called()
    mocked_asyncio.run.assert_called_once_with(mock.ANY)


@mock.patch("api.graphql_app.helpers.cfn_ops")
@mock.patch("api.graphql_app.helpers.asyncio")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status")
@mock.patch("api.graphql_app.helpers._update_aws_cluster_status_details")
@mock.patch("api.graphql_app.helpers.time")
@mock.patch("api.graphql_app.helpers._get_hosted_zone")
@mock.patch("api.graphql_app.helpers._retrieve_dns_informations")
@mock.patch("api.graphql_app.helpers._check_route53_record_exists")
@mock.patch("api.graphql_app.helpers._create_jupyter_dns_record")
def test__monitor_aws_cluster_status_task__check_when_dns_is_created(
    mocked_create_jupyter_dns_record: mock.MagicMock,
    mocked_check_route53_record_exists: mock.MagicMock,
    mocked_retrieve_dns_informations: mock.MagicMock,
    mocked_get_hosted_zone: mock.MagicMock,
    mocked_time: mock.MagicMock,
    mocked__update_aws_cluster_status_details: mock.MagicMock,
    mocked__update_aws_cluster_status: mock.MagicMock,
    mocked_asyncio: mock.MagicMock,
    mocked_cfn_ops: mock.MagicMock,
):
    """Verify the behaviour of the dns creation when cluster is in CREATE_IN_PROGRESS status.

    Check when the dns is created.
    """
    db = "db-1"
    cluster_name = "dummy-cluster-1"
    role_arn = "dummy-role-arn-1"
    region_name = "dummy-region-1"
    stack_name = "dummy-stack-1"
    stack_id = "dummy-stack-id-1"
    hosted_zone_id = "AABBCC0019191"
    instance_ip = "190.10.10.10"
    jupyterhub_dns = "https://test.dev.vantagecompute.ai"

    mocked_time.sleep = mock.Mock()

    mocked_cfn_ops.get_stack_id = mock.Mock(return_value=stack_id)
    # need side effect so the function can exit the loop
    mocked_cfn_ops.get_stack_status.side_effect = ["CREATE_IN_PROGRESS", "CREATE_COMPLETE"]
    mocked_cfn_ops.get_create_failed_events = mock.Mock()
    mocked_get_hosted_zone.return_value = hosted_zone_id
    mocked_retrieve_dns_informations.return_value = (instance_ip, jupyterhub_dns)
    mocked_check_route53_record_exists.return_value = False

    mocked_asyncio.run = mock.Mock()

    mocked__update_aws_cluster_status.return_value = None

    _monitor_aws_cluster_status_task(db, region_name, role_arn, stack_name, cluster_name)

    mocked_create_jupyter_dns_record.assert_called_once_with(
        ip_address=instance_ip, dns_name=jupyterhub_dns, hosted_zone_id=hosted_zone_id
    )

    mocked_time.sleep.assert_called_once_with(SETTINGS.MONITOR_AWS_CLUSTER_STATUS_INTERVAL)
    mocked__update_aws_cluster_status_details.assert_not_called()
    mocked__update_aws_cluster_status.assert_called_once_with(db, cluster_name, ClusterStatusEnum.ready)
    mocked_cfn_ops.get_create_failed_events.assert_not_called()
    mocked_asyncio.run.assert_called_once_with(mock.ANY)
