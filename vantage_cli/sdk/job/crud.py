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
"""CRUD SDK for Jobbergate resources (Job Scripts, Templates, Submissions)."""

from vantage_cli.sdk.base import BaseRestApiResourceSDK


class JobScriptSDK(BaseRestApiResourceSDK):
    """SDK for Job Script CRUD operations via Jobbergate REST API."""

    def __init__(self):
        super().__init__(
            resource_name="job_script", base_path="/jobbergate", endpoint_path="/job-scripts"
        )


class JobTemplateSDK(BaseRestApiResourceSDK):
    """SDK for Job Template CRUD operations via Jobbergate REST API."""

    def __init__(self):
        super().__init__(
            resource_name="job_template",
            base_path="/jobbergate",
            endpoint_path="/job-script-templates",
        )


class JobSubmissionSDK(BaseRestApiResourceSDK):
    """SDK for Job Submission CRUD operations via Jobbergate REST API."""

    def __init__(self):
        super().__init__(
            resource_name="job_submission",
            base_path="/jobbergate",
            endpoint_path="/job-submissions",
        )


# Create singleton instances
job_script_sdk = JobScriptSDK()
job_template_sdk = JobTemplateSDK()
job_submission_sdk = JobSubmissionSDK()


__all__ = [
    "JobScriptSDK",
    "JobTemplateSDK",
    "JobSubmissionSDK",
    "job_script_sdk",
    "job_template_sdk",
    "job_submission_sdk",
]
