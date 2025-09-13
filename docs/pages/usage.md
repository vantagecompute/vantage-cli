---
title: Usage Examples
description: Practical examples of using Vantage CLI
---

The `vantage` cli comes preconfigured to work with [https://vantagecompute.ai](https://vantagecompute.ai) by default.

If you are connecting to a privately hosted Vantage instance you will need to set up your profile accordingly.

## 1. Private Deployment First-Time Setup

Install `vantage-cli` via `pip`:

```bash
pip install vantage-cli
```

Create a profile:

```bash
vantage profile create vantage-example-com \
    --oidc-url=https://auth.example.vantagecompute.ai \
    --api-url=https://apis.example.vantagecompute.ai \
    --tunnel-url=https://tunnel.example.vantagecompute.ai \
     --activate
```

```bash
╭───────────────────────────── Profile Created ───────────────────────────╮
│ ✅ Profile 'vantage-example-com' created successfully!                  │
│ 🎯 Set as active profile!                                               │
╰─────────────────────────────────────────────────────────────────────────╯

                   Profile Details: vantage-example-com                   
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property           ┃ Value                                              ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Profile Name       │ vantage-example-com                                │
│ API Base URL       │ https://apis.example.vantagecompute.ai             │
│ OIDC Base URL      │ https://auth.example.vantagecompute.ai             │
│ Tunnel Base URL    │ https://tunnel.example.vantagecompute.ai           │
│ OIDC Domain        │ auth.example.vantagecompute.ai/auth/realms         │
│ OIDC Client ID     │ default                                            │
│ OIDC Max Poll Time │ 300 seconds                                        │
│ Supported Clouds   │ maas, localhost, aws, gcp, azure, on-premises, k8s │
└────────────────────┴────────────────────────────────────────────────────┘
```

## 2. Inspect Identity

```bash
vantage whoami
```

```bash
                Current User Information                
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property      ┃ Value                                ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Email         │ james@vantagecompute.ai              │
│ Client ID     │ default                              │
│ Profile       │ vantage-example-com                  │
│ Name          │ James Beedy                          │
│ User ID       │ 028da929-d0cf-4984-8bbe-9bc83f49f797 │
│ Token Issued  │ 2025-09-12T22:25:06                  │
│ Token Expires │ 2025-09-12T23:25:06 (✅ Valid)       │
│ Status        │ ✅ Logged in                         │
└───────────────┴──────────────────────────────────────┘
```

```bash
vantage whoami --json | jq '{email: .email, client_id: .client_id}'
```

```bash
{
  "email": "james@vantagecompute.ai",
  "client_id": "default"
}
```

## 3. Cloud Provider Management

```bash
# Add cloud providers
vantage cloud add aws-prod --provider aws
vantage cloud add gcp-dev --provider gcp
vantage cloud add gcp-dev --provider localhost


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

## 4. Cluster Management

```bash
# List clusters (using alias)
vantage clusters
vantage clusters --json | jq '.clusters | length'

# Get specific cluster
vantage cluster get demo --json | jq '.cluster | {name,id,status}'

# Create new cluster
vantage cluster create compute-01 --cloud aws-prod
```

## 5. Application Deployment

```bash
# List available applications
vantage apps

# Deploy application
vantage app deploy --app slurm-multipass-singlenode --cluster compute-01
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
vantage team add-member --team team-123 --user alice@company.com --role admin
vantage team add-member --team team-123 --user bob@company.com --role member

# List team members
vantage team list-members --team team-123
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
vantage clusters list --json | jq '{count: (.clusters | length), names: [.clusters[].name]}'
```

---
See also: [Commands](/vantage-cli/commands/) | [Troubleshooting](/vantage-cli/troubleshooting/)
