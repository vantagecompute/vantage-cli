"""Core module for defining the subscriptions router."""
from datetime import datetime, timedelta, timezone

from armasec import TokenPayload
from fastapi import APIRouter, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import delete, insert, select
from sqlalchemy.sql.expression import Delete, Insert, Select

from api.body.input import FinalizeAwsSubscriptionModel
from api.body.output import MessageModel
from api.body.output import (
    PendingAwsSubscriptionModel as PendingAwsSubscriptionModelOutput,
)
from api.body.output import (
    SubscriptionModel as SubscriptionModelOutput,
)
from api.metering_mktplace_app.metering_mktplace_ops import get_metering_mkt_client
from api.routers.subscriptions import helpers
from api.settings import SETTINGS
from api.sql_app.enums import SubscriptionTiersNames, SubscriptionTypesNames
from api.sql_app.models import OrganizationFreeTrialsModel, PendingAwsSubscriptionsModel, SubscriptionModel
from api.sql_app.schemas import PendingAwsSubscriptionRow, SubscriptionRow
from api.sql_app.session import async_session
from api.utils import response
from api.utils.helpers import unpack_organization_id_from_token

router = APIRouter()


@router.get(
    "/subscriptions/aws-subscription/pending",
    responses={
        404: {"description": "No pending AWS subscription found.", "model": MessageModel},
        200: {
            "description": "Return the pending AWS subscription.",
            "model": PendingAwsSubscriptionModelOutput,
        },
        400: {"description": "Organization not found in token.", "model": MessageModel},
    },
)
async def get_pending_aws_subscription(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Return the pending AWS subscription."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        query = select(PendingAwsSubscriptionsModel).where(
            PendingAwsSubscriptionsModel.organization_id == organization_id
        )
        pending_aws_subscription = (await sess.execute(query)).scalar_one_or_none()
        if pending_aws_subscription is None:
            return response.not_found(MessageModel(message="No pending AWS subscription found").dict())
        return response.success(PendingAwsSubscriptionModelOutput.from_orm(pending_aws_subscription).dict())


