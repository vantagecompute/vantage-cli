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
"""Constants for JupyterHub MicroK8s localhost deployment app."""

# Default JupyterHub configuration
DEFAULT_NAMESPACE = "jupyterhub"
DEFAULT_RELEASE_NAME = "jupyterhub"
DEFAULT_JUPYTERHUB_VERSION = "3.3.7"
DEFAULT_SLURM_IMAGE = "ghcr.io/slinkyproject/login:25.05-ubuntu24.04"
DEFAULT_NOTEBOOK_IMAGE = "localhost:32000/slurm-notebook:latest"

# Keycloak OAuth configuration
DEFAULT_KEYCLOAK_URL = "http://192.168.7.5:8081"
DEFAULT_KEYCLOAK_REALM = "master"
DEFAULT_KEYCLOAK_CLIENT_ID = "jupyterhub"

# Slurm integration
SLURM_CONTROLLER_FQDN = "slurm-controller.slurm.svc.cluster.local:6817"
