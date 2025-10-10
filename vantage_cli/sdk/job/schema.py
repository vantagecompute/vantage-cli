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
"""Job schemas for the Vantage CLI SDK."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobScriptFile(BaseModel):
    """Schema for job script file."""

    parent_id: int = Field(..., description="Parent job script ID")
    filename: str = Field(..., description="File name")
    file_type: str = Field(..., description="File type (e.g., ENTRYPOINT)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class JobScript(BaseModel):
    """Schema for job script."""

    id: int = Field(..., description="Job script ID")
    name: str = Field(..., description="Job script name")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(False, description="Whether the script is archived")
    description: str = Field("", description="Script description")
    parent_template_id: Optional[int] = Field(
        None, description="Parent template ID if created from template"
    )
    cloned_from_id: Optional[int] = Field(None, description="Source script ID if cloned")
    files: List[JobScriptFile] = Field(default_factory=list, description="Associated script files")
    template: Optional[Dict[str, Any]] = Field(None, description="Template data if applicable")


class JobTemplate(BaseModel):
    """Schema for job script template."""

    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(False, description="Whether the template is archived")
    description: str = Field("", description="Template description")
    parent_template_id: Optional[int] = Field(None, description="Parent template ID if derived")
    cloned_from_id: Optional[int] = Field(None, description="Source template ID if cloned")
    template: Optional[Dict[str, Any]] = Field(None, description="Template configuration data")


class JobSubmission(BaseModel):
    """Schema for job submission."""

    id: int = Field(..., description="Submission ID")
    name: str = Field(..., description="Submission name")
    owner_email: str = Field(..., description="Owner email address")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(False, description="Whether the submission is archived")
    description: str = Field("", description="Submission description")
    job_script_id: int = Field(..., description="Associated job script ID")
    slurm_job_id: Optional[int] = Field(None, description="Slurm job ID if submitted")
    client_id: str = Field(..., description="Client/cluster ID where job was submitted")
    status: str = Field(..., description="Submission status")
    slurm_job_state: Optional[str] = Field(None, description="Slurm job state")
    cloned_from_id: Optional[int] = Field(None, description="Source submission ID if cloned")
    execution_directory: Optional[str] = Field(None, description="Execution directory path")
    report_message: Optional[str] = Field(None, description="Report or error message")
    slurm_job_info: Optional[str] = Field(None, description="Slurm job info JSON string")
    sbatch_arguments: List[str] = Field(
        default_factory=list, description="Sbatch command arguments"
    )
