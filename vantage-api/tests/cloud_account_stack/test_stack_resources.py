"""Test the stack resources of the CloudAccountStack."""
from aws_cdk.assertions import Template


def test_stack_parameters(cloud_account_stack: Template):
    """Test if the stack has the correct parameters."""
    cloud_account_stack.has_parameter(
        logical_id="CloudAccountName",
        props={
            "Type": "String",
            "AllowedPattern": "^[a-zA-Z][a-zA-Z0-9-]{0,44}$",
            "Description": "Name of the cloud account on Vantage. Do not change this value.",
            "MaxLength": 45,
            "MinLength": 1,
        },
    )
    cloud_account_stack.has_parameter(
        logical_id="ApiKey",
        props={
            "Type": "String",
            "Description": "API key to authenticate with Vantage's API. Do not change this value.",
        },
    )
    cloud_account_stack.has_parameter(
        logical_id="OrganizationId",
        props={
            "Type": "String",
            "Description": "Organization ID to which the cloud account will be associated. "
            "Do not change this value.",
        },
    )
    cloud_account_stack.has_parameter(
        logical_id="CloudAccountDescription",
        props={
            "Type": "String",
            "Description": "Description of the cloud account on Vantage. Do not change this value.",
            "MaxLength": 1000,
            "MinLength": 1,
        },
    )
    cloud_account_stack.has_parameter(
        logical_id="Stage",
        props={
            "Type": "String",
            "Default": "prod",
            "AllowedValues": ["dev", "qa", "staging", "prod"],
            "Description": "Stage of the environment. Do not change this value.",
        },
    )


def test_stack_conditions(cloud_account_stack: Template):
    """Test if the stack has the correct conditions."""
    cloud_account_stack.has_condition(logical_id="IsProd", props={"Fn::Equals": [{"Ref": "Stage"}, "prod"]})
    cloud_account_stack.has_condition(
        logical_id="IsStaging", props={"Fn::Equals": [{"Ref": "Stage"}, "staging"]}
    )
    cloud_account_stack.has_condition(logical_id="IsQa", props={"Fn::Equals": [{"Ref": "Stage"}, "qa"]})


def test_stack_iam_roles(cloud_account_stack: Template):
    """Test if the stack has the correct IAM roles."""
    cloud_account_stack.resource_count_is("AWS::IAM::Role", 2)
    cloud_account_stack.has_resource_properties(
        type="AWS::IAM::Role",
        props={
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                    }
                ],
                "Version": "2012-10-17",
            },
            "ManagedPolicyArns": [
                {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {"Ref": "AWS::Partition"},
                            ":iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        ],
                    ]
                }
            ],
            "RoleName": {"Fn::Join": ["", ["LambdaExecution-", {"Ref": "CloudAccountName"}]]},
            "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}],
        },
    )
    cloud_account_stack.has_resource_properties(
        type="AWS::IAM::Role",
        props={
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": {
                                "Fn::Join": [
                                    "",
                                    ["arn:", {"Ref": "AWS::Partition"}, ":iam::266735843730:root"],
                                ]
                            }
                        },
                        "Condition": {"ArnLike": {"aws:PrincipalArn": "arn:aws:iam::266735843730:role/*"}},
                    }
                ],
                "Version": "2012-10-17",
            },
            "RoleName": {"Fn::Join": ["", ["VantageIntegration-", {"Ref": "CloudAccountName"}]]},
            "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}],
        },
    )


