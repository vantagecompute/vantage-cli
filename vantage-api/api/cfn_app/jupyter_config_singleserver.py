# Configuration file for Jupyter Server
import os
dns_name = "@JUPYTERHUB_DNS@"
oidc_dns = "@AUTH_OIDC_DNS@"

from oauthenticator.generic import GenericOAuthenticator

c = get_config()

# GenericOAuthenticator Config
os.environ['OAUTH2_TOKEN_URL'] = f"https://{oidc_dns}/realms/vantage/protocol/openid-connect/token"
os.environ['OAUTH2_AUTHORIZE_URL'] = f"https://{oidc_dns}/realms/vantage/protocol/openid-connect/auth"
os.environ['OAUTH2_USERDATA_URL'] = f"https://{oidc_dns}/realms/vantage/protocol/openid-connect/userinfo"
os.environ['OAUTH2_USERNAME_KEY'] = 'jhuser'
os.environ['OAUTH2_TLS_VERIFY'] = '0'
os.environ['OAUTH_TLS_VERIFY'] = '0'

c.GenericOAuthenticator.login_service = "KeyCloak"
c.GenericOAuthenticator.client_id = "default"
c.GenericOAuthenticator.token_url = f"https://{oidc_dns}/realms/vantage/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = f"https://{oidc_dns}/realms/vantage/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.oauth_callback_url = f"https://{dns_name}:8888/hub/oauth_callback"
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