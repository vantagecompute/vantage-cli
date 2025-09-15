"""Core module for maintening the functions to deploy and destroy a Slurm cluster on AWS by CloudFormation."""
import json
import secrets
from enum import Enum
from typing import Dict, List, Union

import boto3
from mypy_boto3_cloudformation.client import CloudFormationClient
from mypy_boto3_cloudformation.literals import StackStatusType
from mypy_boto3_cloudformation.service_resource import CloudFormationServiceResource
from mypy_boto3_cloudformation.type_defs import StackEventTypeDef, StackResourceTypeDef

from api.cfn_app.contants import AMI_MAPPER, AVZ_MAPPER
from api.cfn_app.helpers import generate_stack_template, verify_networking_inputs
from api.cfn_app.schemas import AwsNetworking
from api.ec2_app import ec2_ops
from api.schemas.aws import AwsOpsConfig
from api.settings import SETTINGS
from api.sts_app import sts_ops
from api.utils.logging import logger


def _get_cfn_client(credentials: sts_ops.AssumedSessionCredentials) -> CloudFormationClient:
    """Receive AWS credentials and return the CloudFormation boto3 client."""
    cfn: CloudFormationClient = boto3.client(
        "cloudformation", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL
    )
    return cfn


def _get_cfn_resource(credentials: sts_ops.AssumedSessionCredentials) -> CloudFormationServiceResource:
    """Receive AWS credentials and return the CloudFormation boto3 resource."""
    cfn: CloudFormationServiceResource = boto3.resource(
        "cloudformation", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL
    )
    return cfn


def apply_template(
    config: AwsOpsConfig,
    slurm_cluster_name: str,
    api_cluster_name: str,
    client_id: str,
    client_secret: str,
    jupyterhub_token: str,
    networking: Union[Dict[str, Union[str, None]], AwsNetworking, None],
    partitions: list[dict[str, str | int | bool]],
    **params,
) -> None:
    """Receive the AWS attributes and deploy a Slurm cluster on AWS by CloudFormation."""
    head_node_instance_type = params.get("head_node_instance_type")
    if isinstance(head_node_instance_type, Enum):
        head_node_instance_type = head_node_instance_type.value

    if isinstance(config.get("region_name"), Enum):
        config["region_name"] = config.get("region_name").value

    match SETTINGS.STAGE:
        case "production":
            vantage_agents_base_api_url = f"https://apis.{SETTINGS.APP_DOMAIN}"
            vantage_agents_oidc_domain = f"auth.{SETTINGS.APP_DOMAIN}/realms/vantage"
            jupyterhub_dns = f"{client_id}.{SETTINGS.APP_DOMAIN}"
            snap_channel = "stable"
        case "staging":
            vantage_agents_base_api_url = f"https://apis.staging.{SETTINGS.APP_DOMAIN}"
            vantage_agents_oidc_domain = f"auth.staging.{SETTINGS.APP_DOMAIN}/realms/vantage"
            jupyterhub_dns = f"{client_id}.staging.{SETTINGS.APP_DOMAIN}"
            snap_channel = "candidate"
        case "qa":
            vantage_agents_base_api_url = f"https://apis.qa.{SETTINGS.APP_DOMAIN}"
            vantage_agents_oidc_domain = f"auth.qa.{SETTINGS.APP_DOMAIN}/realms/vantage"
            jupyterhub_dns = f"{client_id}.qa.{SETTINGS.APP_DOMAIN}"

            snap_channel = "beta"
        case _:
            vantage_agents_base_api_url = f"https://apis.{SETTINGS.STAGE.lower()}.{SETTINGS.APP_DOMAIN}"
            vantage_agents_oidc_domain = f"auth.{SETTINGS.STAGE.lower()}.{SETTINGS.APP_DOMAIN}/realms/vantage"
            jupyterhub_dns = f"{client_id}.{SETTINGS.STAGE.lower()}.{SETTINGS.APP_DOMAIN}"
            snap_channel = "edge"

    stack_parameters = [
        {
            "ParameterKey": "ClientId",
            "ParameterValue": client_id,
        },
        {
            "ParameterKey": "ClientSecret",
            "ParameterValue": client_secret,
        },
        {
            "ParameterKey": "JupyterHubToken",
            "ParameterValue": jupyterhub_token,
        },
        {
            "ParameterKey": "JupyterHubDns",
            "ParameterValue": jupyterhub_dns,
        },
        {
            "ParameterKey": "HeadNodeAmiId",
            "ParameterValue": AMI_MAPPER.get("head").get(config.get("region_name")),
        },
        {
            "ParameterKey": "VantageAgentsBaseApiUrl",
            "ParameterValue": vantage_agents_base_api_url,
        },
        {
            "ParameterKey": "VantageAgentsOidcDomain",
            "ParameterValue": vantage_agents_oidc_domain,
        },
        {
            "ParameterKey": "SlurmdbdPassword",
            "ParameterValue": secrets.token_urlsafe(32),
        },
        {
            "ParameterKey": "InfluxdbPassword",
            "ParameterValue": secrets.token_urlsafe(32),
        },
        {
            "ParameterKey": "ClusterName",
            "ParameterValue": slurm_cluster_name,
        },
        {
            "ParameterKey": "ApiClusterName",
            "ParameterValue": api_cluster_name,
        },
        {
            "ParameterKey": "KeyPair",
            "ParameterValue": params.get("key_pair"),
        },
        {
            "ParameterKey": "HeadNodeInstanceType",
            "ParameterValue": head_node_instance_type,
        },
        {
            "ParameterKey": "SnapChannel",
            "ParameterValue": snap_channel,
        },
    ]

    role_arn = config.get("role_arn")
    region_name = config.get("region_name")
    assert role_arn is not None
    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    session_credentials, sts = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)

    cfn = _get_cfn_client(session_credentials)
    ec2 = ec2_ops.get_ec2_resource(session_credentials)

    if networking is not None:
        if isinstance(networking, dict):
            networking = AwsNetworking(**networking)
        verify_networking_inputs(ec2, networking)
        stack_parameters.extend(
            [
                {"ParameterKey": "VpcId", "ParameterValue": networking.vpc_id},
                {"ParameterKey": "HeadNodeSubnetId", "ParameterValue": networking.head_node_subnet_id},
                {"ParameterKey": "ComputeNodeSubnetId", "ParameterValue": networking.compute_node_subnet_id},
            ]
        )
        create_vpc = False
        logger.debug("Set to use the Slurm cluster stack with networking resources supplied")
    else:
        avz = AVZ_MAPPER.get(region_name)
        assert avz is not None
        assert avz.get("public") is not None
        assert avz.get("private") is not None
        stack_parameters.extend(
            [
                {
                    "ParameterKey": "PublicAvailabilityZone",
                    "ParameterValue": avz.get("public"),
                },
                {
                    "ParameterKey": "PrivateAvailabilityZone",
                    "ParameterValue": avz.get("private"),
                },
            ]
        )
        create_vpc = True
        logger.debug("Set to use the Slurm cluster stack with self networking deployment")

    template = generate_stack_template(create_vpc=create_vpc, region=region_name, partitions=partitions)

    cfn.create_stack(
        StackName=slurm_cluster_name,
        TemplateBody=json.dumps(template),
        Parameters=stack_parameters,
        Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
        OnFailure="DELETE",
    )
    logger.debug("CloudFormation stack submitted to AWS on behalf of the user successfully")


