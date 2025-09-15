"""Core module for storing output body models."""
import enum
import re
from datetime import datetime
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, ValidationError, root_validator, validator

from api.sql_app.schemas import OrganizationFreeTrialsRow, PendingAwsSubscriptionRow, SubscriptionRow


class BaseOutputModel(BaseModel):

    """Common model for all models in this module.

    It provides an interface for alias input, e.g. suppose the following model:

    class ExampleModel(BaseOutputModel):
        example_field: str

    it's possible to instantiate the class as `ExampleModel(exampleField="it's just an example")`. In the case
    of this implementation, it's very useful when managing data from Keycloak's Admin API.
    """

    class Config:

        """Configuration class for the model."""

        alias_generator = lambda string: re.sub(r"_(\w)", lambda match: match.group(1).upper(), string)  # noqa: E731


class MessageModel(BaseOutputModel):

    """Model for a general message."""

    message: str = Field(..., description="General message about the request.")
    error: Optional[str] = Field(None, description="Error happened.")

    class Config:

        """Configuration class for the model."""

        extra = "allow"


class UserModel(BaseOutputModel):

    """Model for a single user."""

    user_id: str = Field(..., description="User ID.", alias="id")
    email: Optional[EmailStr] = Field(None, description="User email.")
    name: Optional[str] = Field(None, description="User names.")
    avatar_url: Optional[AnyHttpUrl] = Field(None, description="User avatar URL.")

    @root_validator(pre=True)
    def extract_picture_from_attributes_and_build_name(cls, values):  # noqa: N805
        """Extract the avatar URL from the attributes field and parse the user's name."""
        if values.get("avatar_url") is None:
            if "attributes" in values:
                if "picture" in values["attributes"]:
                    values["avatar_url"] = values["attributes"]["picture"][0]
            elif "picture" in values:
                values["avatar_url"] = values["picture"]

        if values.get("name") is None or "name" not in values:
            first_name = (values.get("firstName") or "").strip()
            last_name = (values.get("lastName") or "").strip()
            full_name = f"{first_name} {last_name}".strip()
            values["name"] = full_name if full_name else None

        return values

    def dict(self, *args, **kwargs):
        """Override the dict method to convert the avatar_url to a string."""
        d = super().dict(*args, **kwargs)
        if "avatar_url" in d and isinstance(d["avatar_url"], AnyHttpUrl):
            d["avatar_url"] = str(d["avatar_url"])
        return d

    class Config:

        """Configuration class for the model."""

        extra = "ignore"
        allow_population_by_field_name = True


class UserListModel(BaseOutputModel):

    """Model for listing users."""

    users: List[UserModel]


class UserIDP(BaseOutputModel):

    """Model for a user from an identity provider."""

    identity_provider: Optional[str] = Field(
        None, description="Name of the identity provider, e.g. google, microsoft."
    )
    user_name: Optional[str] = Field(None, description="User name form the IDP.")


class CompleteUserModel(BaseOutputModel):

    """Model for a complete user."""

    def __init__(
        self, avatar_url: str | None = None, attributes: dict = {}, picture: str | None = None, **kwargs
    ) -> None:
        """Initialize the class."""
        super().__init__(**kwargs)
        if attributes is not None:
            self.avatar_url = attributes.get("picture", [None])[0] or picture
        if avatar_url is not None:
            self.avatar_url = avatar_url

    avatar_url: Optional[str] = Field(
        None,
        description="The user avatar url.",
        alias="avatarUrl",
    )
    created_at: Optional[str] = Field(
        None,
        description="Date and time when this user was created. Format: according to ISO 8601",
        alias="createdTimestamp",
    )
    email: Optional[EmailStr] = Field(None, description="Email address of this user.")
    email_verified: Optional[bool] = Field(
        None, description="Whether this email address is verified (true) or unverified (false)."
    )
    username: Optional[str] = Field(None, description="Username of this user.")
    family_name: Optional[str] = Field(
        None, description="Family name/last name/surname of this user.", alias="lastName"
    )
    given_name: Optional[str] = Field(
        None, description="Given name/first name/forename of this user.", alias="firstName"
    )
    federated_identities: Optional[List[UserIDP]] = Field(
        [], description="List of identity providers from which the user comes from."
    )
    blocked: Optional[bool] = Field(
        None,
        description="Whether this user was blocked by an administrator (true) or is not (false).",
        alias="enabled",
    )
    user_id: Optional[str] = Field(None, description="ID of the user.", alias="id")

    @validator("created_at", pre=True, always=True)
    def datetime_from_timestamp(cls, v):  # noqa: N805
        """Transform the timestamp to a datetime object."""
        if isinstance(v, int):
            return datetime.fromtimestamp(v / 1000).isoformat(timespec="seconds")
        if isinstance(v, str):
            return datetime.fromisoformat(v).isoformat(timespec="seconds")


