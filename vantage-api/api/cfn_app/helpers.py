"""Core module for storing helper functions to retrieve AWS information."""
import json
import string
from typing import Any, Union, cast, get_args

import boto3
import botocore.exceptions
from mypy_boto3_ec2.literals import InstanceTypeType
from mypy_boto3_ec2.service_resource import EC2ServiceResource

from api.cfn_app.schemas import AwsNetworking
from api.utils.logging import logger

ec2 = boto3.client("ec2")


def get_cpu_by_instance_type(instance_type: InstanceTypeType) -> int:
    """Retrieve the number of VCPUs a instance has by its type."""
    instance_details = ec2.describe_instance_types(InstanceTypes=[instance_type])["InstanceTypes"][0]
    return instance_details["VCpuInfo"]["DefaultVCpus"]


def get_memory_by_instance_type(instance_type: InstanceTypeType) -> int:
    """Retrieve the number of memory (in MiB) a instance has by its type."""
    instance_details = ec2.describe_instance_types(InstanceTypes=[instance_type])["InstanceTypes"][0]
    return instance_details["MemoryInfo"]["SizeInMiB"]


def get_gpu_count_by_instance_type(instance_type: InstanceTypeType) -> int:
    """Retrieve the number of GPUs a instance has by its type."""
    instance_details = ec2.describe_instance_types(InstanceTypes=[instance_type])["InstanceTypes"][0]
    if gpu_info := instance_details.get("GpuInfo"):
        instance_gpus = gpu_info["Gpus"]
        return instance_gpus[0]["Count"]
    return 0


def _validate_vpc_state(ec2: EC2ServiceResource, vpc_id: str) -> None:
    """Check if the supplied VPC ID is valid. In case it is, check if the VPC is available."""
    vpc = ec2.Vpc(vpc_id)
    try:
        vpc_state = vpc.state
    except botocore.exceptions.ClientError as err:
        # check https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
        # for details
        raise Exception(err.response["Error"]["Message"])
    else:
        if vpc_state != "available":
            raise Exception(f"VPC {vpc_id} is not available for usage")


def _validate_subnet(ec2: EC2ServiceResource, subnet_id: str) -> None:
    """Check if the supplied Subnet ID is valid. In case it is, check if the subnet is available."""
    subnet = ec2.Subnet(subnet_id)
    try:
        logger.debug(f"Attempting to validate subnet ({subnet_id}) state")
        subnet_state = subnet.state
    except botocore.exceptions.ClientError as err:
        logger.debug(f"Subnet {subnet_id} is not valid. Error message: {err.response['Error']['Message']}")
        raise Exception(err.response["Error"]["Message"])
    else:
        logger.debug(f"Subnet {subnet_id} is valid. Checking if it is available for usage")
        if subnet_state != "available":
            logger.debug(
                f"Subnet {subnet_id} has state {subnet_state}, which indicates it isn't available for usage"
            )
            raise Exception(f"Subnet {subnet_id} is not available for usage")
        logger.debug(f"Subnet {subnet_id} is valid and available for usage")


def verify_networking_inputs(ec2: boto3.Session.resource, networking: Union[AwsNetworking, None]) -> None:
    """Check if network resources from AWS are valid and able for usage.

    After all network resources are checked and verified, return a
    pydantic model.
    """
    _validate_vpc_state(ec2, networking.vpc_id)
    _validate_subnet(ec2, networking.head_node_subnet_id)
    if networking.compute_node_subnet_id != networking.head_node_subnet_id:
        _validate_subnet(ec2, networking.compute_node_subnet_id)


def load_stack_template(create_vpc: bool) -> dict[str, Any]:
    """Load the CloudFormation template based on whether create or not the VPC."""
    stack_template_path = (
        "api/cfn_app/stacks/slurm_cluster_with_self_deployed_networking.json"
        if create_vpc
        else "api/cfn_app/stacks/slurm_cluster_with_supplied_networking.json"
    )
    stack_template = json.load(open(stack_template_path))
    return stack_template


