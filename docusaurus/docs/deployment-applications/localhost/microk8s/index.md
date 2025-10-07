---
title: Slurm on MicroK8S 
description: Deploy slurm on MicroK8s Kubernetes cluster for localhost development
---

Deploy a production-like slurm cluster in K8S on localhost using MicroK8S, a lightweight Kubernetes distribution perfect for development and testing.

## Overview

MicroK8s provides a complete Kubernetes experience that can be deployed locally with:

- **MicroK8s**: Lightweight Kubernetes distribution
- **Helm**: Package manager for Kubernetes applications
- **SLURM**: HPC workload management on Kubernetes
- **JupyterHub**: Multi-user Jupyter notebook environment
- **Keycloak**: Identity and access management
- **Vantage CLI**: Streamlined deployment and management

## Prerequisites

Before proceeding, ensure you have completed the MicroK8s prerequisites from the localhost deployment applications overview.

### Required Components

- MicroK8s (1.29/stable)
- Enabled addons: hostpath-storage, dns, metallb
- Vantage CLI
- kubectl access configured

## Available Applications

### SLURM MicroK8s Localhost

Deploy a SLURM cluster on MicroK8s using Helm charts.

```bash
vantage app deploy slurm-microk8s-localhost
```

**Features:**

- Containerized SLURM cluster on Kubernetes
- Horizontal pod autoscaling
- Persistent volume storage
- Service mesh integration
- Cloud-native monitoring

### JupyterHub MicroK8s Localhost

Deploy a multi-user JupyterHub environment for data science and development.

```bash
vantage app deploy jupyterhub-microk8s-localhost
```

**Features:**

- Multi-user Jupyter notebook environment
- GPU support (if available)
- Custom Docker images
- Persistent user storage
- OAuth integration

### Keycloak MicroK8s Localhost

Deploy Keycloak for identity and access management.

```bash
vantage app deploy keycloak-microk8s-localhost
```

**Features:**

- Single Sign-On (SSO)
- User federation
- Identity brokering
- Multi-factor authentication
- LDAP/Active Directory integration

### Full MicroK8s Localhost

Deploy the complete Vantage platform stack on MicroK8s.

```bash
vantage app deploy full-microk8s-localhost
```

**Components:**

- SLURM cluster with job scheduling
- JupyterHub for interactive computing
- Keycloak for authentication
- Monitoring and logging stack
- Service mesh for communication

## Quick Start

### 1. Verify MicroK8s Installation

```bash
# Check MicroK8s status
microk8s status

# Verify kubectl access
microk8s kubectl get nodes

# Check enabled addons
microk8s status --addon
```

### 2. Deploy Your First Application

```bash
# Deploy SLURM cluster
vantage app deploy slurm-microk8s-localhost

# Monitor deployment
vantage app status slurm-microk8s-localhost

# Watch pods come online
microk8s kubectl get pods -w
```

### 3. Access Applications

```bash
# Get service endpoints
vantage app info slurm-microk8s-localhost

# Port forward to access locally
microk8s kubectl port-forward svc/slurm-controller 8080:80
```

## Configuration

### Resource Management

```bash
# Configure resource limits
vantage app deploy slurm-microk8s-localhost \
  --set resources.limits.memory=4Gi \
  --set resources.limits.cpu=2

# Enable autoscaling
vantage app config slurm-microk8s-localhost \
  --autoscaling-enabled=true \
  --min-replicas=1 \
  --max-replicas=5
```

### Storage Configuration

```bash
# Configure persistent storage
vantage app config slurm-microk8s-localhost \
  --storage-class=hostpath \
  --storage-size=10Gi

# Enable shared storage
microk8s enable hostpath-storage
```

### Networking

```bash
# Configure LoadBalancer services
vantage app config slurm-microk8s-localhost \
  --service-type=LoadBalancer \
  --load-balancer-ip=10.64.140.43

# Enable ingress
microk8s enable ingress
vantage app config slurm-microk8s-localhost \
  --ingress-enabled=true \
  --ingress-host=slurm.localhost
```

## Management Commands

### Application Lifecycle

```bash
# List deployed applications
vantage app list

# Start application
vantage app start slurm-microk8s-localhost

# Stop application
vantage app stop slurm-microk8s-localhost

# Update application
vantage app update slurm-microk8s-localhost

# Delete application
vantage app delete slurm-microk8s-localhost
```

