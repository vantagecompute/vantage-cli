"""Core module for storing helper functions for GraphQL operations."""
import asyncio
import base64
import operator
import re
import string
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Type, Union

import boto3
import jsondiff
import strawberry
from fastapi import HTTPException
from httpx import HTTPStatusError, Response
from loguru import logger
from mypy_boto3_cloudformation.type_defs import StackEventTypeDef
from sqlalchemy import String, and_, delete, func, insert, inspect, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ColumnProperty, attributes, relationship, subqueryload
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.expression import Insert, Select, Update
from strawberry.permission import BasePermission

from api.cfn_app import cfn_ops
from api.ec2_app import ec2_ops
from api.graphql_app.types import (
    Cluster,
    ClusterNode,
    ClusterOrderingInput,
    ClusterPartition,
    ClusterQueue,
    ClusterQueueActions,
    ClusterRegion,
    Connection,
    Context,
    Edge,
    Info,
    JSONScalar,
    PageInfo,
    Partition,
    SlurmClusterConfig,
    Storage,
    StorageOrderingInput,
)
from api.identity.management_api import backend_client
from api.schemas.aws import AwsOpsConfig
from api.settings import SETTINGS
from api.sql_app import Base
from api.sql_app import models as db_models
from api.sql_app.enums import (
    ClusterStatusEnum,
    SubscriptionTierClusters,
    SubscriptionTiersNames,
    SubscriptionTierStorageSystems,
    SubscriptionTypesNames,
)
from api.sql_app.schemas import (
    CloudAccountRow,
    NodeRow,
    PartitionInfoRow,
    SubscriptionRow,
)
from api.sql_app.session import create_async_session
from api.sts_app import sts_ops


class HasResourceRequests(BasePermission):

    """Permission class to check if the user's organization has permission to create the requested resources.

    This permission class is intended to be used only by the GraphQL schema, which means only
    cluster and storage resources are going to be checked. The task of checking the allowability
    for inviting users is going to be done in the organization router.

    When inheriting from this class, the following attributes must be set:
    - resource: The SQLAlchemy model that represents the resource.
    - resource_tier_enum: The enum that represents the subscription tier for the resource.
    - subscription_tier_column: The column name that represents the subscription tier for the resource.
        It specifically refers to any attribute present in the
        :class:`api.sql_all.schemas.SubscriptionTierRow` class.

    Example usage:

    .. code-block:: python

            class HasClusterResourceRequests(HasResourceRequests):
                resource = db_models.ClusterModel
                resource_tier_enum = SubscriptionTierClusters
                subscription_tier_column = "clusters"
    """

    message = "The resource creation is blocked because it requires a higher subscription tier."
    error_class = HTTPException
    error_extensions = {"code": "FORBIDDEN"}
    resource: Type[db_models.ClusterModel] | Type[db_models.StorageModel] | None = None
    resource_tier_enum: Type[SubscriptionTierClusters] | Type[SubscriptionTierStorageSystems] | None = None
    subscription_tier_column: str | None = None

    async def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        """Check if the user's organization has permission to create the requested resources."""
        assert (
            self.resource is not None
            and self.resource_tier_enum is not None
            and self.subscription_tier_column is not None
        )
        organization_id = info.context.token_data.organization
        async with info.context.db_session(organization_id) as sess:
            query = (
                select(db_models.SubscriptionModel)
                .where(db_models.SubscriptionModel.organization_id == organization_id)
                .options(subqueryload(db_models.SubscriptionModel.subscription_tier))
                .options(subqueryload(db_models.SubscriptionModel.subscription_type))
            )
            subscription = (await sess.execute(query)).scalar_one_or_none()
            if subscription is None:
                return False

            subscription_data = SubscriptionRow.from_orm(subscription)
            assert subscription_data.subscription_type is not None  # mypy assertion
            assert subscription_data.subscription_tier is not None  # mypy assertion

            if subscription_data.subscription_type.name == SubscriptionTypesNames.aws:
                if (await _count_rows(None, self.resource, sess)) >= self.resource_tier_enum.pro.value:
                    return False
            elif subscription_data.subscription_type.name == SubscriptionTypesNames.cloud:
                if subscription_data.subscription_tier.name == SubscriptionTiersNames.enterprise:
                    return True
                if (await _count_rows(None, self.resource, sess)) >= getattr(
                    subscription_data.subscription_tier, self.subscription_tier_column
                ):
                    return False
        return True


class HasClusterResourceRequests(HasResourceRequests):

    """Check if user's org can create the requested cluster."""

    resource = db_models.ClusterModel
    resource_tier_enum = SubscriptionTierClusters
    subscription_tier_column = "clusters"


class HasStorageResourceRequests(HasResourceRequests):

    """Check if user's org can create the requested storage resource."""

    resource = db_models.StorageModel
    resource_tier_enum = SubscriptionTierStorageSystems
    subscription_tier_column = "storage_systems"


