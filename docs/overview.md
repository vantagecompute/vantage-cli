---
layout: default
title: Overview
nav_order: 1
permalink: /overview/
---

## Vantage CLI Overview

Vantage CLI is a **unified command-line interface** for interacting with the Vantage Compute platform. It provides:

- **Authentication & Token Management**: Secure OIDC device flow with cached token sets
- **Profile Management**: Create, switch, and isolate multiple environment profiles
- **Cluster Operations**: Discover, list, inspect, and manage clusters
- **Cloud Metadata**: Enumerate supported clouds / regions
- **App Commands**: Interact with platform applications and deployment helpers
- **GraphQL Integration**: Built-in async client with retries and JSON output
- **Rich UX**: Tables, panels, and JSON formatting powered by Rich

The CLI is implemented with Typer (async variant) and emphasizes reliability, clarity, and scriptability.

## Core Concepts

### Profiles
Profiles encapsulate authentication state and configuration. Each profile stores its own token cache so you can quickly switch identities or environments.

### Authentication
Run `vantage login` to complete a device authorization flow. Tokens are cached and automatically refreshed. Use `vantage whoami` to inspect the active identity (JSON capable via `--json`).

### Clusters
List clusters, inspect details, and retrieve structured data for automation. Output can be rendered as Rich tables or raw JSON.

### Apps
Application subcommands (under `vantage apps ...`) expose platform-level operations and discovery endpoints.

### GraphQL Client
All data operations route through an async GraphQL client with:
- Automatic retries & backoff
- Timeout protection
- Structured error surfacing
- Optional pretty JSON output

## Feature Highlights

| Area | Capabilities |
|------|--------------|
| Auth | Device login, token cache, logout, whoami |
| Profiles | Create, list, activate, delete, isolated credentials |
| Clusters | List, get details, JSON export |
| Apps | Namespaced commands for platform applications |
| Output | Rich tables, panels, JSON (`--json`) |
| Resilience | Retry logic, error panels, clear messaging |

## Common Commands

```bash
 # Create & activate profile
vantage profile create --name dev --set-active

# Authenticate (device code flow)
vantage login

# Show current identity
vantage whoami

# List clusters
vantage clusters list

# Get cluster details (JSON)
vantage clusters get --name demo --json

# Switch profile
vantage profile use --name staging

# Logout
vantage logout
```

## Use Cases

- **Developer Onboarding**: Fast, consistent environment bootstrap
- **Automation Pipelines**: JSON-friendly commands for CI/CD integration
- **Multi-Environment Workflows**: Seamless profile switching
- **Operational Visibility**: Quick inspection of identity & cluster state

## Next Steps

- [Installation Guide](/vantage-cli/installation/) – Install & configure
- [Architecture](/vantage-cli/architecture/) – Internals & module layout
- [Usage Examples](/vantage-cli/usage/) – Practical command patterns
- [API Reference](/vantage-cli/api-reference/) – Complete command catalogue
