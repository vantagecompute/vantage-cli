---
layout: home
title: "Vantage CLI - Unified Cluster & Auth Tool"
description: "Authenticate, manage profiles & clusters, deploy apps, and run GraphQL queries against Vantage Compute"
permalink: /
---

## 🚀 Vantage CLI

### The unified command-line interface for Vantage Compute

Vantage CLI is a modern async Python tool that unifies authentication, profile management, cluster operations and GraphQL querying against the Vantage Compute platform.

**[Get Started →](installation)** | **[View on GitHub →](https://github.com/vantagecompute/vantage-cli)**

---

## Key Features

- 🏗️ **Modern Architecture**: Built with Typer CLI framework and modular Python design
- 📦 **Relocatable Packages**: Runtime path configuration for cross-environment deployment
- 🔧 **Exception Handling**: Comprehensive error management with custom exception hierarchy
- 🧪 **Tested**: 100% test coverage with 363 passing tests

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

- [Installation](installation)
- [Commands](commands)
- [Usage Examples](usage)
- [Contributing](contributing)
- [Architecture](architecture)

---

**Made with ❤️ by [Vantage Compute](https://vantagecompute.ai)**