def _first_block_of_partition_string(
    partition_name: str, max_node_count: int, region: str, node_type: InstanceTypeType, num_gpu: int
) -> str:
    return (
        string.Template(
            """
            {
                "PartitionName": "$partition_name",
                "NodeGroups": [
                {
                    "NodeGroupName": "$partition_name",
                    "MaxNodes": $max_node_count,
                    "Region": "$region",
                    "SlurmSpecifications": {
                        "Weight": 1,
                        "Feature": "cloud",
                        $gres
                        "CPUs": $vcpu,
                        "RealMemory": $memory
                    },
                    "PurchasingOption": "on-demand",
                    "OnDemandOptions": {
                        "AllocationStrategy": "lowest-price"
                    },
                    "LaunchTemplateSpecification": {
                        "LaunchTemplateId": "
            """
        )
        .substitute(
            partition_name=partition_name,
            max_node_count=max_node_count,
            region=region,
            vcpu=get_cpu_by_instance_type(node_type),
            memory=get_memory_by_instance_type(node_type),
            gres=f'"Gres": "gpu:{num_gpu}",' if num_gpu else "",
        )
        .strip()
        .replace("\n", "")
        .replace("\t", "")
        .replace(" ", "")
    )


def _second_block_of_partition_string() -> dict[str, str]:
    return {"Ref": "ComputeNodeLaunchTemplateE8D45573"}


def _third_block_of_partition_string(node_type: InstanceTypeType) -> str:
    return (
        string.Template(
            """
            ","Version": "$$Latest"},
            "LaunchTemplateOverrides": [
                {"InstanceType": "$node_type"}
            ],"SubnetIds": ["
            """
        )
        .substitute(node_type=node_type)
        .strip()
        .replace("\n", "")
        .replace("\t", "")
        .replace(" ", "")
    )


def _fourth_block_of_partition_string(create_vpc: bool) -> dict[str, str]:
    return {"Ref": "PrivateSubnetD9FAAE02" if create_vpc else "ComputeNodeSubnetId"}


def _fifth_block_of_partition_string(is_default: bool) -> str:
    return (
        string.Template(
            """
            "]}],"PartitionOptions": {"Default": "$default"}}
            """
        )
        .substitute(default="Yes" if is_default else "No")
        .strip()
    )


