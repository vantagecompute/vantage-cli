This app deploys the slurm-operator to microk8s for a fully functional slurm on k8s on localhost.

For more on the slurm-operator see: https://github.com/SlinkyProject/slurm-operator
For more on microk8s see <https://microk8s>

### Install and Configure microk8s
```bash
sudo snap install microk8s --channel 1.29-strict/stable

sudo microk8s.enable hostpath-storage
sudo microk8s.enable dns
sudo microk8s.enable metallb:10.64.140.43-10.64.140.49
```

### install slurm operator
```bash
sudo microk8s.helm repo add jetstack https://charts.jetstack.io
sudo microk8s.helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
sudo microk8s.helm repo update

sudo microk8s.helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace
sudo microk8s.helm install prometheus prometheus-community/kube-prometheus-stack --namespace prometheus --create-namespace
sudo microk8s.helm install slurm-operator-crds oci://ghcr.io/slinkyproject/charts/slurm-operator-crds

curl -L https://raw.githubusercontent.com/SlinkyProject/slurm-operator/refs/tags/v0.4.0/helm/slurm-operator/values.yaml -o values-operator.yaml
sudo microk8s.helm install slurm-operator oci://ghcr.io/slinkyproject/charts/slurm-operator --values=values-operator.yaml --version=0.4.0 --namespace=slinky --create-namespace

microk8s.kubectl --namespace=slinky get pods

# Install SLURM Cluster
curl -L https://raw.githubusercontent.com/SlinkyProject/slurm-operator/refs/tags/v0.4.0/helm/slurm/values.yaml -o values-slurm.yaml

sudo microk8s.helm install slurm oci://ghcr.io/slinkyproject/charts/slurm --values=values-slurm.yaml --version=0.4.0 --namespace=slurm --create-namespace

microk8s.kubectl --namespace=slurm get pods
```


### Testing
```bash
SLURM_LOGIN_IP="$(kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
SLURM_LOGIN_PORT="$(kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ports[0].port}')"
## Assuming your public SSH key was configured in `login.rootSshAuthorizedKeys`.
ssh -p ${SLURM_LOGIN_PORT:-22} root@${SLURM_LOGIN_IP}
## Assuming SSSD is configured.
ssh -p ${SLURM_LOGIN_PORT:-22} ${USER}@${SLURM_LOGIN_IP}
```
