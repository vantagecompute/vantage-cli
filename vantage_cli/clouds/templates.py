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

from textwrap import dedent


def generate_sssd_conf(ldap_uri: str, ord_id: str, sssd_binder_password: str) -> str:
    """Generate SSSD configuration."""
    return dedent("""\
    [sssd]
    # Core configuration
    config_file_version = 2
    services = nss, pam, ssh
    domains  = vantagecompute.ai

    # Debugging (for NSS)
    [nss]
    debug_level = 7
    # Filter out system users from LDAP lookups
    # This prevents SSSD from trying to resolve local system accounts via LDAP
    filter_users = root,ubuntu,slurm,slurmrestd,daemon,bin,sys,sync,games,man,lp,mail,news,uucp,proxy,www-data,backup,list,irc,gnats,nobody,systemd-network,systemd-resolve,messagebus,systemd-timesync,syslog,_apt,tss,uuidd,tcpdump,landscape,pollinate,sshd,fwupd-refresh

    filter_groups = root,ubuntu,slurm,slurmrestd,daemon,bin,sys,adm,tty,disk,lp,mail,news,uucp,man,proxy,kmem,dialout,fax,voice,cdrom,floppy,tape,sudo,audio,dip,www-data,backup,operator,list,irc,src,gnats,shadow,utmp,video,sasl,plugdev,staff,games,users,nogroup,systemd-network,systemd-resolve,messagebus,systemd-timesync,syslog,_apt,tss,uuidd,tcpdump,landscape,pollinate,sshd,fwupd-refresh,netdev,lxd

    # Entry cache timeout for NSS lookups (in seconds)
    entry_cache_timeout = 300

    # ============================================================================
    # PAM Configuration (Authentication)
    # ============================================================================
    [pam]
    # How long to allow offline authentication with cached credentials (in days)
    offline_credentials_expiration = 60

    # Reconnection retries if LDAP server is unavailable
    reconnection_retries = 3

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
    ldap_uri               = {ldap_uri}
    ldap_search_base       = ou={org_id},ou=organizations,dc=vantagecompute,dc=ai
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

    # User object class and attributes
    ldap_user_object_class = posixAccount
    ldap_user_name = uid
    ldap_user_uid_number = uidNumber
    ldap_user_gid_number = gidNumber
    ldap_user_home_directory = homeDirectory
    ldap_user_shell = loginShell
    ldap_user_gecos = cn
    ldap_user_fullname = cn

    # ─── Group mapping ─────────────────────────────────────────────────────────────
    ldap_group_object_class = groupOfNames
    ldap_group_member       = member
    ldap_group_name         = cn
    ldap_group_gid_number   = gidNumber

    # Use memberOf attribute for efficient group lookups
    ldap_user_memberof = memberOf

    # Use memberOf attribute for efficient group lookups
    # ============================================================================
    # Caching and Performance
    # ============================================================================

    cache_credentials = true
    enumerate = false

    entry_cache_timeout = 300
    entry_cache_user_timeout = 300
    entry_cache_group_timeout = 300
    entry_cache_sudo_timeout = 300

    entry_negative_timeout = 15

    # ─── Schema type ───────────────────────────────────────────────────────────────
    ldap_schema = rfc2307bis
    """)
