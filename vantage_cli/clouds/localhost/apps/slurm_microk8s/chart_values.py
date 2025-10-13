"""Helm chart values for SLURM MicroK8s localhost deployment."""

from textwrap import dedent
from typing import Any, Dict

from vantage_cli.clouds.localhost.apps.slurm_microk8s.constants import (
    LOGINSET_IMAGE,
    LOGINSET_IMAGE_TAG,
)

EXTRA_SSHD_CONF = dedent(
    """\
    # Custom SSHD configuration
    AuthorizedKeysCommand /usr/bin/sss_ssh_authorizedkeys
    AuthorizedKeysCommandUser root
    """
)


CHART_VALUES_SLURM_OPERATOR: Dict[str, Any] = {
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


CHART_VALUES_SLURM_CLUSTER: Dict[str, Any] = {
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
                    "repository": LOGINSET_IMAGE,
                    "tag": LOGINSET_IMAGE_TAG,
                },
                "env": [],
                "securityContext": {"privileged": False},
                "resources": {
                    "limits": {"cpu": "1000m", "memory": "1024Mi"},
                },
                "volumeMounts": [],
            },
            "rootSshAuthorizedKeys": "",
            "extraSshdConfig": EXTRA_SSHD_CONF,
            "sssdConf": "",
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
