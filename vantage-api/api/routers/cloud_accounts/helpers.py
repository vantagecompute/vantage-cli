"""Helper functions for the cloud_accounts router."""
from fastapi import HTTPException, status

from api.body.output import CloudAccountModel

sort_field_exception = HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Field not available for sorting",
)


class ListCloudAccountsFieldChecker:

    """Core class for checking if a given input field is available to sort cloud accounts by."""

    _model = CloudAccountModel
    _not_available_fields = ["attributes"]

    def __call__(self, sort_field: None | str = None) -> None | str:
        """Check if the given field is available for sorting."""
        if sort_field is not None:
            if sort_field not in self._model.__fields__.keys() or sort_field == "attributes":
                raise sort_field_exception
        return sort_field

    @classmethod
    def available_fields(cls):
        """Return a list of available fields for sorting."""
        all_fields = list(cls._model.__fields__.keys())
        # remove fields that are not available for sorting
        return [field for field in all_fields if field not in cls._not_available_fields]

    @classmethod
    def not_available_fields(cls) -> list[str]:
        """Return a list of fields that are not available for sorting."""
        return cls._not_available_fields
