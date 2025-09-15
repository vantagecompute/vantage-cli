"""Helper functions for the groups router."""
from typing import Optional

from fastapi import HTTPException, status

from api.body.output import GroupModel, RoleModel, UserModel

sort_field_exception = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Field not available for sorting",
)


class ListGroupsSortFieldChecker:

    """Core class for checking if a given input field is available to sort groups by."""

    _model = GroupModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in GroupModel.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


class ListUsersByGroupSortFieldChecker:

    """Core class for checking if a given input field is available to sort users by."""

    _model = UserModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())


class ListRolesByGroupsSortFieldChecker:

    """Core class for checking if a given input field is available to sort roles by."""

    _model = RoleModel

    def __call__(self, sort_field: Optional[str] = None) -> str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys():
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        return list(cls._model.__fields__.keys())
