"""Constants for SLURM MicroK8s localhost deployment app."""

# Application name
APP_NAME = "slurm-microk8s-localhost"

# Default namespaces
DEFAULT_NAMESPACE_SLURM = "slurm"
DEFAULT_NAMESPACE_SLINKY = "slinky"
DEFAULT_NAMESPACE_PROMETHEUS = "prometheus"
DEFAULT_NAMESPACE_CERT_MANAGER = "cert-manager"

# Default release names
DEFAULT_RELEASE_CERT_MANAGER = "cert-manager"
DEFAULT_RELEASE_PROMETHEUS = "prometheus"
DEFAULT_RELEASE_SLURM_OPERATOR_CRDS = "slurm-operator-crds"
DEFAULT_RELEASE_SLURM_OPERATOR = "slurm-operator"
DEFAULT_RELEASE_SLURM_CLUSTER = "slurm"

# Repository URLs
REPO_JETSTACK_URL = "https://charts.jetstack.io"
REPO_PROMETHEUS_URL = "https://prometheus-community.github.io/helm-charts"
REPO_SLURM_URL = "https://jamesbeedy.github.io/slurm-operator"

# Chart repositories
CHART_CERT_MANAGER = "oci://quay.io/jetstack/charts/cert-manager"
CHART_PROMETHEUS = "prometheus-community/kube-prometheus-stack"
CHART_SLURM_OPERATOR_CRDS = "jamesbeedy-slinky-slurm/slurm-operator-crds"
CHART_SLURM_OPERATOR = "oci://ghcr.io/slinkyproject/charts/slurm-operator"
CHART_SLURM_CLUSTER = "oci://ghcr.io/slinkyproject/charts/slurm"

# Chart versions
VERSION_CERT_MANAGER = "v1.18.2"
VERSION_SLURM_OPERATOR_CRDS = "0.4.0"
VERSION_SLURM_OPERATOR = "0.4.0"
VERSION_SLURM_CLUSTER = "0.4.0"

# URLs for default values files
VALUES_URL_SLURM_OPERATOR = "https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm-operator/values.yaml"
VALUES_URL_SLURM_CLUSTER = "https://raw.githubusercontent.com/jamesbeedy/slurm-operator/refs/tags/v0.4.0/helm/slurm/values.yaml"