class IdPModel(BaseModel):

    """Model for an identity provider."""

    id: str = Field(..., description="ID of the identity provider.", alias="internalId")
    client_id: str = Field(..., description="ID of the identity provider.", alias="config")
    provider_id: str = Field(..., description="Provider ID of the identity provider.", alias="providerId")

    @validator("client_id", pre=True, always=True)
    def client_id_from_config(cls, v):  # noqa: N805
        """Get the client_id from the config field."""
        if isinstance(v, dict):
            return v.get("clientId", "")
        elif isinstance(v, str):
            return v
        else:
            raise ValidationError("Invalid client_id")


class IdPsListModel(BaseOutputModel):

    """Model for listing identity providers."""

    idps: List[IdPModel]


class InvitationModel(BaseOutputModel):

    """Model for a single invitation."""

    id: str = Field(..., description="ID of the invitation.")
    email: EmailStr = Field(..., description="Email of the user who is invited.")
    inviter_id: str = Field(..., description="User ID who invited the user matching the id field.")
    created_at: datetime = Field(
        ...,
        description=(
            "The ISO 8601 formatted timestamp representing the creation time of the invitation in UTC."
        ),
    )


class InvitationPayloadModel(BaseOutputModel):

    """Model for a single invitation."""

    invitation: InvitationModel


class InvitationListPayloadModel(BaseOutputModel):

    """Model for listing invitations."""

    invitations: List[InvitationModel]
    total: int


class PermissionModel(BaseOutputModel):

    """Model for a permission."""

    permission_name: str = Field(..., description="Permission name")
    description: str = Field(..., description="Role description")
    resource_server_name: str = Field(..., description="Resource server (API) name this permission is for")
    resource_server_identifier: str = Field(
        ..., description="Resource server (API) identifier that this permission is for"
    )


class RoleModel(BaseOutputModel):

    """Model for a role."""

    id: str = Field(..., description="ID of the role.")
    name: str = Field(..., description="Name of the role.")
    description: str = Field(..., description="Role description.")


class RoleListModel(BaseOutputModel):

    """Model for listing roles."""

    roles: List[RoleModel]
    total: int


class GroupModel(BaseOutputModel):

    """Model for a group."""

    id: str = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    roles: Optional[List[str]] = Field([], description="Role list attached to the group")
    description: Optional[str] = Field(str(), description="Description of the group.")


class GroupListModel(BaseOutputModel):

    """Model for listing groups."""

    groups: List[GroupModel]


class FailureGroupAttached(BaseOutputModel):

    """Model for a group that could not be attached to an user."""

    id: str = Field(..., description="ID of the group that could not have been attached to an user.")
    error: Optional[str] = Field(None, description="Error description.")
    code: Optional[int] = Field(None, description="Error code from the OIDC provider.")


class GroupAttachmentResults(BaseOutputModel):

    """Model for the results of attaching groups to users."""

    successes: Optional[List[str]] = Field([], description="Group IDs that could be attached successfully.")
    failures: Optional[List[FailureGroupAttached]] = Field(
        [], description="Group IDs that could not be attached successfully."
    )


class ClientModel(BaseOutputModel):

    """Model for a client."""

    id: str = Field(..., description="Id of the client represented in the database")
    client_id: str = Field(..., description="ID of the client", alias="clientId")
    name: Optional[str] = Field(str(), description="Name of the client", min_length=1)
    description: Optional[str] = Field(str(), description="Description of the client", max_length=255)
    client_secret: Optional[str] = Field(str(), description="Client secret", alias="clientSecret")


class ClientListModel(BaseOutputModel):

    """Model for listing clients."""

    clients: List[ClientModel]


