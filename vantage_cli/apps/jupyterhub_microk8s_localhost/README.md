# jupyterhub-microk8s-localhost

Deploy Jupyterhub in Microk8s on localhost.

## Getting Started

Use the Vantage CLI to deploy Vantage compatible Jupyterhub on Microk8s.

### Install Vantage CLI

```bash
uv venv
source .venv/bin/activate

uv pip install vantage-cli
```

### Deploy Jupyterhub

```bash
uv run vantage deployment create jupyterhub-microk8s-localhost --dev-run
```

### Following Deployment Run the Proxy to Access

```bash
microk8s kubectl port-forward --address 0.0.0.0     -n keycloak service/keycloak 8080:80
```