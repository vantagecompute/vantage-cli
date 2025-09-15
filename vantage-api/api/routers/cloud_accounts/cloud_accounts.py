"""Cloud accounts endpoints."""

import re
import uuid

from armasec import TokenPayload
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy import String, delete, func, insert, select, update
from sqlalchemy.orm import subqueryload
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.expression import Delete, Insert, Select

from api.body.input import CreateCloudAccountModel, UpdateCloudAccountModel
from api.body.output import (
    CloudAccountApiKey,
    CloudAccountModel,
    IamRoleState,
    IamRoleStateEnum,
    MessageModel,
)
from api.iam_app import iam_ops
from api.routers.cloud_accounts.helpers import ListCloudAccountsFieldChecker
from api.settings import SETTINGS
from api.sql_app import models
from api.sql_app.enums import CloudAccountEnum
from api.sql_app.session import create_async_session
from api.utils import response
from api.utils.helpers import unpack_organization_id_from_token

router = APIRouter()


@router.get(
    "/cloud_accounts",
    response_model=list[CloudAccountModel],
    responses={
        200: {
            "description": "List of cloud accounts.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "provider": "aws",
                            "name": "my-aws-account",
                            "description": "My AWS account",
                            "attributes": {
                                "role_arn": "arn:aws:iam::123456789012:role/eksctl-foo-cluster-nodegroup-foo-ng-NodeInstanceRole-1GJGJGJGJGJGJ"  # noqa: E501
                            },
                            "created_at": "2021-07-05T15:00:00.000Z",
                            "updated_at": "2021-07-05T15:00:00.000Z",
                        }
                    ]
                }
            },
        }
    },
)
async def list_cloud_accounts(
    search: str | None = Query(None, description="Search value for fetching cloud accounts by name."),
    after: int = Query(0, ge=0, description="First index to be returned."),
    max: int = Query(50, ge=1, description="Maximum number of results returned."),
    sort_field: None | str = Depends(ListCloudAccountsFieldChecker()),
    sort_ascending: bool = Query(True, description="Whether to sort ascending or not"),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """List cloud accounts."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    session = await create_async_session(organization_id)
    async with session() as sess:
        query = (
            select(models.CloudAccountModel)
            .options(subqueryload(models.CloudAccountModel.storage))
            .options(subqueryload(models.CloudAccountModel.cluster))
        )

        if search:
            query = query.filter(models.CloudAccountModel.name.ilike(f"%{search}%"))
        if sort_field:
            sort_field_attr: InstrumentedAttribute = getattr(models.CloudAccountModel, sort_field)
            if sort_ascending:
                query = query.order_by(sort_field_attr.asc())
            else:
                query = query.order_by(sort_field_attr.desc())
        query = query.offset(after).limit(max)
        cloud_account_rows = (await sess.execute(query)).scalars().all()

        cloud_accounts = []
        for ca in cloud_account_rows:
            cloud_account = CloudAccountModel.from_orm(ca)
            cloud_account.in_use = len(ca.storage) + len(ca.cluster) > 0
            cloud_accounts.append(cloud_account)

        return cloud_accounts


@router.get(
    "/cloud_accounts/check-iam-role/{role_arn:path}",
    responses={
        200: {"model": IamRoleState, "description": "IAM role state well defined."},
        400: {"description": "Missing organization in the token.", "model": MessageModel},
    },
    dependencies=[Depends(SETTINGS.GUARD.lockdown())],
)
async def check_iam_role(
    role_arn: str = Path(..., description="IAM role ARN."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Check the state of the supplied IAM role."""
    if not re.match(r"arn:aws:iam::[0-9]{12}:role\/[a-zA-Z0-9_+=,.@-]{1,64}$", role_arn):
        return response.success(IamRoleState(state=IamRoleStateEnum.MALFORMED_ARN).dict())
    role_state = await iam_ops.check_iam_role_state(role_arn)

    if role_state is not IamRoleStateEnum.VALID:
        return response.success(IamRoleState(state=role_state).dict())

    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    session = await create_async_session(organization_id)
    async with session() as sess:
        query = select(models.CloudAccountModel).filter(
            func.cast(models.CloudAccountModel.attributes["role_arn"], String).ilike(f"%{role_arn}%")
        )
        cloud_account_row = (await sess.execute(query)).scalar_one_or_none()
        if cloud_account_row is not None:
            return response.success(IamRoleState(state=IamRoleStateEnum.IN_USE).dict())

    return response.success(IamRoleState(state=role_state).dict())


@router.get(
    "/cloud_accounts/{role_arn:path}",
    responses={
        200: {
            "description": "Cloud account retrieved. Only a single object will be returned",
            "model": CloudAccountModel,
        },
        404: {"description": "No cloud account found.", "model": MessageModel},
    },
)
async def get_cloud_account_by_role_arn(
    role_arn: str = Path(..., description="Cloud account role ARN."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Get cloud account by role ARN."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    session = await create_async_session(organization_id)
    async with session() as sess:
        query = (
            select(models.CloudAccountModel)
            .filter(func.cast(models.CloudAccountModel.attributes["role_arn"], String).ilike(f"%{role_arn}%"))
            .options(subqueryload(models.CloudAccountModel.storage))
            .options(subqueryload(models.CloudAccountModel.cluster))
        )
        cloud_account_row = (await sess.execute(query)).scalar()
        if not cloud_account_row:
            return response.not_found(
                MessageModel(message="No cloud account was found with the given role ARN").dict()
            )
        cloud_account = CloudAccountModel.from_orm(cloud_account_row)
        cloud_account.in_use = len(cloud_account_row.storage) + len(cloud_account_row.cluster) > 0
        return response.success(cloud_account.dict())


@router.post(
    "/cloud_accounts",
    responses={
        201: {
            "description": "Cloud account created.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "provider": "aws",
                        "name": "my-aws-account",
                        "description": "My AWS account",
                        "attributes": {
                            "role_arn": "arn:aws:iam::123456789012:role/eksctl-foo-cluster-nodegroup-foo-ng-NodeInstanceRole-1GJGJGJGJGJGJ"  # noqa: E501
                        },
                        "created_at": "2021-07-05T15:00:00.000Z",
                        "updated_at": "2021-07-05T15:00:00.000Z",
                    }
                }
            },
        },
        409: {"description": "Cloud account already exists.", "model": MessageModel},
        403: {"description": "Forbidden access due to bad API key.", "model": MessageModel},
    },
)
async def create_cloud_account(
    body: CreateCloudAccountModel,
):
    """Create cloud account."""
    if body.assisted_cloud_account is False:
        # TODO: verify the role permissions here
        pass

    session = await create_async_session(body.organization_id)
    async with session() as sess:
        query: Select | Insert | Delete

        query = select(models.CloudAccountApiKeyModel).where(
            models.CloudAccountApiKeyModel.api_key == body.api_key,
            models.CloudAccountApiKeyModel.organization_id == body.organization_id,
        )
        api_key_row = (await sess.execute(query)).scalar_one_or_none()
        if not api_key_row:
            return response.forbidden(MessageModel(message="Bad API key").dict())

        query = select(models.CloudAccountModel).filter(models.CloudAccountModel.name == body.name)
        cloud_account_row = (await sess.execute(query)).scalar()
        if cloud_account_row:
            return response.conflict(MessageModel(message="Cloud account already exists").dict())

        cloud_account_row_data = {
            "name": body.name,
            "description": body.description,
            "attributes": {"role_arn": body.role_arn},
            "provider": CloudAccountEnum.aws,
            "assisted_cloud_account": body.assisted_cloud_account,
        }
        query = (
            insert(models.CloudAccountModel)
            .values(cloud_account_row_data)
            .returning(models.CloudAccountModel)
        )
        cloud_account_row = (await sess.execute(query)).fetchone()

        query = delete(models.CloudAccountApiKeyModel).where(
            models.CloudAccountApiKeyModel.api_key == body.api_key
        )
        await sess.execute(query)

        await sess.commit()

        return response.created(CloudAccountModel.from_orm(cloud_account_row).dict())