@router.get(
    "/subscriptions/free-trial/check-availability",
    responses={
        200: {
            "description": "Successful check if the organization has a free trial available.",
            "content": {
                "application/json": {
                    "free-trial-available": {"free_trial_available": True},
                    "free-trial-not-available": {"free_trial_available": False},
                }
            },
        },
        400: {"description": "Organization not found in token.", "model": MessageModel},
    },
)
async def get_organization_free_trial(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Return if the organization has a free trial available.

    If there's an entry in the organization_free_trials table, then the
    organization doesn't have a free trial available, otherwise, it does.
    """
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        query = select(OrganizationFreeTrialsModel).where(
            OrganizationFreeTrialsModel.organization_id == organization_id
        )
        organization_free_trial = (await sess.execute(query)).scalar_one_or_none()
        return response.success({"free_trial_available": organization_free_trial is None})


@router.post(
    "/subscriptions/free-trial",
    responses={
        201: {"description": "Free trial created.", "model": SubscriptionModelOutput},
        400: {"description": "Organization not found in token.", "model": MessageModel},
        409: {"description": "Organization already has a free trial subscription.", "model": MessageModel},
    },
)
async def create_organization_free_trial(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Create a new free trial for an organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        query: Select | Insert

        # verify if the organization already has a free trial
        query = select(OrganizationFreeTrialsModel).where(
            OrganizationFreeTrialsModel.organization_id == organization_id
        )
        organization_free_trial = (await sess.execute(query)).scalar_one_or_none()
        if organization_free_trial is not None:
            return response.conflict(MessageModel(message="Organization already has a free trial").dict())

        type_id = await helpers.get_type_id_by_name(sess, SubscriptionTypesNames.cloud)
        tier_id = await helpers.get_tier_id_by_name(sess, SubscriptionTiersNames.starter)

        # create a free trial for the organization
        query = (
            insert(SubscriptionModel)
            .values(
                {
                    "organization_id": organization_id,
                    "type_id": type_id,
                    "tier_id": tier_id,
                    "detail_data": {},
                    "created_at": datetime.now(tz=timezone.utc),
                    "expires_at": datetime.now(tz=timezone.utc) + timedelta(days=14),
                    "is_free_trial": True,
                }
            )
            .returning(SubscriptionModel.id)
        )
        subscription_id: int = (await sess.execute(query)).scalar_one()

        # insert the organization into the organization_free_trials table
        query = insert(OrganizationFreeTrialsModel).values({"organization_id": organization_id})
        await sess.execute(query)
        await sess.commit()

    async with async_session(organization_id) as sess:
        subscription = await helpers.get_subscription_by_id(sess, subscription_id)
        assert subscription is not None
        subscription_data = SubscriptionRow.from_orm(subscription)

    return response.created(SubscriptionModelOutput(is_active=True, **subscription_data.dict()).dict())


@router.get(
    "/subscriptions/my",
    responses={
        status.HTTP_200_OK: {
            "description": "Return the subscription for the current user's organization.",
            "model": SubscriptionModelOutput,
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "organization_id": "4c3b2959-739c-4c42-964e-0ad70572127f",
                        "type_id": 2,
                        "tier_id": 3,
                        "detail_data": {
                            "product_code": "XA13VSDU926V",
                            "customer_identifier": 123,
                            "customer_aws_account_id": 201598653201,
                        },
                        "created_at": "2024-02-13T15:41:07.533400+00:00",
                        "is_free_trial": True,
                        "subscription_type": {"id": 2, "name": "aws"},
                        "subscription_tier": {"id": 3, "name": "teams", "seats": 10},
                        "is_active": False,
                    }
                }
            },
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized."},
        status.HTTP_400_BAD_REQUEST: {"description": "Organization not found in token."},
        status.HTTP_404_NOT_FOUND: {"description": "No subscription found.", "model": MessageModel},
    },
)
async def get_user_organization_subscription(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Return the subscription for the current user's organization."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        subscription = await helpers.get_subscription_by_organization_id(sess, organization_id)
        if subscription is None:
            return response.not_found(MessageModel(message="No subscription found").dict())

        subscription_data = SubscriptionRow.from_orm(subscription)

        if subscription_data.expires_at is not None:
            is_active = subscription_data.expires_at > datetime.now(tz=timezone.utc)
        else:
            is_active = True

    return response.success(SubscriptionModelOutput(is_active=is_active, **subscription_data.dict()).dict())


@router.get(
    "/subscriptions/my/is-active",
    responses={
        status.HTTP_200_OK: {
            "description": "Return if the subscription for the current user's organization is active.",
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized."},
        status.HTTP_400_BAD_REQUEST: {"description": "Organization not found in token."},
        status.HTTP_402_PAYMENT_REQUIRED: {"description": "Subscription is expired."},
    },
)
async def check_if_subscription_is_active(
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown()),
):
    """Verify if the subscription for a given tenant is active or not.

    Essentially, this endpoint is used for 3rd party services to verify whether or not
    a subscription is active for an organization. The payload itself has no value since
    the endpoint returns a 200 status code if the subscription is active and a 4xx status
    if it's not. This is intended to be used exclusively for checking whether or not the
    3rd party software should allow the user to access the service.
    """
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        subscription = await helpers.get_subscription_by_organization_id(sess, organization_id)
        if subscription is None:
            return response.not_found(MessageModel(message="No subscription found").dict())

        subscription_data = SubscriptionRow.from_orm(subscription)

        if subscription_data.expires_at is not None:
            is_active = subscription_data.expires_at > datetime.now(tz=timezone.utc)
        else:
            is_active = True

    if is_active:
        return response.success({})
    return response.payment_required({})


@router.post(
    "/subscriptions/aws-subscription/initialize",
    status_code=status.HTTP_303_SEE_OTHER,
    response_class=RedirectResponse,
    responses={
        status.HTTP_303_SEE_OTHER: {"description": "Redirect to the new endpoint."},
        status.HTTP_400_BAD_REQUEST: {
            "description": (
                "One of the following: "
                "the *x-amzn-marketplace-token* token has expired, "
                "internal service error in the AWS API, "
                "the *x-amzn-marketplace-token* token is invalid, "
                "too many requests in the AWS API, or "
                "the AWS API is disabled."
            ),
            "model": MessageModel,
        },
    },
)
async def initialize_aws_subscription(
    x_amzn_marketplace_token: str = Form(
        ...,
        description="AWS Marketplace token.",
        alias="x-amzn-marketplace-token",
        media_type="application/x-www-form-urlencoded",
    ),
):
    """Initialize the AWS subscription.

    Note that the response code is set to 303 to respect the fact
    that the response is a redirect to another method (GET).
    [Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/303)
    """
    mkt_client = get_metering_mkt_client()

    try:
        resolve_customer_response = mkt_client.resolve_customer(RegistrationToken=x_amzn_marketplace_token)
    except mkt_client.exceptions.ExpiredTokenException:
        return response.bad_request(
            MessageModel(message="The token has expired", error="ExpiredTokenException").dict()
        )
    except mkt_client.exceptions.InternalServiceErrorException as e:
        return response.bad_request(
            MessageModel(message=str(e), error="InternalServiceErrorException").dict()
        )
    except mkt_client.exceptions.InvalidTokenException:
        return response.bad_request(
            MessageModel(message="The token is invalid", error="InvalidTokenException").dict()
        )
    except mkt_client.exceptions.ThrottlingException:
        return response.bad_request(
            MessageModel(message="Too many requests in the AWS API", error="ThrottlingException").dict()
        )
    except mkt_client.exceptions.DisabledApiException:
        return response.bad_request(
            MessageModel(message="The AWS API is disabled", error="DisabledApiException").dict()
        )

    product_code = resolve_customer_response["ProductCode"]
    customer_identifier = resolve_customer_response["CustomerIdentifier"]
    customer_aws_account_id = resolve_customer_response["CustomerAWSAccountId"]

    # this dummy endpoint is needed for local testing purposes,
    # otherwise it'd be impossible to verify the endpoint's behaviour
    # during development, specifically the redirection and the cookies
    if SETTINGS.TEST_ENV:
        endpoint_response = RedirectResponse(
            url="http://localhost:8080/admin/management/subscriptions/aws-subscription/dummy-confirm",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        cookie_domain = "localhost"
    elif SETTINGS.STAGE == "production":
        endpoint_response = RedirectResponse(
            url=f"https://app.{SETTINGS.APP_DOMAIN}", status_code=status.HTTP_303_SEE_OTHER
        )
        cookie_domain = SETTINGS.APP_DOMAIN
    else:
        endpoint_response = RedirectResponse(
            url=f"https://app.{SETTINGS.STAGE}.{SETTINGS.APP_DOMAIN}", status_code=status.HTTP_303_SEE_OTHER
        )
        cookie_domain = SETTINGS.APP_DOMAIN

    endpoint_response.set_cookie(key="product_code", value=product_code, domain=cookie_domain)
    endpoint_response.set_cookie(key="customer_identifier", value=customer_identifier, domain=cookie_domain)
    endpoint_response.set_cookie(
        key="customer_aws_account_id", value=customer_aws_account_id, domain=cookie_domain
    )

    return endpoint_response


@router.post(
    "/subscriptions/aws-subscription/finalize",
    responses={
        status.HTTP_201_CREATED: {
            "description": "Pending AWS subscription created.",
            "model": PendingAwsSubscriptionModelOutput,
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Organization not found in token.",
            "model": MessageModel,
        },
        status.HTTP_409_CONFLICT: {
            "description": "The organization already has a pending AWS subscription.",
            "model": MessageModel,
        },
    },
)
async def finalize_aws_subscription(
    body: FinalizeAwsSubscriptionModel,
    decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown("admin:subscriptions:create")),
):
    """Finalize the AWS subscription by creating a pending subscription."""
    try:
        organization_id = unpack_organization_id_from_token(decoded_token)
    except AssertionError:
        return response.bad_request(MessageModel(message="Organization not found in token").dict())

    async with async_session(organization_id) as sess:
        query: Insert | Select | Delete
        pending_aws_subscription = await helpers.get_pending_aws_subscription_by_organization_id(
            sess, organization_id
        )
        if pending_aws_subscription is not None:
            return response.conflict(
                MessageModel(message="The organization already has a pending AWS subscription.").dict()
            )

        # check if the organization has a free trial subscription
        query = select(SubscriptionModel.id).where(
            SubscriptionModel.organization_id == organization_id, SubscriptionModel.is_free_trial.is_(True)
        )
        free_trial_subscription_id: int | None = (await sess.execute(query)).scalar_one_or_none()
        if free_trial_subscription_id is not None:
            query = delete(SubscriptionModel).where(SubscriptionModel.id == free_trial_subscription_id)
            await sess.execute(query)

        query = (
            insert(PendingAwsSubscriptionsModel)
            .values(
                {
                    "organization_id": organization_id,
                    "customer_aws_account_id": body.customer_aws_account_id,
                    "customer_identifier": body.customer_identifier,
                    "product_code": body.product_code,
                    "has_failed": False,
                }
            )
            .returning(PendingAwsSubscriptionsModel)
        )

        pending_subscription = (await sess.execute(query)).one()
        assert pending_subscription is not None  # mypy assertion
        subscription_data = PendingAwsSubscriptionRow.from_orm(pending_subscription)

        await sess.commit()

    endpoint_response = response.created(PendingAwsSubscriptionModelOutput(**subscription_data.dict()).dict())

    if SETTINGS.TEST_ENV:
        cookie_domain = "localhost"
    else:
        cookie_domain = SETTINGS.APP_DOMAIN

    # [Reference](https://www.starlette.io/responses/#set-cookie)
    endpoint_response.set_cookie(key="product_code", value="", domain=cookie_domain, max_age=0)
    endpoint_response.set_cookie(key="customer_identifier", value="", domain=cookie_domain, max_age=0)
    endpoint_response.set_cookie(key="customer_aws_account_id", value="", domain=cookie_domain, max_age=0)

    return endpoint_response


# endpoint used for testing purposes
if SETTINGS.TEST_ENV:

    @router.get("/subscriptions/aws-subscription/dummy-confirm")
    async def dummy_confirmation_endpoint():
        """Dummy endpoint to test the redirection given by /subscriptions/aws-subscription/initialize."""  # noqa: D401
        return HTMLResponse(content="<h1>Subscription confirmed</hjson>", status_code=status.HTTP_200_OK)
