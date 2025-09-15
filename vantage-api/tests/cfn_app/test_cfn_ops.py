"""Test cases for cfn_ops module."""
import itertools
import json
import random
import uuid
from unittest import mock

import pytest
from pytest_mock import MockerFixture

from api.cfn_app.cfn_ops import _get_cfn_client, apply_template, destroy_stack
from api.cfn_app.contants import AMI_MAPPER, AVZ_MAPPER
from api.schemas.aws import AwsOpsConfig
from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stage_snap_channel_tuple, region_name, app_domain",
    itertools.product(
        [
            ("production", "stable"),
            ("staging", "candidate"),
            ("qa", "beta"),
            (str(uuid.uuid4()), "edge"),
            (str(uuid.uuid4()).upper(), "edge"),
        ],
        AVZ_MAPPER.keys(),
        ["example.click", "dummy.co.uk"],
    ),
)
async def test_cfn_ops__apply_template_with_success(
    stage_snap_channel_tuple: tuple[str, str], region_name: str, app_domain: str
):
    """Test when apply_template function is called and returns without errors."""
    stage, snap_channel = stage_snap_channel_tuple
    cluster_name = str(uuid.uuid4())
    credentials = {
        "role_arn": str(uuid.uuid4()),
        "region_name": region_name,
    }
    key_pair = str(uuid.uuid4())
    head_node_instance_type = str(uuid.uuid4())
    compute_node_instance_type = str(uuid.uuid4())
    params = {
        "key_pair": key_pair,
        "head_node_instance_type": head_node_instance_type,
        "compute_node_instance_type": compute_node_instance_type,
    }
    client_secret = str(uuid.uuid4())
    jupyterhub_token = str(uuid.uuid4())
    aws_account = str(uuid.uuid4())
    partitions = [
        {
            "name": str(uuid.uuid4()),
            "max_node_count": random.randint(1, 100),
            "node_type": str(uuid.uuid4()),
            "is_default": True,
        }
    ]

    cfn_mock = mock.Mock()
    cfn_mock.create_stack = mock.Mock()
    mock_get_cfn_client = mock.Mock(return_value=cfn_mock)

    mock_get_ec2_resource = mock.Mock(return_value=cfn_mock)

    sts_mock = mock.Mock()
    sts_mock.get_caller_identity = mock.Mock()
    sts_mock.get_caller_identity.return_value = {"Account": aws_account}
    session_credentials = {
        "aws_access_key_id": str(uuid.uuid4()),
        "aws_secret_access_key": str(uuid.uuid4()),
        "aws_session_token": str(uuid.uuid4()),
        "role_name": region_name,
    }
    mock_get_session_credentials = mock.Mock(return_value=(session_credentials, sts_mock))

    mock_generate_template = mock.Mock(return_value={})

    slurmdbd_password = str(uuid.uuid4())
    influxdb_password = str(uuid.uuid4())

    mock_secrets = mock.Mock()
    mock_secrets.token_urlsafe = mock.Mock()
    mock_secrets.token_urlsafe.side_effect = [slurmdbd_password, influxdb_password]

    with mock.patch.object(SETTINGS, "STAGE", stage), mock.patch.object(
        SETTINGS, "APP_DOMAIN", app_domain
    ), mock.patch("api.cfn_app.cfn_ops._get_cfn_client", mock_get_cfn_client), mock.patch(
        "api.cfn_app.cfn_ops.ec2_ops.get_ec2_resource", mock_get_ec2_resource
    ), mock.patch(
        "api.cfn_app.cfn_ops.sts_ops.get_session_credentials", mock_get_session_credentials
    ), mock.patch("api.cfn_app.cfn_ops.generate_stack_template", mock_generate_template), mock.patch(
        "api.cfn_app.cfn_ops.secrets", mock_secrets
    ):
        response = apply_template(
            config=credentials,
            slurm_cluster_name=cluster_name,
            api_cluster_name=cluster_name,
            client_id=cluster_name,
            client_secret=client_secret,
            jupyterhub_token=jupyterhub_token,
            networking=None,
            partitions=partitions,
            **params,
        )
    assert response is None

    match stage:
        case "production":
            vantage_agents_base_api_url = f"https://apis.{app_domain}"
            vantage_agents_oidc_domain = f"auth.{app_domain}/realms/vantage"
            jupyterhub_dns = f"{cluster_name}.{app_domain}"
            snap_channel = "stable"
        case "staging":
            vantage_agents_base_api_url = f"https://apis.staging.{app_domain}"
            vantage_agents_oidc_domain = f"auth.staging.{app_domain}/realms/vantage"
            jupyterhub_dns = f"{cluster_name}.staging.{app_domain}"
            snap_channel = "candidate"
        case "qa":
            vantage_agents_base_api_url = f"https://apis.qa.{app_domain}"
            vantage_agents_oidc_domain = f"auth.qa.{app_domain}/realms/vantage"
            jupyterhub_dns = f"{cluster_name}.qa.{app_domain}"
            snap_channel = "beta"
        case _:
            vantage_agents_base_api_url = f"https://apis.{stage.lower()}.{app_domain}"
            vantage_agents_oidc_domain = f"auth.{stage.lower()}.{app_domain}/realms/vantage"
            jupyterhub_dns = f"{cluster_name}.{stage.lower()}.{app_domain}"
            snap_channel = "edge"

    mock_get_cfn_client.assert_called_once_with(session_credentials)
    mock_get_ec2_resource.assert_called_once_with(session_credentials)
    mock_get_session_credentials.assert_called_once_with(
        role_arn=credentials.get("role_arn"), region_name=credentials.get("region_name")
    )
    mock_generate_template.assert_called_once_with(
        create_vpc=True, region=credentials.get("region_name"), partitions=partitions
    )

    cfn_mock.create_stack.assert_called_once_with(
        StackName=cluster_name,
        TemplateBody=json.dumps({}),
        Parameters=[
            {"ParameterKey": "ClientId", "ParameterValue": cluster_name},
            {"ParameterKey": "ClientSecret", "ParameterValue": client_secret},
            {"ParameterKey": "JupyterHubToken", "ParameterValue": jupyterhub_token},
            {"ParameterKey": "JupyterHubDns", "ParameterValue": jupyterhub_dns},
            {
                "ParameterKey": "HeadNodeAmiId",
                "ParameterValue": AMI_MAPPER.get("head").get(credentials.get("region_name")),
            },
            {"ParameterKey": "VantageAgentsBaseApiUrl", "ParameterValue": vantage_agents_base_api_url},
            {"ParameterKey": "VantageAgentsOidcDomain", "ParameterValue": vantage_agents_oidc_domain},
            {"ParameterKey": "SlurmdbdPassword", "ParameterValue": slurmdbd_password},
            {"ParameterKey": "InfluxdbPassword", "ParameterValue": influxdb_password},
            {"ParameterKey": "ClusterName", "ParameterValue": cluster_name},
            {"ParameterKey": "ApiClusterName", "ParameterValue": cluster_name},
            {"ParameterKey": "KeyPair", "ParameterValue": key_pair},
            {"ParameterKey": "HeadNodeInstanceType", "ParameterValue": head_node_instance_type},
            {"ParameterKey": "SnapChannel", "ParameterValue": snap_channel},
            {
                "ParameterKey": "PublicAvailabilityZone",
                "ParameterValue": AVZ_MAPPER.get(credentials.get("region_name")).get("public"),
            },
            {
                "ParameterKey": "PrivateAvailabilityZone",
                "ParameterValue": AVZ_MAPPER.get(credentials.get("region_name")).get("private"),
            },
        ],
        Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        OnFailure="DELETE",
    )
    mock_secrets.token_urlsafe.assert_has_calls([mock.call(32), mock.call(32)])