def test_stack_iam_policies(cloud_account_stack: Template):
    """Test if the stack has the correct IAM policies."""
    cloud_account_stack.resource_count_is("AWS::IAM::Policy", 2)
    cloud_account_stack.has_resource_properties(
        type="AWS::IAM::Policy",
        props={
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": ["iam:GetRolePolicy", "iam:PutRolePolicy"],
                        "Effect": "Allow",
                        "Resource": {"Fn::GetAtt": ["VantageIntegrationRole", "Arn"]},
                    }
                ],
                "Version": "2012-10-17",
            },
            "PolicyName": {"Fn::Join": ["", ["LambdaExecutionPolicy-", {"Ref": "CloudAccountName"}]]},
            "Roles": [{"Ref": "LambdaExecutionRole"}],
        },
    )
    cloud_account_stack.has_resource_properties(
        type="AWS::IAM::Policy",
        props={
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": [
                            "cloudformation:CreateStack",
                            "cloudformation:DeleteStack",
                            "cloudformation:DescribeStackEvents",
                            "cloudformation:DescribeStackResources",
                            "cloudformation:DescribeStacks",
                            "cloudformation:ListChangeSets",
                            "cloudformation:ListStacks",
                            "cloudformation:SetStackPolicy",
                            "cloudformation:TagResource",
                            "cloudformation:UntagResource",
                            "cloudformation:UpdateStack",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "AllowCreateStacks",
                    },
                    {
                        "Action": [
                            "elasticfilesystem:CreateFileSystem",
                            "elasticfilesystem:CreateMountTarget",
                            "elasticfilesystem:CreateTags",
                            "elasticfilesystem:DeleteFileSystem",
                            "elasticfilesystem:DeleteFileSystemPolicy",
                            "elasticfilesystem:DeleteMountTarget",
                            "elasticfilesystem:DeleteTags",
                            "elasticfilesystem:DescribeFileSystems",
                            "elasticfilesystem:DescribeMountTargets",
                            "elasticfilesystem:DescribeTags",
                            "elasticfilesystem:ListTagsForResource",
                            "elasticfilesystem:PutFileSystemPolicy",
                            "elasticfilesystem:TagResource",
                            "elasticfilesystem:UntagResource",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "AllowCreateStorages",
                    },
                    {
                        "Action": ["ec2:DescribeSubnets", "ec2:DescribeVpcs"],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "AllowDescribeVpcResources",
                    },
                    {
                        "Action": [
                            "ec2:AllocateAddress",
                            "ec2:AssociateAddress",
                            "ec2:AssociateNatGatewayAddress",
                            "ec2:AssociateRouteTable",
                            "ec2:AttachInternetGateway",
                            "ec2:AttachNetworkInterface",
                            "ec2:AuthorizeSecurityGroupEgress",
                            "ec2:AuthorizeSecurityGroupIngress",
                            "ec2:CreateInternetGateway",
                            "ec2:CreateLaunchTemplate",
                            "ec2:CreateLaunchTemplateVersion",
                            "ec2:CreateNatGateway",
                            "ec2:CreateNetworkInterface",
                            "ec2:CreateRoute",
                            "ec2:CreateRouteTable",
                            "ec2:CreateSecurityGroup",
                            "ec2:CreateSubnet",
                            "ec2:CreateTags",
                            "ec2:CreateVpc",
                            "ec2:DeleteInternetGateway",
                            "ec2:DeleteLaunchTemplate",
                            "ec2:DeleteLaunchTemplateVersions",
                            "ec2:DeleteNatGateway",
                            "ec2:DeleteNetworkInterface",
                            "ec2:DeleteRoute",
                            "ec2:DeleteRouteTable",
                            "ec2:DeleteSecurityGroup",
                            "ec2:DeleteSubnet",
                            "ec2:DeleteTags",
                            "ec2:DeleteVpc",
                            "ec2:DescribeAddresses",
                            "ec2:DescribeAvailabilityZones",
                            "ec2:DescribeInstances",
                            "ec2:DescribeInternetGateways",
                            "ec2:DescribeKeyPairs",
                            "ec2:DescribeLaunchTemplates",
                            "ec2:DescribeNatGateways",
                            "ec2:DescribeNetworkInterfaceAttribute",
                            "ec2:DescribeNetworkInterfacePermissions",
                            "ec2:DescribeNetworkInterfaces",
                            "ec2:DescribeRegions",
                            "ec2:DescribeRouteTables",
                            "ec2:DescribeSecurityGroups",
                            "ec2:DetachInternetGateway",
                            "ec2:DetachNetworkInterface",
                            "ec2:DisassociateAddress",
                            "ec2:DisassociateNatGatewayAddress",
                            "ec2:DisassociateRouteTable",
                            "ec2:GetLaunchTemplateData",
                            "ec2:ModifyLaunchTemplate",
                            "ec2:ModifySecurityGroupRules",
                            "ec2:ModifySubnetAttribute",
                            "ec2:ModifyVpcAttribute",
                            "ec2:ReleaseAddress",
                            "ec2:ReplaceRouteTableAssociation",
                            "ec2:RevokeSecurityGroupEgress",
                            "ec2:RevokeSecurityGroupIngress",
                            "ec2:RunInstances",
                            "ec2:StartInstances",
                            "ec2:StopInstances",
                            "ec2:TerminateInstances",
                            "ec2:UpdateSecurityGroupRuleDescriptionsEgress",
                            "ec2:UpdateSecurityGroupRuleDescriptionsIngress",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "AllowCreateEC2Resources",
                    },
                    {
                        "Action": [
                            "iam:AddRoleToInstanceProfile",
                            "iam:AttachRolePolicy",
                            "iam:CreateInstanceProfile",
                            "iam:CreateRole",
                            "iam:DeleteInstanceProfile",
                            "iam:DeleteRole",
                            "iam:DeleteRolePolicy",
                            "iam:DetachRolePolicy",
                            "iam:GetInstanceProfile",
                            "iam:GetRole",
                            "iam:GetRolePolicy",
                            "iam:ListRolePolicies",
                            "iam:PassRole",
                            "iam:PutRolePolicy",
                            "iam:RemoveRoleFromInstanceProfile",
                            "iam:TagRole",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "AllowCreateRoles",
                    },
                    {
                        "Action": [
                            "ssm:CreateAssociation",
                            "ssm:GetCommandInvocation",
                            "ssm:SendCommand",
                            "ssm:StartAssociationsOnce",
                        ],
                        "Effect": "Allow",
                        "Resource": "*",
                        "Sid": "SSMCommands",
                    },
                ],
                "Version": "2012-10-17",
            },
            "PolicyName": {"Fn::Join": ["", ["VantageIntegrationPolicy-", {"Ref": "CloudAccountName"}]]},
            "Roles": [{"Ref": "VantageIntegrationRole"}],
        },
    )