class IsAuthorized(BasePermission):

    """Permission class to check if the user is authorized."""

    message = "User does not have permission to access this resource."
    error_class = HTTPException
    error_extensions = {"code": "FORBIDDEN"}
    permission: str | None = None
    section: Literal["compute", "storage", "notebook"] | None = None

    async def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        """Check if the user is authenticated."""
        assert self.section is not None, "Section must be set internally when using this base class."

        if self.permission is None:
            raise ValueError("Permission must be set internally.")
        decoded_token = await info.context.decoded_token
        assert decoded_token is not None
        permissions = decoded_token.permissions
        return any(permission in permissions for permission in [self.permission, f"{self.section}:admin"])


class ClusterQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query clusters."""

    section = "compute"
    permission = "compute:cluster:read"


class NotebookQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query notebook servers."""

    section = "notebook"
    permission = "notebook:server:read"


class StorageQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query storage."""

    section = "storage"
    permission = "storage:file-system:read"


class SshKeyQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query SSH keys."""

    section = "compute"
    permission = "compute:ssh-keys:read"


class VpcQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query VPCs."""

    section = "compute"
    permission = "compute:vpcs:read"


class SubnetQueryAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to query subnets."""

    section = "compute"
    permission = "compute:subnets:read"


class CreateClusterMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to create clusters."""

    section = "compute"
    permission = "compute:cluster:create"


class CreateNotebookMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to create notebook servers."""

    section = "notebook"
    permission = "notebook:server:create"


class DeleteNotebookMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to delete notebook servers."""

    section = "notebook"
    permission = "notebook:server:delete"


class UpdateClusterMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to update clusters."""

    section = "compute"
    permission = "compute:cluster:update"


class DeleteClusterMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to delete clusters."""

    section = "compute"
    permission = "compute:cluster:delete"


class CreateStorageMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to create storage."""

    section = "storage"
    permission = "storage:file-system:create"


class UpdateStorageMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to update storage."""

    section = "storage"
    permission = "storage:file-system:update"


class DeleteStorageMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to delete storage."""

    section = "storage"
    permission = "storage:file-system:delete"


class MountStorageMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to mount a storage."""

    section = "storage"
    permission = "storage:mount:create"


class UnmountStorageMutationAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to unmount a storage."""

    section = "storage"
    permission = "storage:mount:delete"


class UploadSlurmInfoAuthorization(IsAuthorized):

    """Permission class to check if the user is authorized to upload a Slurm config."""

    section = "compute"
    permission = "compute:slurm-info:upsert"


class AddQueueActionMutationAuthorization(IsAuthorized):
    """Permission class to check if the user is authorized to add a queue action."""

    section = "compute"
    permission = "compute:queue-action:create"


class QueryQueueActionAuthorization(IsAuthorized):
    """Permission class to check if the user is authorized to query queue actions."""

    section = "compute"
    permission = "compute:queue-action:read"


class RemoveQueueActionMutationAuthorization(IsAuthorized):
    """Permission class to check if the user is authorized to remove a queue action."""

    section = "compute"
    permission = "compute:queue-action:delete"


@dataclass
class FetchDataResponse:

    """Dataclass to store records fetched from the database and how many of them indeed exist."""

    total: int
    records: List[db_models.ClusterModel]


async def get_context() -> Context:
    """Fetch the Strawberry context."""
    return Context()


def convert_camel_case(name: str):
    """Convert camel case string to snake case."""
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    name = pattern.sub("_", name).lower()
    return name


def parse_column_and_json_field(
    input_string: str,
    table: Union[
        Type[db_models.ClusterModel],
        Type[db_models.StorageModel],
        Type[db_models.CloudAccountModel],
        Type[db_models.NodeModel],
    ],
) -> tuple[str, str | None]:
    """Parse a string in the format 'column_name.json_field' and extract the column name and JSON field.

    Raises
    ------
        - ValueError: If the JSONB field is nested or the column isn't a JSONB if expected.

    """
    pattern = (
        r"(?P<column>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<field>[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*)"
    )
    match = re.fullmatch(pattern, input_string)

    if match:
        column_name = match.group("column")
        json_field = match.group("field")

        if "." in json_field:
            raise ValueError("More than one JSONB field found. Expected only one.")

        column_attribute = getattr(table, column_name)

        # If the column is a JSONB field, return it
        if isinstance(column_attribute.property, ColumnProperty) and isinstance(
            column_attribute.property.columns[0].type, JSONB
        ):
            return column_name, json_field
        else:
            raise ValueError(f"Column {column_name} is not a JSONB field.")
    else:
        return input_string, None


