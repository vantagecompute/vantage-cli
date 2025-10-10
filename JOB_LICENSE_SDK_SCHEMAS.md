# Job and License SDK Schemas

This document describes the Pydantic schemas created for Job and License objects in the Vantage CLI SDK.

## Job SDK (`vantage_cli/sdk/job/`)

### Created Files
- `__init__.py` - Module initialization with exports
- `schema.py` - Pydantic model schemas

### Schemas

#### JobScriptFile
Represents a file associated with a job script.

**Fields:**
- `parent_id` (int) - Parent job script ID
- `filename` (str) - File name
- `file_type` (str) - File type (e.g., ENTRYPOINT)
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp

#### JobScript
Represents a job script in the Jobbergate system.

**Fields:**
- `id` (int) - Job script ID
- `name` (str) - Job script name
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `is_archived` (bool) - Whether the script is archived
- `description` (str) - Script description
- `parent_template_id` (Optional[int]) - Parent template ID if created from template
- `cloned_from_id` (Optional[int]) - Source script ID if cloned
- `files` (List[JobScriptFile]) - Associated script files
- `template` (Optional[Dict[str, Any]]) - Template data if applicable

#### JobTemplate
Represents a job script template.

**Fields:**
- `id` (int) - Template ID
- `name` (str) - Template name
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `is_archived` (bool) - Whether the template is archived
- `description` (str) - Template description
- `parent_template_id` (Optional[int]) - Parent template ID if derived
- `cloned_from_id` (Optional[int]) - Source template ID if cloned
- `template` (Optional[Dict[str, Any]]) - Template configuration data

#### JobSubmission
Represents a job submission to a Slurm cluster.

**Fields:**
- `id` (int) - Submission ID
- `name` (str) - Submission name
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `is_archived` (bool) - Whether the submission is archived
- `description` (str) - Submission description
- `job_script_id` (int) - Associated job script ID
- `slurm_job_id` (Optional[int]) - Slurm job ID if submitted
- `client_id` (str) - Client/cluster ID where job was submitted
- `status` (str) - Submission status
- `slurm_job_state` (Optional[str]) - Slurm job state
- `cloned_from_id` (Optional[int]) - Source submission ID if cloned
- `execution_directory` (Optional[str]) - Execution directory path
- `report_message` (Optional[str]) - Report or error message
- `slurm_job_info` (Optional[str]) - Slurm job info JSON string
- `sbatch_arguments` (List[str]) - Sbatch command arguments

## License SDK (`vantage_cli/sdk/license/`)

### Created Files
- `__init__.py` - Module initialization with exports
- `schema.py` - Pydantic model schemas

### Schemas

#### LicenseServer
Represents a license server (FlexLM, RLM, etc.).

**Fields:**
- `id` (str) - License server ID
- `name` (str) - Server name
- `host` (str) - Server host address
- `port` (int) - Server port
- `license_type` (str) - License type (e.g., FlexLM, RLM)
- `status` (str) - Server status
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Server description

#### LicenseFeature
Represents a feature available from a license server.

**Fields:**
- `id` (str) - Feature ID
- `name` (str) - Feature name
- `server_id` (str) - Associated license server ID
- `product_id` (Optional[str]) - Associated product ID
- `total_licenses` (int) - Total number of licenses
- `in_use` (int) - Number of licenses currently in use
- `available` (int) - Number of available licenses
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Feature description
- `version` (Optional[str]) - Feature version
- `expiration_date` (Optional[datetime]) - License expiration date

#### LicenseProduct
Represents a licensed software product.

**Fields:**
- `id` (str) - Product ID
- `name` (str) - Product name
- `vendor` (str) - Product vendor
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Product description
- `version` (Optional[str]) - Product version
- `features` (List[str]) - Associated feature IDs

#### LicenseConfiguration
Represents a license server configuration.

**Fields:**
- `id` (str) - Configuration ID
- `name` (str) - Configuration name
- `server_id` (str) - Associated license server ID
- `configuration_type` (str) - Configuration type
- `configuration_data` (Dict[str, Any]) - Configuration data
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Configuration description
- `is_active` (bool) - Whether configuration is active

#### LicenseBooking
Represents a license reservation/booking.

**Fields:**
- `id` (str) - Booking ID
- `feature_id` (str) - Associated feature ID
- `user_email` (str) - User email who made the booking
- `cluster_id` (Optional[str]) - Associated cluster ID
- `num_licenses` (int) - Number of licenses booked
- `start_time` (datetime) - Booking start time
- `end_time` (Optional[datetime]) - Booking end time
- `status` (str) - Booking status (active, expired, cancelled)
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Booking description

#### LicenseDeployment
Represents a license server deployment to a cluster.

**Fields:**
- `id` (str) - Deployment ID
- `server_id` (str) - Associated license server ID
- `cluster_id` (str) - Associated cluster ID
- `deployment_status` (str) - Deployment status
- `owner_email` (str) - Owner email address
- `created_at` (datetime) - Creation timestamp
- `updated_at` (datetime) - Last update timestamp
- `description` (Optional[str]) - Deployment description
- `configuration_id` (Optional[str]) - Associated configuration ID
- `endpoint_url` (Optional[str]) - Deployment endpoint URL

## Usage Examples

### Job Schemas

```python
from vantage_cli.sdk.job import JobScript, JobTemplate, JobSubmission

# Parse API response
job_script = JobScript(**api_response)
print(f"Script: {job_script.name}, Files: {len(job_script.files)}")

# Access nested data
for file in job_script.files:
    print(f"  - {file.filename} ({file.file_type})")
```

### License Schemas

```python
from vantage_cli.sdk.license import (
    LicenseServer,
    LicenseFeature,
    LicenseProduct,
    LicenseBooking
)

# Parse server data
server = LicenseServer(**server_data)
print(f"Server: {server.name} at {server.host}:{server.port}")

# Parse feature data
feature = LicenseFeature(**feature_data)
print(f"Feature: {feature.name}, Available: {feature.available}/{feature.total_licenses}")
```

## Benefits

1. **Type Safety**: Pydantic provides runtime type validation
2. **Auto-completion**: IDEs can provide accurate autocomplete
3. **Documentation**: Field descriptions serve as inline documentation
4. **Validation**: Automatic validation of API responses
5. **Serialization**: Easy conversion to/from JSON
6. **Consistency**: Matches existing SDK pattern (cluster, deployment, etc.)

## Testing

All schemas have been tested with actual API data:
- ✅ Import test passed
- ✅ JobScript validation with real API response
- ✅ Nested JobScriptFile objects properly parsed

## Next Steps

These schemas can now be used in:
1. Job and license command implementations
2. Type hints for better code quality
3. API response validation
4. SDK client methods
5. Documentation generation
