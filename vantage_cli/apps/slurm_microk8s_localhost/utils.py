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
"""Utility functions for SLURM on MicroK8s localhost deployments."""

import shutil
import subprocess
from textwrap import dedent
from typing import Any

import snick
import yaml
from rich.console import Console

from vantage_cli.exceptions import Abort


def check_microk8s_available() -> None:
    """Check if MicroK8s is available and provide installation instructions if not.

    Raises:
        Abort: If MicroK8s is not found, with installation instructions
    """
    if not shutil.which("microk8s"):
        message = snick.dedent(
            """
            • MicroK8s not found. Please install MicroK8s first.

            • To install MicroK8s, run the following command:
              sudo snap install microk8s --channel 1.29/stable --classic

            • Then enable required addons:
              sudo microk8s.enable hostpath-storage
              sudo microk8s.enable dns
              sudo microk8s.enable metallb:10.64.140.43-10.64.140.49

            • Note: Adjust the MetalLB IP range (10.64.140.43-10.64.140.49) to match your network.
            """
        ).strip()

        raise Abort(
            message,
            subject="MicroK8s Required",
            log_message="MicroK8s binary not found",
        )


def check_microk8s_addons() -> None:
    """Check if required MicroK8s addons are enabled and provide installation help.

    Checks the following required addons:
    - dns: CoreDNS for cluster DNS resolution
    - hostpath-storage: Storage provisioner for persistent volumes
    - metallb: Load balancer for services
    - helm3: Helm package manager for application deployment

    Raises:
        Abort: If any required addons are missing, with installation instructions
    """
    required_addons = {
        "dns": {
            "description": "CoreDNS for cluster DNS resolution",
            "enable_command": "sudo microk8s.enable dns",
        },
        "hostpath-storage": {
            "description": "Storage provisioner for persistent volumes",
            "enable_command": "sudo microk8s.enable hostpath-storage",
        },
        "metallb": {
            "description": "Load balancer for services",
            "enable_command": "sudo microk8s.enable metallb:10.64.140.43-10.64.140.49",
            "note": "Adjust the IP range (10.64.140.43-10.64.140.49) to match your network",
        },
        "helm3": {
            "description": "Helm package manager for application deployment",
            "enable_command": "sudo microk8s.enable helm3",
        },
    }

    try:
        # Get MicroK8s status in YAML format
        result = subprocess.run(
            ["microk8s", "status", "--format", "yaml"], capture_output=True, text=True, check=True
        )
        status_data = yaml.safe_load(result.stdout)
    except subprocess.CalledProcessError as e:
        raise Abort(
            "Failed to get MicroK8s status. Please ensure MicroK8s is properly installed and running.",
            subject="MicroK8s Status Error",
            log_message=f"microk8s status failed: {e}",
        )
    except yaml.YAMLError as e:
        raise Abort(
            "Failed to parse MicroK8s status output.",
            subject="MicroK8s Status Parse Error",
            log_message=f"YAML parse error: {e}",
        )

    # Check if MicroK8s is running
    if not status_data.get("microk8s", {}).get("running", False):
        raise Abort(
            "MicroK8s is not running. Please start it with: sudo microk8s start",
            subject="MicroK8s Not Running",
            log_message="MicroK8s service is not running",
        )

    # Get enabled addons
    enabled_addons: set[str] = set()
    addons_list = status_data.get("addons", [])
    for addon in addons_list:
        if addon.get("status") == "enabled":
            addon_name = addon.get("name")
            if addon_name:
                enabled_addons.add(addon_name)

    # Check for missing addons
    missing_addons: list[tuple[str, dict[str, str]]] = []
    enabled_status: list[str] = []

    for addon_name, addon_info in required_addons.items():
        if addon_name in enabled_addons:
            enabled_status.append(f"✓ {addon_name}: {addon_info['description']}")
        else:
            missing_addons.append((addon_name, addon_info))

    # Show status and handle missing addons
    if missing_addons:
        message_parts: list[str] = []

        if enabled_status:
            message_parts.append("✅ Enabled addons:")
            for status in enabled_status:
                message_parts.append(f"  {status}")
            message_parts.append("")

        message_parts.append("❌ Missing required addons:")
        for addon_name, addon_info in missing_addons:
            message_parts.append(f"  • {addon_name}: {addon_info['description']}")
            message_parts.append(f"    Command: {addon_info['enable_command']}")
            if "note" in addon_info:
                message_parts.append(f"    Note: {addon_info['note']}")

        message_parts.extend(
            ["", "Please enable all missing addons before proceeding with deployment."]
        )

        raise Abort(
            "\n".join(message_parts),
            subject="MicroK8s Addons Required",
            log_message=f"Missing addons: {[name for name, _ in missing_addons]}",
        )
    else:
        # All addons are enabled - could optionally show success message
        # For now, just return silently to continue with deployment
        pass