def aggregate_filters(
    filters: Union[JSONScalar, None],
    table: Union[Type[db_models.ClusterModel], Type[db_models.StorageModel]],
) -> List[BinaryExpression]:
    """Generate a list of where statements based on input filters.

    The following is a list of supported operations:
    * gt - greater than (>)
    * lt - less than (<)
    * ge - greater or equal than (>=)
    * le - less or equal than (<=)
    * eq - equal to (==)
    * ne - not equal to (!=)
    * in - in list
    * contains - contain "a" in "b"

    Examples
    --------
    1. Fetch user whose id is equal to 1 and email is either
    john.doe@omnivector.solutions or jane.doe@omnivector.solutions

    aggregate_filters(
        {
            "id": {"eq": 1},
            "userEmail": {"in": ["john.doe@omnivector.solutions", "jane.doe@omnivector.solutions"]}
        },
        models.Tickets,
    )

    2. Fetch comments whose raw text is equal to "whatever"

    aggregate_filters(
        {
            "rawText": {"eq": "whatever"},
        },
        models.Comments,
    )

    3. Fetch files whose size is grater than 100 bytes

    aggregate_filters(
        {
            "size": {"gt": 200},
        },
        models.Attachments,
    )

    4. Fetch tickets whose title contain the word "problem"

    aggregate_filters(
        {
            "title": {"contains": "problem"},
        },
        models.Tickets,
    )

    5. Fetch data filtered by a JSONB column
    aggregate_filters(
        {
            "attributes.roleArn": {
                "eq": "arn:aws:iam::123456789012:role/foo"
            },
        },
        models.CloudAccountModel,
    )

    6. Fetch data in an array column
    aggregate_filters(
        {
            "partition_names": {
                "contains": ["partition-1", "partition-2"]
            },
        },
        models.NodeModel,
    )

    """
    where_statements: list[BinaryExpression] = []
    if filters is not None:
        for table_column, value in filters.items():
            table_column = convert_camel_case(table_column)
            table_column, json_field = parse_column_and_json_field(table_column, table)
            ops = {
                "gt": operator.gt,
                "lt": operator.lt,
                "ge": operator.ge,
                "le": operator.le,
                "eq": operator.eq,
                "ne": operator.ne,
            }
            for comparison_operator, comparison_value in value.items():
                if json_field is not None:
                    json_column = getattr(table, table_column)[json_field].astext.cast(String)
                    sqlalchemy_binary_expression = ops[comparison_operator](json_column, comparison_value)
                elif comparison_operator == "in":
                    sqlalchemy_binary_expression = getattr(table, table_column).in_(comparison_value)
                elif comparison_operator == "contains" and isinstance(comparison_value, str):
                    # [Reference]
                    # (https://docs.sqlalchemy.org/en/14/core/sqlelement.html#sqlalchemy.sql.expression.ColumnElement.ilike)
                    comparison_value = f"%{comparison_value}%"
                    sqlalchemy_binary_expression = getattr(table, table_column).ilike(comparison_value)
                elif comparison_operator == "contains" and isinstance(comparison_value, list):
                    sqlalchemy_binary_expression = getattr(table, table_column).op("@>")(comparison_value)
                else:
                    sqlalchemy_binary_expression = ops[comparison_operator](
                        getattr(table, table_column), comparison_value
                    )
                where_statements.append(sqlalchemy_binary_expression)

    return where_statements


async def _count_rows(
    filters: Union[JSONScalar, None],
    table: Union[Type[db_models.ClusterModel], Type[db_models.StorageModel]],
    sess: AsyncSession,
) -> int:
    """Count the number of elements in the database based on supplied filters."""
    where_statements = aggregate_filters(filters, table)
    query = select(func.count()).select_from(table).where(and_(*where_statements))

    result = await sess.execute(query)

    return result.scalars().one()


def _build_cursor(_type: Any):
    """Build the GraphQL cursor based on the Strawberry type id."""
    bookid = f"{id(_type)}".encode("utf-8")
    return base64.b64encode(bookid).decode()


async def fetch_user_email_from_context(info: Info) -> str:
    """Fetch the user (requester) email from the context."""
    return (await info.context.decoded_token).email  # type: ignore # pragma: no cover


async def _fetch_data(  # noqa: D417
    info: Info,
    first: int,
    model: Union[
        Type[db_models.ClusterModel],
        Type[db_models.StorageModel],
        Type[db_models.SlurmClusterConfig],
        Type[db_models.PartitionModel],
        Type[db_models.NodeModel],
    ],
    model_relations: List[relationship],
    filters: JSONScalar = None,
    subfilters: JSONScalar = None,
    ordering: Optional[Union[ClusterOrderingInput, StorageOrderingInput]] = None,
    after: int = strawberry.UNSET,
) -> FetchDataResponse:  # pragma: no cover
    """Build the SQLAlchemy query based on common pattern and fetch the data.

    Arguments:
    ---------
        info (Info): Strawberry's Info type from which we access the context.
            [Reference](https://github.com/strawberry-graphql/strawberry/blob/0.149.2/strawberry/types/info.py#L24-L79).
        first (integer): The maximum number of rows to be returned by the SQL query.
            [Reference](https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query.limit).
        model (Type[models.*]): The SQLAlchemy table object that indicates which table will be queried.
            [Reference](../sql_app/models.py).
        model_relations (list[relationship]): List containing all relationships from the model passed
            to the `model` param, e.g. (model=models.Tickets, relationships=[models.Tickets.comments]).
        filters (JSONScalar): Dict containing all filter statements, e.g. {"id": {"eq": 1}}. They are appended
            by the `and` operator.
        subfilters (JSONScalar): Dict containing all filter statements, e.g. {"id": {"eq": 1}}.
            They are appended by the or operator.
        ordering (Optional[Union[ClusterOrderingInput, StorageOrderingInput]]): The ordering field.
        after (integer): The SQL query offset.
            [Reference](https://docs.sqlalchemy.org/en/14/orm/query.html#sqlalchemy.orm.Query.offset).

    This function is not covered by the tests because of the difficulty of mocking the info parameter.
    More specifically, mocking the asynchronous context manager `info.context.db_session` is not an
    easy task and would consume more time than the available for the task.
    [Reference](https://app.clickup.com/t/18022949/PFT-948).

    """
    after = after if after is not strawberry.UNSET else 1
    and_filters = aggregate_filters(filters=filters, table=model)
    or_filters = aggregate_filters(subfilters, table=model)

    async with info.context.db_session(info.context.token_data.organization) as sess:
        total = await _count_rows(filters=filters, table=model, sess=sess)
        query: Select
        query = (
            select(model)
            .where(*and_filters)
            .filter(or_(*or_filters))
            .offset((after - 1) * first)
            .limit(first)
        )
        if ordering is not None:
            query = query.order_by(
                # equivalent of doing Table.id.desc() for example
                getattr(getattr(model, ordering.field.value), ordering.direction.value)()
            )
        for model_relation in model_relations:
            query = query.options(subqueryload(model_relation))
        records = (await sess.execute(query)).scalars().all()

    return FetchDataResponse(total, records)