@pytest.mark.asyncio
async def test_cfn_ops__destroy_stack_with_success(mocker: MockerFixture):
    """Test when destroy_stack function is called and returns without errors."""
    cluster_name = "DummyCluster"
    credentials: AwsOpsConfig = {
        "role_arn": "123123",
        "region_name": "region",
    }
    formatted_credentials = {
        "aws_access_key_id": "dummy_access_key_id",
        "aws_secret_access_key": "dummy_secret",
        "aws_session_token": "dummy_token",
        "region_name": credentials["region_name"],
    }

    sts_mock = mock.Mock()
    stack_mock = mock.Mock()
    stack_mock.delete = mock.Mock()
    cfn_mock = mock.Mock()
    cfn_mock.Stack = mock.Mock(return_value=stack_mock)
    get_cfn_resource_mock = mock.Mock(return_value=cfn_mock)
    get_session_credentials = mock.Mock(return_value=(formatted_credentials, sts_mock))

    mocker.patch("api.cfn_app.cfn_ops._get_cfn_resource", get_cfn_resource_mock)
    mocker.patch("api.cfn_app.cfn_ops.sts_ops.get_session_credentials", get_session_credentials)

    destroy_stack(cluster_name, credentials)

    get_cfn_resource_mock.assert_called_once_with(formatted_credentials)
    cfn_mock.Stack.assert_called_once_with(cluster_name)
    stack_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_cfn_ops__get_boto3_cfn_client(mocker: MockerFixture):
    """Test function to get boto3 client with the cloudformation service."""
    credentials: AssumedSessionCredentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }

    cfn_mock = mock.Mock()
    cfn_mock.create_stack = mock.Mock()
    client_mock = mock.Mock(return_value=cfn_mock)

    mocker.patch("boto3.client", client_mock)

    response = _get_cfn_client(credentials)

    assert response is cfn_mock
    client_mock.assert_called_once_with(
        "cloudformation", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL
    )


@pytest.mark.asyncio
async def test_cfn_ops__get_boto3_cfn_resource(mocker: MockerFixture):
    """Test function to get boto3 resource with the cloudformation resource."""
    from api.cfn_app.cfn_ops import _get_cfn_resource

    credentials: AssumedSessionCredentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }

    cfn_mock = mock.Mock()
    cfn_mock.create_stack = mock.Mock()
    resource_mock = mock.Mock(return_value=cfn_mock)
    mocker.patch("boto3.resource", resource_mock)

    response = _get_cfn_resource(credentials)

    assert response is cfn_mock
    resource_mock.assert_called_once_with(
        "cloudformation", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL
    )
