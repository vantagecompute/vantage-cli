---
layout: page
title: Usage Examples
nav_order: 3
permalink: /usage/
description: Practical scripting and usage examples for Vantage CLI
---

## 1. First-Time Setup

```bash
pip install vantage-cli
vantage profile create --name dev --set-active
vantage set-config \
  --oidc-base-url https://auth.vantagecompute.ai \
  --api-base-url https://apis.vantagecompute.ai
vantage login
```

## 2. Inspect Identity

```bash
vantage whoami --json | jq '{email: .identity.email, client: .identity.client_id}'
```

## 3. List Clusters (Table & JSON)

```bash
vantage clusters list
vantage clusters list --json | jq '.clusters | length'
```

## 4. Retrieve a Cluster

```bash
vantage clusters get --name demo --json | jq '.cluster | {name,id,status}'
```

## 5. Switch Profiles

```bash
vantage profile list
vantage profile create --name staging --set-active
vantage set-config --oidc-base-url https://auth.vantagecompute.ai --api-base-url https://apis.vantagecompute.ai
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