def _build_edges(
    records: List[
        Union[
            db_models.ClusterModel,
            db_models.StorageModel,
            db_models.SlurmClusterConfig,
            db_models.ClusterQueueActionsModel,
            db_models.QueueModel,
        ]
    ],
    scalar_type: Union[
        Type[Cluster],
        Type[Storage],
        Type[SlurmClusterConfig],
        Type[ClusterNode],
        Type[ClusterPartition],
        Type[Partition],
        Type[ClusterQueueActions],
        Type[ClusterQueue],
    ],
):
    return [Edge(node=scalar_type.from_db_model(record), cursor=_build_cursor(record)) for record in records]


async def build_connection(
    after: int,
    first: int,
    info: Info,
    model: Union[
        Type[db_models.ClusterModel],
        Type[db_models.StorageModel],
        Type[db_models.SlurmClusterConfig],
        Type[db_models.PartitionModel],
        Type[db_models.NodeModel],
        Type[db_models.ClusterQueueActionsModel],
        Type[db_models.QueueModel],
    ],
    scalar_type: Union[
        Type[Cluster],
        Type[Storage],
        Type[SlurmClusterConfig],
        Type[ClusterNode],
        Type[ClusterPartition],
        Type[ClusterQueueActions],
        Type[ClusterQueue],
    ],
    model_relations: List[relationship],
    filters: JSONScalar = None,
    subfilters: JSONScalar = None,
    ordering: Optional[Union[ClusterOrderingInput, StorageOrderingInput]] = None,
) -> Connection:
    """Build the GraphQL connection type."""
    data = await _fetch_data(
        info=info,
        first=first,
        model=model,
        model_relations=model_relations,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        after=after,
    )
    edges = _build_edges(data.records, scalar_type)
    return Connection(
        page_info=PageInfo(
            has_previous_page=after - 1 > 0 if after else False,
            has_next_page=(after - 1 + first) < data.total,
            start_cursor=edges[0].cursor if edges else None,
            end_cursor=edges[-1].cursor if len(edges) > 1 else None,
        ),
        edges=edges,
        total=data.total,
    )


def clean_cluster_name(cluster_name: str) -> str:
    """Clean a given cluster name by removing symbols, spaces, and converting it to lower case."""
    # remove punctuation
    for symbol in string.punctuation:
        cluster_name = cluster_name.replace(symbol, " ")

    # remove possible spaces in the beginning of the string
    cluster_name = cluster_name.strip()

    # remove possibly white spaces in the middle of the string
    cluster_name = " ".join(cluster_name.split())

    # substitute spaces by hyphens
    cluster_name = re.sub(r"\s", "-", cluster_name.lower())
    return cluster_name


def cluster_name_to_client_id(cluster_name: str, organization: str) -> str:
    """Format a given cluster name into a client id string.

    This function must receive a generic cluster name possibly contianing symbols and numbers and
    must return a lower case string admissible to be a client id. Example:

    cluster_name_to_client_id("OSL Cluster", "foo-org")
    #> osl-cluster-foo-org
    cluster_name_to_client_id("OSL Cluster 123456", "boo-org")
    #> osl-cluster-123456-boo-org
    cluster_name_to_client_id("!@#$Cluster", "123-org")
    #> cluster-123-org
    """
    cluster_name = clean_cluster_name(cluster_name)

    return f"{cluster_name}-{organization}"


def mount_post_client_request(
    client_uuid: str,
    client_id: str,
    client_name: str,
    client_description: str,
    client_secret: Optional[str] = None,
):
    """Build the payload required to create a Keycloak client to act as a cluster.

    This client is mainly used for agent authentication purposes.
    """
    return {
        "id": str(client_uuid),
        "clientId": client_id,
        "name": client_name,
        "description": client_description,
        "secret": client_secret,
        "enabled": True,
        "clientAuthenticatorType": "client-secret",
        "redirectUris": ["*"],
        "bearerOnly": False,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": True,
        "publicClient": False,
        "protocol": "openid-connect",
        "fullScopeAllowed": False,
        "protocolMappers": [
            {
                "name": "Permissions",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-client-role-mapper",
                "config": {
                    "multivalued": "true",
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "permissions",
                    "jsonType.label": "String",
                    "usermodel.clientRoleMapping.clientId": client_id,
                },
            },
        ],
        "attributes": {
            "access.token.lifespan": "86400",
            "oauth2.device.authorization.grant.enabled": "true",
            "id.token.signed.response.alg": "RS256",
            "client_credentials.use_refresh_token": "false",
            "access.token.signed.response.alg": "RS256",
            "token.response.type.bearer.lower-case": "false",
        },
    }


