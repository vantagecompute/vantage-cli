---
title: Multipass Single-node Slurm Cluster
description: Deploy a single-node SLURM cluster using a Multipass virtual machine
---

Deploy a complete single-node SLURM cluster using a Multipass virtual machine for isolated HPC development and testing.

## Overview

Multipass provides lightweight Ubuntu virtual machines that can host complete HPC environments:

- **Multipass**: Ubuntu VM manager by Canonical
- **SLURM**: Complete HPC workload manager in a single VM
- **Shared Storage**: NFS or local filesystem sharing
- **Development Tools**: Compilers, libraries, and development environment
- **Vantage CLI**: Streamlined VM and cluster management

## Prerequisites

Before proceeding, ensure you have completed the Multipass prerequisites from the localhost deployment applications overview.

### Required Components

- Multipass installed and running
- Sufficient system resources (4GB RAM, 20GB disk minimum)
- Vantage CLI
- Network connectivity for package installation

## Available Applications

### SLURM Multipass Localhost

Deploy a complete single-node SLURM cluster in an Ubuntu VM.

```bash
vantage app deploy slurm-multipass-localhost
```

**Features:**

- Complete SLURM installation in single VM
- Controller, database, and compute in one node
- Pre-configured user environment
- Development tools and compilers
- Shared home directory
- SSH access configured

**Architecture:**

- **Single VM**: Ubuntu 22.04 LTS
- **SLURM Controller**: slurmctld daemon
- **SLURM Database**: slurmdbd with MySQL
- **Compute Daemon**: slurmd on localhost
- **Munge**: Authentication service

## Quick Start

### 1. Deploy SLURM VM

```bash
# Deploy single-node SLURM cluster
vantage app deploy slurm-multipass-localhost

# Monitor deployment progress
vantage app status slurm-multipass-localhost

# Wait for VM to be ready
multipass list
```

### 2. Access Your Cluster

```bash
# Get VM connection details
vantage app info slurm-multipass-localhost

# SSH into the VM
multipass shell slurm-node

# Or use direct SSH
ssh ubuntu@$(multipass info slurm-node --format json | jq -r '.info."slurm-node".ipv4[0]')
```

### 3. Submit Test Jobs

```bash
# Enter the VM
multipass shell slurm-node

# Check SLURM status
sinfo
squeue

# Submit simple job
srun --nodes=1 --ntasks=1 hostname

# Submit batch job
sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=hello-world
#SBATCH --output=hello-output.txt
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=00:01:00

echo "Hello from SLURM in Multipass!"
hostname
uname -a
date
EOF
```

## Configuration

### VM Specifications

Customize VM resources during deployment:

```bash
# Deploy with custom resources
vantage app deploy slurm-multipass-localhost \
  --cpus=4 \
  --memory=8G \
  --disk=50G

# Deploy with specific Ubuntu version
vantage app deploy slurm-multipass-localhost \
  --image=22.04 \
  --name=my-slurm-cluster
```

### SLURM Configuration

```bash
# Configure SLURM partitions
vantage app config slurm-multipass-localhost \
  --partition-name=compute \
  --max-time=24:00:00 \
  --max-nodes=1

# Set resource limits
vantage app config slurm-multipass-localhost \
  --cpus-per-node=4 \
  --memory-per-cpu=2048
```

### Network Configuration

```bash
# Configure port forwarding
vantage app config slurm-multipass-localhost \
  --forward-port=6817:6817 \
  --forward-port=6818:6818

# Set up bridge networking
vantage app config slurm-multipass-localhost \
  --network=bridge \
  --network-name=mp-bridge
```

## Management Commands

### VM Lifecycle

```bash
# Start VM
vantage app start slurm-multipass-localhost
# OR
multipass start slurm-node

# Stop VM
vantage app stop slurm-multipass-localhost
# OR
multipass stop slurm-node

# Restart VM
vantage app restart slurm-multipass-localhost
# OR
multipass restart slurm-node

# Delete VM
vantage app delete slurm-multipass-localhost
# OR
multipass delete slurm-node --purge
```

### VM Information

```bash
# Get VM details
vantage app info slurm-multipass-localhost
# OR
multipass info slurm-node

# List all VMs
multipass list

# Check VM resource usage
multipass exec slurm-node -- htop
```

### File Transfer

```bash
# Copy files to VM
multipass transfer myfile.txt slurm-node:/home/ubuntu/

# Copy files from VM
multipass transfer slurm-node:/home/ubuntu/results.txt ./

# Mount local directory in VM
multipass mount ./workspace slurm-node:/mnt/workspace
```

## SLURM Operations

### Cluster Management

```bash
# SSH into VM
multipass shell slurm-node

# Check cluster status
sinfo -N -l
slurmd -D

# View job queue
squeue -u $USER

# Check accounting
sacct -X --starttime=today
```

### Job Submission

```bash
# Interactive job
srun --pty bash

# Batch job with resources
sbatch --nodes=1 --ntasks-per-node=2 --time=01:00:00 my-script.sh

# Array job
sbatch --array=1-10 array-job.sh

# GPU job (if GPU passthrough configured)
sbatch --gres=gpu:1 gpu-job.sh
```

### Monitoring

