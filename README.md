<div align="center">
<a href="https://www.vantagecompute.ai/">
  <img src="https://vantage-compute-public-assets.s3.us-east-1.amazonaws.com/branding/vantage-logo-text-black-horz.png" alt="Vantage Compute Logo" width="100" style="margin-bottom: 0.5em;"/>
</a>
</div>
<div align="center">

# Vantage CLI
A modern Python CLI tool to interface to Vantage Compute.

[![License](https://img.shields.io/badge/license-GPLv3-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/vantage-cli.svg)](https://pypi.org/project/vantage-cli/)

![Build Status](https://img.shields.io/github/actions/workflow/status/vantagecompute/vantage-cli/ci.yaml?branch=main&label=build&logo=github&style=plastic)
![GitHub Issues](https://img.shields.io/github/issues/vantagecompute/vantage-cli?label=issues&logo=github&style=plastic)
![Pull Requests](https://img.shields.io/github/issues-pr/vantagecompute/vantage-cli?label=pull-requests&logo=github&style=plastic)
![GitHub Contributors](https://img.shields.io/github/contributors/vantagecompute/vantage-cli?logo=github&style=plastic)

</br>

## 🚀 Quick Start

</div>


### Option 1: Install from PyPI (Recommended)

```bash
# Install LXD
pip install vantage-cli

# Login to Vantage
vantage login

# Check your logged in user
vantage whoami
```

### Option 2: Install from Source

```bash
# Clone and setup
git clone https://github.com/vantagecompute/vantage-cli.git
cd vantage-cli && uv sync

# Login to Vantage
uv run vantage login
```

## Deploy a Slurm Cluster

### Localhost

#### Create a Singlenode Slurm Cluster using Multipass

```bash
vantage cluster create my-slurm-multipass-cluster \
    --cloud localhost \
    --app slurm-multipass-localhost
```

#### Create a Slurm Cluster on LXD

```bash
vantage cluster create my-slurm-lxd-cluster \
    --cloud localhost \
    --app slurm-juju-localhost
```

#### Create a Slurm Cluster on MicroK8S

```bash
vantage cluster create my-slurm-microk8s-cluster \
    --cloud localhost \
    --app slurm-microk8s-localhost
```

#### Add SSSD Configuration to MicroK8S Slurm Deployment

```bash
vantage deployment slurm-microk8s-localhost deploy \
    --sssd-conf="$(juju exec --unit nfs-home/leader 'cat /etc/sssd/sssd.conf')"
```

```bash
microk8s.kubectl port-forward --address 0.0.0.0 -n jupyter-test service/proxy-public 8080:80
```

## 📚 Documentation

Visit our comprehensive documentation site:
**[vantagecompute.github.io/vantage-cli](https://vantagecompute.github.io/vantage-cli)**

- **[Installation Guide](https://vantagecompute.github.io/vantage-cli/installation/)**: Detailed setup instructions
- **[Architecture Overview](https://vantagecompute.github.io/vantage-cli/architecture/)**: How vantage-cli works
- **[Command Reference](https://vantagecompute.github.io/vantage-cli/commands/)**: Complete command documentation
- **[Troubleshooting](https://vantagecompute.github.io/vantage-cli/troubleshooting/)**: Common issues and solutions


## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/vantagecompute/vantage-cli/issues)
- **Discussions**: [GitHub Discussions](https://github.com/vantagecompute/vantage-cli/discussions)
- **Email**: [james@vantagecompute.ai](mailto:james@vantagecompute.ai)


## 📄 License

Copyright &copy; 2025 Vantage Compute Corporation

This project is licensed under the GPLv3 License - see the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ by [Vantage Compute](https://vantagecompute.ai)**