def cluster_client_roles_mapping() -> List[Dict[str, str]]:
    """Map all permissions required by a cluster."""
    return [
        # License manager
        {
            "name": "license-manager:feature:read",
            "description": "Allow to read the features in License Manager.",
        },
        {"name": "license-manager:job:delete", "description": "Allow to delete a job in License Manager."},
        {"name": "license-manager:job:create", "description": "Allow to create a job in License Manager."},
        {"name": "license-manager:job:read", "description": "Allow to read the jobs in License Manager."},
        {"name": "license-manager:config:read", "description": "Allow to read the license configurations."},
        {
            "name": "license-manager:booking:delete",
            "description": "Allow to delete a booking in the License Manager.",
        },
        {
            "name": "license-manager:feature:update",
            "description": "Allow to update a feature in License Manager.",
        },
        # Jobbergate
        {
            "name": "jobbergate:job-submissions:update",
            "description": "Allow to update owned job submissions in Jobbergate.",
        },
        {
            "name": "jobbergate:job-submissions:read",
            "description": "Allow to read any job submissions in Jobbergate.",
        },
        {"name": "jobbergate:job-scripts:read", "description": "Allow to read any job script in Jobbergate."},
        {"name": "jobbergate:clusters:read", "description": "Allow to read cluster status in Jobbergate."},
        {
            "name": "jobbergate:clusters:update",
            "description": "Allow to update cluster status in Jobbergate.",
        },
        # Vantage API
        {
            "name": "compute:slurm-info:upsert",
            "description": "Allow to insert/update Slurm information for a cluster.",
        },
        {
            "name": "compute:cluster:read",
            "description": "Allow to view clusters informations.",
        },
        {
            "name": "compute:queue-action:read",
            "description": "Allow to view queue actions.",
        },
        {
            "name": "compute:queue-action:delete",
            "description": "Allow to delete queue actions.",
        },
    ]


async def set_up_cluster_config_on_keycloak(
    *,
    client_uuid: str,
    client_id: str,
    client_name: str,
    client_description: str,
    client_secret: str,
    organization_id: str,
) -> None:
    """Set up the cluster configuration on the Keycloak server.

    It creates a client for the cluster. In sequence, it adds roles to the client
    service account and add the service account user to the organization.
    """
    try:
        # create client on Keycloak
        client_response = await backend_client.post(
            "/admin/realms/vantage/clients",
            json=mount_post_client_request(
                client_uuid=client_uuid,
                client_id=client_id,
                client_name=client_name,
                client_description=client_description,
                client_secret=client_secret,
            ),
        )
        client_response.raise_for_status()

        # create roles for the client on Keycloak
        tasks = [
            backend_client.post(f"/admin/realms/vantage/clients/{client_uuid}/roles", json=role)
            for role in cluster_client_roles_mapping()
        ]
        roles_responses: List[Response] = await asyncio.gather(*tasks)
        for role_response in roles_responses:
            role_response.raise_for_status()

        # fetch the service account user id for the client
        service_account_user_response = await backend_client.get(
            f"/admin/realms/vantage/clients/{client_uuid}/service-account-user"
        )
        service_account_user_response.raise_for_status()
        service_account_user = service_account_user_response.json()
        service_account_user_id = service_account_user.get("id")

        # add service account to organization
        add_service_account_to_organization_response = await backend_client.post(
            f"/admin/realms/vantage/organizations/{organization_id}/members/", content=service_account_user_id
        )
        add_service_account_to_organization_response.raise_for_status()

        # get all roles created above. Needed for fetching their IDs
        available_roles_response = await backend_client.get(
            f"/admin/realms/vantage/users/{service_account_user_id}"
            f"/role-mappings/clients/{client_uuid}/available"
        )
        available_roles_response.raise_for_status()

        # assign all roles to the service account user
        roles = [
            {"id": role.get("id"), "name": role.get("name"), "containerId": role.get("containerId")}
            for role in available_roles_response.json()
        ]
        user_response = await backend_client.post(
            f"/admin/realms/vantage/users/{service_account_user_id}/role-mappings/clients/{client_uuid}",
            json=roles,
        )
        user_response.raise_for_status()
    except HTTPStatusError as err:
        logger.error(
            f"Error while requesting {err.request.url!r}: {err.response.text} - {err.response.status_code}"
        )
        await backend_client.delete(f"/admin/realms/vantage/clients/{client_uuid}")
        raise err


def get_sqlalchemy_model_columns(model: Base) -> List[attributes.InstrumentedAttribute]:
    """Get the SQLAlchemy model columns."""
    return [getattr(model, c_attr.key) for c_attr in inspect(model).mapper.column_attrs]


