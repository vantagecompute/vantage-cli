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
"""Template engine for deployment configurations."""

import io
from typing import Any, Dict, List

from ruamel.yaml import YAML

from vantage_cli.exceptions import ConfigurationError
from vantage_cli.schemas import VantageClusterContext


class CloudInitTemplate:
    """Template engine for cloud-init configurations using proper YAML structure."""

    def __init__(self):
        """Initialize YAML processor with proper settings."""
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 4096

    def generate_multipass_config(self, context: VantageClusterContext) -> str:
        """Generate cloud-init configuration for multipass instances."""
        try:
            # Build the cloud-config as a proper Python dictionary
            cloud_config = {
                "snap": {
                    "commands": {
                        0: "snap refresh vantage-agent --channel=edge --classic",
                        1: "snap refresh jobbergate-agent --channel=edge --classic",
                    }
                },
                "runcmd": self._build_runcmd_list(context),
            }

            # Convert to YAML string
            stream = io.StringIO()
            stream.write("#cloud-config\n")
            self.yaml.dump(cloud_config, stream)
            return stream.getvalue()

        except (AttributeError, KeyError, TypeError) as e:
            raise ConfigurationError(f"Failed to generate multipass cloud-init config: {e}")

    def _build_runcmd_list(self, context: VantageClusterContext) -> List[str]:
        """Build the runcmd list for cloud-init."""
        commands = []

        # SLURM configuration commands
        commands.extend(
            [
                'sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurmdbd.conf',
                "sed -i \"s|@HEADNODE_ADDRESS@|$(hostname -I | awk '{print $1}')|g\" /etc/slurm/slurm.conf",
                'sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurm.conf',
            ]
        )

        # CPU configuration script
        cpu_script = """
cpu_info=$(lscpu -J | jq)
CPUs=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "CPU(s):") | .data')
sed -i "s|@CPUs@|$CPUs|g" /etc/slurm/slurm.conf

THREADS_PER_CORE=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Thread(s) per core:") | .data')
sed -i "s|@THREADS_PER_CORE@|$THREADS_PER_CORE|g" /etc/slurm/slurm.conf

CORES_PER_SOCKET=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Core(s) per socket:") | .data')
sed -i "s|@CORES_PER_SOCKET@|$CORES_PER_SOCKET|g" /etc/slurm/slurm.conf

SOCKETS=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Socket(s):") | .data')
sed -i "s|@SOCKETS@|$SOCKETS|g" /etc/slurm/slurm.conf

REAL_MEMORY=$(free -m | grep -oP '\\d+' | head -n 1)
sed -i "s|@REAL_MEMORY@|$REAL_MEMORY|g" /etc/slurm/slurm.conf""".strip()

        commands.append(cpu_script)

        # SLURM service restart commands
        commands.extend(
            [
                "systemctl enable --now slurmdbd",
                "sleep 10",
                "systemctl enable --now slurmctld",
                "systemctl enable --now slurmd",
                "systemctl enable --now slurmrestd",
                "scontrol update NodeName=$(hostname) State=RESUME",
            ]
        )

        # Agent configuration commands
        commands.extend(self._generate_vantage_agent_cloud_init_snap_config(context))
        commands.extend(self._generate_jobbergate_agent_cloud_init_snap_config(context))
        commands.append("snap start vantage-agent.start --enable")
        commands.append("snap start jobbergate-agent.start --enable")

        # JupyterHub configuration commands
        commands.extend(self._generate_jupyterhub_config(context))
        commands.append("systemctl --now enable vantage-jupyterhub.service")

        return commands

    def _generate_agent_config(self, agent_name: str, context: VantageClusterContext) -> List[str]:
        """Generate base agent configuration commands."""
        return [
            f"snap set {agent_name} base-api-url={context.base_api_url}",
            f"snap set {agent_name} oidc-domain={context.oidc_domain}",
            f"snap set {agent_name} oidc-client-id={context.client_id}",
            f"snap set {agent_name} oidc-client-secret={context.client_secret}",
            f"snap set {agent_name} task-jobs-interval-seconds=10",
        ]

    def _generate_vantage_agent_cloud_init_snap_config(
        self, context: VantageClusterContext
    ) -> List[str]:
        """Generate vantage-agent specific cloud-init snap configuration."""
        base_config = self._generate_agent_config("vantage-agent", context)
        vantage_specific = [f"snap set vantage-agent cluster-name={context.cluster_name}"]
        return base_config + vantage_specific

    def _generate_jobbergate_agent_cloud_init_snap_config(
        self, context: VantageClusterContext
    ) -> List[str]:
        """Generate jobbergate-agent specific cloud-init snap configuration."""
        base_config = self._generate_agent_config("jobbergate-agent", context)
        jobbergate_specific = [
            "snap set jobbergate-agent x-slurm-user-name=ubuntu",
            "snap set jobbergate-agent influx-dsn=influxdb://slurm:rats@localhost:8086/slurm-job-metrics",
        ]
        return base_config + jobbergate_specific

    def _generate_jupyterhub_config(self, context: VantageClusterContext) -> List[str]:
        """Generate JupyterHub configuration commands."""
        return [
            'echo "JUPYTERHUB_VENV_DIR=/srv/vantage-nfs/vantage-jupyterhub" >> /etc/default/vantage-jupyterhub',
            f'echo "OIDC_CLIENT_ID={context.client_id}" >> /etc/default/vantage-jupyterhub',
            f'echo "OIDC_CLIENT_SECRET={context.client_secret}" >> /etc/default/vantage-jupyterhub',
            f'echo "JUPYTERHUB_TOKEN={context.jupyterhub_token}" >> /etc/default/vantage-jupyterhub',
            f'echo "OIDC_BASE_URL={context.oidc_base_url}" >> /etc/default/vantage-jupyterhub',
            f'echo "TUNNEL_API_URL={context.tunnel_api_url}" >> /etc/default/vantage-jupyterhub',
            f'echo "VANTAGE_API_URL={context.base_api_url}" >> /etc/default/vantage-jupyterhub',
            f'echo "OIDC_DOMAIN={context.oidc_domain}" >> /etc/default/vantage-jupyterhub',
        ]


class JujuBundleTemplate:
    """Template engine for Juju bundle configurations."""

    @staticmethod
    def generate_bundle_config(context: VantageClusterContext) -> Dict[str, Any]:
        """Generate Juju bundle configuration."""
        # This would contain the bundle configuration
        # For now, returning a basic structure
        return {
            "bundle": "vantage-jupyterhub-slurm",
            "applications": {
                "vantage-jupyterhub": {
                    "charm": "vantage-jupyterhub",
                    "options": {
                        "client_id": context.client_id,
                        "oidc_domain": context.oidc_domain,
                        "base_api_url": context.base_api_url,
                    },
                }
            },
        }
