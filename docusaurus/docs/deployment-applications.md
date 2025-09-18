---
title: Deployment Applications
description: Deployment Application Example Usage
---

The Vantage CLI comes pre-baked with automation for deploying slurm on localhost virtual machine and container
mediums called, "Deployment Applications".

## 1. Install the Vantage CLI

Install `vantage-cli` with `uv`:

```bash
uv venv
source .venv/bin/activate

uv pip install vantage-cli
```

## 2. Create a Localhost Cluster

Create a new cluster on your local machine with one of three pre-backed automations that come `vantage-cli`:

### Multipass

Deploy a single node slurm cluster in a multipass virtual-machine.

#### Multipass Prereqs

You must have multipass installed on your machine to use this command.

```bash
sudo snap install multipass
```

* [`multipass`](https://canonical.com/multipass)

#### Create the Cluster in Vantage and Deploy a Singlenode Multipass Cluster

```bash
vantage cluster create my-slurm-multipass-cluster \
    --cloud localhost \
    --app slurm-multipass-localhost
```

### Charmed HPC

Deploy a [charmed-hpc](https://github.com/charmed-hpc) slurm cluster in containers and virtual-machines on localhost.

#### Charmed HPC Prereqs

You must have a bootstrapped localhost juju controller for this command to work.

```bash
sudo snap install lxd --channel latest/stable
sudo snap install juju --channel 3/stable

juju bootstrap localhost
```

Please see the [extended setup documentation](troubleshooting.md) for setup information.

* [`lxd`](https://canonical.com/lxd)
* [`juju`](https://canonical.com/juju)

#### Create the Cluster in Vantage and Deploy Charmed HPC on Localhost

```bash
vantage cluster create my-charmed-hpc-cluster \
    --cloud localhost \
    --app slurm-juju-localhost
```

### MicroK8S

Deploy slurm to MicroK8S running on localhost.

#### MicroK8S Prereqs

Install and configure MicroK8S:

```bash
sudo snap install microk8s --channel 1.29/stable --classic

sudo microk8s.enable hostpath-storage
sudo microk8s.enable dns
sudo microk8s.enable metallb:10.64.140.43-10.64.140.49
```

More on MicroK8S:

* [`microk8s`](https://canonical.com/microk8s)

#### Create the Cluster in Vantage and SLURM to MicroK8S

```bash
vantage cluster create my-slurm-microk8s-cluster \
    --cloud localhost \
    --app slurm-microk8s-localhost
```

Connect to the cluster following deployment:

```bash
SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ports[0].port}')"
## Assuming your public SSH key was configured in `login.rootSshAuthorizedKeys`.
ssh -p ${SLURM_LOGIN_PORT:-22} root@${SLURM_LOGIN_IP}
```

Using identity user:

```bash
ssh -p ${SLURM_LOGIN_PORT:-22} ${USER}@${SLURM_LOGIN_IP}
```

## 3. List Vantage Clusters

```bash
vantage clusters
```

## 4. Create a Notebook

```bash
vantage notebook create mynotebook --cluster my-slurm-multipass-cluster --partition compute
```

---
See also: [Commands](/cli/commands) | [Troubleshooting](/cli/troubleshooting)
