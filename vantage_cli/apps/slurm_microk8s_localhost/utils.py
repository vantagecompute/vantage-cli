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

from textwrap import dedent
from typing import Any

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
                        "repository": "ghcr.io/slinkyproject/login",
                        "tag": "25.05-ubuntu24.04",
                    },
                    "env": [],
                    "securityContext": {"privileged": False},
                    "resources": {},
                    "volumeMounts": [],
                },
                "rootSshAuthorizedKeys": None,
                "extraSshdConfig": None,
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
