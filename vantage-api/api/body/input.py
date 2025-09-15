"""Core module for storing input body models."""
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import AnyHttpUrl, BaseModel, Field, conlist, constr, root_validator, validator
from pydantic.main import ModelMetaclass


class MembersModel(BaseModel):

    """Model for input members."""

    members: conlist(item_type=str, min_items=1)


class CreateInvitationModel(BaseModel):

    """Model for creating an invitation."""

    invitee_email: str = Field(..., description="The invitee's email.")
    connection_id: Optional[str] = Field(
        ..., description="The id of the connection to force invitee to authenticate with."
    )
    app_metadata: Optional[Dict[str, str]] = {}
    user_metadata: Optional[Dict[str, str]] = {}
    ttl_sec: Optional[int] = Field(
        default=0,
        ge=0,
        le=2592000,
        description=(
            "Number of seconds for which the invitation is valid before expiration. "
            "If unspecified or set to 0, this value defaults to 604800 seconds (7 days). "
            "Max value: 2592000 seconds (30 days)."
        ),
    )
    roles: List[str] = Field(..., description="List of roles IDs to associate with the user.")


class InputGroupsModel(BaseModel):

    """Model for input groups."""

    groups: conlist(item_type=str, min_items=1) = Field(
        ..., description="List of group IDs to be associated/dissociated"
    )


class CreateClientModel(BaseModel):

    """Model for creating a client."""

    client_id: str = Field(
        ...,
        description=(
            "Desirable client ID name. It's a unique no-spaced string, e.g. unique-client-id, "
            "unique-client-id-1, unique-client-id-2. Also, the string contains no symbols other "
            "than hyphens and all letters are lower case."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "Name of the client. Generally it will be the cluster name, which means "
            "it can be a human-friendly string, e.g. Unique Client, OSL Client. "
            "Constraints: unique, sysmbols allowed, numbers allowed, spaces allowed."
        ),
    )
    description: str = Field(
        ..., description="Description of the client. Generally it will be the cluster description."
    )
    secret: Optional[str] = Field(None, min_length=24, max_length=32, description="Client secret.")


class InviteModel(BaseModel):

    """Model for inviting a user."""

    email: str = Field(
        ...,
        description="Email which will be used as the `to address` when sending the invitation email.",
    )
    groups: List[str] = Field([], description="List of group names to attach to the created user.")
    roles: List[str] = Field([], description="List of roles names to attach to the created user.")


class GoogleIdPModel(BaseModel):

    """Model for Google IdP."""

    idp_name: str = Field("google", const=True)
    client_id: str = Field(..., description="OAuth 2.0 client ID from Google Cloud.")
    client_secret: str = Field(..., description="OAuth 2.0 client secret from Google Cloud.")


class GitHubIdPModel(BaseModel):

    """Model for GitHub IdP."""

    idp_name: str = Field("github", const=True)
    client_id: str = Field(..., description="OAuth 2.0 client ID from GitHub.")
    client_secret: str = Field(..., description="OAuth 2.0 client secret from GitHub.")


class AzureIdPModel(BaseModel):

    """Model for Azure IdP."""

    idp_name: str = Field("azure", const=True)
    client_id: str = Field(..., description="OAuth 2.0 client ID from Azure AD.")
    client_secret: str = Field(..., description="OAuth 2.0 client secret from Azure AD.")
    app_identifier: str = Field(
        ...,
        description=(
            "Application identifier from Azure AD. This value can be retrieved from the issuer URL, e.g. "
            "https://login.microsoftonline.com/<AZURE_AD_IDENTIFIER>/v2.0"
        ),
    )


class AllOptional(ModelMetaclass):

    """Provide a metaclass to make all fields optional, except the `idp_name` field in the IdP models.

    Code modified from [StackOverflow](https://stackoverflow.com/a/67733889).
    """

    def __new__(cls, name, bases, namespaces, **kwargs):
        """Make all fields optional, except the `idp_name` field in the IdP models."""
        annotations = namespaces.get("__annotations__", {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith("__") and field != "idp_name":
                annotations[field] = Optional[annotations[field]]
        namespaces["__annotations__"] = annotations
        return super().__new__(cls, name, bases, namespaces, **kwargs)


class PatchGoogleIdpModel(GoogleIdPModel, metaclass=AllOptional):

    """Model for patching the Google IdP."""

    pass


class PatchAzureIdpModel(AzureIdPModel, metaclass=AllOptional):

    """Model for patching the Azure IdP."""

    pass


class PatchGitHubIdpModel(GitHubIdPModel, metaclass=AllOptional):

    """Model for patching the GitHub IdP."""

    pass


class CreateOrganizationModel(BaseModel):

    """Model for creating an organization."""

    name: constr(strip_whitespace=True, to_lower=True, max_length=63, min_length=1) = Field(
        ...,
        description=(
            "Name of the organization. This value will be parsed later to remove all non-ASCII characters"
            " and also to replace white spaces for hyphens. In case there's a similar character matching"
            " the non-ASCII one, e.g. ä -> a, the character will be simply replaced. Also, this value will be"
            " parsed to a lower case word."
        ),
    )
    logo: Optional[AnyHttpUrl] = Field(str(), description="URL of the organization's logo.")
    display_name: str = Field(..., description="Display name of the organization.")


class UpdateOrganizationModel(BaseModel):

    """Model for updating an organization."""

    logo: Optional[AnyHttpUrl] = Field(None, description="URL of the organization's logo.")
    display_name: Optional[str] = Field(None, description="Display name of the organization.")
    domain: Optional[str] = Field(None, description="Domain of the organization.")

    @validator("domain")
    def validate_domain(cls, value: str | None) -> str | None:  # noqa: N805
        """Validate the domain."""
        if value is not None and value == "":
            return None
        return value


class CreateCloudAccountModel(BaseModel):

    """Model for creating a cloud account."""

    name: str = Field(..., description=("Name of the cloud account."), max_length=45, min_length=1)
    description: str = Field(..., description="Description of the cloud account.", max_length=1000)
    role_arn: str = Field(
        ...,
        description="ARN of the role to be assumed by the cloud account.",
        regex=r"^arn:aws:iam::\d{12}:role/[a-zA-Z0-9+=,.@_-]{1,64}$",
    )
    assisted_cloud_account: bool = Field(
        False,
        description=(
            "Whether the cloud account is created by the assisted process or not. "
            "If so, the value must be `true`."
        ),
    )
    api_key: str = Field(..., description="API key to authenticate against the API itself.")
    organization_id: str = Field(
        ..., description="Organization ID to which the cloud account will be associated."
    )


class UpdateCloudAccountModel(BaseModel):

    """Model for updating a cloud account."""

    description: str = Field(
        ..., description="Description of the cloud account.", max_length=1000, min_length=1
    )


class FinalizeAwsSubscriptionModel(BaseModel):

    """Model for finalizing an AWS subscription."""

    product_code: str = Field(..., description="Product code.")
    customer_identifier: str = Field(..., description="Customer identifier.")
    customer_aws_account_id: str = Field(..., description="Customer AWS account ID.")


class UpdateUserProfile(BaseModel):

    """Model for updating a user's profile."""

    first_name: Optional[str] = Field(None, description="First name of the user.")
    last_name: Optional[str] = Field(None, description="Last name of the user.")
    avatar_url: Optional[AnyHttpUrl] = Field(None, description="URL of the user's avatar.")

    @root_validator(pre=True)
    def validate_at_least_one_present(cls, values: dict[str, str | None]) -> dict[str, str | None]:  # noqa: N805
        """Validate that at least one field is present."""
        if not any(values.values()):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided.",
            )
        return values
