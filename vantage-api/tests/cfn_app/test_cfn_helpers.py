"""Test cases for cfn_ops module."""
import json
import uuid
from typing import cast
from unittest import mock

import pytest
from botocore.stub import Stubber
from mypy_boto3_ec2.literals import InstanceTypeType

from api.cfn_app.helpers import (
    build_dynamic_partitions,
    get_cpu_by_instance_type,
    get_gpu_count_by_instance_type,
)
from api.cfn_app.helpers import (
    ec2 as ec2_client,
)


@pytest.mark.parametrize(
    "create_vpc,template_path",
    [
        (True, "tests/cfn_app/slurm_cluster_with_self_deployed_networking.json"),
        (False, "tests/cfn_app/slurm_cluster_with_supplied_networking.json"),
    ],
)
def test_cfn_ops__load_cloudformation_template(create_vpc: bool, template_path: str):
    """Test when generate_template function is called and returns without errors."""
    from api.cfn_app.helpers import load_stack_template

    expected_template = json.loads(open(template_path).read())

    current_template = load_stack_template(create_vpc=create_vpc)

    assert expected_template == current_template


class TestBuildDynamicPartitions:
    """Test cases for the build_dynamic_partitions function."""

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__only_cpu_instances(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the correct built of the partitions block when there's no instance with GPU."""
        mocked_get_cpu_by_instance_type.side_effect = [2, 4]
        mocked_get_memory_by_instance_type.side_effect = [2048, 4096]
        mocked_get_gpu_count_by_instance_type.side_effect = [0, 0]
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "node_type": "m5.large", "max_node_count": 10, "is_default": True},
            {"name": "partition2", "node_type": "c7i-flex.xlarge", "max_node_count": 3, "is_default": False},
        ]
        expected = {
            "Fn::Join": [
                "",
                [
                    '{"Partitions": [',
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition1","NodeGroups":[{"NodeGroupName":"partition1","MaxNodes":10,"Region":"us-east-1","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":2,"RealMemory":2048},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"m5.large"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "Yes"}}',
                                ",",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition2","NodeGroups":[{"NodeGroupName":"partition2","MaxNodes":3,"Region":"us-east-1","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":4,"RealMemory":4096},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"c7i-flex.xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "No"}}',
                                "",
                            ],
                        ]
                    },
                    "]}",
                ],
            ]
        }

        response_block = build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-east-1")

        assert response_block == expected
        mocked_get_cpu_by_instance_type.assert_has_calls(
            [mock.call("m5.large"), mock.call("c7i-flex.xlarge")]
        )
        mocked_get_gpu_count_by_instance_type.assert_has_calls(
            [mock.call("m5.large"), mock.call("c7i-flex.xlarge")]
        )

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__only_gpu_instances(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the correct built of the partitions block when there are only instances with GPU."""
        mocked_get_cpu_by_instance_type.side_effect = [4, 96]
        mocked_get_memory_by_instance_type.side_effect = [2048, 4096]
        mocked_get_gpu_count_by_instance_type.side_effect = [1, 8]
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "node_type": "g4dn.xlarge", "max_node_count": 4, "is_default": True},
            {"name": "partition2", "node_type": "p4d.24xlarge", "max_node_count": 1, "is_default": False},
        ]
        expected = {
            "Fn::Join": [
                "",
                [
                    '{"Partitions": [',
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition1","NodeGroups":[{"NodeGroupName":"partition1","MaxNodes":4,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","Gres":"gpu:1","CPUs":4,"RealMemory":2048},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',  # noqa
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"g4dn.xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "Yes"}}',
                                ",",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition2","NodeGroups":[{"NodeGroupName":"partition2","MaxNodes":1,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","Gres":"gpu:8","CPUs":96,"RealMemory":4096},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',  # noqa
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"p4d.24xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "No"}}',
                                "",
                            ],
                        ]
                    },
                    "]}",
                ],
            ]
        }

        response_block = build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        assert response_block == expected
        mocked_get_cpu_by_instance_type.assert_has_calls(
            [mock.call("g4dn.xlarge"), mock.call("p4d.24xlarge")]
        )
        mocked_get_gpu_count_by_instance_type.assert_has_calls(
            [mock.call("g4dn.xlarge"), mock.call("p4d.24xlarge")]
        )

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__mix_of_instances(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the correct built of the partitions block when there are only instances with GPU."""
        mocked_get_cpu_by_instance_type.side_effect = [192, 48, 128, 4]
        mocked_get_memory_by_instance_type.side_effect = [2048, 4096, 8192, 16384]
        mocked_get_gpu_count_by_instance_type.side_effect = [8, 0, 0, 1]
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "node_type": "p5.48xlarge", "max_node_count": 2, "is_default": True},
            {"name": "partition2", "node_type": "m6g.12xlarge", "max_node_count": 14, "is_default": False},
            {"name": "partition3", "node_type": "i4i.metal", "max_node_count": 3, "is_default": False},
            {"name": "partition3", "node_type": "g5.xlarge", "max_node_count": 5, "is_default": False},
        ]
        expected = {
            "Fn::Join": [
                "",
                [
                    '{"Partitions": [',
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition1","NodeGroups":[{"NodeGroupName":"partition1","MaxNodes":2,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","Gres":"gpu:8","CPUs":192,"RealMemory":2048},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',  # noqa
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"p5.48xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "Yes"}}',
                                ",",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition2","NodeGroups":[{"NodeGroupName":"partition2","MaxNodes":14,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":48,"RealMemory":4096},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"m6g.12xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "No"}}',
                                ",",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition3","NodeGroups":[{"NodeGroupName":"partition3","MaxNodes":3,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","CPUs":128,"RealMemory":8192},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"i4i.metal"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "No"}}',
                                ",",
                            ],
                        ]
                    },
                    {
                        "Fn::Join": [
                            "",
                            [
                                '{"PartitionName":"partition3","NodeGroups":[{"NodeGroupName":"partition3","MaxNodes":5,"Region":"us-west-2","SlurmSpecifications":{"Weight":1,"Feature":"cloud","Gres":"gpu:1","CPUs":4,"RealMemory":16384},"PurchasingOption":"on-demand","OnDemandOptions":{"AllocationStrategy":"lowest-price"},"LaunchTemplateSpecification":{"LaunchTemplateId":"',  # noqa
                                {"Ref": "ComputeNodeLaunchTemplateE8D45573"},
                                '","Version":"$Latest"},"LaunchTemplateOverrides":[{"InstanceType":"g5.xlarge"}],"SubnetIds":["',
                                {"Ref": "PrivateSubnetD9FAAE02"},
                                '"]}],"PartitionOptions": {"Default": "No"}}',
                                "",
                            ],
                        ]
                    },
                    "]}",
                ],
            ]
        }

        response_block = build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        assert response_block == expected
        mocked_get_cpu_by_instance_type.assert_has_calls(
            [
                mock.call("p5.48xlarge"),
                mock.call("m6g.12xlarge"),
                mock.call("i4i.metal"),
                mock.call("g5.xlarge"),
            ]
        )
        mocked_get_gpu_count_by_instance_type.assert_has_calls(
            [
                mock.call("p5.48xlarge"),
                mock.call("m6g.12xlarge"),
                mock.call("i4i.metal"),
                mock.call("g5.xlarge"),
            ]
        )

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__partition_name_is_none(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the build_dynamic_partitions function when the input partition has no `name` key."""
        partitions: list[dict[str, str | int | bool]] = [
            {"node_type": "p5.48xlarge", "max_node_count": 2, "is_default": True},
            {"node_type": "m6g.12xlarge", "max_node_count": 14, "is_default": False},
        ]

        with pytest.raises(ValueError, match="Partition name must be a non-empty string."):
            build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        mocked_get_cpu_by_instance_type.assert_not_called()
        mocked_get_memory_by_instance_type.assert_not_called()
        mocked_get_gpu_count_by_instance_type.assert_not_called()

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__partition_name_is_not_string(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the build_dynamic_partitions function when the input partition has no `name` key."""
        partitions: list[dict[str, str | int | bool]] = [
            {"name": 123, "node_type": "p5.48xlarge", "max_node_count": 2, "is_default": True},
            {"name": False, "node_type": "m6g.12xlarge", "max_node_count": 14, "is_default": False},
        ]

        with pytest.raises(ValueError, match="Partition name must be a non-empty string."):
            build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        mocked_get_cpu_by_instance_type.assert_not_called()
        mocked_get_memory_by_instance_type.assert_not_called()
        mocked_get_gpu_count_by_instance_type.assert_not_called()

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__node_type_is_none(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the build_dynamic_partitions function when the input partition has no `name` key."""
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "max_node_count": 2, "is_default": True},
            {"name": "partition2", "max_node_count": 14, "is_default": False},
        ]

        with pytest.raises(ValueError, match="Node type must be a non-empty string."):
            build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        mocked_get_cpu_by_instance_type.assert_not_called()
        mocked_get_memory_by_instance_type.assert_not_called()
        mocked_get_gpu_count_by_instance_type.assert_not_called()

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__node_type_is_not_string(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the build_dynamic_partitions function when the input partition has no `name` key."""
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "node_type": False, "max_node_count": 2, "is_default": True},
            {"name": "partition2", "node_type": 13265478, "max_node_count": 14, "is_default": False},
        ]

        with pytest.raises(ValueError, match="Node type must be a non-empty string."):
            build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        mocked_get_cpu_by_instance_type.assert_not_called()
        mocked_get_memory_by_instance_type.assert_not_called()
        mocked_get_gpu_count_by_instance_type.assert_not_called()

    @mock.patch("api.cfn_app.helpers.get_cpu_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_memory_by_instance_type")
    @mock.patch("api.cfn_app.helpers.get_gpu_count_by_instance_type")
    def test_build_partitions_block__node_type_is_not_a_valid_instance(
        self,
        mocked_get_gpu_count_by_instance_type: mock.MagicMock,
        mocked_get_memory_by_instance_type: mock.MagicMock,
        mocked_get_cpu_by_instance_type: mock.MagicMock,
    ):
        """Test the build_dynamic_partitions function when the input partition has no `name` key."""
        node_type = str(uuid.uuid4())
        partitions: list[dict[str, str | int | bool]] = [
            {"name": "partition1", "node_type": node_type, "max_node_count": 2, "is_default": True},
        ]

        with pytest.raises(ValueError, match=f"Node type '{node_type}' is not a valid instance type."):
            build_dynamic_partitions(partitions=partitions, create_vpc=True, region="us-west-2")

        mocked_get_cpu_by_instance_type.assert_not_called()
        mocked_get_memory_by_instance_type.assert_not_called()
        mocked_get_gpu_count_by_instance_type.assert_not_called()


