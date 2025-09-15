"""Core module for email operations related."""
import json
from datetime import datetime
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_ses.client import SESClient

from api.settings import SETTINGS
from api.utils.logging import logger


class EmailOps:

    """Base class to employ email operations, such as to build the email body and send emails."""

    def __init__(  # noqa: D107
        self, source: str, configuration_set: str, reply_to: Optional[str] = None
    ) -> None:
        self._client: SESClient = boto3.client("ses")
        self._source = source
        self._reply_to = reply_to if reply_to is not None else self._source
        self._configuration_set = configuration_set

    def _build_invite_template_data(self, tenant: str) -> Dict[str, str]:
        """Build the template data dict to correctly send the template email regarding invitations."""
        return {
            "orgname": tenant,
            "invitationurl": f"https://app.{SETTINGS.APP_DOMAIN}"
            if SETTINGS.STAGE == "production"
            else f"https://app.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}",
        }

    def _build_common_arguments_for_email_body(self) -> dict[str, str | list[str] | list[dict[str, str]]]:
        """Build the common arguments for the email body."""
        return {
            "Source": self._source,
            "ReplyToAddresses": [self._reply_to],
            "Tags": [
                {"Name": "project", "Value": "Vantage"},
            ],
            "ConfigurationSetName": self._configuration_set,
        }

    def _build_invitation_email_body(
        self, to_addresses: List[str], tenant: str
    ) -> dict[str, str | dict[str, list[str]] | list[str] | list[dict[str, str]]]:
        """Build the email body required by the `SendTemplatedEmail` operation."""
        return {
            **self._build_common_arguments_for_email_body(),
            "Destination": {
                "ToAddresses": to_addresses,
            },
            "Template": SETTINGS.INVITE_TEMPLATE_NAME,
            "TemplateData": json.dumps(self._build_invite_template_data(tenant)),
        }

    def _build_org_deletion_email_body(
        self, to_addresses: List[str]
    ) -> dict[str, str | dict[str, list[str]] | list[str] | list[dict[str, str]]]:
        """Build the email body required by the `SendTemplatedEmail` operation."""
        return {
            **self._build_common_arguments_for_email_body(),
            "Destination": {
                "ToAddresses": to_addresses,
            },
            "Template": SETTINGS.DELETE_ORG_TEMPLATE_NAME,
            "TemplateData": json.dumps(self._build_delete_organization_template_data()),
        }

    def _build_delete_organization_template_data(self) -> dict[str, str]:
        """Build the template data to correctly send the email regarding the organization deletion."""
        return {
            "deletiondate": datetime.now().strftime("%B %d, %Y"),
        }

    def send_invite_email(self, to_addresses: List[str], tenant: str) -> None:
        """Send emails on behalf of an Omnivector account."""
        args = self._build_invitation_email_body(to_addresses, tenant)
        try:
            send_email_response = self._client.send_templated_email(**args)
        except ClientError as e:
            logger.error(
                f"Error when sending an email to {to_addresses}\n" "Error info: {}".format(
                    {
                        "request-id": e.response["ResponseMetadata"]["RequestId"],
                        "message": e.response["Error"]["Message"],
                        "code": e.response["Error"]["Code"],
                    }
                )
            )
            raise e
        else:
            logger.info(
                f"Sent email whose message ID is {send_email_response['MessageId']} to {to_addresses}"
            )

    def send_delete_organization_email(self, to_addresses: List[str]) -> None:
        """Send emails on behalf of an Omnivector account."""
        args = self._build_org_deletion_email_body(to_addresses)
        try:
            send_email_response = self._client.send_templated_email(**args)
        except ClientError as e:
            logger.error(
                f"Error when sending an email to {to_addresses}\n" "Error info: {}".format(
                    {
                        "request-id": e.response["ResponseMetadata"]["RequestId"],
                        "message": e.response["Error"]["Message"],
                        "code": e.response["Error"]["Code"],
                    }
                )
            )
            raise e
        else:
            logger.info(
                f"Sent email whose message ID is {send_email_response['MessageId']} to {to_addresses}"
            )


EMAIL_OPS = EmailOps(
    SETTINGS.SOURCE_EMAIL,
    SETTINGS.CONFIGURATION_SET,
    SETTINGS.REPLY_TO,
)
