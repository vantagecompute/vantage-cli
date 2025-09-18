---
title: Usage Examples
description: Practical examples of using Vantage CLI
---

## 1. Install the Vantage CLI

Install `vantage-cli` with `uv`:

```bash
uv venv
source .venv/bin/activate

uv pip install vantage-cli
```

## 2. Vantage Login

```bash
vantage login
```

## 3. Cluster Management

```bash
# List clusters (using alias)
vantage clusters
vantage clusters --json | jq '.clusters | length'

# Create new cluster using juju
vantage cluster create compute-juju-00 --cloud localhost --app slurm-juju-localhost

# Create new local vm singlenode cluster using multipass
vantage cluster create compute-multipass-00 --cloud localhost --app slurm-multipass-localhost

# Create new local vm singlenode cluster using microk8s
vantage cluster create compute-microk8s-00 --cloud localhost --app slurm-microk8s-localhost

# Get specific cluster
vantage cluster get compute-juju-00 --json | jq '.cluster | {name,id,status}'
```

## 4. Vantage Applications (apps)

```bash
# List available applications
vantage apps
```

## 5. Cloud Provider Management

```bash
# Add cloud providers
vantage cloud add aws-prod --provider aws
vantage cloud add gcp-dev --provider gcp
vantage cloud add compute-a-on-site-us-east --provider on-premises


# List configurations
vantage clouds --json | jq '.clouds[] | {name, provider, status}'

{
  "name": "aws-prod",
  "provider": "aws",
  "status": "active"
}
{
  "name": "gcp-dev",
  "provider": "gcp",
  "status": "active"
}
```

## 6. Network and Storage

```bash
# Create a storage volume
vantage storage create data-vol --size 100GB

# Create network
vantage network create cluster-net --cidr 10.0.0.0/16

# List resources
vantage storage list --json | jq '.volumes[] | {name, size, status}'
vantage networks --json | jq '.networks[] | {name, cidr}'
```

## 7. Job Management Workflow

```bash
# Create job script
vantage job script create analysis --file ./my_script.py

# Create job template for reuse
vantage job template create gpu-analysis \
  --memory 16GB --gpus 2 --queue gpu

# Submit job
vantage job submission create myjobsubmission \
  --script script-123 \
  --template template-456 \
  --priority high

# Monitor job status
vantage job submission get --id sub-789 --json | jq '.status'
```

## 8. Team Collaboration

```bash
# Create team
vantage team create ml-research --description "ML Research Team"

# Add team members
vantage team member add --team ml-research --user alice@company.com --role admin
vantage team member add --team ml-research --user bob@company.com --role member

# List team members
vantage team member list --team ml-research
```

## 9. Switch Profiles

```bash
vantage profile list
vantage profile create staging --activate
vantage login
```

## 6. GraphQL Query (Programmatic)

```python
import asyncio
from vantage_cli.gql_client import create_async_graphql_client
from vantage_cli.config import Settings
from vantage_cli.auth import extract_persona

async def main():
    settings = Settings()
    persona = extract_persona("default")
    client = create_async_graphql_client(settings, "default")
    data = await client.execute_async("""query { __typename }""")
    print(data)

asyncio.run(main())
```

## 7. Token Cache Inspection

```python
from vantage_cli.cache import load_tokens_from_cache
from vantage_cli.schemas import TokenSet

tokens: TokenSet = load_tokens_from_cache("default")
print(tokens.access_token[:16] + "..." if tokens.access_token else "NO TOKEN")
```

## 8. Piping & Automation

```bash
# Email of current authenticated user
auth_email=$(vantage whoami --json | jq -r '.identity.email')

echo "Authenticated as: $auth_email"

# Collect cluster names into a shell array
mapfile -t clusters < <(vantage clusters list --json | jq -r '.clusters[].name')
printf 'Found %d clusters\n' "${#clusters[@]}"
```

## 9. Handling Errors

Add `-v` to surface debug logs:

```bash
vantage -v whoami
```

If tokens are expired the CLI will attempt a refresh; if that fails re-run `vantage login`.

## 10. JSON Extraction Template

```bash
vantage clusters --json | jq '{count: (.clusters | length), names: [.clusters[].name]}'
```

---
See also: [Commands](./commands) | [Troubleshooting](./troubleshooting)
