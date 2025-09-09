---
layout: home
title: "Vantage CLI - Unified Cluster & Auth Tool"
description: "Authenticate, manage profiles & clusters, deploy apps, and run GraphQL queries against Vantage Compute"
permalink: /
---

Vantage CLI is a modern async Python tool that unifies authentication, profile management, cluster operations and GraphQL querying.

## Key Features

- 🏗️ **Modern Architecture**: Built with Typer CLI framework and modular Python design
- 📦 **Relocatable Packages**: Runtime path configuration for cross-environment deployment
- ⚡ **Intelligent Caching**: Multi-layer build caching for ultra-fast rebuilds
- 🔧 **Exception Handling**: Comprehensive error management with custom exception hierarchy
- 🧪 **Tested**: 100% test coverage with 112 passing tests using proper LXD mocking
- 🚀 **GPU Support**: CUDA-enabled builds for GPU-accelerated workloads

## Quick Start {#quick-start}

### Installation

From pypi:

```bash
pip install vantage-cli
```

From source:

```bash
# Install from source
git clone https://github.com/vantagecomputevantage-cli
cd vantage-cli
uv sync
uv run vantage --help
```

### Prerequisites

```bash
# Install and configure LXD
sudo snap install lxd
sudo lxd init
```

### Basic Workflow

```bash
vantage profile create --name dev --set-active
vantage set-config --oidc-base-url https://auth.vantagecompute.ai --api-base-url https://apis.vantagecompute.ai
vantage login
vantage clusters list --json | jq '.clusters | length'
```

### Deploy Anywhere

The CLI operates against remote services; no local package relocation required.

## Architecture Overview

```text
┌──────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│  Vantage CLI     │───▶│ Auth & Profiles    │───▶│  GraphQL Client     │
│  (Typer + Rich)  │    │ Token Cache        │    │  (async retries)    │
└──────────────────┘    └────────────────────┘    └────────────────────┘
       │                    │                           │
       ▼                    ▼                           ▼
     ┌──────────────┐     ┌────────────────┐         ┌──────────────────┐
     │ Cluster Cmds │     │ App Helpers    │         │ Output (JSON/Rich)│
     └──────────────┘     └────────────────┘         └──────────────────┘
```

## Where Next?

- [Installation](/vantage-cli/installation/)
- [Commands](/vantage-cli/commands/)
- [Usage Examples](/vantage-cli/usage/)
- [Contributing](/vantage-cli/contributing/)
- [Architecture](/vantage-cli/architecture/)

---

Built by Vantage Compute.

