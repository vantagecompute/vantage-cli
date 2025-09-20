# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Constants for Vantage CLI."""

from pathlib import Path

# Cloud and deployment type constants
CLOUD_LOCALHOST = "localhost"
CLOUD_AWS = "aws"
CLOUD_GCP = "gcp"
CLOUD_AZURE = "azure"

CLOUD_TYPE_K8S = "k8s"
CLOUD_TYPE_VM = "vm"
CLOUD_TYPE_CONTAINER = "container"


PROVIDER_SUBSTRATE_MAPPINGS = {
    "localhost": ["multipass", "microk8s", "lxd"],
    "aws": ["eks"],
    "azure": ["aks"],  # Azure Kubernetes Service
    "gcp": ["gke"],
}

VANTAGE_CLI_LOCAL_USER_BASE_DIR: Path = Path.home() / ".vantage-cli"
VANTAGE_CLI_DEV_APPS_DIR: Path = VANTAGE_CLI_LOCAL_USER_BASE_DIR / "vantage_cli_dev_apps"
VANTAGE_CLI_DEPLOYMENTS_CACHE_PATH: Path = VANTAGE_CLI_LOCAL_USER_BASE_DIR / "deployments"
VANTAGE_CLI_ACTIVE_PROFILE: Path = VANTAGE_CLI_LOCAL_USER_BASE_DIR / "active_profile"

USER_CONFIG_FILE: Path = VANTAGE_CLI_LOCAL_USER_BASE_DIR / "config.json"

USER_TOKEN_CACHE_DIR: Path = VANTAGE_CLI_LOCAL_USER_BASE_DIR / "token_cache"

# Common deployment constants
DEFAULT_CLUSTER_NAME = "vantage-cluster"
DEFAULT_MODEL_PREFIX = "vantage"
# Multipass-specific constants
MULTIPASS_ARCH = "arm64"
MULTIPASS_CLOUD_IMAGE_URL = "https://vantage-public-assets.s3.us-west-2.amazonaws.com/multipass-singlenode/multipass-singlenode.img"
MULTIPASS_CLOUD_IMAGE_DEST = Path("/tmp/multipass-singlenode.img")
MULTIPASS_CLOUD_IMAGE_LOCAL = (
    Path.home() / "multipass-singlenode" / "build" / "multipass-singlenode.img"
)

# Juju-specific constants
JUJU_SECRET_NAME = "vantage-jupyterhub-config"
JUJU_APPLICATION_NAME = "vantage-jupyterhub"

# Environment variable names
ENV_CLIENT_SECRET = "VANTAGE_CLIENT_SECRET"
ENV_OIDC_DOMAIN = "VANTAGE_OIDC_DOMAIN"
ENV_BASE_API_URL = "VANTAGE_BASE_API_URL"
ENV_TUNNEL_API_URL = "VANTAGE_TUNNEL_API_URL"

# Error messages
ERROR_NO_CLUSTER_DATA = "[red]Error: No cluster data provided.[/red]"
ERROR_NO_CLIENT_ID = "[red]Error: No client ID found in cluster data.[/red]"
ERROR_NO_CLIENT_SECRET = "[red]Error: No client secret found in cluster data.[/red]"
ERROR_MULTIPASS_NOT_FOUND = "[red]Error: 'multipass' is not installed or not found in PATH.[/red]"
