---
layout: page
title: Commands
nav_order: 2
permalink: /commands/
description: Command reference for Vantage CLI
---

Quick reference for core Vantage CLI commands. Use `--help` on any command for full details.

## Global Pattern

```bash
vantage [GLOBAL_OPTIONS] COMMAND [ARGS]...
```

Global options:

- `-v, --verbose` enable debug logging
- `-p, --profile TEXT` select profile
- `-j, --json` JSON output when supported
- `--help` show help


## Authentication & Identity

| Command | Description |
|---------|-------------|
| `vantage set-config --oidc-base-url URL --api-base-url URL` | Store settings for active profile |
| `vantage login` | Start device code auth flow |
| `vantage whoami` | Show decoded identity (supports `--json`) |
| `vantage logout` | (If implemented) Clear cached tokens |

## Profiles

| Command | Description |
|---------|-------------|
| `vantage profile list` | List profiles & active marker |
| `vantage profile create --name NAME [--set-active]` | Create profile |
| `vantage profile use --name NAME` | Switch active profile |
| `vantage profile delete --name NAME` | Remove a profile |

## Clusters

| Command | Description |
|---------|-------------|
| `vantage clusters list` | List clusters (add `--json`) |
| `vantage clusters get --name NAME` | Show cluster details |
| `vantage clusters create --name NAME --cloud PROVIDER` | Create cluster (backend dependent) |
| `vantage clusters delete --name NAME` | Delete cluster |
| `vantage clusters render --name NAME` | Render artifacts (if supported) |

## Apps

Application-specific utilities; command set evolves with the platform. Run:

```bash
vantage apps --help
```

## Examples

```bash
# Configure & authenticate
vantage profile create --name dev --set-active
vantage set-config --oidc-base-url https://auth.vantagecompute.ai --api-base-url https://apis.vantagecompute.ai
vantage login

# Identity
vantage whoami --json | jq '.email'

# Clusters
vantage clusters list --json | jq '.clusters[] | {name,id}'

# Switch profile
vantage profile create --name staging
vantage profile use --name staging
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (configuration, auth, validation, API) |

## Tips

- Use `--json` for automation.
- Pipe JSON output through `jq` for extraction.
- Add `-v` early when debugging authentication.