def destroy_stack(stack_name: str, cfn_config: AwsOpsConfig) -> None:
    """Given the stack name, destroy the CloudFormation stack related to the cluster."""
    region_name = cfn_config.get("region_name")
    if isinstance(region_name, Enum):
        assert isinstance(region_name, Enum)  # mypy purposes
        region_name = region_name.value

    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    role_arn = cfn_config.get("role_arn")
    assert role_arn is not None

    session_credentials, _ = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = _get_cfn_resource(session_credentials)
    stack = cfn.Stack(stack_name)
    stack.delete()


def get_stack_resources(stack_name: str, cfn_config: AwsOpsConfig) -> List[StackResourceTypeDef] | None:
    """Given the stack name, return the CloudFormation stack related to the cluster."""
    region_name = cfn_config.get("region_name")
    if isinstance(region_name, Enum):
        assert isinstance(region_name, Enum)  # mypy purposes
        region_name = region_name.value

    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    role_arn = cfn_config.get("role_arn")
    assert role_arn is not None

    session_credentials, _ = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = _get_cfn_client(session_credentials)
    try:
        stack_resources = cfn.describe_stack_resources(
            StackName=stack_name,
        )["StackResources"]
    except cfn.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ValidationError":
            logger.warning("Stack does not exist")
            return None

    return stack_resources


def get_stack_status(stack_name: str, cfn_config: AwsOpsConfig) -> StackStatusType | None:
    """Given the stack name, return the status of the CloudFormation stack related to the cluster."""
    region_name = cfn_config.get("region_name")
    if isinstance(region_name, Enum):
        assert isinstance(region_name, Enum)  # mypy purposes
        region_name = region_name.value

    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    role_arn = cfn_config.get("role_arn")
    assert role_arn is not None

    session_credentials, _ = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = _get_cfn_client(session_credentials)
    try:
        stack_status = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]["StackStatus"]
    except cfn.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ValidationError":
            logger.warning("Stack does not exist")
            return None

    return stack_status


def get_stack_id(stack_name: str, cfn_config: AwsOpsConfig) -> str | None:
    """Fetch the CloudFormation stack id given a CloudFormation stack name."""
    region_name = cfn_config.get("region_name")
    if isinstance(region_name, Enum):
        assert isinstance(region_name, Enum)  # mypy purposes
        region_name = region_name.value

    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    role_arn = cfn_config.get("role_arn")
    assert role_arn is not None

    session_credentials, _ = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = _get_cfn_client(session_credentials)

    stack_id: str | None = None

    paginator = cfn.get_paginator("list_stacks")
    for page in paginator.paginate():
        for stack in page["StackSummaries"]:
            if stack["StackName"] == stack_name:
                stack_id = stack["StackId"]
                break

    return stack_id


def get_create_failed_events(stack_name: str, cfn_config: AwsOpsConfig) -> List[StackEventTypeDef]:
    """Fetch the CloudFormation stack events given a CloudFormation stack name."""
    region_name = cfn_config.get("region_name")
    if isinstance(region_name, Enum):
        assert isinstance(region_name, Enum)  # mypy purposes
        region_name = region_name.value

    assert region_name is not None and isinstance(region_name, str)  # mypy purposes

    role_arn = cfn_config.get("role_arn")
    assert role_arn is not None

    session_credentials, _ = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = _get_cfn_client(session_credentials)

    failed_events = []
    paginator = cfn.get_paginator("describe_stack_events")
    for page in paginator.paginate(StackName=stack_name):
        for event in page["StackEvents"]:
            if event["ResourceStatus"] == "CREATE_FAILED":
                failed_events.append(event)

    return failed_events
