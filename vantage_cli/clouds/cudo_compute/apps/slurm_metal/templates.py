"""Templates for Slurm Metal app."""

from textwrap import dedent
from typing import Dict

from vantage_cli.sdk.cluster.schema import VantageClusterContext


def head_node_init_script(
    vantage_cluster_ctx: VantageClusterContext, cudo_ctx: Dict[str, str]
) -> str:
    """Return the initialization script for the head node.

    This script downloads the complete Slurm installation tarball and runs
    the slurm_install.sh script contained within it, following the pattern
    established in the multipass-singlenode project.
    """
    cudo_api_key = cudo_ctx.get("api_key", "")
    cudo_data_center = cudo_ctx.get("data_center_id", "")

    return dedent(f"""\
        #!/bin/bash
        set -euo pipefail

        export CLUSTER_NAME="{vantage_cluster_ctx.cluster_name}"
        export SSSD_BINDER_PASSWORD="{vantage_cluster_ctx.sssd_binder_password}"
        export LDAP_URL="{vantage_cluster_ctx.ldap_url}"
        export ORG_ID="{vantage_cluster_ctx.org_id}"
        export OIDC_CLIENT_ID="{vantage_cluster_ctx.client_id}"
        export OIDC_CLIENT_SECRET="{vantage_cluster_ctx.client_secret}"
        export JUPYTERHUB_TOKEN="{vantage_cluster_ctx.jupyterhub_token}"
        export OIDC_BASE_URL="{vantage_cluster_ctx.oidc_base_url}"
        export TUNNEL_API_URL="{vantage_cluster_ctx.tunnel_api_url}"
        export VANTAGE_API_URL="{vantage_cluster_ctx.base_api_url}"
        export OIDC_DOMAIN="{vantage_cluster_ctx.oidc_domain}"
        export CUDO_API_KEY="${CUDO_API_KEY}"
        export CUDO_DATA_CENTER="${CUDO_DATA_CENTER}"

        # Install snap packages
        snap install vantage-agent --channel=edge --classic
        snap install jobbergate-agent --channel=edge --classic
        snap install just --classic
        snap install astral-uv --classic

        # Download and extract the Slurm software tarball
        echo "Downloading Slurm tarball..."
        mkdir -p /opt/slurm
        wget -qO- https://vantage-public-assets.s3.us-west-2.amazonaws.com/slurm/25.05/slurm-latest.tar.gz | \\
            tar --no-same-owner --no-same-permissions --touch -xz -C /opt/slurm

        # Run the slurm_install.sh script from the tarball
        echo "Running slurm_install.sh..."
        bash /opt/slurm/view/assets/slurm_assets/slurm_install.sh \
                  --head-node-init \
                  --full-init \
                  --start-services \
                  --cluster-name $CLUSTER_NAME \
                  --org-id $ORG_ID \
                  --ldap-uri $LDAP_URL \
                  --sssd-binder-password $SSSD_BINDER_PASSWORD

        # Enable and start system services
        # and Authselect SSSD with-mkhomedir
        mkdir -p /etc/authselect
        pam-auth-update --enable mkhomedir
        authselect select sssd with-mkhomedir --force

        # Setup Vantage JupyterHub
        mkdir -p /srv/vantage-nfs/working
        mkdir -p /srv/vantage-nfs/logs
        chmod -R 777 /srv/vantage-nfs
        wget -qO- https://vantage-public-assets.s3.amazonaws.com/vantage-jupyterhub/vantage-jupyterhub-venv-latest.tar.gz | \\
            tar --dereference --no-same-owner --no-same-permissions --touch -xz -C /srv/vantage-nfs
        cp /srv/vantage-nfs/vantage-jupyterhub/vantage-jupyterhub.service /usr/lib/systemd/system/vantage-jupyterhub.service
        systemctl daemon-reload

        # Configure Vantage agents
        for agent_name in vantage-agent jobbergate-agent; do
            snap set $agent_name base-api-url=$VANTAGE_API_URL
            snap set $agent_name oidc-domain=$OIDC_DOMAIN
            snap set $agent_name oidc-client-id=$OIDC_CLIENT_ID
            snap set $agent_name oidc-client-secret=$OIDC_CLIENT_SECRET
            snap set $agent_name task-jobs-interval-seconds=10
        done
        snap set vantage-agent cluster-name=$CLUSTER_NAME
        snap set jobbergate-agent influx-dsn=influxdb://slurm:rats@localhost:8086/slurm-job-metrics
        snap start vantage-agent.start --enable
        snap start jobbergate-agent.start --enable

        # Configure JupyterHub
        cat > /etc/default/vantage-jupyterhub << EOF
        JUPYTERHUB_VENV_DIR=/srv/vantage-nfs/vantage-jupyterhub
        OIDC_CLIENT_ID=$OIDC_CLIENT_ID
        OIDC_CLIENT_SECRET=$OIDC_CLIENT_SECRET
        JUPYTERHUB_TOKEN=$JUPYTERHUB_TOKEN
        OIDC_BASE_URL=$OIDC_BASE_URL
        TUNNEL_API_URL=$TUNNEL_API_URL
        VANTAGE_API_URL=$VANTAGE_API_URL
        OIDC_DOMAIN=$OIDC_DOMAIN
        EOF
        systemctl --now enable vantage-jupyterhub.service

        # Configure Cudo Compute SDK
        cat > /etc/default/cudo << EOF
        CUDO_API_KEY=${CUDO_API_KEY}
        CUDO_DATA_CENTER=${CUDO_DATA_CENTER}
        EOF
        uv venv /srv/vantage-nfs/cudo
        source /srv/vantage-nfs/cudo/bin/activate && uv pip install cudo-compute-sdk

        echo "Slurm installation complete!"
        """)
