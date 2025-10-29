"""Utility functions for Cudo Compute."""

from typing import Optional


def get_datacenter_id_from_credentials() -> Optional[str]:
    """Get datacenter_id from the default Cudo Compute credentials.

    Returns:
        datacenter_id from credentials if set, None otherwise
    """
    from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk

    cudo_credential = cloud_credential_sdk.get_default(cloud_name="cudo-compute")
    if cudo_credential is None:
        return None

    return cudo_credential.credentials_data.get("default_datacenter_id")
