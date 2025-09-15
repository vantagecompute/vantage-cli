"""Lambda function to integrate with the Vantage platform.

It is designed to receive two source of events:
- CloudFormation Custom Resource: to notify Omnivector about the new Cloud Account.
- EventBridge: to update the integration role with the latest policies.

An Eventbridge rule is created to trigger the Lambda function once an hour.
"""
import json

import boto3
import cfnresponse
import urllib3

iam = boto3.client("iam")
http = urllib3.PoolManager()


def lambda_handler(event, context):
    """Handle Lambda events."""
    print("Received event: ", event)

    stack_response = {}

    # event from CloudFormation Custom Resource
    if event.get("RequestType") == "Create":
        try:
            notify_omnivector(event)
            stack_response["Message"] = "Resource creation successful!"
            cfnresponse.send(event, context, cfnresponse.SUCCESS, stack_response)
        except Exception as e:
            print(">>> Exception raised: ", e)
            stack_response["Message"] = str(e)
            cfnresponse.send(event, context, "FAILED", stack_response)

    # event from CloudFormation Custom Resource
    # Used mainly for integration testing.
    elif event.get("RequestType") == "Delete":
        stack_response["Message"] = "Resource deletion successful!"
        cfnresponse.send(event, context, cfnresponse.SUCCESS, stack_response)

    # event from EventBridge
    else:
        current_policy_document, upstream_policy_document = fetch_policies(event)
        if current_policy_document == upstream_policy_document:
            print("The Vantage integration role policy is up to date.")
        else:
            print("The Vantage integration role policy is outdated.")
            patch_role_policy(event, upstream_policy_document)


def notify_omnivector(event):
    """Notify Omnivector about the new Cloud Account."""
    body_payload = {
        "name": event.get("ResourceProperties").get("CloudAccountName"),
        "description": event.get("ResourceProperties").get("CloudAccoutDescription"),
        "role_arn": event.get("ResourceProperties").get("VantageIntegrationRoleArn"),
        "assisted_cloud_account": True,
        "api_key": event.get("ResourceProperties").get("VantageApiKey"),
        "organization_id": event.get("ResourceProperties").get("VantageOrganizationId"),
    }
    encoded_body_payload = json.dumps(body_payload).encode("utf-8")

    response = http.request(
        "POST",
        event.get("ResourceProperties").get("VantageUrl"),
        body=encoded_body_payload,
        headers={
            "Content-Type": "application/json",
        },
    )
    print("Notify response: ", response.data)


def fetch_policies(event: dict[str, str]) -> tuple[str, str | list[dict[str, str | list[str]]]]:
    """Detect outdated policies in the integration role."""
    print("Fetching policies current policy document and upstream policy document.")
    integration_role_policy = iam.get_role_policy(
        RoleName=event.get("VantageIntegrationRoleName"),
        PolicyName=event.get("VantageIntegrationRolePolicyName"),
    )
    current_policy_document = integration_role_policy.get("PolicyDocument")
    print("Policy document: ", current_policy_document)

    upstream_policy_document_response = http.request("GET", event.get("VantageIntegrationPolicyUrl"))
    upstream_policy_document = json.loads(upstream_policy_document_response.data)
    print("Upstream policy document: ", upstream_policy_document)

    return current_policy_document, upstream_policy_document


def patch_role_policy(event, policy_document):
    """Patch the integration role with the latest policies."""
    print("Patching the integration role with the latest policies.")
    response = iam.put_role_policy(
        RoleName=event.get("VantageIntegrationRoleName"),
        PolicyName=event.get("VantageIntegrationRolePolicyName"),
        PolicyDocument=json.dumps(policy_document),
    )
    print("Patching response: ", response)
