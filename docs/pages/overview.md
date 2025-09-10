---
title: Overview
description: Overview of Vantage CLI features and capabilities
---

## Vantage CLI Overview

Vantage CLI is a **comprehensive command-line interface** for interacting with the Vantage Compute platform. It provides:

- **Authentication & Token Management**: Secure OIDC device flow with cached token sets
- **Profile Management**: Create, switch, and isolate multiple environment profiles
- **Cluster Operations**: Create, manage, and monitor compute clusters
- **Cloud Provider Integration**: Multi-cloud support (AWS, GCP, Azure, on-premises)
- **Application Deployment**: Deploy and manage HPC applications and workloads
- **Job Management**: Submit, monitor, and manage computational jobs
- **Resource Management**: Manage storage, networks, and infrastructure
- **Team Collaboration**: Team management with role-based access
- **License Management**: Software license tracking and server management
- **Notebook Support**: Jupyter notebook management and execution
- **Federation**: Multi-cluster federation and resource sharing
- **Support Integration**: Built-in support ticket management
- **GraphQL Integration**: Built-in async client with retries and JSON output
- **Rich UX**: Tables, panels, and JSON formatting powered by Rich

The CLI is implemented with AsyncTyper and emphasizes reliability, scalability, and enterprise-grade functionality.

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
| **Authentication** | Device login, token cache, logout, whoami |
| **Profiles** | Create, list, activate, delete, isolated credentials |
| **Cloud Providers** | AWS, GCP, Azure, on-premises configuration management |
| **Clusters** | Create, list, get details, delete, federation support |
| **Applications** | Deploy HPC applications, list available services |
| **Job Management** | Script management, job submission, templates, monitoring |
| **Storage** | Volume creation, attachment, management across clouds |
| **Networking** | Virtual networks, subnets, security groups |
| **Teams** | User management, role-based access, collaboration |
| **Notebooks** | Jupyter notebook deployment and management |
| **Licenses** | Software license tracking, server management |
| **Support** | Integrated ticket creation and management |
| **Output** | Rich tables, panels, JSON (`--json`) for all commands |
| **Resilience** | Retry logic, error panels, clear messaging |

## Common Commands

```bash
# Setup and authentication
vantage profile create --name dev --set-active
vantage login
vantage whoami

# Cloud and cluster management
vantage cloud add --name aws-prod --provider aws
vantage cluster create --name compute-01 --cloud aws-prod
vantage clusters  # List clusters (alias)

# Application deployment
vantage apps  # List available applications
vantage app deploy --app slurm-multipass-singlenode

# Job management
vantage job script create --name analysis --file ./script.py
vantage job submission create --script script-123

# Resource management
vantage storage create --name data-vol --size 100GB
vantage networks  # List networks (alias)

# Team collaboration
vantage team create --name ml-research
vantage teams  # List teams (alias)

# Get details (JSON output)
vantage cluster get --name demo --json
vantage job submission get --id sub-123 --json
```

## Use Cases

- **Enterprise HPC Management**: Complete lifecycle management of compute clusters
- **Multi-Cloud Deployment**: Unified interface across AWS, GCP, Azure, and on-premises
- **Research Computing**: Job submission, notebook management, and resource allocation
- **Team Collaboration**: Role-based access control and shared resource management
- **Automation Pipelines**: JSON-friendly commands for CI/CD integration
- **Developer Onboarding**: Fast, consistent environment bootstrap
- **Infrastructure Operations**: Storage, network, and license management
- **Support Integration**: Built-in ticketing and troubleshooting workflows
- **Multi-Environment Workflows**: Seamless profile switching between dev/staging/prod

## Next Steps

- [Installation Guide](/vantage-cli/installation/) – Install & configure
- [Commands Reference](/vantage-cli/commands/) – Complete command catalogue
- [Usage Examples](/vantage-cli/usage/) – Practical command patterns
- [Architecture](/vantage-cli/architecture/) – Internals & module layout
- [Troubleshooting](/vantage-cli/troubleshooting/) – Common issues and solutions