def test_stack_lambda_function(cloud_account_stack: Template):
    """Test if the stack has the correct Lambda function."""
    cloud_account_stack.resource_count_is("AWS::Lambda::Function", 1)

    lambda_function_inline_code = open(
        "cloud_account_stack/cloud_account_stack/lambda_function.py", "r"
    ).read()

    cloud_account_stack.has_resource_properties(
        type="AWS::Lambda::Function",
        props={
            "Code": {"ZipFile": lambda_function_inline_code},
            "FunctionName": {"Fn::Join": ["", ["VantageIntegration-", {"Ref": "CloudAccountName"}]]},
            "Handler": "index.lambda_handler",
            "Role": {"Fn::GetAtt": ["LambdaExecutionRole", "Arn"]},
            "Runtime": "python3.10",
            "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}],
            "Timeout": 60,
        },
    )


def test_stack_custom_resource(cloud_account_stack: Template):
    """Test if the stack has the correct Custom Resource."""
    cloud_account_stack.resource_count_is("AWS::CloudFormation::CustomResource", 1)
    cloud_account_stack.has_resource_properties(
        type="AWS::CloudFormation::CustomResource",
        props={
            "ServiceToken": {"Fn::GetAtt": ["CloudAccountStackLambda", "Arn"]},
            "VantageIntegrationRolePolicyName": {
                "Fn::Join": ["", ["VantageIntegrationPolicy-", {"Ref": "CloudAccountName"}]]
            },
            "VantageIntegrationRoleName": {"Ref": "VantageIntegrationRole"},
            "VantageIntegrationPolicyUrl": "https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json",
            "CloudAccountName": {"Ref": "CloudAccountName"},
            "VantageIntegrationStackName": "CloudAccountStack",
            "VantageIntegrationRoleArn": {"Fn::GetAtt": ["VantageIntegrationRole", "Arn"]},
            "VantageApiKey": {"Ref": "ApiKey"},
            "VantageOrganizationId": {"Ref": "OrganizationId"},
            "CloudAccoutDescription": {"Ref": "CloudAccountDescription"},
            "VantageUrl": {
                "Fn::If": [
                    "IsProd",
                    "https://apis.vantagecompute.ai/admin/management/cloud_accounts",
                    {
                        "Fn::If": [
                            "IsStaging",
                            "https://apis.staging.vantagecompute.ai/admin/management/cloud_accounts",
                            {
                                "Fn::If": [
                                    "IsQa",
                                    "https://apis.qa.vantagecompute.ai/admin/management/cloud_accounts",
                                    "https://apis.dev.vantagecompute.ai/admin/management/cloud_accounts",
                                ]
                            },
                        ]
                    },
                ]
            },
        },
    )


def test_stack_event_rule(cloud_account_stack: Template):
    """Test if the stack has the correct Event Rule."""
    cloud_account_stack.resource_count_is("AWS::Events::Rule", 1)
    cloud_account_stack.has_resource_properties(
        type="AWS::Events::Rule",
        props={
            "Description": {
                "Fn::Join": [
                    "",
                    [
                        "Rule to update the ",
                        {"Ref": "VantageIntegrationRole"},
                        " role with the latest policies.",
                    ],
                ]
            },
            "Name": {"Fn::Join": ["", ["VantageIntegration-", {"Ref": "CloudAccountName"}]]},
            "ScheduleExpression": "rate(1 hour)",
            "State": "ENABLED",
            "Targets": [
                {
                    "Arn": {"Fn::GetAtt": ["CloudAccountStackLambda", "Arn"]},
                    "Id": "Target0",
                    "Input": {
                        "Fn::Join": [
                            "",
                            [
                                '{"VantageIntegrationRolePolicyName":"VantageIntegrationPolicy-',
                                {"Ref": "CloudAccountName"},
                                '","VantageIntegrationRoleName":"',
                                {"Ref": "VantageIntegrationRole"},
                                '","VantageIntegrationPolicyUrl":"https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json","CloudAccountName":"',
                                {"Ref": "CloudAccountName"},
                                '","VantageIntegrationStackName":"CloudAccountStack","VantageIntegrationRoleArn":"',
                                {"Fn::GetAtt": ["VantageIntegrationRole", "Arn"]},
                                '","VantageIntegrationRoleLogicalId":"VantageIntegrationRole"}',
                            ],
                        ]
                    },
                }
            ],
        },
    )


def test_stack_invoke_lambda_permission(cloud_account_stack: Template):
    """Test if the stack defines the correct Invoke Lambda Permission."""
    cloud_account_stack.resource_count_is("AWS::Lambda::Permission", 1)
    cloud_account_stack.has_resource_properties(
        type="AWS::Lambda::Permission",
        props={
            "Action": "lambda:InvokeFunction",
            "FunctionName": {"Fn::GetAtt": ["CloudAccountStackLambda", "Arn"]},
            "Principal": "events.amazonaws.com",
            "SourceArn": {"Fn::GetAtt": ["UpdateVantageIntegrationRoleRule", "Arn"]},
        },
    )
