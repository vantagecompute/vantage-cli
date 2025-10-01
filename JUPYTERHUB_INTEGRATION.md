# JupyterHub Integration for Notebook Creation

## Overview

This implementation adds JupyterHub API integration to create notebook servers on Vantage clusters. It follows the established SDK architecture pattern.

## Components Created

### 1. JupyterHub Client (`vantage_cli/jupyterhub_client.py`)

Low-level HTTP client for JupyterHub REST API:

```python
class JupyterHubClient:
    """Client for interacting with JupyterHub REST API."""
    
    async def create_user_server(username, server_name=None, options=None)
    async def get_user_server(username, server_name=None)
    async def stop_user_server(username, server_name=None)
    async def list_users()
```

**Features:**
- Token-based authentication using cluster's jupyterhub_token
- Async HTTP client with proper error handling
- Support for named servers and default servers
- Configurable server options (resources, partition, etc.)

### 2. JupyterHub SDK (`vantage_cli/jupyterhub_sdk.py`)

High-level SDK wrapping JupyterHub operations:

```python
class JupyterHubSDK:
    """SDK for JupyterHub notebook server operations."""
    
    async def get_cluster_jupyterhub_client(ctx, cluster_name)
    async def create_notebook_server(ctx, cluster_name, username, server_name=None, server_options=None)
    async def get_notebook_server(ctx, cluster_name, username, server_name=None)
    async def stop_notebook_server(ctx, cluster_name, username, server_name=None)
    async def list_cluster_users(ctx, cluster_name)
```

**Features:**
- Automatic cluster lookup and JupyterHub URL/token extraction
- Uses Cluster model's computed fields: `jupyterhub_url` and `jupyterhub_token`
- Graceful error handling with Abort exceptions
- Resource cleanup with async context management

### 3. Notebook SDK Extension (`vantage_cli/sdk/notebook/crud.py`)

Added `create_notebook()` method to NotebookSDK:

```python
async def create_notebook(
    ctx,
    cluster_name,
    username,
    server_name=None,
    server_options=None
) -> Dict[str, Any]
```

**Features:**
- Uses JupyterHub SDK internally
- Returns standardized response format
- Supports server options for resource specifications

### 4. Notebook Create Command (`vantage_cli/commands/notebook/create.py`)

Refactored to use the new SDK:

```bash
vantage notebook create --cluster CLUSTER [OPTIONS]
```

**Options:**
- `--cluster, -c`: Target cluster (required)
- `--username, -u`: JupyterHub username (defaults to authenticated user)
- `--name, -n`: Named server (optional, creates default if not provided)
- `--partition`: SLURM partition to use
- `--cpu-cores`: Number of CPU cores
- `--mem`: Memory specification (e.g., 4G, 8G)
- `--gpu`: Number of GPUs
- `--node`: Specific node to use

**Features:**
- Automatic username extraction from authenticated user's email
- UniversalOutputFormatter for consistent output (table/JSON)
- Resource specifications passed to JupyterHub as server options
- Proper error handling and user feedback

## Architecture Flow

```
Command (create.py)
    ↓
NotebookSDK.create_notebook()
    ↓
JupyterHubSDK.create_notebook_server()
    ↓
ClusterSDK.get_cluster() → Get cluster details
    ↓
JupyterHubClient.create_user_server() → JupyterHub REST API
```

## Usage Examples

### Basic notebook creation (auto-detect username):
```bash
vantage notebook create --cluster my-cluster
```

### Create with specific username:
```bash
vantage notebook create --cluster my-cluster --username john.doe
```

### Create named server:
```bash
vantage notebook create --cluster my-cluster --name my-analysis
```

### Create with resource specifications:
```bash
vantage notebook create \
  --cluster my-cluster \
  --partition gpu \
  --cpu-cores 8 \
  --mem 16G \
  --gpu 1
```

### Create on specific node:
```bash
vantage notebook create \
  --cluster my-cluster \
  --node compute-01 \
  --cpu-cores 4 \
  --mem 8G
```

### JSON output:
```bash
vantage notebook create --cluster my-cluster --json
```

## Server Options Format

The `server_options` dictionary passed to JupyterHub can include:

```python
{
    "partition": "gpu",      # SLURM partition
    "cpu_cores": 8,          # Number of CPU cores
    "memory": "16G",         # Memory specification
    "gpus": 1,               # Number of GPUs
    "node": "compute-01"     # Specific node
}
```

These options are passed directly to JupyterHub's spawner configuration.

## JupyterHub API Reference

The implementation uses the following JupyterHub API endpoints:

- `POST /hub/api/users/{username}/server` - Create default server
- `POST /hub/api/users/{username}/servers/{server_name}` - Create named server
- `GET /hub/api/users/{username}` - Get user and server info
- `DELETE /hub/api/users/{username}/server` - Stop default server
- `DELETE /hub/api/users/{username}/servers/{server_name}` - Stop named server

## Cluster Schema Integration

The implementation leverages the Cluster model's computed fields:

```python
class Cluster(BaseModel):
    @computed_field
    @property
    def jupyterhub_url(self) -> str:
        return f"https://{self.client_id}.vantagecompute.ai"
    
    @computed_field
    @property
    def jupyterhub_token(self) -> str:
        return self.creation_parameters.get("jupyterhubToken", "")
```

## Error Handling

The implementation includes comprehensive error handling:

1. **Cluster not found**: Clear error message if cluster doesn't exist
2. **Missing JupyterHub token**: Validation that cluster has token configured
3. **JupyterHub API errors**: HTTP errors mapped to user-friendly Abort exceptions
4. **Username resolution**: Falls back to prompting if auto-detection fails
5. **Connection errors**: Proper handling of network/timeout issues

## Future Enhancements

Potential additions for future iterations:

1. **Server templates**: Pre-configured resource profiles
2. **Status polling**: Wait for server to be fully spawned
3. **Server logs**: Stream JupyterHub spawner logs
4. **Batch creation**: Create multiple servers at once
5. **Server persistence**: Save/restore server configurations
6. **Resource validation**: Check cluster capacity before creation