@router.patch(
    "/cloud_accounts/{cloud_account_id}",
    responses={
        200: {
            "description": "Cloud account updated.",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "provider": "aws",
                        "name": "my-aws-account",
                        "description": "My AWS account",
                        "attributes": {
                            "role_arn": "arn:aws:iam::123456789012:role/eksctl-foo-cluster-nodegroup-foo-ng-NodeInstanceRole-1GJGJGJGJGJGJ"  # noqa: E501
                        },
                        "created_at": "2021-07-05T15:00:00.000Z",
                        "updated_at": "2021-07-05T15:00:00.000Z",
                    }
                }
            },
            "model": CloudAccountModel,
        },
        404: {"description": "Cloud account not found.", "model": MessageModel},
    },
)
async def update_cloud_account_description(
    body: UpdateCloudAccountModel,
    cloud_account_id: int = Path(..., description="Cloud account ID."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:cloud-accounts:update")),
):
    """Update cloud account description."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    session = await create_async_session(organization_id)
    async with session() as sess:
        cloud_account_row = (
            await sess.execute(
                select(models.CloudAccountModel).filter(models.CloudAccountModel.id == cloud_account_id)
            )
        ).scalar()
        if not cloud_account_row:
            return response.not_found(MessageModel(message="Cloud account not found").dict())
        query = (
            update(models.CloudAccountModel)
            .values({"description": body.description})
            .where(models.CloudAccountModel.id == cloud_account_id)
            .returning(models.CloudAccountModel)
        )
        cloud_account_row = (await sess.execute(query)).fetchone()
        await sess.commit()
        return response.success(CloudAccountModel.from_orm(cloud_account_row).dict())


@router.delete(
    "/cloud_accounts/{cloud_account_id}",
    responses={
        204: {"description": "Cloud account deleted."},
        404: {"description": "Cloud account not found.", "model": MessageModel},
        400: {"description": "When the cloud account is being in use.", "model": MessageModel},
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_cloud_account(
    cloud_account_id: int = Path(..., description="Cloud account ID."),
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:cloud-accounts:delete")),
):
    """Delete cloud account."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    session = await create_async_session(organization_id)
    async with session() as sess:
        cloud_account_row = (
            await sess.execute(
                select(models.CloudAccountModel)
                .filter(models.CloudAccountModel.id == cloud_account_id)
                .options(subqueryload(models.CloudAccountModel.storage))
                .options(subqueryload(models.CloudAccountModel.cluster))
            )
        ).scalar()
        if not cloud_account_row:
            return response.not_found(
                MessageModel(message="No cloud account was found with the given ID").dict()
            )

        if len(cloud_account_row.storage) + len(cloud_account_row.cluster) > 0:
            return response.bad_request(
                MessageModel(message="The Cloud Account is being used by either storage or cluster.").dict()
            )

        cloud_account_row_data = CloudAccountModel.from_orm(cloud_account_row)
        if cloud_account_row_data.assisted_cloud_account is True:
            # TODO: logic to delete the cloudformation stack
            # WAITING ON: integration with the cluster section and the storage section
            # [PENG-1823](https://app.clickup.com/t/18022949/PENG-1823)
            # [PENG-1800](https://app.clickup.com/t/18022949/PENG-1800)
            pass

        await sess.delete(cloud_account_row)
        await sess.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cloud_accounts/api-key",
    responses={
        200: {"model": CloudAccountApiKey, "description": "API key fetched successfully."},
        400: {"model": MessageModel, "description": "Organization not found in token."},
    },
)
async def create_api_key_for_cloud_account(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:cloud-accounts:create")),
):
    """Create an API key for the cloud account."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    api_key = uuid.uuid4().hex

    session = await create_async_session(organization_id)
    async with session() as sess:
        query = insert(models.CloudAccountApiKeyModel).values(
            api_key=api_key, organization_id=organization_id
        )
        await sess.execute(query)
        await sess.commit()

    return response.success(CloudAccountApiKey(api_key=api_key).dict())