```bash
# Real-time job monitoring
watch squeue

# System monitoring
htop
iotop
nvidia-smi  # if GPU available
```

## Development Environment

### Software Installation

```bash
# SSH into VM
multipass shell slurm-node

# Install development tools
sudo apt update
sudo apt install -y build-essential gfortran python3-dev

# Install HPC libraries
sudo apt install -y openmpi-bin openmpi-dev libopenmpi-dev
sudo apt install -y libfftw3-dev libhdf5-dev

# Install Python packages
pip3 install numpy scipy matplotlib mpi4py
```

### Compiler Setup

```bash
# GCC compiler
gcc --version
gfortran --version

# Intel oneAPI (if needed)
wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB | sudo apt-key add -
sudo add-apt-repository "deb https://apt.repos.intel.com/oneapi all main"
sudo apt install intel-oneapi-toolkit

# Module system
sudo apt install environment-modules
```

### Storage Configuration

```bash
# Set up shared storage
sudo mkdir -p /shared
sudo chown ubuntu:ubuntu /shared

# Configure NFS (for multi-node expansion)
sudo apt install nfs-kernel-server
sudo echo "/shared *(rw,sync,no_subtree_check)" >> /etc/exports
sudo systemctl restart nfs-kernel-server
```

## Troubleshooting

### VM Issues

**VM Won't Start:**

```bash
# Check Multipass status
multipass version
sudo snap logs multipass

# Restart Multipass service
sudo snap restart multipass

# Check system resources
free -h
df -h
```

**Network Issues:**

```bash
# Check VM connectivity
multipass exec slurm-node -- ping google.com

# Reset network
multipass stop slurm-node
multipass start slurm-node

# Check bridge configuration
brctl show
```

### SLURM Issues

**SLURM Services Not Running:**

```bash
# SSH into VM
multipass shell slurm-node

# Check service status
sudo systemctl status slurmctld
sudo systemctl status slurmd
sudo systemctl status slurmdbd

# Restart services
sudo systemctl restart slurmctld slurmd slurmdbd

# Check logs
sudo journalctl -u slurmctld -f
```

**Job Submission Issues:**

```bash
# Check node status
sinfo -N
scontrol show node localhost

# Test basic functionality
srun --nodes=1 --ntasks=1 /bin/true

# Check user permissions
id
groups
```

### Performance Issues

**Resource Constraints:**

```bash
# Monitor resource usage
htop
iostat 1

# Adjust VM resources
multipass stop slurm-node
# Edit VM config or redeploy with more resources
vantage app deploy slurm-multipass-localhost --cpus=8 --memory=16G
```

**Storage Issues:**

```bash
# Check disk usage
df -h
du -sh /home/ubuntu/*

# Clean up old files
sudo apt autoremove
sudo apt autoclean
```

## Advanced Topics

### GPU Passthrough

```bash
# Stop VM
multipass stop slurm-node

# Configure GPU passthrough (requires host GPU)
# Note: GPU passthrough support varies by platform

# Install NVIDIA drivers in VM
sudo apt install nvidia-driver-525
sudo apt install nvidia-cuda-toolkit

# Configure SLURM for GPU
sudo nano /etc/slurm/slurm.conf
# Add: NodeName=localhost CPUs=4 Gres=gpu:1
# Add: GresTypes=gpu
```

### Multi-Node Simulation

```bash
# Deploy multiple VMs
vantage app deploy slurm-multipass-localhost --name=head-node
vantage app deploy slurm-multipass-localhost --name=compute-node-1 --compute-only
vantage app deploy slurm-multipass-localhost --name=compute-node-2 --compute-only

# Configure cluster networking
vantage app config slurm-multipass-localhost --cluster-nodes=head-node,compute-node-1,compute-node-2
```

### Custom Images

```bash
# Create custom image with pre-installed software
multipass launch --name template-vm
multipass shell template-vm
# Install required software
# Configure environment

# Create snapshot (if supported)
# Or create custom cloud-init
vantage app deploy slurm-multipass-localhost --cloud-init=./custom-init.yaml
```

## Integration Examples

### VS Code Remote Development

```bash
# Install VS Code Server in VM
multipass shell slurm-node
wget -O- https://aka.ms/install-vscode-server/setup.sh | sh

# Connect from VS Code using Remote-SSH
# Host: ubuntu@$(multipass info slurm-node --format json | jq -r '.info."slurm-node".ipv4[0]')
```

### Jupyter Notebook

```bash
# Install Jupyter in VM
multipass shell slurm-node
pip3 install jupyter

# Start Jupyter with SLURM integration
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser

# Access via port forwarding
# Jupyter will be available at localhost:8888
```

### Data Science Stack

```bash
# Install data science tools
multipass shell slurm-node
sudo apt install -y r-base
pip3 install pandas scikit-learn tensorflow

# Install R packages
R -e "install.packages(c('ggplot2', 'dplyr', 'shiny'))"
```

## Next Steps

- Scale to Multi-Node
- HPC Workloads
- Production Deployment
- Advanced Configuration

## Support

For Multipass single-node deployment support:

- [Troubleshooting Guide](../../../troubleshooting.md)
- [Community Support](../../../contact.md)
- [Multipass Documentation](https://multipass.run/docs)
