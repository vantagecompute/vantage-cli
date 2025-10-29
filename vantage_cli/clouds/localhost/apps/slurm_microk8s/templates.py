"""Templates for configuration files."""

from textwrap import dedent


def sssd_conf(ldap_url: str, org_id: str, sssd_binder_password: str) -> str:
    """Render the SSSD configuration for LDAP integration.

    Returns:
        The SSSD configuration as a string
    """
    return dedent(
        f"""\
        [sssd]
        # Core configuration
        config_file_version = 2
        services = nss, pam, ssh
        domains  = vantagecompute.ai

        # Debugging (for NSS)
        [nss]
        debug_level = 7

        # -----------------------------------------------------------------------------
        # Domain-specific settings for vantagecompute.ai
        # -----------------------------------------------------------------------------
        [domain/vantagecompute.ai]
        # ─── Identity and Authentication ─────────────────────────────────────────────
        id_provider      = ldap
        auth_provider    = ldap
        chpass_provider  = ldap
        access_provider  = ldap

        # LDAP servers and search bases
        ldap_uri               = {ldap_url}
        ldap_search_base       = dc=vantagecompute,dc=ai
        ldap_user_search_base  = ou=People,ou={org_id},ou=organizations,dc=vantagecompute,dc=ai
        ldap_group_search_base = ou=Groups,ou={org_id},ou=organizations,dc=vantagecompute,dc=ai

        # Credentials for binding to LDAP
        ldap_default_bind_dn      = cn=sssd-binder,ou=ServiceAccounts,ou={org_id},ou=organizations,dc=vantagecompute,dc=ai
        ldap_default_authtok      = {sssd_binder_password}
        ldap_default_authtok_type = password

        # ─── Access control ───────────────────────────────────────────────────────────
        # Only allow slurm-users to log in
        ldap_access_filter = memberOf=cn=slurm-users,ou=Groups,ou={org_id},ou=organizations,dc=vantagecompute,dc=ai

        # ─── SSH public key lookup ────────────────────────────────────────────────────
        ldap_user_ssh_public_key = sshPublicKey

        # ─── Group mapping ─────────────────────────────────────────────────────────────
        ldap_group_object_class = groupOfNames
        ldap_group_member       = member
        ldap_group_name         = cn
        ldap_group_gid_number   = gidNumber

        # ─── Caching and performance ──────────────────────────────────────────────────
        cache_credentials   = true
        entry_cache_timeout = 600
        enumerate           = false

        # ─── Schema type ───────────────────────────────────────────────────────────────
        ldap_schema = rfc2307bis
        """
    )
