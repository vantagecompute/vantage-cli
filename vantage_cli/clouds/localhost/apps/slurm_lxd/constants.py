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
"""Constants for SLURM LXD localhost deployment."""

APP_NAME = "slurm-lxd-localhost"

CLOUD = "localhost"

SUBSTRATE = "lxd"

JUPYTERHUB_SECRET_NAME = "vantage-jupyterhub-config"
JUPYTERHUB_APPLICATION_NAME = "vantage-jupyterhub"

SSSD_SECRET_NAME = "vantage-sssd-config"
SSSD_APPLICATION_NAME = "vantage-sssd"

# Bundle deployment timeout in seconds (15 minutes)
# This allows sufficient time for complex deployments with multiple charms
# and dependencies, especially on slower systems or during high network latency
BUNDLE_DEPLOY_TIMEOUT = 900