class OrganizationAttributesModel(BaseModel):

    """Attributes model for the organization."""

    created_at: Optional[Union[datetime, List[str]]] = Field(
        ..., description="Timestamp in which the organization got created."
    )
    logo: Optional[Union[AnyHttpUrl, List[str], str]] = Field(
        str(),
        description="URL of the organization's logo.",
    )
    owner: Optional[str] = Field(None, description="ID of the user who created the organization.")

    @validator("created_at", pre=True, always=True)
    def check_created_at(cls, v):  # noqa: N805
        """Check if the created_at is a list, if so, return the first element."""
        if isinstance(v, list):
            return v[0]
        return v

    @validator("logo", pre=True, always=True)
    def check_logo(cls, v):  # noqa: N805
        """Check if the logo is a list, if so, return the first element."""
        if isinstance(v, list):
            return v[0]
        return v

    @validator("owner", pre=True, always=True)
    def check_owner(cls, v):  # noqa: N805
        """Check if the owner is a list, if so, return the first element."""
        if isinstance(v, list):
            return v[0]
        return v


class OrganizationModel(BaseModel):

    """Model for the organization."""

    id: str = Field(..., description="Organization identifier.")
    name: str = Field(..., description="The name of the organization.")
    display_name: str = Field(..., description="Friendly name for the organization.")
    url: Optional[str] = Field(str(), description="URL of the organization.")
    domains: Optional[List[str]] = Field([], description="List of domains of the organization.")
    attributes: OrganizationAttributesModel


class IsOrgNameAvailableModel(BaseModel):

    """Model for checking if an organization name is available."""

    available: bool = Field(..., description="Whether the organization name is available.")


class IsUserInvited(BaseModel):

    """Model for checking if a user is invited to any organization."""

    invited: bool = Field(..., description="Whether the user is invited or not.")


class DetailModel(BaseModel):

    """Detail model for error responses."""

    detail: str


class CloudAccountModel(BaseModel):

    """Model for a cloud account."""

    id: int = Field(..., description="ID of the cloud account.")
    provider: str = Field(..., description="Provider of the cloud account.")
    name: str = Field(..., description="Name of the cloud account.")
    assisted_cloud_account: bool = Field(
        ..., description="Whether the cloud account is created by the assisted mode."
    )
    description: Optional[str] = Field(None, description="Description of the cloud account.")
    attributes: dict[str, str] = Field(..., description="Attributes of the cloud account.")
    created_at: datetime = Field(..., description="Date and time when the cloud account was created.")
    updated_at: datetime = Field(..., description="Date and time when the cloud account was updated.")
    in_use: Optional[bool] = Field(
        False, description="Artificial field to indicate if the Cloud Account is in use."
    )

    class Config:

        """Configuration class for the model."""

        orm_mode = True


class IamRoleStateEnum(str, enum.Enum):
    """Enum for the state of an IAM role."""

    IN_USE = "IN_USE"
    MALFORMED_ARN = "MALFORMED_ARN"
    MISSING_PERMISSIONS = "MISSING_PERMISSIONS"
    NOT_FOUND_OR_NOT_ACCESSIBLE = "NOT_FOUND_OR_NOT_ACCESSIBLE"
    VALID = "VALID"


class IamRoleState(BaseModel):

    """Model for the state of an IAM role."""

    state: IamRoleStateEnum = Field(
        ...,
        description=(
            "State of the IAM role. "
            "*VALID* indicates the role exists and has the required permissions. "
            "*MALFORMED_ARN* indicates the role ARN is malformed. "
            "*MISSING_PERMISSIONS* indicates the role does not have the required permissions."
        ),
    )


class CloudAccountApiKey(BaseModel):

    """Model for the API key of a cloud account."""

    api_key: str = Field(..., description="API key of the cloud account.")


class SubscriptionModel(SubscriptionRow):

    """Model for a subscription."""

    is_active: bool = Field(..., description="Whether the subscription is active or not.")


class PendingAwsSubscriptionModel(PendingAwsSubscriptionRow):

    """Model for a pending AWS subscription.

    This is replicated from the database schema for consistency across the code.
    """

    class Config:

        """Configuration class for the model."""

        orm_mode = True


class OrganizationFreeTrialsModel(OrganizationFreeTrialsRow):

    """Model for an organization free trial.

    This is replicated from the database schema for consistency across the code.
    """

    class Config:

        """Configuration class for the model."""

        orm_mode = True
