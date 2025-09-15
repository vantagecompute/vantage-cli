# ruff: noqa
import json

import aws_cdk as core
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from constructs import Construct
from string import Template
from pathlib import Path

from api.cfn_app.contants import AMI_MAPPER
from api.settings import SETTINGS


class BaseCluster(core.Stack):
    """Base class with common resources defined."""

    vpc: ec2.Vpc = None
    head_node_subnet: str = None
    compute_node_subnet: str = None

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.client_id = core.CfnParameter(
            self,
            "ClientId",
            type="String",
            description="Client ID of the OIDC application",
        )
        self.client_secret = core.CfnParameter(
            self,
            "ClientSecret",
            type="String",
            description="Client secret of the OIDC application",
        )
        self.jupyterhub_token = core.CfnParameter(
            self,
            "JupyterHubToken",
            type="String",
            description="Default Jupyter Hub Token",
        )
        self.jupyterhub_dns = core.CfnParameter(
            self,
            "JupyterHubDns",
            type="String",
            description="Default Jupyter Hub Dns",
        )
        self.head_node_ami_id = core.CfnParameter(
            self,
            "HeadNodeAmiId",
            type="String",
            description="AMI ID of the head node",
            allowed_values=list(AMI_MAPPER["head"].values()),
        )
        self.vantage_agents_base_api_url = core.CfnParameter(
            self,
            "VantageAgentsBaseApiUrl",
            type="String",
            description="Base API URL for the Vantage Agents",
        )
        self.vantage_agents_oidc_domain = core.CfnParameter(
            self,
            "VantageAgentsOidcDomain",
            type="String",
            description="OIDC domain of the agents",
        )
        self.slurmdbd_password = core.CfnParameter(
            self,
            "SlurmdbdPassword",
            type="String",
            description="Slurmdbd database password",
        )
        self.influxdb_password = core.CfnParameter(
            self,
            "InfluxdbPassword",
            type="String",
            description="InfluxDB password",
        )
        self.acct_gather_node_freq = core.CfnParameter(
            self,
            "AcctGatherNodeFreq",
            type="Number",
            description="Acct gather node frequency",
            default=10,
        )
        self.slurm_cluster_name = core.CfnParameter(
            self,
            "ClusterName",
            max_length=64,
            min_length=1,
            allowed_pattern=r"^[0-9a-z-]+$",
            type="String",
            description="Name of the cluster to be created",
        )
        self.api_cluster_name = core.CfnParameter(
            self,
            "ApiClusterName",
            type="String",
            description="Name of the the cluster in the API level.",
        )
        self.key_pair = core.CfnParameter(
            self,
            "KeyPair",
            type="AWS::EC2::KeyPair::KeyName",
            description="Key pair to be used to SSH in the machines",
        )
        self.head_node_instance_type = core.CfnParameter(
            self,
            "HeadNodeInstanceType",
            type="String",
            description="Head node instance type",
        )
        self.snap_channel = core.CfnParameter(
            self,
            "SnapChannel",
            type="String",
            description="Snap channel to install the agents",
            default="stable",
            allowed_values=["stable", "candidate", "beta", "edge"],
        )

    def __call__(self) -> None:
        """Configure all CloudFormation resources."""
        self._configure_vpc()
        self._configure_iam_roles()
        self._configure_head_node_instance_profile()
        self._configure_security_groups()
        self._configure_launch_templates()
        self._configure_head_node_instance()

    def _configure_vpc(self) -> None:
        raise NotImplementedError("It is needed to configure the VPC")

    def _configure_iam_roles(self) -> None:
        """Configure base IAM roles to make the cluster to work properly."""
        self.compute_node_role = iam.Role(
            self,
            "ComputeNodeRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )
        self.compute_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeTags",
                    "ec2:DescribeInstances",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )
        self.compute_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:GetSecretValue",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        self.head_node_role = iam.Role(
            self,
            "HeadNodeRole",
            assumed_by=iam.ServicePrincipal(service="ec2.amazonaws.com"),
        )
        self.head_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:CreateFleet",
                    "ec2:RunInstances",
                    "ec2:TerminateInstances",
                    "ec2:CreateTags",
                    "ec2:DescribeInstances",
                    "ec2:DescribeTags",
                    "iam:CreateServiceLinkedRole",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )
        self.head_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"], effect=iam.Effect.ALLOW, resources=[self.compute_node_role.role_arn]
            )
        )
        self.head_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )
        self.head_node_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "elasticfilesystem:DescribeMountTargets",
                    "elasticfilesystem:CreateMountTarget",
                    "elasticfilesystem:DeleteMountTarget",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )

        self.head_node_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMFullAccess")
        )

    def _configure_head_node_instance_profile(self) -> None:
        """Attach an instance profile to the head node instance."""
        self.head_node_instance_profile = iam.CfnInstanceProfile(
            self,
            "HeadNodeInstaceProfile",
            roles=[self.head_node_role.role_name],
            instance_profile_name=self.slurm_cluster_name.value_as_string + "-hn-instance-profile",
        )

    def _configure_security_groups(self) -> None:
        """Configure EC2 security groups to allow traffic to the internet and between the nodes themselves."""
        self.head_node_security_group = ec2.SecurityGroup(
            self, "HeadNodeSecurityGroup", vpc=self.vpc, description="Enable access to the head node"
        )
        self.head_node_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(22), description="Allow SSH connection"
        )
        self.head_node_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80), description="Allow Http Connection"
        )
        self.head_node_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(443), description="Allow Https Connection"
        )

        self.compute_node_security_group = ec2.SecurityGroup(
            self,
            "ComputeSecurityGroup",
            allow_all_outbound=True,
            vpc=self.vpc,
            description="Allow access to compute nodes",
        )

        self.compute_node_security_group.connections.allow_from(
            self.head_node_security_group, port_range=ec2.Port.all_traffic()
        )
        self.head_node_security_group.connections.allow_from(
            self.compute_node_security_group, port_range=ec2.Port.all_traffic()
        )
        self.compute_node_security_group.connections.allow_internally(port_range=ec2.Port.all_traffic())

        self.head_node_network_interface = ec2.CfnNetworkInterface(
            self,
            "HeadNodeNetworkInterface",
            subnet_id=self.head_node_subnet,
            group_set=[self.head_node_security_group.security_group_id],
        )

    def _configure_launch_templates(self) -> None:
        """Configure the launch templates for both head and compute nodes."""
        compute_node_user_data_template = Path("api/cfn_app/compute-node.sh").read_text()
        compute_node_user_data_as_string = compute_node_user_data_template.replace(
            "@head_node_private_ip_address@", self.head_node_network_interface.attr_primary_private_ip_address
        )
        compute_node_user_data = ec2.UserData.custom(compute_node_user_data_as_string)

        self.compute_node_launch_template = ec2.LaunchTemplate(
            self,
            "ComputeNodeLaunchTemplate",
            key_name=self.key_pair.value_as_string,
            role=self.compute_node_role,
            security_group=self.compute_node_security_group,
            machine_image=ec2.MachineImage.generic_linux(ami_map=AMI_MAPPER.get("compute")),
            user_data=compute_node_user_data,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=100,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True,
                    ),
                )
            ],
        )

        head_node_user_data_template = Path("api/cfn_app/head-node.sh").read_text()
        head_node_user_data_as_string = (
            head_node_user_data_template.replace("@stack_name@", core.Aws.STACK_NAME)
            .replace("@aws_region@", self.region)
            .replace("@environment@", SETTINGS.STAGE)
            .replace("@client_id@", self.client_id.value_as_string)
            .replace("@client_secret@", self.client_secret.value_as_string)
            .replace("@signal_resource@", "HeadNodeInstance")
            .replace("@init_resource@", "HeadNodeLaunchTemplate")
        )

        self.head_node_launch_template = ec2.CfnLaunchTemplate(
            self,
            "HeadNodeLaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                image_id=self.head_node_ami_id.value_as_string,
                instance_type=self.head_node_instance_type.value_as_string,
                iam_instance_profile=ec2.CfnLaunchTemplate.IamInstanceProfileProperty(
                    name=self.head_node_instance_profile.instance_profile_name
                ),
                key_name=self.key_pair.value_as_string,
                network_interfaces=[
                    ec2.CfnLaunchTemplate.NetworkInterfaceProperty(
                        device_index=0,
                        network_interface_id=self.head_node_network_interface.attr_id,
                    )
                ],
                user_data=core.Fn.base64(head_node_user_data_as_string),
                tag_specifications=[
                    ec2.CfnLaunchTemplate.TagSpecificationProperty(
                        resource_type="instance",
                        tags=[
                            core.CfnTag(
                                key="Name", value=self.slurm_cluster_name.value_as_string + "/head-node"
                            )
                        ],
                    )
                ],
                block_device_mappings=[
                    ec2.CfnLaunchTemplate.BlockDeviceMappingProperty(
                        device_name="/dev/sda1",
                        ebs=ec2.CfnLaunchTemplate.EbsProperty(
                            delete_on_termination=True, volume_size=100, volume_type="gp2"
                        ),
                    )
                ],
            ),
        )

        cfn_init = self._build_cfn_options()

        self.head_node_launch_template.add_metadata("AWS::CloudFormation::Init", cfn_init)

    def _configure_head_node_instance(self) -> None:
        """Configure the head node instance and its properties."""
        head_node_instance = ec2.CfnInstance(
            self,
            "HeadNodeInstance",
            launch_template=ec2.CfnInstance.LaunchTemplateSpecificationProperty(
                launch_template_id=self.head_node_launch_template.ref,
                version=self.head_node_launch_template.attr_latest_version_number,
            ),
        )
        head_node_instance.node.add_dependency(self.head_node_instance_profile)
        head_node_instance.cfn_options.creation_policy = core.CfnCreationPolicy(
            resource_signal=core.CfnResourceSignal(count=1, timeout="PT10M")
        )
        head_node_instance.apply_removal_policy(policy=core.RemovalPolicy.DESTROY)

    def _build_cfn_options(self) -> dict:
        """
        Build the CloudFormation options for the head node instance.

        [Docs](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-init.html)
        """
        nfs_home = "/nfs/slurm"

        cfn_init = {
            "configSets": {
                "setup": ["a", "b", "c", "d", "e", "f", "g"],
                "run": ["h", "i", "j", "k", "l", "m", "n"],
            },
            "a": {
                "commands": {
                    "a": {"command": f"mkdir -p {nfs_home}/etc/aws"},
                    "b": {"command": f"mkdir -p {nfs_home}/etc/agents/services"},
                    "c": {"command": f"mkdir {nfs_home}/etc/agents/timers"},
                    "d": {"command": "mkdir -p /var/spool/slurm"},
                    "e": {"command": "dd if=/dev/urandom of=/etc/munge/munge.key bs=1 count=1024"},
                    "f": {"command": "cp /etc/munge/munge.key /nfs"},
                    "g": {"command": "chown munge:munge /etc/munge/munge.key"},
                    "h": {"command": "chmod 600 /etc/munge/munge.key"},
                    "i": {"command": "chown -R munge /etc/munge/ /var/log/munge/"},
                    "j": {"command": "chmod 0700 /etc/munge/ /var/log/munge/"},
                    "k": {"command": "mkdir /nfs/mnt"},
                    "l": {"command": "chown -R ubuntu:ubuntu /nfs/mnt"},
                    "m": {
                        "command": "mkdir -p /nfs/jupyter /nfs/jupyterlogs /nfs/.jupyter/cert /nfs/working"
                    },
                },
            },
            "b": {
                "files": {
                    f"{nfs_home}/etc/aws/config.json": {
                        "content": json.dumps(
                            {
                                "LogLevel": "DEBUG",
                                "LogFileName": "/var/log/slurm_plugin.log",
                                "SlurmBinPath": "/bin",
                                "SlurmConf": {
                                    "PrivateData": "CLOUD",
                                    "ResumeProgram": f"{nfs_home}/etc/aws/resume.py",
                                    "SuspendProgram": f"{nfs_home}/etc/aws/suspend.py",
                                    "ResumeRate": 100,
                                    "SuspendRate": 100,
                                    "ResumeTimeout": 600,
                                    "SuspendTime": 350,
                                    "TreeWidth": 60000,
                                },
                            }
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    f"{nfs_home}/etc/aws/partitions.json": {
                        "content": "<DynamicPartitionBlock>",
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    f"{nfs_home}/etc/aws/common.py": {
                        "source": "https://raw.githubusercontent.com/omnivector-solutions/aws-plugin-for-slurm/0.1.0-alpha.1/common.py",  # noqa
                        "mode": "000755",
                        "owner": "root",
                        "group": "root",
                    },
                    f"{nfs_home}/etc/aws/resume.py": {
                        "source": "https://raw.githubusercontent.com/omnivector-solutions/aws-plugin-for-slurm/0.1.0-alpha.1/resume.py",  # noqa
                        "mode": "000755",
                        "owner": "root",
                        "group": "root",
                    },
                    f"{nfs_home}/etc/aws/suspend.py": {
                        "source": "https://raw.githubusercontent.com/omnivector-solutions/aws-plugin-for-slurm/0.1.0-alpha.1/suspend.py",  # noqa
                        "mode": "000755",
                        "owner": "root",
                        "group": "root",
                    },
                    f"{nfs_home}/etc/aws/generate_conf.py": {
                        "source": "https://raw.githubusercontent.com/omnivector-solutions/aws-plugin-for-slurm/0.1.0-alpha.1/generate_conf.py",  # noqa
                        "mode": "000755",
                        "owner": "root",
                        "group": "root",
                    },
                    f"{nfs_home}/etc/aws/change_state.py": {
                        "source": "https://raw.githubusercontent.com/omnivector-solutions/aws-plugin-for-slurm/0.1.0-alpha.1/change_state.py",  # noqa
                        "mode": "000755",
                        "owner": "root",
                        "group": "root",
                    },
                    f"{nfs_home}/etc/slurm/slurm.conf": {
                        "content": (
                            Template(Path("api/cfn_app/slurm.conf").read_text()).substitute(
                                slurm_cluster_name=self.slurm_cluster_name.value_as_string,
                                acct_gather_node_freq=self.acct_gather_node_freq.value_as_number,
                            )
                            + "\n"
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    f"{nfs_home}/etc/slurm/slurmdbd.conf": {
                        "content": (Template(Path("api/cfn_app/slurmdbd.conf").read_text()).substitute()),
                        "mode": "000600",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    f"{nfs_home}/etc/slurm/slurmrestd.conf": {
                        "content": (
                            Template(Path("api/cfn_app/slurmrestd.conf").read_text()).substitute(
                                nfs_home=nfs_home
                            )
                        ),
                        "mode": "000600",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    f"{nfs_home}/etc/slurm/acct_gather.conf": {
                        "content": (
                            Template(Path("api/cfn_app/acct_gather.conf").read_text()).substitute(
                                head_node_network_interface=self.head_node_network_interface.attr_primary_private_ip_address,
                                influxdb_password=self.influxdb_password.value_as_string,
                            )
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                },
                "commands": {
                    "a": {
                        "command": f'sed -i "s|@SLURMDBD_DATABASE_PASSWORD@|$SLURMDBD_DATABASE_PASSWORD|g" {nfs_home}/etc/slurm/slurmdbd.conf',  # noqa
                        "env": {"SLURMDBD_DATABASE_PASSWORD": self.slurmdbd_password.value_as_string},  # noqa
                    },
                    "b": {
                        "command": f'sed -i "s|@PRIVATE_IP@|$PRIVATE_IP|g" {nfs_home}/etc/slurm/slurm.conf',
                        "env": {
                            "PRIVATE_IP": self.head_node_network_interface.attr_primary_private_ip_address
                        },
                    },
                    "c": {
                        "command": f'sed -i "s|@HEADNODE@|$HOSTNAME|g" {nfs_home}/etc/slurm/slurm.conf',
                        # the result of the following HOSTNAME variables looks like "ip-10-0-0-1"
                        "env": {
                            "HOSTNAME": core.Fn.join(
                                "-",
                                [
                                    "ip",
                                    core.Fn.join(
                                        "-",
                                        core.Fn.split(
                                            ".",
                                            self.head_node_network_interface.attr_primary_private_ip_address,
                                        ),
                                    ),
                                ],
                            )
                        },
                    },
                    "d": {
                        "command": f'sed -i "s|@HEADNODE@|$HOSTNAME|g" {nfs_home}/etc/slurm/slurmdbd.conf',
                        "env": {
                            "HOSTNAME": core.Fn.join(
                                "-",
                                [
                                    "ip",
                                    core.Fn.join(
                                        "-",
                                        core.Fn.split(
                                            ".",
                                            self.head_node_network_interface.attr_primary_private_ip_address,
                                        ),
                                    ),
                                ],
                            )
                        },
                    },
                    "e": {"command": "groupadd --gid 64031 slurmrestd"},
                    "f": {
                        "command": "adduser --system --gid 64031 --uid 64031 --no-create-home --home /nonexistent slurmrestd"
                    },
                },
            },
            "c": {
                "commands": {
                    "a": {"command": f"{nfs_home}/etc/aws/generate_conf.py", "cwd": f"{nfs_home}/etc/aws"},
                    "b": {
                        "command": f"cat {nfs_home}/etc/aws/slurm.conf.aws >> {nfs_home}/etc/slurm/slurm.conf"
                    },
                    "c": {"command": f"cp {nfs_home}/etc/aws/gres.conf.aws {nfs_home}/etc/gres.conf"},
                }
            },
            "d": {
                "commands": {
                    "a": {"command": f"'cp' {nfs_home}/etc/slurm/slurm.conf /etc/slurm"},
                    "b": {"command": f"'cp' {nfs_home}/etc/slurm/slurmdbd.conf /etc/slurm"},
                    "c": {"command": f"'cp' {nfs_home}/etc/slurm/slurmrestd.conf /etc/slurm"},
                    "d": {"command": f"'cp' {nfs_home}/etc/slurm/acct_gather.conf /etc/slurm"},
                    "e": {"command": f"'cp' {nfs_home}/etc/gres.conf /etc/slurm"},
                }
            },
            "e": {
                "files": {
                    f"{nfs_home}/change_state_cron": {
                        "content": f"* * * * * {nfs_home}/etc/aws/change_state.py &>/dev/null\n",
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                },
                "commands": {
                    "a": {"command": f"crontab {nfs_home}/change_state_cron"},
                    "b": {"command": f"rm {nfs_home}/change_state_cron"},
                },
            },
            "f": {
                "commands": {
                    "a": {"command": "mkdir -p /var/spool/slurmctld || true"},
                    "b": {"command": "openssl genrsa -out /var/spool/slurmctld/jwt_hs256.key 2048"},
                    "c": {"command": "chown root /var/spool/slurmctld/jwt_hs256.key"},
                    "d": {"command": "chmod 0600 /var/spool/slurmctld/jwt_hs256.key"},
                }
            },
            "g": {
                "files": {
                    "/etc/slurm/slurmctld.service": {
                        "content": (
                            "[Unit]\n"
                            "Description=Slurm controller daemon\n"
                            "After=network.target munge.service\n"
                            "ConditionPathExists=/etc/slurm/slurm.conf\n\n"
                            "[Service]\n"
                            "Type=forking\n"
                            "EnvironmentFile=-/etc/sysconfig/slurmctld\n"
                            "ExecStart=/usr/sbin/slurmctld $SLURMCTLD_OPTIONS\n"  # noqa
                            "ExecReload=/bin/kill -HUP $MAINPID\n"  # noqa
                            "PIDFile=/var/run/slurmctld.pid\n"
                            "LimitNOFILE=65536\n\n"
                            "[Install]\n"
                            "WantedBy=multi-user.target\n"
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    "/etc/slurm/slurmdbd.service": {
                        "content": (
                            "[Unit]\n"
                            "Description=Slurm DBD accounting daemon\n"
                            "After=network.target munge.service\n"
                            "ConditionPathExists=/etc/slurm/slurmdbd.conf\n\n"
                            "[Service]\n"
                            "Type=simple\n"
                            "EnvironmentFile=-/etc/sysconfig/slurmdbd\n"
                            "ExecStart=/usr/sbin/slurmdbd -D $SLURMDBD_OPTIONS\n"  # noqa
                            "ExecReload=/bin/kill -HUP $MAINPID\n"  # noqa
                            "LimitNOFILE=65536\n\n"
                            "[Install]\n"
                            "WantedBy=multi-user.target\n"
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                    "/etc/slurm/slurmrestd.service": {
                        "content": (
                            "[Unit]\n"
                            "Description=Slurm restd daemon\n"
                            "After=network.target slurmctl.service\n"
                            "ConditionPathExists=/etc/slurm/slurmrestd.conf\n\n"
                            "[Service]\n"
                            "Type=simple\n"
                            "EnvironmentFile=-/etc/default/slurmrestd\n"
                            'Environment="SLURM_JWT=daemon"\n'
                            "ExecStart=/usr/sbin/slurmrestd $SLURMRESTD_OPTIONS -vvvv 0.0.0.0:6820\n"
                            "ExecReload=/bin/kill -HUP $MAINPID\n"
                            "User=slurmrestd\n"
                            "Group=slurmrestd\n\n"  # noqa
                            "[Install]\n"
                            "WantedBy=multi-user.target\n"
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                },
                "commands": {
                    "a": {"command": "cp /etc/slurm/slurmctld.service /lib/systemd/system"},
                    "b": {"command": "cp /etc/slurm/slurmdbd.service /lib/systemd/system"},
                    "c": {"command": "cp /etc/slurm/slurmrestd.service /lib/systemd/system"},
                },
            },
            "h": {
                "commands": {
                    "a": {
                        "command": (
                            "docker run --name slurmdbd-database "
                            "-e MYSQL_ROOT_PASSWORD=$SLURMDBD_DATABASE_PASSWORD "
                            "-e MYSQL_DATABASE=slurm_acct_db "
                            "-e MYSQL_USER=slurm "
                            "-e MYSQL_PASSWORD=$SLURMDBD_DATABASE_PASSWORD "
                            "-p 3306:3306 "
                            "-d mysql:5.7.38"
                        ),
                        "env": {"SLURMDBD_DATABASE_PASSWORD": self.slurmdbd_password.value_as_string},
                    }
                }
            },
            "i": {
                "commands": {
                    "a": {
                        "command": f"systemctl start influxdb",
                        "test": 'test "$(systemctl is-active influxdb)" = "active"',
                    },
                    "b": {
                        "command": f"influx -execute \"CREATE USER slurm WITH PASSWORD '{self.influxdb_password.value_as_string}'\""
                    },
                    "c": {"command": "influx -execute 'CREATE DATABASE \"slurm-job-metrics\"'"},
                    "d": {"command": "influx -execute 'GRANT ALL ON \"slurm-job-metrics\" TO slurm'"},
                    "e": {
                        "command": 'influx -execute \'CREATE RETENTION POLICY "three_days" ON "slurm-job-metrics" DURATION 3d REPLICATION 1 DEFAULT\''
                    },
                }
            },
            "j": {
                "commands": {
                    "a": {"command": "systemctl enable munge"},
                    "b": {"command": "systemctl enable slurmctld"},
                    "c": {"command": "systemctl enable slurmdbd"},
                    "d": {"command": "systemctl enable slurmctld"},
                }
            },
            "k": {
                "commands": {
                    "a": {"command": "systemctl start munge"},
                    "b": {"command": "systemctl start slurmdbd"},
                    "c": {"command": "sleep 30"},
                    "d": {"command": "systemctl start slurmctld"},
                    "e": {"command": "systemctl start slurmrestd"},
                    "f": {"command": "systemctl restart munge"},
                }
            },
            "l": {
                "commands": {
                    "a": {
                        "command": f"snap install vantage-agent --channel {self.snap_channel.value_as_string} --classic"
                    },
                    "b": {
                        "command": f"snap set vantage-agent base-api-url={self.vantage_agents_base_api_url.value_as_string}"
                    },
                    "c": {
                        "command": f"snap set vantage-agent oidc-domain={self.vantage_agents_oidc_domain.value_as_string}"
                    },
                    "d": {
                        "command": f"snap set vantage-agent oidc-client-id={self.client_id.value_as_string}"
                    },
                    "e": {
                        "command": f"snap set vantage-agent oidc-client-secret={self.client_secret.value_as_string}"
                    },
                    "f": {"command": f"snap set vantage-agent task-jobs-interval-seconds=30"},
                    "g": {
                        "command": f"snap set vantage-agent cluster-name={self.api_cluster_name.value_as_string}"
                    },
                    "h": {"command": "snap set vantage-agent is-cloud-cluster=true"},
                    "i": {"command": "snap start vantage-agent.start"},
                }
            },
            "m": {
                "commands": {
                    "a": {
                        "command": f"snap install jobbergate-agent --channel {self.snap_channel.value_as_string} --classic"
                    },
                    "b": {
                        "command": f"snap set jobbergate-agent base-api-url={self.vantage_agents_base_api_url.value_as_string}"
                    },
                    "c": {
                        "command": f"snap set jobbergate-agent oidc-domain={self.vantage_agents_oidc_domain.value_as_string}"
                    },
                    "d": {
                        "command": f"snap set jobbergate-agent oidc-client-id={self.client_id.value_as_string}"
                    },
                    "e": {
                        "command": f"snap set jobbergate-agent oidc-client-secret={self.client_secret.value_as_string}"
                    },
                    "f": {"command": "snap set jobbergate-agent x-slurm-user-name=root"},
                    "g": {"command": f"snap set jobbergate-agent task-jobs-interval-seconds=30"},
                    "h": {
                        "command": f"snap set jobbergate-agent influx-dsn=influxdb://slurm:{self.influxdb_password.value_as_string}@localhost:8086/slurm-job-metrics"
                    },
                    "i": {"command": "snap start jobbergate-agent.start"},
                }
            },
            "n": {
                "files": {
                    "/nfs/.jupyter/jupyter_config.py": {
                        "content": (
                            Path("api/cfn_app/jupyter_config.py")
                            .read_text()
                            .replace("@JUPYTERHUB_DNS@", self.jupyterhub_dns.value_as_string)
                            .replace("@JUPYTERHUB_TOKEN@", self.jupyterhub_token.value_as_string)
                            .replace("@AUTH_OIDC_DNS@", self.vantage_agents_oidc_domain.value_as_string)
                            + "\n"
                        ),
                        "mode": "000666",
                        "owner": "ubuntu",
                        "group": "ubuntu",
                    },
                    "/nfs/.jupyter/jupyter_config_singleserver.py": {
                        "content": (
                            Path("api/cfn_app/jupyter_config_singleserver.py")
                            .read_text()
                            .replace("@JUPYTERHUB_DNS@", self.jupyterhub_dns.value_as_string)
                            .replace("@AUTH_OIDC_DNS@", self.vantage_agents_oidc_domain.value_as_string)
                            + "\n"
                        ),
                        "mode": "000666",
                        "owner": "ubuntu",
                        "group": "ubuntu",
                    },
                    "/lib/systemd/system/jupyterhub.service": {
                        "content": (
                            "[Unit]\n"
                            "Description=JupyterHub\n"
                            "After=syslog.target network.target\n"
                            "[Service]\n"
                            "User=root\n"
                            'Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/nfs/jupyter/venv/bin:/nfs/jupyter/venv/sbin"\n'  # noqa
                            "WorkingDirectory=/nfs/jupyter\n"
                            "ExecStart=/nfs/jupyter/bin/jupyterhub -f /nfs/.jupyter/jupyter_config.py --debug\n"  # noqa
                            "[Install]\n"
                            "WantedBy=multi-user.target\n"
                        ),
                        "mode": "000644",
                        "owner": "root",
                        "group": "root",
                        "encoding": "plain",
                    },
                },
                "commands": {
                    "a": {
                        "command": ". /nfs/jupyter/bin/activate && pip install -v git+https://github.com/omnivector-solutions/jupyterhub-theme.git",
                    },
                    "b": {
                        "command": f'sed -i "s|JupyterLab\ Light|jh-vantage-theme|g" /nfs/jupyter/share/jupyter/lab/schemas/@jupyterlab/apputils-extension/themes.json',  # noqa
                    },
                    # Wait for the jupyterdns being ready
                    "c": {
                        "command": f"""
                        timeout 120 bash -c '
                            PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
                            until nslookup {self.jupyterhub_dns.value_as_string} | grep "$PUBLIC_IP"; do
                                echo "Waiting Jupyter DNS..."
                                sleep 5
                            done
                        '
                    """
                    },
                    "d": {"command": "snap install certbot --classic"},  # noqa
                    "e": {
                        "command": f"certbot certonly --standalone --non-interactive --agree-tos -d '{self.jupyterhub_dns.value_as_string}'"
                    },  # noqa
                    "f": {
                        "command": f"cp /etc/letsencrypt/archive/{self.jupyterhub_dns.value_as_string}/fullchain1.pem /nfs/.jupyter/cert/fullchain.pem"
                    },  # noqa
                    "g": {
                        "command": f"cp /etc/letsencrypt/archive/{self.jupyterhub_dns.value_as_string}/privkey1.pem /nfs/.jupyter/cert/privkey.pem"
                    },  # noqa
                    "h": {
                        "command": '(crontab -l 2>/dev/null; echo "0 3,15 * * * certbot renew --quiet >> /var/log/certbot-renew.log 2>&1") | crontab -'
                    },
                    "i": {
                        "command": "chown -R ubuntu:ubuntu /nfs/jupyter /nfs/.jupyter /nfs/jupyterlogs /nfs/working"
                    },
                    "j": {"command": "systemctl daemon-reload"},
                    "k": {"command": "systemctl start jupyterhub.service"},
                },
            },
        }

        return cfn_init


class ClusterWithNetworkingSupplied(BaseCluster):
    """Slurm cluster stack whose VPC is supplied by the API requester."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc_id = core.CfnParameter(
            self,
            "VpcId",
            type="AWS::EC2::VPC::Id",
            description="VPC which the cluster will be deployed in",
        )
        self.head_node_subnet_id = core.CfnParameter(
            self,
            "HeadNodeSubnetId",
            type="AWS::EC2::Subnet::Id",
            description="Subnet which the head node will be in",
        )
        self.compute_node_subnet_id = core.CfnParameter(
            self,
            "ComputeNodeSubnetId",
            type="AWS::EC2::Subnet::Id",
            description="Subnet which the compute node will be in",
        )

    def _configure_vpc(self) -> None:
        self.vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "ImportedVpc",
            availability_zones=self.availability_zones,
            vpc_id=self.vpc_id.value_as_string,
        )
        self.head_node_subnet = self.head_node_subnet_id.value_as_string
        self.compute_node_subnet = self.compute_node_subnet_id.value_as_string


class ClusterWithSelfDeployedNetworking(BaseCluster):
    """Slurm cluster stack whose VPC is deployed by the stack itself."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.name = self.slurm_cluster_name.value_as_string
        self.public_avz_zone = core.CfnParameter(
            self,
            "PublicAvailabilityZone",
            type="AWS::EC2::AvailabilityZone::Name",
            description="Availability zone for the public subnet",
        )
        self.private_avz_zone = core.CfnParameter(
            self,
            "PrivateAvailabilityZone",
            type="AWS::EC2::AvailabilityZone::Name",
            description="Availability zone for the private subnet",
        )

    def _configure_vpc(self) -> None:
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            cidr="10.0.0.0/16",
            max_azs=0,
            subnet_configuration=list(),
            vpc_name=self.slurm_cluster_name.value_as_string,
        )

        self._configure_public_subnet()
        self._configure_private_subnet()

    def _configure_public_subnet(self) -> None:
        public_subnet = ec2.Subnet(
            self,
            "PublicSubnet",
            availability_zone=self.public_avz_zone.value_as_string,
            cidr_block="10.0.0.0/24",
            vpc_id=self.vpc.vpc_id,
            map_public_ip_on_launch=True,
        )
        core.Tags.of(public_subnet).add(key="Name", value=self.name + "-public-1")

        self.head_node_subnet = public_subnet.subnet_id

        igw = ec2.CfnInternetGateway(self, "InternetGateway", tags=[core.CfnTag(key="Name", value=self.name)])

        vpc_gtw_attachment = ec2.CfnVPCGatewayAttachment(
            self,
            "VpcGatewayAttachment",
            vpc_id=self.vpc.vpc_id,
            internet_gateway_id=igw.attr_internet_gateway_id,
        )

        public_subnet.add_default_internet_route(igw.attr_internet_gateway_id, vpc_gtw_attachment)

        eip = ec2.CfnEIP(
            self, "PrivateSubnetEIP", domain="vpc", tags=[core.CfnTag(key="Name", value=self.name)]
        )

        self.nat_gtw = ec2.CfnNatGateway(
            self,
            "PrivateSubnetNATGateway",
            subnet_id=public_subnet.subnet_id,
            allocation_id=eip.attr_allocation_id,
            tags=[core.CfnTag(key="Name", value=self.name)],
        )

    def _configure_private_subnet(self) -> None:
        private_subnet = ec2.Subnet(
            self,
            "PrivateSubnet",
            availability_zone=self.private_avz_zone.value_as_string,
            cidr_block="10.0.1.0/24",
            vpc_id=self.vpc.vpc_id,
            map_public_ip_on_launch=False,
        )
        core.Tags.of(private_subnet).add(key="Name", value=self.name + "-private-1")

        self.compute_node_subnet = private_subnet.subnet_id

        private_subnet.add_default_nat_route(self.nat_gtw.attr_nat_gateway_id)
