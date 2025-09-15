"""Core module for AWS EC2 related operations."""
from collections.abc import Generator
from typing import List

import boto3
from mypy_boto3_ec2.client import EC2Client
from mypy_boto3_ec2.service_resource import EC2ServiceResource
from mypy_boto3_ec2.type_defs import KeyPairInfoTypeDef, SubnetTypeDef, VpcTypeDef

from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials, get_session_credentials


def get_ec2_client(credentials: AssumedSessionCredentials) -> EC2Client:
    """Return the EC2 boto3 client using the input credentals."""
    return boto3.client("ec2", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)


def get_ssh_key_pairs(*, role_arn: str, region_name: str) -> List[KeyPairInfoTypeDef]:
    """Retrieve the SSH key pairs from the AWS account."""
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EC2Client = get_ec2_client(credentials)
    return client.describe_key_pairs()["KeyPairs"]


def get_vpcs(*, role_arn: str, region_name: str) -> Generator[VpcTypeDef, None, None]:
    """Retrieve the VPCs from the AWS account."""
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EC2Client = get_ec2_client(credentials)
    paginator = client.get_paginator("describe_vpcs")
    for page in paginator.paginate(Filters=[{"Name": "state", "Values": ["available"]}]):
        for vpc in page["Vpcs"]:
            yield vpc


def get_subnets(*, role_arn: str, region_name: str, vpc_id: str) -> Generator[SubnetTypeDef, None, None]:
    """Retrieve the subnets from the AWS account."""
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EC2Client = get_ec2_client(credentials)
    paginator = client.get_paginator("describe_subnets")
    for page in paginator.paginate(
        Filters=[{"Name": "state", "Values": ["available"]}, {"Name": "vpc-id", "Values": [vpc_id]}]
    ):
        for subnet in page["Subnets"]:
            yield subnet


def get_ec2_resource(credentials: AssumedSessionCredentials) -> EC2ServiceResource:
    """Receive AWS credentials and return the EC2 boto3 client."""
    ec2: EC2ServiceResource = boto3.resource("ec2", **credentials)
    return ec2


def tag_instance(instance_id: str, tags: dict[str, str], credentials: AssumedSessionCredentials) -> None:
    """Tag the instance with the input tags."""
    client: EC2Client = get_ec2_client(credentials)
    client.create_tags(Resources=[instance_id], Tags=[{"Key": k, "Value": v} for k, v in tags.items()])


def untag_instance(instance_id: str, tags: dict[str, str], credentials: AssumedSessionCredentials) -> None:
    """Untag the instance with the input tags."""
    client: EC2Client = get_ec2_client(credentials)
    client.delete_tags(Resources=[instance_id], Tags=[{"Key": k, "Value": v} for k, v in tags.items()])


def list_instances_by_vpc_id(*, vpc_id: str, role_arn: str, region_name: str) -> List[str]:
    """List the instances by the VPC ID."""
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EC2Client = get_ec2_client(credentials)
    response = client.describe_instances(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    return [
        instance["InstanceId"]
        for reservation in response["Reservations"]
        for instance in reservation["Instances"]
    ]


def list_enabled_regions(role_arn: str) -> List[str]:
    """List the enabled regions."""
    credentials, _ = get_session_credentials(role_arn, "us-east-1")
    client: EC2Client = get_ec2_client(credentials)
    response = client.describe_regions()
    return [region["RegionName"] for region in response["Regions"]]
