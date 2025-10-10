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
"""Job SDK module for Vantage CLI."""

from .crud import job_script_sdk, job_submission_sdk, job_template_sdk
from .schema import JobScript, JobScriptFile, JobSubmission, JobTemplate

__all__ = [
    # Schemas
    "JobScript",
    "JobScriptFile",
    "JobSubmission",
    "JobTemplate",
    # CRUD SDK instances
    "job_script_sdk",
    "job_template_sdk",
    "job_submission_sdk",
]
