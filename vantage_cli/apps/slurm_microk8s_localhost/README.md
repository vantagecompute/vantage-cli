This app deploys the slurm-operator to microk8s for a fully functional slurm on k8s on localhost.

For more on the slurm-operator see: https://github.com/SlinkyProject/slurm-operator
For more on microk8s see <https://microk8s>

### Install and Configure MicroK8S
```bash
sudo snap install microk8s --channel 1.29/stable --classic

sudo microk8s.enable hostpath-storage
sudo microk8s.enable dns
sudo microk8s.enable metallb:10.64.140.43-10.64.140.49
```

### Install SLURM on MickroK8S
```bash
microk8s.helm repo add jetstack https://charts.jetstack.io
microk8s.helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
microk8s.helm repo add jamesbeedy-slinky-slurm https://jamesbeedy.github.io/slurm-operator

microk8s.helm repo update

# Cert Manager
microk8s.helm install cert-manager oci://quay.io/jetstack/charts/cert-manager \
    --set 'crds.enabled=true' \
    --namespace cert-manager \
    --create-namespace \
    --version v1.18.2

# Prometheus
microk8s.helm install prometheus prometheus-community/kube-prometheus-stack \
    --namespace prometheus \
    --create-namespace

# Install slurm crds
# Patch until the crds are available upstream
microk8s.helm install slurm-operator-crds jamesbeedy-slinky-slurm/slurm-operator-crds --version 0.4.0

# Install slurm-operator
curl -L https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm-operator/values.yaml -o values-operator.yaml
microk8s.helm install slurm-operator oci://ghcr.io/slinkyproject/charts/slurm-operator --values=values-operator.yaml --version=0.4.0 --namespace=slinky --create-namespace

# Install SLURM Cluster
curl -L https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm/values.yaml -o values-slurm.yaml
microk8s.helm install slurm oci://ghcr.io/slinkyproject/charts/slurm --values=values-slurm.yaml --version=0.4.0 --namespace=slurm --create-namespace
```


### Testing
Watch the deployment spin up

```bash
microk8s.kubectl --namespace=slurm get pods
microk8s.kubectl --namespace=slurm get pods -l helm.sh/chart=slurm-0.4.0 --watch
```

Access the login node
```bash
SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ports[0].port}')"
## Assuming your public SSH key was configured in `login.rootSshAuthorizedKeys`.
ssh -p ${SLURM_LOGIN_PORT:-22} root@${SLURM_LOGIN_IP}
## Assuming SSSD is configured.
ssh -p ${SLURM_LOGIN_PORT:-22} ${USER}@${SLURM_LOGIN_IP}
```
