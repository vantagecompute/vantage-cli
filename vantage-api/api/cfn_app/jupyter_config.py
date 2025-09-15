# Configuration file for JupyterHub
import os
import socket

from oauthenticator.generic import GenericOAuthenticator
from batchspawner import SlurmSpawner

dns_name = "@JUPYTERHUB_DNS@"
default_token = "@JUPYTERHUB_TOKEN@"
oidc_dns = "@AUTH_OIDC_DNS@"

def get_host_ip():
    """Gets the IP address of the host machine.
    This function tries to establish a connection to an external address,
    which forces the system to reveal its local IP.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = "127.0.0.1"  # If connection fails, return loopback
    finally:
        s.close()
    return ip_address

ip_address = get_host_ip()

os.environ["JUPYTERHUB_SERVICE_URL"] = f"http://{ip_address}:443"

c = get_config()

# Jupyterhub Config
c.JupyterHub.hub_ip = ip_address
c.JupyterHub.hub_port = 443

c.JupyterHub.hub_connect_ip = ip_address
c.JupyterHub.hub_connect_port = 8081
c.JupyterHub.hub_connect_url = f"http://{ip_address}:8081"
c.JupyterHub.public_url = f"https://{dns_name}/hub"

c.SlurmSpawner.hub_connect_url = f"http://{ip_address}:8081"

c.JupyterHub.reset_db = False

c.JupyterHub.spawner_class = "batchspawner.SlurmSpawner"

c.JupyterHub.authenticator_class = GenericOAuthenticator
c.JupyterHub.ssl_cert = '/nfs/.jupyter/cert/fullchain.pem'
c.JupyterHub.ssl_key = '/nfs/.jupyter/cert/privkey.pem'
c.JupyterHub.bind_url = 'https://:443'


# GenericOAuthenticator Config
os.environ['OAUTH2_TOKEN_URL'] = f"https://{oidc_dns}/protocol/openid-connect/token"
os.environ['OAUTH2_AUTHORIZE_URL'] = f"https://{oidc_dns}/protocol/openid-connect/auth"
os.environ['OAUTH2_USERDATA_URL'] = f"https://{oidc_dns}/protocol/openid-connect/userinfo"
os.environ['OAUTH2_USERNAME_KEY'] = 'jhuser'
os.environ['OAUTH2_TLS_VERIFY'] = '0'
os.environ['OAUTH_TLS_VERIFY'] = '0'

c.GenericOAuthenticator.login_service = "KeyCloak"
c.GenericOAuthenticator.client_id = "default"
c.GenericOAuthenticator.token_url = f"https://{oidc_dns}/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = f"https://{oidc_dns}/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.oauth_callback_url = f"https://{dns_name}/hub/oauth_callback"
c.GenericOAuthenticator.userdata_params = {"state": "state"}
c.GenericOAuthenticator.userdata_method = "GET"
c.GenericOAuthenticator.username_claim = "jhuser"
c.GenericOAuthenticator.scope = ["openid"]
c.GenericOAuthenticator.auto_login = True
c.GenericOAuthenticator.tls_verify = False
c.GenericOAuthenticator.allow_all = True

# ServerApp Config
c.ServerApp.certfile = "/nfs/.jupyter/cert/fullchain.pem"
c.ServerApp.keyfile = "/nfs/.jupyter/cert/privkey.pem"
c.ServerApp.allow_origin = '*'
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.open_browser = False


c.ServerApp.tornado_settings = {
  'headers':{
    'Content-Security-Policy': "frame-ancestors *"
  }
}
c.JupyterHub.tornado_settings = {
  'headers': {
    'Content-Security-Policy': "frame-ancestors *",
    "X-Frame-Options": "ALLOWALL"
    }
}

# Spawner Config
c.Spawner.args = [
  '--NotebookApp.allow_origin=*',
  '--ServerApp.disable_check_xsfr=True',
  '--ServerApp.tornado_settings={"headers": {"Content-Security-Policy": "frame-ancestors *"}}'
]
c.Spawner.default_url = "/lab"
c.Spawner.notebook_dir = "~"
c.Spawner.notebook_dir = "/nfs/working"
c.Spawner.start_timeout = 300
c.Spawner.http_timeout = 300
c.Spawner.debug = True

# Batchspawner SlurmSpawner Config
c.Spawner.debug = True
c.SlurmSpawner.batch_query_cmd = "echo \"$(squeue  -h --job {job_id} --Format=State:11)\" \"$(scontrol show node $(scontrol show job {job_id} | tr ' ' '\n' | grep '^NodeList=' | cut -d= -f2) | tr ' ' '\n' | grep '^NodeAddr=' | cut -d= -f2)\""
c.SlurmSpawner.batch_script = """#!/bin/bash
#SBATCH --output=/nfs/jupyterlogs/slurmspawner_%j.log
#SBATCH --error=/nfs/jupyterlogs/slurmspawner_%j.log
#SBATCH --job-name=spawner-jupyterhub
#SBATCH --chdir={{homedir}}
#SBATCH --export={{keepvars}}
#SBATCH --get-user-env=L
{% if partition  %}#SBATCH --partition={{partition}}
{% endif %}{% if runtime    %}#SBATCH --time={{runtime}}
{% endif %}{% if memory     %}#SBATCH --mem={{memory}}
{% endif %}{% if gres       %}#SBATCH --gres={{gres}}
{% endif %}{% if nprocs     %}#SBATCH --cpus-per-task={{nprocs}}
{% endif %}{% if reservation%}#SBATCH --reservation={{reservation}}
{% endif %}{% if options    %}#SBATCH {{options}}{% endif %}

set -euo pipefail

trap 'echo SIGTERM received' TERM
{{prologue}}
srun  /usr/bin/bash -c 'source /nfs/jupyter/bin/activate && exec /nfs/jupyter/bin/batchspawner-singleuser /nfs/jupyter/bin/jupyterhub-singleuser --config /nfs/.jupyter/jupyter_config_singleserver.py'

echo "jupyterhub-singleuser ended gracefully"
{{epilogue}}
"""

# Allowed admins
admin = os.environ.get("JUPYTERHUB_ADMIN")
if admin:
  c.Authenticator.admin_users = [admin]

c.Application.log_level = 'DEBUG'
c.JupyterHub.allow_named_servers = True

c.JupyterHub.services = [
  {
    "name": "vantage",
    "api_token": default_token,
    "admin": True,
  },
]

c.JupyterHub.load_roles = [
  {
    "name": "service-role",
    "scopes": [
      "admin:users",
      "admin:servers",
      "admin:groups",
      "delete:servers!user=ubuntu",
      "read:servers!user=ubuntu",
      "servers!user=ubuntu",
      "users:activity!user=ubuntu"
    ],
    "services": [
      "vantage",
    ],
  }
]

c.Authenticator.allowed_users = {"ubuntu"}