async def get_role_arn_of_cloud_account(cloud_account_id: int, session: AsyncSession) -> Optional[str]:  # noqa: D417
    """Get the role arn of a cloud account."""
    cloud_account = (
        await session.execute(
            select(db_models.CloudAccountModel).where(db_models.CloudAccountModel.id == cloud_account_id)
        )
    ).scalar_one_or_none()
    if cloud_account is not None:
        cloud_account_data = CloudAccountRow.from_orm(cloud_account)
        return cloud_account_data.attributes.get("role_arn")
    return None


async def is_valid_instance_for_region(info: Info, instance_type: str, region: ClusterRegion) -> bool:
    """Check if the instance type is valid for the given region."""
    organization_id = info.context.token_data.organization
    async with info.context.db_session(organization_id) as sess:
        query = select(db_models.AwsNodeTypesModel).where(
            db_models.AwsNodeTypesModel.instance_type == instance_type,
            db_models.AwsNodeTypesModel.aws_region == region.value,
        )
        result = (await sess.execute(query)).scalar_one_or_none()
        if result is None:
            return False
    return True


async def _update_aws_cluster_status_details(
    db: str, failed_events: list[StackEventTypeDef], cluster_name: str
):
    session = await create_async_session(db, use_cached_engines=False)
    async with session() as sess:
        query = (
            update(db_models.ClusterModel)
            .where(db_models.ClusterModel.name == cluster_name)
            .values(
                creation_status_details=[
                    {
                        "logical_resource_id": event["LogicalResourceId"],
                        "reason": event["ResourceStatusReason"],
                    }
                    for event in failed_events
                ]
            )
        )
        await sess.execute(query)
        await sess.commit()


async def _update_aws_cluster_status(db: str, cluster_name: str, status: ClusterStatusEnum):
    session = await create_async_session(db, use_cached_engines=False)
    async with session() as sess:
        query = (
            update(db_models.ClusterModel)
            .where(db_models.ClusterModel.name == cluster_name)
            .values(status=status)
        )
        await sess.execute(query)
        await sess.commit()


def _get_hosted_zone():
    r53 = boto3.client("route53")
    hosted_zone_id = None
    hosted_zones = r53.list_hosted_zones_by_name(DNSName=SETTINGS.APP_DOMAIN)

    for zone in hosted_zones["HostedZones"]:
        zone_name = zone["Name"].rstrip(".")
        if zone_name == SETTINGS.APP_DOMAIN:
            hosted_zone_id = zone["Id"].split("/")[-1]

    logger.debug(f"Hosted zone found: {hosted_zone_id}. List: {hosted_zones}")
    return hosted_zone_id


def _check_route53_record_exists(dns_name: str, hosted_zone_id: str):
    logger.debug(f"Checking if dns for {dns_name} exist.")
    r53 = boto3.client("route53")
    record_sets = r53.list_resource_record_sets(
        HostedZoneId=hosted_zone_id, StartRecordName=dns_name, StartRecordType="A", MaxItems="1"
    )
    record_sets = record_sets.get("ResourceRecordSets", [])
    if not record_sets:
        return False

    record = record_sets[0]

    if record["Name"].rstrip(".") != dns_name.rstrip(".") or record["Type"] != "A":
        return False

    return True


def _retrieve_dns_informations(region_name: str, role_arn: str, stack_name: str):
    session_credentials, sts = sts_ops.get_session_credentials(role_arn=role_arn, region_name=region_name)
    cfn = cfn_ops._get_cfn_client(session_credentials)
    ec2 = ec2_ops.get_ec2_client(session_credentials)
    jupyterdns = None
    instance_id = None
    instance_ip = None

    resources_response = cfn.describe_stack_resources(StackName=stack_name)
    for res in resources_response["StackResources"]:
        if res["ResourceType"] == "AWS::EC2::Instance":
            instance_id = res.get("PhysicalResourceId", None)
            break

    if instance_id is None:
        return instance_ip, jupyterdns

    instance_response = ec2.describe_instances(InstanceIds=[instance_id])
    instance = instance_response["Reservations"][0]["Instances"][0]
    instance_ip = instance.get("PublicIpAddress", None)

    if instance_ip is None:
        return instance_ip, jupyterdns

    stack = cfn.describe_stacks(StackName=stack_name)["Stacks"][0]
    stack_parameters = stack.get("Parameters", [])
    for param in stack_parameters:
        if param["ParameterKey"] == "JupyterHubDns":
            jupyterdns = param["ParameterValue"]
            break

    return instance_ip, jupyterdns


def _create_jupyter_dns_record(dns_name: str, hosted_zone_id: str, ip_address: str):
    r53 = boto3.client("route53")

    response = r53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": "Auto-created record by deployment system",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": dns_name,
                        "Type": "A",
                        "TTL": 60,
                        "ResourceRecords": [{"Value": ip_address}],
                    },
                }
            ],
        },
    )
    return response


