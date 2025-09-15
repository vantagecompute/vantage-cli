"""Test the email module in the utils package."""
import json
from typing import List, Union
from unittest.mock import patch

import pytest
from botocore.stub import Stubber
from freezegun import freeze_time

from api.utils.email import SETTINGS, EmailOps

EMAIL_SOURCE = "test@omnivector.solutions"
CONFIGURATION_SET = "dummy-config"
INVITE_TEMPLATE_NAME = "dummy-template"


def test_email_ops__check_build_template_data():
    """Test if the `_build_invite_template_data` method returns the correctly payload."""
    tenant = "dummy-tenant"
    invitation_url = f"https://app.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}"

    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET)

    template_data_body = email_ops._build_invite_template_data(tenant)

    assert template_data_body == {"orgname": tenant, "invitationurl": invitation_url}


def test_email_ops__check_build_template_data__check_production_stage():
    """Test if `_build_invite_template_data` returns correct data with `production` stage setting."""
    tenant = "dummy-tenant"
    invitation_url = f"https://app.{SETTINGS.APP_DOMAIN}"

    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET)

    with patch.object(SETTINGS, "STAGE", new="production"):
        template_data_body = email_ops._build_invite_template_data(tenant)

    assert template_data_body == {"orgname": tenant, "invitationurl": invitation_url}


@pytest.mark.parametrize(
    "to_addresses,reply_to",
    [
        (["target@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target@omnivector.solutions"], None),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], None),
    ],
)
def test_email_ops__build_the_expected_payload_from_boto3(to_addresses, reply_to):
    """Test if `_build_invitation_email_body` returns the correct payload for `SendTemplateEmail` in boto3."""
    tenant = "dummy-tenant"
    invitation_url = f"https://{tenant}.omnivector.solutions"

    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET, reply_to)

    payload = email_ops._build_invitation_email_body(to_addresses, tenant)

    payload == {
        "Source": EMAIL_SOURCE,
        "Destination": {
            "ToAddresses": to_addresses,
        },
        "ReplyToAddresses": [reply_to if reply_to is not None else EMAIL_SOURCE],
        "Tags": [
            {"Name": "project", "Value": "Vantage"},
        ],
        "ConfigurationSetName": CONFIGURATION_SET,
        "Template": SETTINGS.INVITE_TEMPLATE_NAME,
        "TemplateData": json.dumps({"orgname": tenant, "invitationurl": invitation_url}),
    }


@pytest.mark.parametrize(
    "to_addresses,reply_to",
    [
        (["target@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target@omnivector.solutions"], None),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], None),
    ],
)
def test_send_email__no_errors(to_addresses, reply_to):
    """Test if the emails are sent correctly with no expected errors."""
    tenant = "dummy-tenant"
    invitation_url = f"https://app.staging.{SETTINGS.APP_DOMAIN}"
    template_data = {"orgname": tenant, "invitationurl": invitation_url}

    message_id = "abcde12345"

    response = {"MessageId": message_id}

    expected_params = {
        "Source": EMAIL_SOURCE,
        "Destination": {
            "ToAddresses": to_addresses,
        },
        "ReplyToAddresses": [reply_to if reply_to is not None else EMAIL_SOURCE],
        "Tags": [
            {"Name": "project", "Value": "Vantage"},
        ],
        "ConfigurationSetName": CONFIGURATION_SET,
        "Template": SETTINGS.INVITE_TEMPLATE_NAME,
        "TemplateData": json.dumps(template_data),
    }

    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET, reply_to)

    stubber = Stubber(email_ops._client)
    stubber.add_response("send_templated_email", response, expected_params)

    with stubber:
        email_ops.send_invite_email(to_addresses, tenant)


@pytest.mark.parametrize(
    "to_addresses,reply_to",
    [
        (["target@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target@omnivector.solutions"], None),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], "reply-to@omnivector.solutions"),
        (["target.1@omnivector.solutions", "target.2@omnivector.solutions"], None),
    ],
)
def test_send_email__expect_loggin_when_client_error_happens(
    to_addresses: List[str], reply_to: Union[str, None]
):
    """Test if the an error is raised when there's a botocore error during sending email."""
    tenant = "dummy-tenant"
    invitation_url = f"https://app.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}"
    template_data = {"orgname": tenant, "invitationurl": invitation_url}

    request_id = "abcde12345"

    expected_params = {
        "Source": EMAIL_SOURCE,
        "Destination": {
            "ToAddresses": to_addresses,
        },
        "ReplyToAddresses": [reply_to if reply_to is not None else EMAIL_SOURCE],
        "Tags": [
            {"Name": "project", "Value": "Vantage"},
        ],
        "ConfigurationSetName": CONFIGURATION_SET,
        "Template": INVITE_TEMPLATE_NAME,
        "TemplateData": json.dumps(template_data),
    }

    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET, reply_to)

    stubber = Stubber(email_ops._client)
    error_code = "MessageRejected"
    message = "Dummy error happened"
    stubber.add_client_error(
        "send_templated_email",
        service_error_code=error_code,
        service_message=message,
        expected_params=expected_params,
        response_meta={"RequestId": request_id},
    )

    with pytest.raises(Exception), stubber:
        email_ops.send_invite_email(to_addresses, tenant)


@pytest.mark.parametrize(
    "freeze_date, output_date",
    [
        ("2024-01-01", "January 01, 2024"),
        ("2024-12-31", "December 31, 2024"),
        ("2022-06-15", "June 15, 2022"),
    ],
)
def test_email_ops__check_build_delete_organization_template_data(freeze_date: str, output_date: str):
    """Test if `_build_delete_organization_template_data` returns the correct payload."""
    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET)

    with freeze_time(freeze_date):
        template_data_body = email_ops._build_delete_organization_template_data()

    assert template_data_body == {"deletiondate": output_date}


@pytest.mark.parametrize("to_addresses, reply_to", [(["foo@boo.com"], "dummy@gmail.com")])
def test_email_ops__check_build_org_deletion_email_body(to_addresses: list[str], reply_to: str):
    """Test if `_build_org_deletion_email_body` returns the correct payload."""
    email_ops = EmailOps(EMAIL_SOURCE, CONFIGURATION_SET, reply_to)

    with freeze_time("2022-06-15"):
        payload = email_ops._build_org_deletion_email_body(to_addresses)

    assert payload == {
        "Source": EMAIL_SOURCE,
        "Destination": {
            "ToAddresses": to_addresses,
        },
        "ReplyToAddresses": [reply_to],
        "Tags": [
            {"Name": "project", "Value": "Vantage"},
        ],
        "ConfigurationSetName": CONFIGURATION_SET,
        "Template": SETTINGS.DELETE_ORG_TEMPLATE_NAME,
        "TemplateData": json.dumps({"deletiondate": "June 15, 2022"}),
    }
