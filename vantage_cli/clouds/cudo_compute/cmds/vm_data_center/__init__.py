# Copyright (c) 2025 Vantage Compute, Inc.
#
# SPDX-License-Identifier: MIT

"""VM data center management commands for Cudo Compute."""

from .get import get_vm_data_center
from .list import list_vm_data_centers

__all__ = [
    "get_vm_data_center",
    "list_vm_data_centers",
]