def _monitor_aws_cluster_status_task(
    db: str, region_name: str, role_arn: str, stack_name: str, cluster_name: str
):
    """Monitor the AWS cluster status for a given stack.

    This function monitors the stack to reach two possible states:
    * CREATE_COMPLETE: The stack was created successfully.
    * DELETE_COMPLETE: The stack was deleted successfully.

    If the stack reaches the DELETE_COMPLETE state, the function fetches all events
    matching the CREATE_FAILED event type and updates the AWS cluster status details.
    """
    logger.debug(f"Starting monitoring of AWS cluster status for stack {stack_name}.")
    cfn_config = AwsOpsConfig(region_name=region_name, role_arn=role_arn)
    stack_id = cfn_ops.get_stack_id(stack_name=stack_name, cfn_config=cfn_config)
    assert stack_id is not None

    while True:
        stack_status = cfn_ops.get_stack_status(stack_name=stack_id, cfn_config=cfn_config)
        if stack_status == "CREATE_COMPLETE":
            logger.debug(f"Stack {stack_name} created successfully.")
            asyncio.run(_update_aws_cluster_status(db, cluster_name, ClusterStatusEnum.ready))
            logger.debug(
                f"AWS cluster status updated for stack {stack_name} with status {ClusterStatusEnum.ready}."
            )
            break
        elif stack_status == "CREATE_IN_PROGRESS":
            hosted_zone_id = _get_hosted_zone()
            if hosted_zone_id is not None:
                instance_ip, jupyter_dns = _retrieve_dns_informations(
                    region_name=region_name, role_arn=role_arn, stack_name=stack_name
                )
                if instance_ip is not None and jupyter_dns is not None:
                    record_exists = _check_route53_record_exists(
                        dns_name=jupyter_dns, hosted_zone_id=hosted_zone_id
                    )

                    if not record_exists:
                        logger.debug(
                            f"Creating Dns record for {stack_name} stack. {instance_ip}, {jupyter_dns}, {hosted_zone_id}"  # noqa
                        )
                        _create_jupyter_dns_record(
                            ip_address=instance_ip, dns_name=jupyter_dns, hosted_zone_id=hosted_zone_id
                        )

            time.sleep(SETTINGS.MONITOR_AWS_CLUSTER_STATUS_INTERVAL)
            continue
        elif stack_status == "DELETE_COMPLETE":
            logger.warning(f"Stack {stack_name} deleted successfully.")
            failed_events = cfn_ops.get_create_failed_events(stack_name=stack_id, cfn_config=cfn_config)
            asyncio.run(_update_aws_cluster_status_details(db, failed_events, cluster_name))
            asyncio.run(_update_aws_cluster_status(db, cluster_name, ClusterStatusEnum.failed))
            logger.debug(
                f"AWS cluster status updated for stack {stack_name} with status {ClusterStatusEnum.failed}."
            )
            break
        else:
            logger.debug(f"Current status of stack {stack_name}: {stack_status}")
        time.sleep(SETTINGS.MONITOR_AWS_CLUSTER_STATUS_INTERVAL)


def monitor_aws_cluster_status(db: str, region_name: str, role_arn: str, stack_name: str, cluster_name: str):
    """Monitor the AWS cluster status by checking the CloudFormation stack."""
    thread = threading.Thread(
        target=_monitor_aws_cluster_status_task,
        args=(db, region_name, role_arn, stack_name, cluster_name),
    )
    thread.start()


async def upsert_slurm_information(
    config: dict[Any, Any],
    client_id: str,
    model: Type[db_models.SlurmClusterConfig]
    | Type[db_models.AllPartitionInfo]
    | Type[db_models.AllNodeInfo]
    | Type[db_models.AllQueueInfo],
    session: AsyncSession,
) -> None:
    """Upsert Slurm information into the database."""
    query: Insert | Select | Update

    query = select(db_models.ClusterModel.name).where(db_models.ClusterModel.client_id == client_id)
    # should purposely raise NoResultFound if there's no cluster matching the query
    cluster_name: str = (await session.execute(query)).scalar_one()

    query = select(model.info).where(model.cluster_name == cluster_name)
    current_info: dict[Any, Any] | None = (await session.execute(query)).scalar_one_or_none()
    if current_info is None:
        query = insert(model).values(
            cluster_name=cluster_name,
            info=jsondiff.patch({}, config, marshal=True),
        )
    else:
        query = (
            update(model)
            .where(model.cluster_name == cluster_name)
            .values(info=jsondiff.patch(current_info, config, marshal=True))
        )

    await session.execute(query)
    await session.commit()


