# Cluster SDK Implementation - Complete

This document describes the complete implementation of the Cluster SDK for the Vantage CLI.

## Overview

The Cluster SDK (`vantage_cli.sdk.cluster.crud.ClusterSDK`) provides a complete CRUD interface for managing Vantage clusters through the GraphQL API. All methods return strongly-typed `Cluster` objects from the Pydantic schema.

## Architecture

### Class Hierarchy
```
BaseGraphQLResourceSDK (abstract)
    └── ClusterSDK (concrete implementation)
```

### Key Files
- `vantage_cli/sdk/cluster/crud.py` - CRUD operations
- `vantage_cli/sdk/cluster/schema.py` - Cluster data model
- `vantage_cli/sdk/base.py` - Base GraphQL SDK class

## Implemented Operations

### 1. List Clusters (`list_clusters`)

**Method**: `async def list_clusters(ctx: typer.Context, **kwargs) -> List[Cluster]`

**GraphQL Query**:
```graphql
query getClusters($first: Int!) {
    clusters(first: $first) {
        edges {
            node {
                name
                status
                clientId
                description
                ownerEmail
                provider
                cloudAccountId
                creationParameters
            }
        }
    }
}
```

**Usage**:
```python
from vantage_cli.sdk.cluster.crud import cluster_sdk

clusters = await cluster_sdk.list_clusters(ctx)
for cluster in clusters:
    print(f"{cluster.name}: {cluster.status}")
```

**CLI Command**: `vantage cluster list`

### 2. Get Single Cluster (`get` / `get_cluster`)

**Method**: `async def get(ctx: typer.Context, resource_id: str, **kwargs) -> Optional[Cluster]`

**GraphQL Query** (with filtering):
```graphql
query getClusters($first: Int!, $filters: JSONScalar) {
    clusters(first: $first, filters: $filters) {
        edges {
            node {
                name
                status
                clientId
                description
                ownerEmail
                provider
                cloudAccountId
                creationParameters
            }
        }
    }
}
```

**Filter Syntax**: `{"name": {"eq": "cluster-name"}}`

**Usage**:
```python
cluster = await cluster_sdk.get_cluster(ctx, "my-cluster")
if cluster:
    print(f"Found: {cluster.name} ({cluster.status})")
```

**CLI Command**: `vantage cluster get <name>`

### 3. Create Cluster (`create` / `create_cluster`)

**Method**: `async def create(ctx: typer.Context, resource_data: Dict[str, Any], **kwargs) -> Cluster`

**GraphQL Mutation**:
```graphql
mutation createCluster($createClusterInput: CreateClusterInput!) {
    createCluster(createClusterInput: $createClusterInput) {
        ... on Cluster {
            name
            status
            clientId
            clientSecret
            description
            ownerEmail
            provider
            cloudAccountId
            creationParameters
        }
        ... on ClusterNameInUse {
            message
        }
        ... on InvalidInput {
            message
        }
        ... on ClusterCouldNotBeDeployed {
            message
        }
        ... on UnexpectedBehavior {
            message
        }
    }
}
```

**Input Parameters**:
```python
{
    "name": "cluster-name",           # Required
    "provider": "on_prem|aws|gcp",    # Required
    "description": "Optional text",    # Optional
    "providerAttributes": {            # Optional, provider-specific
        "aws": {
            "headNodeInstanceType": "t3.medium",
            "keyPair": "default",
            "cloudAccountId": 1,
            "regionName": "us_west_2"
        }
    }
}
```

**Usage** (low-level):
```python
cluster_data = {
    "name": "test-cluster",
    "provider": "on_prem",
    "description": "Test cluster"
}
cluster = await cluster_sdk.create(ctx, cluster_data)
```

**Usage** (high-level helper):
```python
cluster = await cluster_sdk.create_cluster(
    ctx,
    name="test-cluster",
    provider="on_prem",
    description="Test cluster",
    provider_attributes=None
)
```

**CLI Command**: `vantage cluster create <name> --cloud <provider>`

**Error Handling**:
- Raises `Exception` if cluster name already exists
- Raises `Exception` if creation fails with detailed message

### 4. Update Cluster (`update`)

**Method**: `async def update(ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs) -> Cluster`

**Status**: ⚠️ **Not Implemented** - GraphQL API does not support cluster updates

**Behavior**: Raises `NotImplementedError` with message:
```
"Cluster updates are not currently supported by the Vantage API. 
To modify a cluster, you must delete and recreate it."
```

**Future**: When the API adds update support, this method can be implemented with:
```graphql
mutation updateCluster($clusterName: String!, $updateData: UpdateClusterInput!) {
    updateCluster(clusterName: $clusterName, updateData: $updateData) {
        # ... cluster fields
    }
}
```

### 5. Delete Cluster (`delete` / `delete_cluster`)

**Method**: `async def delete(ctx: typer.Context, resource_id: str, **kwargs) -> bool`

**GraphQL Mutation**:
```graphql
mutation deleteCluster($clusterName: String!) {
    deleteCluster(clusterName: $clusterName) {
        ... on ClusterDeleted {
            message
        }
        ... on ClusterNotFound {
            message
        }
        ... on InvalidProviderInput {
            message
        }
        ... on UnexpectedBehavior {
            message
        }
    }
}
```

**Usage**:
```python
success = await cluster_sdk.delete_cluster(ctx, "my-cluster")
if success:
    print("Cluster deleted successfully")
```

**CLI Command**: `vantage cluster delete <name>`

**Error Handling**:
- Raises `Exception` if cluster not found
- Raises `Exception` if deletion fails with detailed message
- Returns `True` on successful deletion

