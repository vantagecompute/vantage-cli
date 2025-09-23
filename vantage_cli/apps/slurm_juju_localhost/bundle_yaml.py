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
# Copyright (c) 2025 Vantage Compute Corporation
# See LICENSE file for licensing details.
"""Juju bundle definition for Vantage JupyterHub cluster deployment on localhost."""

from typing import Any, Dict

VANTAGE_JUPYTERHUB_YAML: Dict[str, Any] = {
    "applications": {
        "jobbergate-agent": {
            "charm": "jobbergate-agent",
            "base": "ubuntu@24.04/stable",
            "channel": "edge",
            "num_units": 0,
            "options": {
                "jobbergate-agent-base-api-url": "",
                "jobbergate-agent-oidc-domain": "",
                "jobbergate-agent-oidc-client-id": "",
                "jobbergate-agent-oidc-client-secret": "",
            },
        },
        "vantage-agent": {
            "charm": "vantage-agent",
            "base": "ubuntu@24.04/stable",
            "channel": "edge",
            "num_units": 0,
            "options": {
                "vantage-agent-base-api-url": "",
                "vantage-agent-oidc-domain": "",
                "vantage-agent-oidc-client-id": "",
                "vantage-agent-oidc-client-secret": "",
                "vantage-agent-cluster-name": "",
            },
        },
        "vantage-jupyterhub-nfs-client": {
            "charm": "filesystem-client",
            "base": "ubuntu@24.04/stable",
            "channel": "latest/edge",
            "num_units": 0,
            "options": {
                "mountpoint": "/srv/vantage-nfs",
            },
        },
        "mysql": {
            "charm": "mysql",
            "base": "ubuntu@22.04/stable",
            "channel": "8.0/stable",
            "num_units": 1,
            "to": ["0"],
            "constraints": "arch=amd64",
            "storage": {
                "database": "rootfs,1,1024M",
            },
        },
        "influxdb": {
            "charm": "influxdb",
            "channel": "stable",
            "base": "ubuntu@20.04/stable",
            "num_units": 1,
            "to": ["1"],
            "constraints": "arch=amd64",
        },
        "slurmdbd": {
            "charm": "slurmdbd",
            "base": "ubuntu@24.04/stable",
            "channel": "latest/edge",
            "num_units": 1,
            "to": ["2"],
            "constraints": "arch=amd64",
        },
        "vantage-jupyterhub": {
            "charm": "vantage-jupyterhub",
            "base": "ubuntu@24.04/stable",
            "channel": "edge",
            "num_units": 1,
            "options": {
                "vantage-jupyterhub-config-secret-id": "",
            },
            "to": ["3"],
            "constraints": "arch=amd64 cores=2 mem=2048 virt-type=virtual-machine",
        },
        "sackd": {
            "charm": "sackd",
            "base": "ubuntu@24.04/stable",
            "channel": "latest/edge",
            "num_units": 1,
            "to": ["3"],
            "constraints": "arch=amd64 cores=2 mem=2048 virt-type=virtual-machine",
        },
        "slurmctld": {
            "charm": "slurmctld",
            "base": "ubuntu@24.04/stable",
            "channel": "latest/edge",
            "num_units": 1,
            "to": ["4"],
            "options": {
                "default-partition": "slurmd",
                "cluster-name": "",
            },
            "constraints": "arch=amd64 cores=2 mem=2048 virt-type=virtual-machine",
        },
        "slurmd": {
            "charm": "slurmd",
            "base": "ubuntu@24.04/stable",
            "channel": "latest/edge",
            "num_units": 1,
            "to": ["5"],
            "constraints": "arch=amd64 cores=4 mem=8192 virt-type=virtual-machine",
        },
    },
    "machines": {
        "0": {
            "constraints": "arch=amd64",
            "base": "ubuntu@22.04/stable",
        },
        "1": {
            "constraints": "arch=amd64",
            "base": "ubuntu@20.04/stable",
        },
        "2": {
            "constraints": "arch=amd64",
            "base": "ubuntu@24.04/stable",
        },
        "3": {
            "constraints": "arch=amd64 cores=2 mem=2048 virt-type=virtual-machine",
            "base": "ubuntu@24.04/stable",
        },
        "4": {
            "constraints": "arch=amd64 cores=2 mem=2048 virt-type=virtual-machine",
            "base": "ubuntu@24.04/stable",
        },
        "5": {
            "constraints": "arch=amd64 cores=4 mem=8192 virt-type=virtual-machine",
            "base": "ubuntu@24.04/stable",
        },
    },
    "relations": [
        ["slurmdbd:database", "mysql:database"],
        ["slurmctld:influxdb", "influxdb:query"],
        ["slurmdbd:slurmctld", "slurmctld:slurmdbd"],
        ["slurmd:slurmctld", "slurmctld:slurmd"],
        ["sackd:slurmctld", "slurmctld:login-node"],
        ["vantage-jupyterhub-nfs-client:juju-info", "slurmd:juju-info"],
        ["vantage-jupyterhub:filesystem", "vantage-jupyterhub-nfs-client:filesystem"],
        ["sackd:juju-info", "vantage-agent:juju-info"],
        ["sackd:juju-info", "jobbergate-agent:juju-info"],
    ],
}
