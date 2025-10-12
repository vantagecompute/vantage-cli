# Cloud Provider SDK Implementation

## Summary

Successfully created the CloudProviderSDK and CloudProviderCredentialSDK with associated schemas.

## Files Created

### 1. `/vantage_cli/sdk/cloud_provider/schema.py`
Defines the data models:
- **VantageProviderLabel**: Enum for Vantage provider labels (on_prem, aws, gcp, azure, cudo)
- **CloudType**: Enum for cloud provider types
- **CloudProviderCredential**: Model for storing cloud provider credentials
  - `id`: Auto-generated UUID
  - `name`: Human-readable name
  - `credential_type`: Type of cloud (from CloudType enum)
  - `cloud_provider_id`: Reference to parent CloudProvider
  - `credentials_data`: Dictionary for encrypted credential data
  
- **CloudProvider**: Model for cloud providers
  - `id`: Auto-generated UUID
  - `name`: Provider name
  - `vantage_provider_label`: Vantage label for GraphQL API
  - `substrates`: List of available substrates (e.g., 'k8s', 'metal', 'lxd')
  - `credential`: Optional associated credential
  - `enabled`: Boolean flag
  - `metadata`: Additional provider metadata
  
- **Cloud**: Simple cloud definition with name and type
- **VantageCloudProviders**: Collection class with helper methods:
  - `get_by_name()`: Find provider by name
  - `get_by_id()`: Find provider by ID
  - `get_by_type()`: Get all providers of a specific type
  - `get_enabled()`: Get all enabled providers

### 2. `/vantage_cli/sdk/cloud_provider/crud.py`
Implements the SDK classes:

#### CloudProviderSDK
- Auto-discovers providers from `PROVIDER_SUBSTRATE_MAPPINGS` and `PROVIDER_VANTAGE_MAPPING` constants
- Methods:
  - `list(enabled_only, vantage_label)`: List providers with filtering
  - `get(provider_name)`: Get provider by name
  - `get_by_id(provider_id)`: Get provider by ID
  - `get_substrates(provider_name)`: Get available substrates
  - `get_all_providers()`: Return VantageCloudProviders collection
  - `refresh()`: Re-discover providers

#### CloudProviderCredentialSDK
- Manages cloud provider credentials
- Methods:
  - `create(name, credential_type, cloud_provider_id, credentials_data)`: Create credential
  - `get(credential_id)`: Get credential by ID
  - `list(cloud_provider_id, credential_type)`: List credentials with filtering
  - `delete(credential_id)`: Delete credential
  - `update(credential_id, name, credentials_data)`: Update credential

Singleton instances are exported as:
- `cloud_provider_sdk`
- `cloud_provider_credential_sdk`

### 3. `/vantage_cli/sdk/cloud_provider/__init__.py`
Package initialization file exporting all SDK classes and schemas.

## Usage Examples

### CloudProviderSDK

```python
from vantage_cli.sdk.cloud_provider import cloud_provider_sdk, VantageProviderLabel

# List all providers
providers = cloud_provider_sdk.list()

# List only on-prem providers
on_prem = cloud_provider_sdk.list(vantage_label=VantageProviderLabel.ON_PREM)

# Get specific provider
localhost = cloud_provider_sdk.get('localhost')
print(f"Substrates: {localhost.substrates}")  # ['multipass', 'microk8s', 'lxd']

# Get all providers as collection
all_providers = cloud_provider_sdk.get_all_providers()
enabled = all_providers.get_enabled()
```

### CloudProviderCredentialSDK

```python
from vantage_cli.sdk.cloud_provider import cloud_provider_credential_sdk, CloudType

# Create credential
cred = cloud_provider_credential_sdk.create(
    name='My AWS Credential',
    credential_type=CloudType.AWS,
    cloud_provider_id=provider.id,
    credentials_data={'access_key': 'xxx', 'secret_key': 'yyy'}
)

# List all credentials
all_creds = cloud_provider_credential_sdk.list()

# List credentials for specific provider
provider_creds = cloud_provider_credential_sdk.list(cloud_provider_id=provider.id)

# Update credential
cloud_provider_credential_sdk.update(cred.id, name='Updated Name')

# Delete credential
cloud_provider_credential_sdk.delete(cred.id)
```

## Testing

All functionality has been tested:
- CloudProviderSDK discovers 5 providers from constants
- Filtering by Vantage label works correctly
- CloudProviderCredentialSDK creates, lists, and manages credentials
- VantageCloudProviders helper methods function as expected
- Existing CLI functionality remains intact

## Integration

The SDK integrates with existing constants:
- Uses `PROVIDER_SUBSTRATE_MAPPINGS` for substrate discovery
- Uses `PROVIDER_VANTAGE_MAPPING` for Vantage label mapping
- Follows the same pattern as `deployment_app` SDK
- Includes logging for debugging with `--verbose` flag