## Cluster Schema

The `Cluster` Pydantic model includes:

### Required Fields
- `name: str` - Cluster name (unique identifier)
- `status: str` - Current status (e.g., "ready", "creating", "failed")
- `client_id: str` - OAuth client ID for cluster
- `description: str` - Human-readable description
- `owner_email: str` - Email of cluster owner
- `provider: str` - Cloud provider ("on_prem", "aws", "gcp", "azure")

### Optional Fields
- `client_secret: Optional[str]` - OAuth client secret (only returned on creation)
- `cloud_account_id: Optional[str]` - Associated cloud account
- `creation_parameters: Dict[str, Any]` - Provider-specific creation params (default: {})

### Computed Properties
- `jupyterhub_url: str` - Computed JupyterHub URL
- `jupyterhub_token: str` - JupyterHub token from creation_parameters
- `is_ready: bool` - True if status is "ready"
- `cluster_type: str` - Human-readable provider name

### Methods
- `to_dict() -> Dict[str, Any]` - Convert to dict for display/JSON output

## Usage Patterns

### Pattern 1: List and Display
```python
from vantage_cli.sdk.cluster.crud import cluster_sdk
from vantage_cli.render import UniversalOutputFormatter

clusters = await cluster_sdk.list_clusters(ctx)
cluster_dicts = [c.to_dict() for c in clusters]

formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=False)
formatter.render_list(cluster_dicts, title="Clusters")
```

### Pattern 2: Get and Check Status
```python
cluster = await cluster_sdk.get_cluster(ctx, "my-cluster")
if cluster and cluster.is_ready:
    print(f"Cluster {cluster.name} is ready at {cluster.jupyterhub_url}")
else:
    print(f"Cluster not ready. Status: {cluster.status if cluster else 'Not Found'}")
```

### Pattern 3: Create with Error Handling
```python
try:
    cluster = await cluster_sdk.create_cluster(
        ctx,
        name="new-cluster",
        provider="on_prem",
        description="Production cluster"
    )
    print(f"Created cluster: {cluster.name}")
    print(f"Client ID: {cluster.client_id}")
    print(f"Client Secret: {cluster.client_secret}")  # Save this!
except Exception as e:
    print(f"Failed to create cluster: {e}")
```

### Pattern 4: Safe Delete with Confirmation
```python
cluster = await cluster_sdk.get_cluster(ctx, "old-cluster")
if not cluster:
    print("Cluster not found")
else:
    # Confirm deletion
    if confirm_deletion(cluster.name):
        try:
            await cluster_sdk.delete_cluster(ctx, cluster.name)
            print(f"Deleted cluster: {cluster.name}")
        except Exception as e:
            print(f"Failed to delete: {e}")
```

## Integration with Commands

The SDK is designed to be used by CLI commands:

### Example: List Command
```python
# vantage_cli/commands/cluster/list.py
from vantage_cli.sdk.cluster.crud import cluster_sdk

async def list_clusters_command(ctx: typer.Context):
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    clusters = await cluster_sdk.list_clusters(ctx)
    cluster_dicts = [c.to_dict() for c in clusters]
    
    if ctx.obj.json_output:
        formatter.render_json(cluster_dicts)
    else:
        formatter.render_list(cluster_dicts, title="Clusters")
```

### Example: Get Command
```python
# vantage_cli/commands/cluster/get.py
from vantage_cli.sdk.cluster.crud import cluster_sdk

async def get_cluster_command(ctx: typer.Context, name: str):
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    cluster = await cluster_sdk.get_cluster(ctx, name)
    if not cluster:
        raise Abort(f"Cluster '{name}' not found")
    
    formatter.render_get(cluster.to_dict(), title=f"Cluster (ID: {name})")
```

## Error Handling

The SDK follows these error handling principles:

1. **GraphQL Errors**: Propagated as exceptions with descriptive messages
2. **Not Found**: Returns `None` for get operations, raises for delete
3. **Validation Errors**: Pydantic validation errors for invalid data
4. **API Errors**: Union type error responses parsed and raised as exceptions

### Common Exceptions
- `Exception("Failed to create cluster: <message>")` - Creation failed
- `Exception("Cluster not found: <name>")` - Cluster doesn't exist
- `NotImplementedError(...)` - Operation not supported by API
- `ValidationError` - Invalid cluster data

## Testing

### Import Test
```bash
uv run python -c "from vantage_cli.sdk.cluster.crud import cluster_sdk; print('✓ OK')"
```

### List Test
```bash
uv run vantage cluster list --json
```

### Get Test
```bash
uv run vantage cluster get b1 --json
```

## Future Enhancements

1. **Update Support**: When API adds update mutation
2. **Filtering**: Advanced filtering for list operations
3. **Pagination**: Support for large cluster lists
4. **Batch Operations**: Create/delete multiple clusters
5. **Async Contexts**: Better async context management
6. **Caching**: Optional caching for frequently accessed clusters
7. **Webhooks**: Cluster status change notifications

## API Compatibility

- **GraphQL API Version**: Compatible with Vantage GraphQL v1
- **Provider Support**: on_prem, aws (gcp, azure planned)
- **Authentication**: Uses OAuth2 via settings/persona
- **Rate Limiting**: Inherits from base GraphQL client

## Summary

✅ **List** - Full implementation with Cluster objects
✅ **Get** - Full implementation with filtering
✅ **Create** - Full implementation with error handling
⚠️ **Update** - Not supported by API (NotImplementedError)
✅ **Delete** - Full implementation with error handling

The Cluster SDK provides a complete, type-safe interface for managing Vantage clusters programmatically.
