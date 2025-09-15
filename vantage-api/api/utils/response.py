"""Core module for HTTP response operations."""
from typing import Any, Dict

import fastapi
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def bad_request(body: Dict[str, Any]):
    """HTTP 400 Bad Request response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_400_BAD_REQUEST,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def created(body: Dict[str, Any]):
    """HTTP 201 Created response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_201_CREATED,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def forbidden(body: Dict[str, Any]):
    """HTTP 403 Forbidden response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_403_FORBIDDEN,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def not_found(body: Dict[str, Any]):
    """HTTP 404 Not Found response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_404_NOT_FOUND,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def internal_error(body: Dict[str, Any]):
    """HTTP 500 Internal Server Error response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def success(body: Dict[str, Any] | list[Any]):
    """HTTP 200 OK response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_200_OK,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def conflict(body: Dict[str, Any]):
    """HTTP 409 Conflict response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_409_CONFLICT,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "WWW-Authenticate": "Bearer",
        },
    )


def payment_required(body: Dict[str, Any]):
    """HTTP 402 Payment Required response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_402_PAYMENT_REQUIRED,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


def precondition_required(body: Dict[str, Any]):
    """HTTP 428 Precondition Required response."""
    return JSONResponse(
        content=jsonable_encoder(body, by_alias=False),
        status_code=fastapi.status.HTTP_428_PRECONDITION_REQUIRED,
        headers={
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
    )


class OK(BaseModel):

    """A response that there was no error, when no other data is required."""

    status: str = "ok"
    message: str = ""
