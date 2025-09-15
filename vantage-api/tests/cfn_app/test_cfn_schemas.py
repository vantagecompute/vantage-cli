"""Test the schemas used in the cfn_app module."""
from api.cfn_app.schemas import AwsNetworking


def test_aws_networking_schema__no_subnet_for_compute_nodes():
    """Test if the AwsNetworking schema is created correctly when no subnet is supplied for compute nodes."""
    vpc_id = "vpc-123456abc"
    head_node_subnet_id = "subnet-12345abc"

    aws_networking = AwsNetworking(vpc_id=vpc_id, head_node_subnet_id=head_node_subnet_id)

    assert aws_networking.vpc_id == vpc_id
    assert aws_networking.head_node_subnet_id == aws_networking.compute_node_subnet_id == head_node_subnet_id


def test_aws_networking_schema__supply_compute_node_subnet():
    """Test if the AwsNetworking schema is created correctly when all inputs are supplied."""
    vpc_id = "vpc-123456abc"
    head_node_subnet_id = "subnet-12345abc"
    compute_node_subnet_id = "subnet-12345abcde"

    aws_networking = AwsNetworking(
        vpc_id=vpc_id, head_node_subnet_id=head_node_subnet_id, compute_node_subnet_id=compute_node_subnet_id
    )

    assert aws_networking.vpc_id == vpc_id
    assert aws_networking.head_node_subnet_id == aws_networking.head_node_subnet_id
    assert aws_networking.compute_node_subnet_id == compute_node_subnet_id