def build_dynamic_partitions(partitions: list[dict[str, str | int | bool]], region: str, create_vpc: bool):
    """Build the dynamic partitions block for the cluster stack.

    This function generates a dynamic partitions structure based on the provided parameters.
    Each partition defines a node group with specific configurations such as instance type, region,
    maximum number of nodes, and more. The resulting structure is used to dynamically configure
    the cluster's resources, facilitating node management and scalability according to requirements.

    Parameters:*
    - partitions (list of dict): A list of dictionaries where each dictionary represents
    a partition with the following keys:
        - name (str): The name of the partition.
        - node_type (str): The instance type for the nodes (e.g., "m5.large").
        - max_node_count (int): The maximum number of nodes allowed in this partition.
        - is_default (bool): Indicates whether this partition is the default (True) or not (False).

    - region (str): The AWS region where the nodes will be deployed (e.g., "us-east-1").

    - create_vpc (bool): Indicates whether to create a VPC (Virtual Private Cloud). If 'True',
    private subnets are used; otherwise, compute node subnets are utilized.

    Returns
    -------
    - 'dict': A dictionary representing the dynamic partitions block, formatted for use in the cluster stack.

    Example Usage:

    ```python
    partitions = [
        {
            "name": "partition1",
            "node_type": "m5.large",
            "max_node_count": 10,
            "is_default": True
        },
        {
            "name": "partition2",
            "node_type": "c5.xlarge",
            "max_node_count": 5,
            "is_default": False
        }
    ]

    region = "us-east-1"
    create_vpc = True

    dynamic_partitions = build_dynamic_partitions(partitions, region, create_vpc)
    ```

    Expected Output:

    ```python dict
    {
        'Fn::Join': [
            '',
            [
                '{"Partitions": [',
                {
                    'Fn::Join': [
                        '',
                        [
                            '{"PartitionName":"partition1","NodeGroups":[{"NodeGroupName":"partition1","MaxNodes":10,"Region":"us-east-1","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":2,"RealMemory":1024},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                            {'Ref': 'ComputeNodeLaunchTemplateE8D45573'},
                            '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"m5.large"}],"SubnetIds":["',
                            {'Ref': 'PrivateSubnetD9FAAE02'},
                            '"]}],"PartitionOptions": {"Default": "Yes"}}',
                            ','
                        ]
                    ]
                },
                {
                    'Fn::Join': [
                        '',
                        [
                            '{"PartitionName":"partition2","NodeGroups":[{"NodeGroupName":"partition2","MaxNodes":5,"Region":"us-east-1","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":4,"RealMemory":1024},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                            {'Ref': 'ComputeNodeLaunchTemplateE8D45573'},
                            '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"c5.xlarge"}],"SubnetIds":["',
                            {'Ref': 'PrivateSubnetD9FAAE02'},
                            '"]}],"PartitionOptions": {"Default": "No"}}',
                            ''
                        ]
                    ]
                },
                ']}'
            ]
        ]
    }
    ```

    Example Description:

    - Defines Two Partitions:
        - partition1:
            - Instance Type: 'm5.large'
            - Maximum Nodes: 10
            - Default Partition: Yes
            - vCPUs: 2 (as returned by 'get_cpu_by_instance_type("m5.large")')
            - memory: 8192 (as returned by 'get_memory_by_instance_type("m5.large")')
        - partition2:
            - Instance Type: 'c5.xlarge'
            - Maximum Nodes: 5
            - Default Partition: No
            - vCPUs: 4 (as returned by 'get_cpu_by_instance_type("c5.xlarge")')
            - memory: 8192 (as returned by 'get_memory_by_instance_type("c5.xlarge")')
    - Region: 'us-east-1' for both partitions.
    - VPC Creation: 'create_vpc=True', hence using 'PrivateSubnetD9FAAE02' for subnet references.
    """
    partitions_blocks = []
    for index, partition in enumerate(partitions):
        partition_name = partition.get("name")
        node_type = partition.get("node_type")

        if partition_name is None or not isinstance(partition_name, str):
            raise ValueError("Partition name must be a non-empty string.")
        if node_type is None or not isinstance(node_type, str):
            raise ValueError("Node type must be a non-empty string.")
        if node_type not in get_args(InstanceTypeType):
            raise ValueError(f"Node type '{node_type}' is not a valid instance type.")
        node_type = cast(InstanceTypeType, node_type)

        num_gpu = get_gpu_count_by_instance_type(node_type)

        dict_block = {
            "Fn::Join": [
                "",
                [
                    _first_block_of_partition_string(
                        partition_name=partition_name,
                        max_node_count=partition.get("max_node_count"),
                        region=region,
                        node_type=node_type,
                        num_gpu=num_gpu,
                    ),
                    _second_block_of_partition_string(),
                    _third_block_of_partition_string(node_type=node_type),
                    _fourth_block_of_partition_string(create_vpc=create_vpc),
                    _fifth_block_of_partition_string(is_default=partition.get("is_default")),
                    "," if index + 1 != len(partitions) else "",
                ],
            ]
        }
        partitions_blocks.append(dict_block)

    content_block = {"Fn::Join": ["", ["""{"Partitions": [""", *partitions_blocks, "]}"]]}

    return content_block


def generate_stack_template(
    partitions: list[dict[str, str | int | bool]],
    region: str,
    create_vpc: bool,
):
    """Generate the CloudFormation template based on whether create or not the VPC and partitions."""
    template = load_stack_template(create_vpc=create_vpc)
    plain_template = json.dumps(template)

    ## Injecting dynamic blocks to the template
    partitions_block = build_dynamic_partitions(partitions=partitions, region=region, create_vpc=create_vpc)
    plain_template = plain_template.replace('"<DynamicPartitionBlock>"', json.dumps(partitions_block))

    template = json.loads(plain_template)
    return template
