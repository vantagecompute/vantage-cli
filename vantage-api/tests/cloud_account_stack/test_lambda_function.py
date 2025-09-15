"""Test the Lambda function used in the CloudAccountStack."""
import json
from typing import Collection
from unittest import mock

from botocore.stub import Stubber

from cloud_account_stack.cloud_account_stack.lambda_function import (
    fetch_policies,
    iam,
    lambda_handler,
    notify_omnivector,
    patch_role_policy,
)


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.cfnresponse")
@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.notify_omnivector")
def test_lambda_handler_on_create_custom_resource(
    mocked_notify_omnivector: mock.MagicMock,
    mocked_cfnresponse: mock.MagicMock,
    lambda_function_custom_resource_create_event: dict[str, Collection[str]],
):
    """Test the lambda_handler function when the event is from a CloudFormation Custom Resource on CREATE action."""  # noqa: E501
    mocked_notify_omnivector.return_value = None

    mocked_cfnresponse.send = mock.Mock()
    mocked_cfnresponse.SUCCESS = "SUCCESS"
    mocked_cfnresponse.send.return_value = None

    context = None

    lambda_handler(lambda_function_custom_resource_create_event, context)

    mocked_notify_omnivector.assert_called_once_with(lambda_function_custom_resource_create_event)
    mocked_cfnresponse.send.assert_called_once_with(
        lambda_function_custom_resource_create_event,
        context,
        "SUCCESS",
        {"Message": "Resource creation successful!"},
    )


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.cfnresponse")
def test_lambda_handler_on_delete_custom_resource(
    mocked_cfnresponse: mock.MagicMock,
    lambda_function_custom_resource_delete_event: dict[str, Collection[str]],
):
    """Test the lambda_handler function when the event is from a CloudFormation Custom Resource on DELETE action."""  # noqa: E501
    mocked_cfnresponse.send = mock.Mock()
    mocked_cfnresponse.SUCCESS = "SUCCESS"
    mocked_cfnresponse.send.return_value = None

    context = None

    lambda_handler(lambda_function_custom_resource_delete_event, context)

    mocked_cfnresponse.send.assert_called_once_with(
        lambda_function_custom_resource_delete_event,
        context,
        "SUCCESS",
        {"Message": "Resource deletion successful!"},
    )


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.fetch_policies")
@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.patch_role_policy")
def test_lambda_handler__event_bridge_event_when_policy_is_up_to_date(
    mocked_patch_role_policy: mock.MagicMock,
    mocked_fetch_policies: mock.MagicMock,
    lambda_function_event_bridge_event: dict[str, Collection[str]],
):
    """Test the lambda_handler function when the event is from EventBridge and the policy is up to date."""
    # The variables here don't matter. We just want to test if nothing happens when they are equal.
    mocked_fetch_policies.return_value = ("policy", "policy")

    context = None

    lambda_handler(lambda_function_event_bridge_event, context)

    mocked_fetch_policies.assert_called_once_with(lambda_function_event_bridge_event)
    mocked_patch_role_policy.assert_not_called()


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.fetch_policies")
@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.patch_role_policy")
def test_lambda_handler__event_bridge_event_when_policy_is_outdated(
    mocked_patch_role_policy: mock.MagicMock,
    mocked_fetch_policies: mock.MagicMock,
    lambda_function_event_bridge_event: dict[str, Collection[str]],
):
    """Test the lambda_handler function when the event is from EventBridge and the policy is outdated."""
    upstream_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "events.amazonaws.com"},
            }
        ],
    }

    # The variables here don't matter. We just want to test the logic when the policy is different.
    mocked_fetch_policies.return_value = ("policy", upstream_policy_document)

    mocked_patch_role_policy.return_value = None

    context = None

    lambda_handler(lambda_function_event_bridge_event, context)

    mocked_fetch_policies.assert_called_once_with(lambda_function_event_bridge_event)
    mocked_patch_role_policy.assert_called_once_with(
        lambda_function_event_bridge_event, upstream_policy_document
    )


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.http")
def test_notify_omnivector(
    mocked_http: mock.MagicMock, lambda_function_custom_resource_create_event: dict[str, str | dict[str, str]]
):
    """Test the notify_omnivector function."""
    mocked_http.request = mock.Mock()
    mocked_http.request.return_value.data = "dummy_response"

    body_payload = {
        "name": lambda_function_custom_resource_create_event.get("ResourceProperties").get(
            "CloudAccountName"
        ),
        "description": lambda_function_custom_resource_create_event.get("ResourceProperties").get(
            "CloudAccoutDescription"
        ),
        "role_arn": lambda_function_custom_resource_create_event.get("ResourceProperties").get(
            "VantageIntegrationRoleArn"
        ),
        "assisted_cloud_account": True,
        "api_key": lambda_function_custom_resource_create_event.get("ResourceProperties").get(
            "VantageApiKey"
        ),
        "organization_id": lambda_function_custom_resource_create_event.get("ResourceProperties").get(
            "VantageOrganizationId"
        ),
    }

    notify_omnivector(lambda_function_custom_resource_create_event)

    mocked_http.request.assert_called_once_with(
        "POST",
        lambda_function_custom_resource_create_event.get("ResourceProperties").get("VantageUrl"),
        body=json.dumps(body_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


@mock.patch("cloud_account_stack.cloud_account_stack.lambda_function.http")
def test_fetch_policies(mocked_http: mock.MagicMock, lambda_function_event_bridge_event: dict[str, str]):
    """Test the fetch_policies function."""
    current_policy_document_stub = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "events.amazonaws.com"},
            }
        ],
    }
    upstream_policy_document_stub = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "events.amazonaws.com"},
            }
        ],
    }

    get_role_policy_response = {
        "PolicyDocument": json.dumps(current_policy_document_stub),
        "RoleName": lambda_function_event_bridge_event.get("VantageIntegrationRoleName"),
        "PolicyName": lambda_function_event_bridge_event.get("VantageIntegrationRolePolicyName"),
    }
    get_role_policy_params = {
        "RoleName": lambda_function_event_bridge_event.get("VantageIntegrationRoleName"),
        "PolicyName": lambda_function_event_bridge_event.get("VantageIntegrationRolePolicyName"),
    }

    stubber = Stubber(iam)
    stubber.add_response("get_role_policy", get_role_policy_response, get_role_policy_params)
    stubber.activate()

    mocked_http.request = mock.Mock()
    mocked_http.request.return_value.data = json.dumps(upstream_policy_document_stub)

    current_policy_document, upstream_policy_document = fetch_policies(lambda_function_event_bridge_event)

    mocked_http.request.assert_called_once_with(
        "GET", lambda_function_event_bridge_event.get("VantageIntegrationPolicyUrl")
    )
    assert current_policy_document == current_policy_document_stub
    assert upstream_policy_document == upstream_policy_document_stub
    stubber.assert_no_pending_responses()

    stubber.deactivate()


def test_patch_role_policy():
    """Test the patch_role_policy function."""
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"Service": "events.amazonaws.com"},
            }
        ],
    }

    put_role_policy_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    put_role_policy_params = {
        "RoleName": "vantage-integration-role",
        "PolicyName": "vantage-integration-policy",
        "PolicyDocument": json.dumps(policy_document),
    }

    stubber = Stubber(iam)
    stubber.add_response("put_role_policy", put_role_policy_response, put_role_policy_params)
    stubber.activate()

    patch_role_policy(
        {
            "VantageIntegrationRoleName": "vantage-integration-role",
            "VantageIntegrationRolePolicyName": "vantage-integration-policy",
        },
        policy_document,
    )

    stubber.assert_no_pending_responses()
    stubber.deactivate()