async def break_out_slurm_information(
    source_model: Type[db_models.AllPartitionInfo]
    | Type[db_models.AllNodeInfo]
    | Type[db_models.AllQueueInfo],
    target_model: Type[db_models.PartitionModel] | Type[db_models.NodeModel] | Type[db_models.QueueModel],
    organization_id: str,
    client_id: str,
):
    """Break out the Slurm information from the database by inserting each entity in a separated table."""
    upsert_stmt: Insert | Update

    logger.debug(f"Breaking out Slurm information for client {client_id}")
    write_session = await create_async_session(organization_id, use_cached_engines=False)
    read_session = await create_async_session(organization_id, use_cached_engines=False, read_only=True)
    async with write_session() as wsess, read_session() as rsess:
        subquery = (
            select(db_models.ClusterModel.name)
            .where(db_models.ClusterModel.client_id == client_id)
            .scalar_subquery()
        )
        stmt = select(source_model).where(source_model.cluster_name == subquery)
        result = await rsess.execute(stmt)
        scalar_row: db_models.AllNodeInfo | db_models.AllPartitionInfo | db_models.AllQueueInfo | None = (
            result.scalar_one_or_none()
        )  # noqa

        if scalar_row is None:
            return

        entities: dict[str, dict[str, str]] = scalar_row.info

        logger.debug(f"Upserting entities {list(entities.keys())} for client {client_id}")
        for entity_name, info_dict in entities.items():
            select_stmt = select(target_model.info).where(
                target_model.cluster_name == scalar_row.cluster_name,
                target_model.name == entity_name,
            )
            current_info: dict[Any, Any] | None = (await rsess.execute(select_stmt)).scalar_one_or_none()
            if current_info is None:
                common_values = {
                    "cluster_name": scalar_row.cluster_name,
                    "name": entity_name,
                    "info": info_dict,
                }
                if target_model is db_models.NodeModel:
                    common_values["partition_names"] = (info_dict.get("Partitions", "") or "").split(",")
                upsert_stmt = insert(target_model).values(**common_values)
            else:
                common_values = {"info": info_dict}
                if target_model is db_models.NodeModel:
                    common_values["partition_names"] = (info_dict.get("Partitions", "") or "").split(",")
                upsert_stmt = (
                    update(target_model)
                    .where(
                        target_model.cluster_name == scalar_row.cluster_name,
                        target_model.name == entity_name,
                    )
                    .values(**common_values)
                )
            await wsess.execute(upsert_stmt)

        # clean up entities that are not present in the current info
        logger.debug(f"Cleaning up entities for client {client_id}")
        delete_stmt = delete(target_model).where(
            target_model.cluster_name == scalar_row.cluster_name,
            ~target_model.name.in_(entities.keys()),
        )
        await wsess.execute(delete_stmt)
        await wsess.commit()

    logger.debug(f"Breaking out Slurm information for client {client_id} completed")


def threaded_break_out_slurm_information(
    source_model: Type[db_models.AllPartitionInfo]
    | Type[db_models.AllNodeInfo]
    | Type[db_models.AllQueueInfo],
    target_model: Type[db_models.PartitionModel] | Type[db_models.NodeModel] | Type[db_models.QueueModel],
    organization_id: str,
    client_id: str,
):
    """Extract and process Slurm job information in a thread-safe manner.

    The purpose of this function is to call the function `break_out_slurm_information` using asyncio.
    This function should be used for multi threading purposes where the logic must be executed after
    the main thread has finished its execution.
    """
    asyncio.run(break_out_slurm_information(source_model, target_model, organization_id, client_id))


async def get_partitions_and_node_info(partitions: list[Partition], sess: AsyncSession):
    """Get the partitions info and node info for a list of partition."""
    for index, partition in enumerate(partitions):
        query: Select = select(db_models.NodeModel).where(
            and_(
                db_models.NodeModel.partition_names.any(partition.name),
                db_models.NodeModel.cluster_name == partition.cluster_name,
            )
        )
        nodes = (await sess.execute(query)).scalars().all()

        query = select(db_models.PartitionModel).where(
            and_(
                db_models.PartitionModel.name == partition.name,
                db_models.PartitionModel.cluster_name == partition.cluster_name,
            )
        )
        partition_infos = (await sess.execute(query)).scalars().one_or_none()

        nodes = [ClusterNode(**NodeRow.from_orm(node).dict()) for node in nodes]
        if partition_infos is not None:
            partition_infos = ClusterPartition(**PartitionInfoRow.from_orm(partition_infos).dict())

        partitions[index].nodes_info = nodes
        partitions[index].partition_infos = partition_infos

    return partitions


def delete_dns_record(client_id: str):
    """Delete the DNS record for the given DNS name."""
    r53 = boto3.client("route53")
    hosted_zone_id = _get_hosted_zone()
    if SETTINGS.STAGE == "production":
        dns_name = f"{client_id}.{SETTINGS.APP_DOMAIN}"
    else:
        dns_name = f"{client_id}.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}"

    logger.debug(f"Deleting DNS record for {dns_name} in hosted zone {hosted_zone_id}")
    dns_name_fqdn = dns_name if dns_name.endswith(".") else dns_name + "."

    # Retrieve the record
    record_sets = r53.list_resource_record_sets(
        HostedZoneId=hosted_zone_id, StartRecordName=dns_name_fqdn, StartRecordType="A", MaxItems="1"
    )

    record = record_sets["ResourceRecordSets"][0]

    if record["Name"] != dns_name_fqdn or record["Type"] != "A":
        raise ValueError(f"No matching 'A' record found for {dns_name_fqdn}")

    response = r53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": f"Deleting DNS record for cluster {client_id}",
            "Changes": [
                {
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": dns_name,
                        "Type": "A",
                        "TTL": 60,
                        "ResourceRecords": record["ResourceRecords"],
                    },
                }
            ],
        },
    )
    logger.debug(f"Delete record response: {response}")
    return response
