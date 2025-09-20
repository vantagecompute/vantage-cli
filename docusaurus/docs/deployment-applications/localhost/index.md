---
id: deployment-applications-localhost
title: Localhost Deployment Applications
description: Deployment Applications for Localhost Sandbox
---

Welcome to the Localhost Deployment Applications Documentation!

We provide a suite of production-like applications configured to work on a
laptop or dev machine to help users get started using Vantage without needing
a cloud account or credit card!

After completing the prereqs for your desired use case below, you will be ready to use the Vantage CLI
to stand up localhost based compute infrastructure compatible with the Vantage platform.

## Localhost Provider Prereqs

To use the localhost deployment applications you will need to install the prereqs, depending on your use case.

### MicroK8S

We use [`microk8s`](https://canonical.com/microk8s) for a k8s sandbox on localhost.

To use the localhost deployment applications on `microk8s`, install `microk8s` first.

#### Install MicroK8S

```bash
sudo snap install microk8s --channel 1.29/stable --classic
```

#### Configure MicroK8S

```bash
sudo microk8s.enable hostpath-storage
sudo microk8s.enable dns
sudo microk8s.enable metallb:10.64.140.43-10.64.140.49

sudo usermod -a -G microk8s $USER
sudo chown -f -R $USER ~/.kube

newgrp microk8s
```

MicroK8S is now configured to work with the Vantage platform!
Proceed to [MicroK8S Deployment Applications](./microk8s.md) to start deploying!

### Multipass

Use [`multipass`](https://canonical.com/multipass) to launch a singlenode virtual-machine slurm cluster with the Vantage CLI.

To use the `multipass` localhost Deployment Applications, install `multipass` first.

#### Install Multipass

```bsh
sudo snap install multipass
```

#### Verify Multipass Installation

```bash
multipass --version
```

Multipass is now installed. Proceed to the [Multipass Singlenode Deployment Application Documentation](./multipass-singlenode.md).

### Charmed HPC

The Vantage CLI provides [charmed-hpc](https://github.com/charmed-hpc), currated to run in containers and vms on
your labtop or local machine.

#### Install [`lxd`](https://canonical.com/lxd) and [`juju`](https://canonical.com/juju)

```bsh
sudo snap install juju --channel 3.6/stable
sudo snap install lxd --channel latest/stable
```

#### Initalize LXD

```bash
sudo lxd init --auto
sudo adduser $USER lxd
lxc network set lxdbr0 ipv6.nat false
```

#### Bootstrap Juju

```bash
juju bootstrap localhost
```

At this point you have bootstrapped a localhost juju controller on a lxd container and are ready to deploy!
Proceed to the [Charmed-HPC Deployment Application Documentation](./charmed-hpc.md).