### Scaling Operations

```bash
# Scale compute nodes
vantage app scale slurm-microk8s-localhost --compute-nodes=3

# Scale JupyterHub user capacity
vantage app scale jupyterhub-microk8s-localhost --max-users=50
```

### Monitoring and Logs

```bash
# View application logs
vantage app logs slurm-microk8s-localhost

# Follow logs in real-time
vantage app logs slurm-microk8s-localhost --follow

# Get detailed status
vantage app describe slurm-microk8s-localhost
```

## Kubernetes Integration

### Direct kubectl Commands

```bash
# View all resources
microk8s kubectl get all -n vantage

# Describe pods
microk8s kubectl describe pod -l app=slurm-controller

# Execute commands in pods
microk8s kubectl exec -it slurm-controller-0 -- /bin/bash

# View persistent volumes
microk8s kubectl get pv,pvc
```

### Helm Integration

```bash
# List Helm releases
microk8s helm list

# Get Helm values
microk8s helm get values slurm-microk8s-localhost

# Upgrade with new values
microk8s helm upgrade slurm-microk8s-localhost ./chart --values custom-values.yaml
```

## Troubleshooting

### Common Issues

**Pod Startup Issues:**

```bash
# Check pod status
microk8s kubectl get pods -o wide

# Describe problematic pods
microk8s kubectl describe pod <pod-name>

# View pod logs
microk8s kubectl logs <pod-name> --previous
```

**Storage Issues:**

```bash
# Check PVC status
microk8s kubectl get pvc

# Describe storage issues
microk8s kubectl describe pvc <pvc-name>

# Check available storage
df -h /var/snap/microk8s/common/default-storage
```

**Network Issues:**

```bash
# Check service endpoints
microk8s kubectl get endpoints

# Test service connectivity
microk8s kubectl run test-pod --image=busybox --rm -it -- nslookup kubernetes.default

# Check MetalLB configuration
microk8s kubectl get configmap config -n metallb-system -o yaml
```

### Performance Optimization

**Resource Allocation:**

```bash
# Monitor resource usage
microk8s kubectl top nodes
microk8s kubectl top pods

# Set resource requests and limits
vantage app config slurm-microk8s-localhost \
  --cpu-request=500m \
  --memory-request=1Gi \
  --cpu-limit=2 \
  --memory-limit=4Gi
```

**Node Optimization:**
```bash
# Enable GPU support (if available)
microk8s enable gpu

# Configure node affinity
vantage app config slurm-microk8s-localhost \
  --node-selector=kubernetes.io/arch=amd64
```

## Advanced Topics

### Custom Images

```bash
# Build custom SLURM image
docker build -t my-slurm:latest .

# Deploy with custom image
vantage app deploy slurm-microk8s-localhost \
  --set image.repository=my-slurm \
  --set image.tag=latest
```

### Service Mesh Integration

```bash
# Enable Istio service mesh
microk8s enable istio

# Deploy with service mesh
vantage app deploy slurm-microk8s-localhost --enable-service-mesh
```

### Monitoring Stack

```bash
# Enable Prometheus monitoring
microk8s enable prometheus

# Access Grafana dashboard
microk8s kubectl port-forward -n monitoring svc/grafana 3000:3000
```

## Integration Examples

### JupyterHub + SLURM

```bash
# Deploy integrated stack
vantage app deploy full-microk8s-localhost

# Configure JupyterHub to submit to SLURM
vantage app config jupyterhub-microk8s-localhost \
  --slurm-controller=slurm-controller.vantage.svc.cluster.local
```

### Keycloak Authentication

```bash
# Configure SSO for applications
vantage app config slurm-microk8s-localhost \
  --auth-provider=keycloak \
  --keycloak-url=http://keycloak.localhost
```

## Next Steps

- [Submit Jobs via Kubernetes](../../../usage.md#7-job-management-workflow)
- [Private Vantage Installation](../../../private-vantage-installation.md)
- [Monitoring Setup](../../../usage.md#7-job-management-workflow)

## Support

For MicroK8s-specific issues:

- [Troubleshooting Guide](../../../troubleshooting.md)
- [Contact Support](../../../contact.md)
- [Community Support](../../../contact.md)
