---
title: "Vantage CLI - Overview"
description: "Authenticate, manage profiles & clusters, deploy apps, and run GraphQL queries against Vantage Compute"
slug: /
---

## The unified command-line interface for Vantage Compute

Vantage CLI is a modern async Python tool that unifies authentication, profile management, cluster operations and GraphQL querying against the Vantage Compute platform.

- 🏗️ **Modern Architecture**: Built with Typer CLI framework and modular Python design
- 📦 **Relocatable Packages**: Runtime path configuration for cross-environment deployment
- 🔧 **Exception Handling**: Comprehensive error management with custom exception hierarchy
- 🧪 **Tested**: 100% test coverage with +400 passing tests

### Quick Start

Install from pypi:

```bash
pip install vantage-cli
```

Or from source:

```bash
git clone https://github.com/vantagecomputevantage-cli
cd vantage-cli
uv sync
uv run vantage --help
```

#### Authenticate

Authenticate against the Vantage platform using the `login` command.

```bash
vantage login
```

#### Create a Multipass Singlenode Cluster

```bash
vantage cluster create my-slurm-multipass-cluster \
    --cloud localhost \
    --deploy slurm-multipass-localhost
```

#### Create a Slurm Cluster in LXD Containers using Juju

```bash
vantage cluster create my-slurm-lxd-cluster \
    --cloud localhost \
    --deploy slurm-juju-localhost
```

#### Create a Slurm Cluster on MicroK8S

```bash
vantage cluster create my-slurm-microk8s-cluster \
    --cloud localhost \
    --deploy slurm-microk8s-locahost
```