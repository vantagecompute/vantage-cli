# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""CRUD SDK for License Management resources."""

from vantage_cli.sdk.base import BaseRestApiResourceSDK


class LicenseServerSDK(BaseRestApiResourceSDK):
    """SDK for License Server CRUD operations via REST API."""

    def __init__(self):
        super().__init__(
            resource_name="license_server", base_path="/lm", endpoint_path="/license_servers"
        )


class LicenseFeatureSDK(BaseRestApiResourceSDK):
    """SDK for License Feature CRUD operations via REST API."""

    def __init__(self):
        super().__init__(
            resource_name="license_feature", base_path="/lm", endpoint_path="/features"
        )


class LicenseProductSDK(BaseRestApiResourceSDK):
    """SDK for License Product CRUD operations via REST API."""

    def __init__(self):
        super().__init__(
            resource_name="license_product", base_path="/lm", endpoint_path="/products"
        )


class LicenseConfigurationSDK(BaseRestApiResourceSDK):
    """SDK for License Configuration CRUD operations via REST API."""

    def __init__(self):
        super().__init__(
            resource_name="license_configuration", base_path="/lm", endpoint_path="/configurations"
        )


class LicenseBookingSDK(BaseRestApiResourceSDK):
    """SDK for License Booking CRUD operations via REST API."""

    def __init__(self):
        super().__init__(
            resource_name="license_booking", base_path="/lm", endpoint_path="/bookings"
        )


# Create singleton instances
license_server_sdk = LicenseServerSDK()
license_feature_sdk = LicenseFeatureSDK()
license_product_sdk = LicenseProductSDK()
license_configuration_sdk = LicenseConfigurationSDK()
license_booking_sdk = LicenseBookingSDK()


__all__ = [
    "LicenseServerSDK",
    "LicenseFeatureSDK",
    "LicenseProductSDK",
    "LicenseConfigurationSDK",
    "LicenseBookingSDK",
    "license_server_sdk",
    "license_feature_sdk",
    "license_product_sdk",
    "license_configuration_sdk",
    "license_booking_sdk",
]
