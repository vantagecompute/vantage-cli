---
title: Charmed HPC
description: Deploy a Charmed HPC clusters on localhost using LXD and Juju
---

Deploy production-like HPC clusters on your localhost using Charmed HPC, LXD containers, and Juju orchestration.

## Overview

Charmed HPC provides a complete High Performance Computing stack that can be deployed locally using:

- **LXD**: Container hypervisor for lightweight virtualization
- **Juju**: Application orchestration and lifecycle management
- **SLURM**: Workload manager and job scheduler
- **Vantage CLI**: Streamlined deployment and management

## Prerequisites

Before proceeding, ensure you have completed the Charmed HPC prerequisites from the localhost deployment applications overview.

### Required Components

- LXD (latest/stable)
- Juju (3.6/stable)
- Vantage CLI
- Bootstrap Juju controller on localhost

## Available Applications

### SLURM Juju Localhost

Deploy a complete SLURM cluster using Juju charms on LXD containers.

```bash
vantage app deploy slurm-juju-localhost
```

**Features:**

- Multi-node SLURM cluster in containers
- Head node with scheduler and controller
- Compute nodes for job execution
- Shared filesystem
- User management integration

**Architecture:**

- **Controller**: SLURM controller daemon (slurmctld)
- **Database**: SLURM accounting database (slurmdbd)
- **Compute Nodes**: SLURM compute daemon (slurmd)
- **Login Node**: User access point

## Quick Start

### 1. Deploy SLURM Cluster

```bash
# Deploy the SLURM cluster
vantage app deploy slurm-juju-localhost

# Monitor deployment progress
vantage app status slurm-juju-localhost
```

### 2. Access Your Cluster

```bash
# Get cluster connection details
vantage app info slurm-juju-localhost

# Connect to login node
juju ssh slurm-login/0
```

### 3. Submit Test Jobs

```bash
# Simple test job
srun --nodes=1 --ntasks=1 hostname

# Batch job example
sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=test-job
#SBATCH --output=test-output.txt
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:05:00

echo "Hello from SLURM on localhost!"
hostname
date
EOF
```

## Configuration

### Cluster Sizing

Customize your cluster configuration:

```bash
# Deploy with specific node count
vantage app deploy slurm-juju-localhost --config nodes=4

# Scale compute nodes
vantage app scale slurm-juju-localhost --compute-nodes=6
```

### Resource Allocation

```bash
# Configure memory and CPU limits
vantage app config slurm-juju-localhost \
  --memory-per-node=4GB \
  --cpus-per-node=2
```

## Management Commands

### Cluster Operations

```bash
# Start cluster
vantage app start slurm-juju-localhost

# Stop cluster
vantage app stop slurm-juju-localhost

# Restart cluster
vantage app restart slurm-juju-localhost

# Delete cluster
vantage app delete slurm-juju-localhost
```

### Monitoring

```bash
# Check cluster status
vantage app status slurm-juju-localhost

# View logs
vantage app logs slurm-juju-localhost

# Get detailed information
vantage app describe slurm-juju-localhost
```

## Troubleshooting

### Common Issues

**Deployment Failures:**
```bash
# Check juju status
juju status

# View application logs
juju debug-log --include slurm-controller

# Retry failed deployments
vantage app deploy slurm-juju-localhost --force
```

**Container Issues:**
```bash
# List LXD containers
lxc list

# Check container logs
lxc logs <container-name>

# Restart containers
lxc restart <container-name>
```

**Network Connectivity:**

```bash
# Check LXD network
lxc network show lxdbr0

# Test container connectivity
lxc exec <container-name> -- ping google.com
```

### Performance Tuning

**Container Resources:**

```bash
# Increase container memory
lxc config set <container-name> limits.memory 4GB

# Set CPU limits
lxc config set <container-name> limits.cpu 2
```

**SLURM Configuration:**

```bash
# Access SLURM configuration
juju ssh slurm-controller/0
sudo nano /etc/slurm/slurm.conf

# Restart SLURM services
sudo systemctl restart slurmctld
```

## Advanced Topics

### Custom Charms

Deploy custom or development charms:

```bash
# Deploy from local charm
vantage app deploy slurm-juju-localhost --charm-path=./my-slurm-charm

# Use specific charm revision
vantage app deploy slurm-juju-localhost --charm-revision=25
```

### Integration

**Storage Integration:**

```bash
# Add shared storage
juju deploy ceph-osd --storage osd-devices=/dev/sdb
juju relate slurm-controller ceph-osd
```

**Monitoring Integration:**

```bash
# Add Prometheus monitoring
vantage app deploy prometheus-localhost
vantage app relate slurm-juju-localhost prometheus-localhost
```

## Next Steps

- [Submit Jobs to Your Cluster](../../../usage.md#7-job-management-workflow)
- [Monitor Cluster Performance](../../../usage.md#7-job-management-workflow)
- [Private Vantage Installation](../../../private-vantage-installation.md)

## Support

For issues specific to Charmed HPC localhost deployments:

- [Troubleshooting Guide](../../../troubleshooting.md)
- [Community Support](../../../contact.md)
- [Charmed HPC Documentation](https://charmed-hpc.readthedocs.io/)