def check_existing_deployment() -> None:
    """Check if a SLURM deployment already exists on MicroK8s.

    Checks for the presence of 'slinky' and 'slurm' namespaces which indicate
    an existing SLURM deployment.

    Raises:
        Abort: If deployment already exists, with cleanup instructions
    """
    try:
        # Get list of namespaces
        result = subprocess.run(
            ["microk8s.kubectl", "get", "namespaces", "-o", "name"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse namespace names
        existing_namespaces: set[str] = set()
        for line in result.stdout.strip().split("\n"):
            if line.startswith("namespace/"):
                namespace_name = line.replace("namespace/", "")
                existing_namespaces.add(namespace_name)

        # Check for SLURM-related namespaces
        slurm_namespaces = {"slinky", "slurm"}
        found_namespaces = slurm_namespaces.intersection(existing_namespaces)

        if found_namespaces:
            namespace_list = "\n".join(
                f"                  • {ns}" for ns in sorted(found_namespaces)
            )
            message = snick.dedent(
                f"""
                🔍 Existing SLURM deployment detected!

                Found the following SLURM-related namespaces:
{namespace_list}

                📋  Options:

                1️⃣  Clean up existing deployment first:
                    vantage deployment slurm-microk8s-localhost cleanup

                2️⃣  Check current deployment status:
                    microk8s.kubectl get pods -n slinky
                    microk8s.kubectl get pods -n slurm

                3️⃣  Connect to existing deployment (if running):
                    # Get connection details
                    SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}')"
                    SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{{.spec.ports[0].port}}')"

                    # Connect via SSH
                    ssh -p ${{SLURM_LOGIN_PORT:-22}} ${{USER}}@${{SLURM_LOGIN_IP}}

                ℹ️  To proceed with a new deployment, please clean up the existing one first.
                """
            ).strip()

            raise Abort(
                message,
                subject="SLURM Deployment Already Exists",
                log_message=f"Found existing namespaces: {found_namespaces}",
            )

    except subprocess.CalledProcessError:
        # If kubectl command fails, it might mean MicroK8s is not running properly
        # Let the deployment continue and let other checks handle this
        pass
    except (OSError, FileNotFoundError):
        # kubectl command not found or other file system issues
        # Let the deployment continue and let other checks handle this
        pass


EXTRA_SSHD_CONF = dedent(
    """\
    # Custom SSHD configuration
    AuthorizedKeysCommand /usr/bin/sss_ssh_authorizedkeys
    AuthorizedKeysCommandUser root
    """
)


SSSD_CONF = dedent("""\
    [sssd]
    config_file_version = 2
    services = nss,pam
    domains = DEFAULT

    [nss]
    filter_groups = root,slurm
    filter_users = root,slurm

    [pam]

    [domain/DEFAULT]
    auth_provider = ldap
    id_provider = ldap
    ldap_uri = ldap://ldap.example.com
    ldap_search_base = dc=example,dc=com
    ldap_user_search_base = ou=Users,dc=example,dc=com
    ldap_group_search_base = ou=Groups,dc=example,dc=com
    """)


def get_chart_values_slurm_operator() -> dict[str, Any]:
    """Get Helm chart values for SLURM operator deployment.

    Returns:
        Dictionary containing Helm chart values for SLURM operator.
    """
    return {
        "nameOverride": "",
        "fullnameOverride": "",
        "namespaceOverride": "",
        "imagePullSecrets": [],
        "priorityClassName": "",
        "crds": {"enabled": False},
        "operator": {
            "enabled": True,
            "replicas": 1,
            "imagePullPolicy": "IfNotPresent",
            "image": {"repository": "ghcr.io/slinkyproject/slurm-operator", "tag": ""},
            "serviceAccount": {"create": True, "name": ""},
            "affinity": {},
            "tolerations": [],
            "resources": {},
            "accountingWorkers": 4,
            "controllerWorkers": 4,
            "loginsetWorkers": 4,
            "nodesetWorkers": 4,
            "restapiWorkers": 4,
            "tokenWorkers": 4,
            "slurmclientWorkers": 2,
            "logLevel": "info",
        },
        "webhook": {
            "enabled": True,
            "replicas": 1,
            "imagePullPolicy": "IfNotPresent",
            "image": {"repository": "ghcr.io/slinkyproject/slurm-operator-webhook", "tag": ""},
            "serviceAccount": {"create": True, "name": ""},
            "timeoutSeconds": 10,
            "affinity": {},
            "tolerations": [],
            "resources": {},
            "logLevel": "info",
        },
        "certManager": {
            "enabled": True,
            "secretName": "slurm-operator-webhook-ca",
            "duration": "43800h0m0s",
            "renewBefore": "8760h0m0s",
        },
    }


def get_chart_values_slurm_cluster() -> dict[str, Any]:
    """Get Helm chart values for SLURM cluster deployment.

    Returns:
        Dictionary containing Helm chart values for SLURM cluster.
    """
    return {
        "nameOverride": None,
        "fullnameOverride": None,
        "namespaceOverride": None,
        "imagePullSecrets": [],
        "imagePullPolicy": "IfNotPresent",
        "priorityClassName": None,
        "slurmKeyRef": {},
        "jwtHs256KeyRef": {},
        "clusterName": None,
        "configFiles": {},
        "prologScripts": {},
        "epilogScripts": {},
        "controller": {
            "slurmctld": {
                "image": {
                    "repository": "ghcr.io/slinkyproject/slurmctld",
                    "tag": "25.05-ubuntu24.04",
                },
                "args": [],
                "resources": {},
            },
            "reconfigure": {
                "image": {
                    "repository": "ghcr.io/slinkyproject/slurmctld",
                    "tag": "25.05-ubuntu24.04",
                },
                "resources": {},
            },
            "logfile": {
                "image": {"repository": "docker.io/library/alpine", "tag": "latest"},
                "resources": {},
            },
            "persistence": {
                "enabled": True,
                "existingClaim": None,
                "storageClassName": None,
                "accessModes": ["ReadWriteOnce"],
                "resources": {"requests": {"storage": "4Gi"}},
            },
            "extraConf": None,
            "extraConfMap": {},
            "metadata": {},
            "podSpec": {
                "initContainers": [],
                "nodeSelector": {"kubernetes.io/os": "linux"},
                "affinity": {},
                "tolerations": [],
            },
            "service": {},
        },
        "restapi": {
            "replicas": 1,
            "slurmrestd": {
                "image": {
                    "repository": "ghcr.io/slinkyproject/slurmrestd",
                    "tag": "25.05-ubuntu24.04",
                },
                "env": [],
                "args": [],
                "resources": {},
            },
            "metadata": {},
            "podSpec": {
                "initContainers": [],
                "nodeSelector": {"kubernetes.io/os": "linux"},
                "affinity": {},
                "tolerations": [],
            },
            "service": {},
        },
        "slurm-exporter": {
            "enabled": True,
            "exporter": {
                "enabled": True,
                "secretName": "slurm-token-exporter",
                "nodeSelector": {"kubernetes.io/os": "linux"},
                "affinity": {},
                "tolerations": [],
            },
        },
        "accounting": {
            "enabled": False,
            "slurmdbd": {
                "image": {
                    "repository": "ghcr.io/slinkyproject/slurmdbd",
                    "tag": "25.05-ubuntu24.04",
                },
                "args": [],
                "resources": {},
            },
            "initconf": {
                "image": {"repository": "ghcr.io/slinkyproject/sackd", "tag": "25.05-ubuntu24.04"},
                "resources": {},
            },
            "storageConfig": {
                "host": "mariadb",
                "port": 3306,
                "database": "slurm_acct_db",
                "username": "slurm",
                "passwordKeyRef": {"name": "mariadb-password", "key": "password"},
            },
            "extraConf": None,
            "extraConfMap": {},
            "metadata": {},
            "podSpec": {
                "initContainers": [],
                "nodeSelector": {"kubernetes.io/os": "linux"},
                "affinity": {},
                "tolerations": [],
            },
            "service": {},
        },
        "loginsets": {
            "slinky": {
                "enabled": True,
                "replicas": 1,
                "login": {
                    "image": {
                        "repository": "ghcr.io/jamesbeedy/login",
                        "tag": "0.0.7",
                    },
                    "env": [],
                    "securityContext": {"privileged": False},
                    "resources": {
                        "limits": {"cpu": "1000m", "memory": "1024Mi"},
                    },
                    "volumeMounts": [],
                },
                "rootSshAuthorizedKeys": None,
                "extraSshdConfig": EXTRA_SSHD_CONF,
                "sssdConf": SSSD_CONF,
                "metadata": {},
                "podSpec": {
                    "initContainers": [],
                    "nodeSelector": {"kubernetes.io/os": "linux"},
                    "affinity": {},
                    "tolerations": [],
                    "volumes": [],
                },
                "service": {"type": "LoadBalancer"},
            }
        },
        "nodesets": {
            "slinky": {
                "enabled": True,
                "replicas": 1,
                "slurmd": {
                    "image": {
                        "repository": "ghcr.io/slinkyproject/slurmd",
                        "tag": "25.05-ubuntu24.04",
                    },
                    "args": [],
                    "resources": {},
                    "volumeMounts": [],
                },
                "logfile": {
                    "image": {"repository": "docker.io/library/alpine", "tag": "latest"},
                    "resources": {},
                },
                "extraConf": None,
                "extraConfMap": {},
                "partition": {"enabled": True, "config": None, "configMap": {}},
                "useResourceLimits": True,
                "metadata": {},
                "podSpec": {
                    "initContainers": [],
                    "nodeSelector": {"kubernetes.io/os": "linux"},
                    "affinity": {},
                    "tolerations": [],
                    "volumes": [],
                },
            }
        },
        "partitions": {
            "all": {
                "enabled": True,
                "nodesets": ["ALL"],
                "config": None,
                "configMap": {"State": "UP", "Default": "YES", "MaxTime": "UNLIMITED"},
            }
        },
        "vendor": {
            "nvidia": {
                "dcgm": {
                    "enabled": False,
                    "jobMappingDir": "/var/lib/dcgm-exporter/job-mapping",
                    "scriptPriority": "90",
                }
            }
        },
    }


def show_getting_started_help(console: Console) -> None:
    """Show getting started help after successful MicroK8s SLURM deployment.

    Displays connection instructions and useful commands for accessing the deployed cluster.
    """
    from rich.panel import Panel

    help_message = snick.dedent(
        """
        🎉 SLURM cluster deployment completed successfully!

        📋 Next Steps:

        1️⃣ Check cluster status:
           microk8s.kubectl get pods -A --namespace slurm

        2️⃣ Get SLURM login service connection details:
           SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
           SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.spec.ports[0].port}')"

        3️⃣ Connect to SLURM login node:
           # Using root access (if rootSshAuthorizedKeys was configured):
           ssh -p ${SLURM_LOGIN_PORT:-22} root@${SLURM_LOGIN_IP}

           # Using SSSD user authentication (if SSSD is configured):
           ssh -p ${SLURM_LOGIN_PORT:-22} ${USER}@${SLURM_LOGIN_IP}

        4️⃣ Useful SLURM commands once connected:
           sinfo                    # Show cluster information
           squeue                   # Show job queue
           srun hostname            # Run simple test job
           sbatch <script.sh>       # Submit batch job

        📚 Additional Resources:
           • MicroK8s docs: https://microk8s.io/docs
           • SLURM docs: https://slurm.schedmd.com/documentation.html
           • Troubleshooting: microk8s.kubectl logs -n slurm <pod-name>
        """
    ).strip()

    console.print(
        Panel(
            help_message,
            title="🚀 Getting Started with Your SLURM Cluster",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
    )