class TestDescribeInstanceTypes:
    """Test cases for the functions that call `ec2.describe_instance_types`."""

    @pytest.mark.parametrize(
        "instance_type, num_cpus",
        [
            ("vt1.3xlarge", 2),
            ("g4dn.xlarge", 4),
            ("h1.8xlarge", 32),
        ],
    )
    def test_get_cpu_by_instance_type(self, instance_type: str, num_cpus: int):
        """Test the correct return of the number of CPUs by instance type."""
        expected_boto3_response = {"InstanceTypes": [{"VCpuInfo": {"DefaultVCpus": num_cpus}}]}
        expected_boto3_params = {"InstanceTypes": [instance_type]}

        instance_type = cast(InstanceTypeType, instance_type)

        stubber = Stubber(ec2_client)
        stubber.add_response("describe_instance_types", expected_boto3_response, expected_boto3_params)

        with stubber:
            response = get_cpu_by_instance_type(instance_type)

        assert response == num_cpus

    @pytest.mark.parametrize(
        "instance_type, num_gpus",
        [
            ("c5.12xlarge", 0),
            ("g4dn.4xlarge", 1),
            ("p3.8xlarge", 4),
        ],
    )
    def test_get_gpu_count_by_instance_type(self, instance_type: str, num_gpus: int):
        """Test the correct return of the number of GPUs by instance type."""
        expected_boto3_response = {
            "InstanceTypes": [{"GpuInfo": {"Gpus": [{"Count": num_gpus}]}} if num_gpus else {}]
        }
        expected_boto3_params = {"InstanceTypes": [instance_type]}

        instance_type = cast(InstanceTypeType, instance_type)

        stubber = Stubber(ec2_client)
        stubber.add_response("describe_instance_types", expected_boto3_response, expected_boto3_params)

        with stubber:
            response = get_gpu_count_by_instance_type(instance_type)

        assert response == num_gpus
