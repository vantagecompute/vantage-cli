"""Core module for defining the Cloud Account stack create by the assisted mode."""
import json
import os

from aws_cdk import (
    CfnCondition,
    CfnParameter,
    CustomResource,
    Duration,
    Fn,
    Stack,
)
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from constructs import Construct

current_dir = os.path.dirname(os.path.abspath(__file__))
policy_path = os.path.join(current_dir, "vantage_integration_policy.json")
lambda_function_path = os.path.join(current_dir, "lambda_function.py")


class CloudAccountStack(Stack):
    """Cloud Account Stack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Create a stack for a cloud account created by the assisted mode.

        The stack creates the integration role that will be assumed by Vantage resources.

        Also, it creates a lambda function that will be triggered by a custom resource in
        order to create the cloud account row in Vantage's database.

        By last, it creates an EventBridge rule to trigger the lambda function each hour.
        The purpose of this trigger is to identify if the integration role has the latest
        policies attached to it. If not, the lambda function will create a change set to
        update the this CloudFormation stack. This change set will only patch the integration
        role with the latest policies. The latest policy will be fetched from a public S3
        bucket.
        """
        super().__init__(scope, construct_id, **kwargs)

        cloud_account_name = CfnParameter(
            self,
            "CloudAccountName",
            type="String",
            description="Name of the cloud account on Vantage. Do not change this value.",
            min_length=1,
            max_length=45,
            allowed_pattern="^[a-zA-Z][a-zA-Z0-9-]{0,44}$",
        )

        api_key = CfnParameter(
            self,
            "ApiKey",
            type="String",
            description="API key to authenticate with Vantage's API. Do not change this value.",
        )

        organization_id = CfnParameter(
            self,
            "OrganizationId",
            type="String",
            description=(
                "Organization ID to which the cloud account will be associated. " "Do not change this value."
            ),
        )

        cloud_account_description = CfnParameter(
            self,
            "CloudAccountDescription",
            type="String",
            description="Description of the cloud account on Vantage. Do not change this value.",
            min_length=1,
            max_length=1000,
        )

        stage = CfnParameter(
            self,
            "Stage",
            type="String",
            description="Stage of the environment. Do not change this value.",
            allowed_values=["dev", "qa", "staging", "prod"],
            default="prod",
        )

        is_prod = CfnCondition(
            self,
            "IsProd",
            expression=Fn.condition_equals(stage, "prod"),
        )
        is_staging = CfnCondition(
            self,
            "IsStaging",
            expression=Fn.condition_equals(stage, "staging"),
        )
        is_qa = CfnCondition(
            self,
            "IsQa",
            expression=Fn.condition_equals(stage, "qa"),
        )
        vantage_url = Fn.condition_if(
            is_prod.logical_id,
            "https://apis.vantagecompute.ai/admin/management/cloud_accounts",
            Fn.condition_if(
                is_staging.logical_id,
                "https://apis.staging.vantagecompute.ai/admin/management/cloud_accounts",
                Fn.condition_if(
                    is_qa.logical_id,
                    "https://apis.qa.vantagecompute.ai/admin/management/cloud_accounts",
                    "https://apis.dev.vantagecompute.ai/admin/management/cloud_accounts",
                ),
            ),
        )

        vantage_integration_policy_json = json.loads(open(policy_path, "r").read())

        vantage_integration_role = iam.Role(
            self,
            "VantageIntegrationRole",
            assumed_by=iam.PrincipalWithConditions(
                principal=iam.AccountPrincipal("266735843730"),
                conditions={"ArnLike": {"aws:PrincipalArn": "arn:aws:iam::266735843730:role/*"}},
            ),
            role_name=f"VantageIntegration-{cloud_account_name.value_as_string}",
        )

        vantage_integration_role.node.default_child.override_logical_id("VantageIntegrationRole")

        vantage_integration_role_policy = iam.Policy(
            self,
            "VantageIntegrationPolicy",
            policy_name=f"VantageIntegrationPolicy-{cloud_account_name.value_as_string}",
            statements=[
                iam.PolicyStatement.from_json(statement)
                for statement in vantage_integration_policy_json.get("Statement")
            ],
        )
        vantage_integration_role_policy.node.default_child.override_logical_id("VantageIntegrationPolicy")

        vantage_integration_role.attach_inline_policy(vantage_integration_role_policy)

        lambda_execution_role_policy = iam.Policy(
            self,
            "LambdaExecutionPolicy",
            policy_name=f"LambdaExecutionPolicy-{cloud_account_name.value_as_string}",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iam:GetRolePolicy", "iam:PutRolePolicy"],
                    resources=[vantage_integration_role.role_arn],
                ),
            ],
        )
        lambda_execution_role_policy.node.default_child.override_logical_id("LambdaExecutionPolicy")

        lambda_execution_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
            role_name=f"LambdaExecution-{cloud_account_name.value_as_string}",
        )
        lambda_execution_role.node.default_child.override_logical_id("LambdaExecutionRole")
        lambda_execution_role.attach_inline_policy(lambda_execution_role_policy)

        lambda_function = _lambda.Function(
            self,
            "CloudAccountStackLambda",
            runtime=_lambda.Runtime.PYTHON_3_10,
            handler="index.lambda_handler",
            code=_lambda.Code.from_inline(open(lambda_function_path).read()),
            timeout=Duration.seconds(60),
            role=lambda_execution_role,
            function_name=f"VantageIntegration-{cloud_account_name.value_as_string}",
        )
        lambda_function.node.add_dependency(vantage_integration_role)
        lambda_function.node.add_dependency(lambda_execution_role)
        lambda_function.node.default_child.override_logical_id("CloudAccountStackLambda")

        lambda_input_data = {
            "VantageIntegrationRolePolicyName": vantage_integration_role_policy.policy_name,
            "VantageIntegrationRoleName": vantage_integration_role.role_name,
            "VantageIntegrationPolicyUrl": "https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-policy.json",
            "CloudAccountName": cloud_account_name.value_as_string,
            "VantageIntegrationStackName": self.stack_name,
            "VantageIntegrationRoleArn": vantage_integration_role.role_arn,
        }
        lambda_on_create_input_data = {
            **lambda_input_data,
            **{
                "VantageApiKey": api_key.value_as_string,
                "VantageOrganizationId": organization_id.value_as_string,
                "CloudAccoutDescription": cloud_account_description.value_as_string,
                "VantageUrl": vantage_url,
            },
        }

        lambda_on_create_cr = CustomResource(
            self,
            "CloudAccountStackCustomResource",
            service_token=lambda_function.function_arn,
            properties=lambda_on_create_input_data,
        )
        lambda_on_create_cr.node.add_dependency(lambda_function)
        lambda_on_create_cr.node.add_dependency(lambda_execution_role)
        lambda_on_create_cr.node.default_child.override_logical_id("CloudAccountStackCustomResource")

        lambda_on_role_update_input_data = {
            **lambda_input_data,
            **{
                "VantageIntegrationRoleLogicalId": vantage_integration_role.node.default_child.logical_id,
            },
        }

        lambda_target_input = events.RuleTargetInput.from_object(lambda_on_role_update_input_data)

        lambda_target = targets.LambdaFunction(handler=lambda_function, event=lambda_target_input)

        update_vantage_integration_role_rule = events.Rule(
            self,
            "UpdateVantageIntegrationRoleRule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            enabled=True,
            description=f"Rule to update the {vantage_integration_role.role_name} role with the latest policies.",  # noqa: E501
            rule_name=f"VantageIntegration-{cloud_account_name.value_as_string}",
        )
        update_vantage_integration_role_rule.node.add_dependency(lambda_function)
        update_vantage_integration_role_rule.node.add_dependency(lambda_execution_role)
        update_vantage_integration_role_rule.add_target(lambda_target)
        update_vantage_integration_role_rule.node.default_child.override_logical_id(
            "UpdateVantageIntegrationRoleRule"
        )

        for construct in update_vantage_integration_role_rule.node.find_all():
            if isinstance(construct, _lambda.CfnPermission):
                construct.override_logical_id("UpdateVantageIntegrationRoleRulePermission")
