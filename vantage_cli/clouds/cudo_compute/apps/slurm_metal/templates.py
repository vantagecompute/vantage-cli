"""Templates for Slurm Metal app."""

from textwrap import dedent

from vantage_cli.sdk.cluster.schema import VantageClusterContext


def init_script_curl(vantage_cluster_ctx: VantageClusterContext) -> str:
    """Return a curl command to fetch the initialization script for the head node."""
    return dedent(f"""\
        #!/bin/bash
        set -euo pipefail
        
        # Set environment variables
        CLUSTER_NAME="{vantage_cluster_ctx.cluster_name}"
        SSSD_BINDER_PASSWORD="{vantage_cluster_ctx.sssd_binder_password}"
        LDAP_URL="{vantage_cluster_ctx.ldap_url}"
        ORG_ID="{vantage_cluster_ctx.org_id}"
        OIDC_CLIENT_ID="{vantage_cluster_ctx.client_id}"
        OIDC_CLIENT_SECRET="{vantage_cluster_ctx.client_secret}"
        JUPYTERHUB_TOKEN="{vantage_cluster_ctx.jupyterhub_token}"
        OIDC_BASE_URL="{vantage_cluster_ctx.oidc_base_url}"
        TUNNEL_API_URL="{vantage_cluster_ctx.tunnel_api_url}"
        VANTAGE_API_URL="{vantage_cluster_ctx.base_api_url}"
        OIDC_DOMAIN="{vantage_cluster_ctx.oidc_domain}"
        
        # Download and execute the initialization script
        curl -fsSL https://vantage-public-assets.s3.us-west-2.amazonaws.com/vantage-cli/clouds/cudo-compute/head_node_init_script.sh | bash -s -- \
            --cluster-name "$CLUSTER_NAME" \
            --sssd-binder-password "$SSSD_BINDER_PASSWORD" \
            --ldap-url "$LDAP_URL" \
            --org-id "$ORG_ID" \
            --oidc-client-id "$OIDC_CLIENT_ID" \
            --oidc-client-secret "$OIDC_CLIENT_SECRET" \
            --jupyterhub-token "$JUPYTERHUB_TOKEN" \
            --oidc-base-url "$OIDC_BASE_URL" \
            --tunnel-api-url "$TUNNEL_API_URL" \
            --vantage-api-url "$VANTAGE_API_URL" \
            --oidc-domain "$OIDC_DOMAIN"
        """
    )


def head_node_init_script() -> str:
    """Return the initialization script for the head node."""
    return dedent("""\
        #!/bin/bash
        set -euo pipefail

        # Parse command-line arguments
        while [[ $# -gt 0 ]]; do
            case $1 in
                --cluster-name)
                    CLUSTER_NAME="$2"
                    shift 2
                    ;;
                --sssd-binder-password)
                    SSSD_BINDER_PASSWORD="$2"
                    shift 2
                    ;;
                --ldap-url)
                    LDAP_URL="$2"
                    shift 2
                    ;;
                --org-id)
                    ORG_ID="$2"
                    shift 2
                    ;;
                --oidc-client-id)
                    OIDC_CLIENT_ID="$2"
                    shift 2
                    ;;
                --oidc-client-secret)
                    OIDC_CLIENT_SECRET="$2"
                    shift 2
                    ;;
                --jupyterhub-token)
                    JUPYTERHUB_TOKEN="$2"
                    shift 2
                    ;;
                --oidc-base-url)
                    OIDC_BASE_URL="$2"
                    shift 2
                    ;;
                --tunnel-api-url)
                    TUNNEL_API_URL="$2"
                    shift 2
                    ;;
                --vantage-api-url)
                    VANTAGE_API_URL="$2"
                    shift 2
                    ;;
                --oidc-domain)
                    OIDC_DOMAIN="$2"
                    shift 2
                    ;;
                *)
                    echo "Unknown parameter: $1"
                    exit 1
                    ;;
            esac
        done

        # Export environment variables
        export CLUSTER_NAME
        export SSSD_BINDER_PASSWORD
        export LDAP_URL
        export ORG_ID
        export OIDC_CLIENT_ID
        export OIDC_CLIENT_SECRET
        export JUPYTERHUB_TOKEN
        export OIDC_BASE_URL
        export TUNNEL_API_URL
        export VANTAGE_API_URL
        export OIDC_DOMAIN

        # Provisioning script converted from cloud-init user-data
        # This script performs the same operations as the cloud-init configuration
        
        echo "=== Starting provisioning ==="
 
        # Create users
        echo "Creating system users..."
        
        # Create slurm user
        if ! id slurm &>/dev/null; then
            useradd --system --uid 64031 --no-create-home --shell /usr/sbin/nologin slurm
        fi
        
        # Create slurmrestd user
        if ! id slurmrestd &>/dev/null; then
            useradd --system --uid 64032 --no-create-home --shell /usr/sbin/nologin slurmrestd
        fi
        
        # Create ubuntu user if it doesn't exist
        if ! id ubuntu &>/dev/null; then
            useradd --shell /bin/bash --create-home --groups adm,cdrom,dip,lxd,sudo ubuntu
            echo 'ubuntu:ubuntu' | chpasswd
            echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu
        fi
        
        ## Set root password
        #echo 'root:$6$canonical.$0zWaW71A9ke9ASsaOcFTdQ2tx1gSmLxMPrsH0rF0Yb.2AEKNPV1lrF94n6YuPJmnUy2K2/JSDtxuiBDey6Lpa/' | chpasswd -e
        
        # Enable SSH password authentication
        echo "Configuring SSH..."
        #sed -i -e '/^[#]*PermitRootLogin/s/^.*$/PermitRootLogin yes/' /etc/ssh/sshd_config
        #sed -i -e '/^[#]*PasswordAuthentication/s/^.*$/PasswordAuthentication yes/' /etc/ssh/sshd_config
        #systemctl restart ssh || systemctl restart sshd
        
        # Update package lists
        echo "Updating package lists..."
        apt-get update
        
        # Add Apptainer PPA
        echo "Adding Apptainer PPA..."
        cat > /etc/apt/sources.list.d/apptainer.list << 'EOF'
        deb https://ppa.launchpadcontent.net/apptainer/ppa/ubuntu noble main
        EOF
        
        cat > /etc/apt/trusted.gpg.d/apptainer.asc << 'EOF'
        -----BEGIN PGP PUBLIC KEY BLOCK-----
        Comment: Hostname:
        Version: Hockeypuck 2.1.0-223-gdc2762b
        
        xsFNBGPKLe0BEADKAHtUqLFryPhZ3m6uwuIQvwUr4US17QggRrOaS+jAb6e0P8kN
        1clzJDuh3C6GnxEZKiTW3aZpcrW/n39qO263OMoUZhm1AliqiViJgthnqYGSbMgZ
        /OB6ToQeHydZ+MgI/jpdAyYSI4Tf4SVPRbOafLvnUW5g/vJLMzgTAxyyWEjvH9Lx
        yjOAXpxubz0Wu2xcoefN0mKCpaPsa9Y8xmog1lsylU+H/4BX6yAG7zt5hIvadc9Z
        Y/vkDLh8kNaEtkXmmnTqGOsLgH6Nc5dnslR6Gwq966EC2Jbw0WbE50pi4g21s6Wi
        wdU27/XprunXhhLdv6PYUaqdXxPRdBh+9u0LmNZsAyUxT6EgN05TAWFtaMOz7I3B
        V6IpHuLqmIcnqulHrLi+0D/aiCv53WEZrBRmDBGX7p52lcyS+Q+LFf0+iYeY7pRG
        fPXboBDr+6DelkYFIxam06purSGR3T9RJyrMP7qMWiInWxcxBoCMNfy8VudP0DAy
        r2yXmHZbgSGjfJey03dnNwQH7huBcQ1VLEqtL+bjn3HubmYK87FltX7xomETFqcl
        QmiT+WBttFRGtO6SFHHiBXOXUn0ihwabtr6gRKeJssCnFS3Y46RDv4z3Je92roLt
        TPY8F9CgZrGiAoKq530BzEhJB6vfW3faRnLKdLePX/LToCP0g2t2jKwkzQARAQAB
        zRtMYXVuY2hwYWQgUFBBIGZvciBBcHB0YWluZXLCwY4EEwEKADgWIQT2sPUZPU8z
        Ae9JH/Cv42U0/GIYrgUCY8ot7QIbAwULCQgHAgYVCgkICwIEFgIDAQIeAQIXgAAK
        CRCv42U0/GIYrut4EAC06vTJP2wgnh3BIZ3n2HKaSp4QsuYKS7F7UQJ5Yt+PpnKn
        Pgjq3R4fYzOHyASv+TCj9QkMaeqWGWb6Zw0n47EtrCW9U5099Vdk2L42KjrqZLiW
        qQ11hwWXUlc1ZYSOb0J4WTumgO6MrUCFkmNrbRE7yB42hxr/AU/XNM38YjN2NyOK
        2gvORRKFwlLKrjE+70HmoCW09Yk64BZl1eCubM/qy5tKzSlC910uz87FvZmrGKKF
        rXa2HGlO4O3Ty7bMSeRKl9m1OYuffAXNwp3/Vale9eDHOeq58nn7wU9pSosmqrXb
        SLOwqQylc1YoLZMj+Xjx644xm5e2bhyD00WiHeqHmvlfQQWCWaPt4i4K0nJuYXwm
        BCA6YUgSfDZJfg/FxJdU7ero5F9st2GK4WDBiz+1Eftw6Ik/WnMDSxXaZ8pwnd9N
        +aAEc/QKP5e8kjxJMC9kfvXGUVzZuMbkUV+PycZhUWl4Aelua91lnTicVYfpuVCC
        GqY0StWQeOxLJneI+1FqLFoBOZghzoTY5AYCp99RjKqQvY1vF4uErltmNeN1vtBm
        CZyDOLQuQfqWWAunUwXVuxMJIENSVeLXunhu9ac24Vnf2rFqH4XVMDxiKc6+sv+v
        fKpamSQOUSmfWJTnry/LiYbspi1OB2x3GQk3/4ANw0S4L83A6oXHUMg8x7/sZw==
        =E71P
        -----END PGP PUBLIC KEY BLOCK-----
        EOF
        
        apt-get update
        
        # Install packages
        echo "Installing packages..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
            libpmix-dev \
            openmpi-bin \
            parallel \
            mysql-server \
            apptainer-suid \
            influxdb \
            influxdb-client \
            wget \
            autossh \
            lmod \
            oddjob-mkhomedir \
            sssd-ldap \
            ldap-utils \
            snapd
        
        # Install snaps
        echo "Installing snap packages..."
        snap install vantage-agent --channel=edge --classic
        snap install jobbergate-agent --channel=edge --classic
        
        # Write configuration files
        echo "Writing configuration files..."
        
        # /etc/slurm/oci.conf
        mkdir -p /etc/slurm
        cat > /etc/slurm/oci.conf << 'EOF'
        ignorefileconfigjson=true
        envexclude="^(SLURM_CONF|SLURM_CONF_SERVER)="
        runtimeenvexclude="^(SLURM_CONF|SLURM_CONF_SERVER)="
        runtimerun="apptainer exec --userns %r %@"
        runtimekill="kill -s SIGTERM %p"
        runtimedelete="kill -s SIGKILL %p"
        EOF
        
        # /etc/slurm/cgroup.conf
        cat > /etc/slurm/cgroup.conf << 'EOF'
        constraincores=yes
        constraindevices=yes
        constrainramspace=yes
        constrainswapspace=yes
        signalchildrenprocesses=yes
        EOF

        # /etc/slurm/slurm.conf
        cat > /etc/slurm/slurm.conf << 'EOF'
        ClusterName=testCluster
        
        # MCS
        MCSPlugin=mcs/label
        MCSParameters=ondemand,ondemandselect
        
        SlurmUser=slurm
        SlurmdUser=root
        SlurmdPort=6818
        SlurmctldPort=6817
        SlurmctldHost=@HEADNODE_HOSTNAME@
        SlurmctldAddr=@HEADNODE_ADDRESS@

        AuthType=auth/slurm
        CredType=auth/slurm
        
        AuthInfo=use_client_ids
        
        SlurmctldPidFile=/run/slurmctld/slurmctld.pid
        SlurmdPidFile=/run/slurmd/slurmd.pid
        
        SlurmctldLogFile=/var/log/slurm/slurmctld.log
        SlurmdLogFile=/var/log/slurm/slurmd.log
        
        SlurmdSpoolDir=/var/lib/slurm/slurmd
        StateSaveLocation=/var/lib/slurm/checkpoint
        
        PluginDir=/opt/slurm/software/lib/slurm
        
        PlugStackConfig=/etc/slurm/plugstack.conf
        
        ProctrackType=proctrack/cgroup
        
        ReturnToService=2
        RebootProgram="/usr/sbin/reboot --reboot"
        MailProg=/usr/bin/mail.mailutils
        
        # Timers
        SlurmctldTimeout=300
        SlurmdTimeout=60
        InactiveLimit=0
        MinJobAge=86400
        KillWait=30
        Waittime=0

        # Slurmctld Parameters
        SlurmctldParameters=enable_configless

        # Scheduling
        SchedulerType=sched/backfill
        SelectType=select/cons_tres
        SelectTypeParameters=CR_CPU_Memory
        
        # Logging
        SlurmctldDebug=debug5
        SlurmdDebug=debug5
        
        # Accounting
        # InfluxDB profiling disabled due to libslurm_curl linking issues
        AcctGatherProfileType=acct_gather_profile/influxdb
        AcctGatherNodeFreq=10
        JobAcctGatherType=jobacct_gather/cgroup
        JobAcctGatherFrequency="task=5"
        
        TaskPlugin="task/cgroup,task/affinity"
        
        # Slurmdbd
        AccountingStorageType=accounting_storage/slurmdbd
        AccountingStorageHost=@HEADNODE_ADDRESS@
        AccountingStorageUser=slurm
        AccountingStoragePort=6839

        # Node Configurations
        NodeName=@HEADNODE_HOSTNAME@ NodeAddr=@HEADNODE_ADDRESS@ CPUs=@CPUs@ ThreadsPerCore=@THREADS_PER_CORE@ CoresPerSocket=@CORES_PER_SOCKET@ Sockets=@SOCKETS@ RealMemory=@REAL_MEMORY@ MemSpecLimit=@MEMSPEC_LIMIT@ State=UNKNOWN Feature=compute

        # Partition Configurations
        PartitionName=compute Nodes=@HEADNODE_HOSTNAME@ MaxTime=INFINITE State=UP Default=Yes

        # NodeSet Configurations
        NodeSet=compute Feature=compute
        EOF

        sed -i "s|@HEADNODE_ADDRESS@|$(hostname -I | awk '{print $1}')|g" /etc/slurm/slurm.conf
        sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurm.conf

        cpu_info=$(lscpu -J | jq)
        CPUs=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "CPU(s):") | .data')
        sed -i "s|@CPUs@|$CPUs|g" /etc/slurm/slurm.conf

        THREADS_PER_CORE=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Thread(s) per core:") | .data')
        sed -i "s|@THREADS_PER_CORE@|$THREADS_PER_CORE|g" /etc/slurm/slurm.conf

        CORES_PER_SOCKET=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Core(s) per socket:") | .data')
        sed -i "s|@CORES_PER_SOCKET@|$CORES_PER_SOCKET|g" /etc/slurm/slurm.conf

        SOCKETS=$(echo $cpu_info | jq -r '.lscpu | .[] | select(.field == "Socket(s):") | .data')
        sed -i "s|@SOCKETS@|$SOCKETS|g" /etc/slurm/slurm.conf

        REAL_MEMORY=$(free -m | grep -oP '\d+' | head -n 1)
        sed -i "s|@REAL_MEMORY@|$REAL_MEMORY|g" /etc/slurm/slurm.conf

        sed -i "s|@REAL_MEMORY@|$(grep MemTotal /proc/meminfo | awk '{print $2}')|g" /etc/slurm/slurm.conf
        sed -i "s|@MEMSPEC_LIMIT@|1024|g" /etc/slurm/slurm.conf
        
        # /etc/slurm/slurmdbd.conf
        cat > /etc/slurm/slurmdbd.conf << 'EOF'
        DbdHost=@HEADNODE_HOSTNAME@
        DbdPort=6839
        
        AuthType=auth/slurm
        SlurmUser=slurm
        PluginDir=/opt/slurm/software/lib/slurm
        PidFile=/run/slurmdbd/slurmdbd.pid
        LogFile=/var/log/slurm/slurmdbd.log
        
        StorageType=accounting_storage/mysql
        StorageHost=127.0.0.1
        StoragePort=3306
        StoragePass=rats
        StorageUser=slurm
        StorageLoc=slurm
        
        DebugLevel=info
        EOF

        sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurmdbd.conf
        
        # /etc/slurm/acct_gather.conf
        cat > /etc/slurm/acct_gather.conf << 'EOF'
        ProfileInfluxDBDatabase=slurm-job-metrics
        ProfileInfluxDBDefault=All
        ProfileInfluxDBHost=localhost:8086
        ProfileInfluxDBPass=rats
        ProfileInfluxDBUser=slurm
        ProfileInfluxDBRTPolicy=three_days
        EOF
        
        # Systemd service files
        mkdir -p /usr/lib/systemd/system
        
        # slurmctld.service
        cat > /usr/lib/systemd/system/slurmctld.service << 'EOF'
        [Unit]
        Description=Slurm controller daemon
        After=network-online.target remote-fs.target munge.service sssd.service
        Wants=network-online.target
        ConditionPathExists=/etc/slurm/slurm.conf
        Documentation=man:slurmctld(8)
        
        [Service]
        Type=notify
        EnvironmentFile=-/etc/default/slurmctld
        User=slurm
        Group=slurm
        RuntimeDirectory=slurmctld
        RuntimeDirectoryMode=0755
        ExecStart=/bin/bash -lc 'source /etc/profile.d/z00_lmod.sh; exec /opt/slurm/software/sbin/slurmctld --systemd $SLURMCTLD_OPTIONS'
        ExecReload=/bin/kill -HUP $MAINPID
        LimitNOFILE=65536
        TasksMax=infinity
        
        [Install]
        WantedBy=multi-user.target
        EOF
        
        # slurmrestd.service
        cat > /usr/lib/systemd/system/slurmrestd.service << 'EOF'
        [Unit]
        Description=Slurmrest API daemon
        After=network.target slurmctld.service
        ConditionPathExists=/etc/slurm/slurm.conf
        Documentation=man:slurmrestd(8)
        
        [Service]
        Type=simple
        EnvironmentFile=-/etc/default/slurmrestd
        Environment=SLURM_JWT=daemon
        
        User=slurmrestd
        Group=slurmrestd
        
        RuntimeDirectory=slurmrestd
        RuntimeDirectoryMode=0755
        
        ExecStart=/bin/bash -lc 'source /etc/profile.d/z00_lmod.sh; exec /usr/sbin/slurmrestd $SLURMRESTD_OPTIONS -vv 0.0.0.0:6820'
        
        ExecReload=/bin/kill -HUP $MAINPID
        
        Restart=on-failure
        RestartSec=30s
        
        LimitMEMLOCK=infinity
        LimitNOFILE=65536
        TasksMax=infinity
        
        [Install]
        WantedBy=multi-user.target
        EOF
        
        # slurmdbd.service
        cat > /usr/lib/systemd/system/slurmdbd.service << 'EOF'
        [Unit]
        Description=Slurm database daemon
        After=network-online.target remote-fs.target sssd.service
        Wants=network-online.target
        ConditionPathExists=/etc/slurm/slurmdbd.conf
        Documentation=man:slurmdbd(8)
        
        [Service]
        Type=simple
        EnvironmentFile=-/etc/default/slurmdbd
        User=slurm
        Group=slurm
        RuntimeDirectory=slurmdbd
        RuntimeDirectoryMode=0755
        ExecStart=/bin/bash -lc 'source /etc/profile.d/z00_lmod.sh; exec /opt/slurm/software/sbin/slurmdbd -D -s'
        ExecReload=/bin/kill -HUP $MAINPID
        LimitNOFILE=65536
        TasksMax=infinity
        
        [Install]
        WantedBy=multi-user.target
        EOF
        
        # slurmd.service
        cat > /usr/lib/systemd/system/slurmd.service << 'EOF'
        [Unit]
        Description=Slurm compute daemon
        After=network-online.target remote-fs.target sssd.service
        Wants=network-online.target
        ConditionPathExists=/etc/slurm/slurm.conf
        Documentation=man:slurmd(8)
        
        [Service]
        Type=notify
        User=root
        Group=root
        RuntimeDirectory=slurmd
        RuntimeDirectoryMode=0755
        EnvironmentFile=-/etc/default/slurmd
        ExecStart=/bin/bash -lc 'source /etc/profile.d/z00_lmod.sh; exec /opt/slurm/software/sbin/slurmd --systemd -F compute $SLURMD_OPTIONS'
        ExecReload=/bin/kill -HUP $MAINPID
        KillMode=process
        LimitNOFILE=131072
        LimitMEMLOCK=infinity
        LimitSTACK=infinity
        Delegate=yes
        TasksMax=infinity

        [Install]
        WantedBy=multi-user.target
        EOF
        
        # Default environment files
        mkdir -p /etc/default
        
        cat > /etc/default/slurmd << 'EOF'
        SLURMD_OPTIONS=""
        SLURM_CONF=/etc/slurm/slurm.conf
        EOF

        cat > /etc/default/slurmctld << 'EOF'
        SLURMCTLD_OPTIONS=""
        SLURM_CONF=/etc/slurm/slurm.conf
        EOF
        
        cat > /etc/default/slurmdbd << 'EOF'
        SLURMDBD_OPTIONS=""
        SLURMDBD_CONF=/etc/slurm/slurmdbd.conf
        EOF
        
        cat > /etc/default/slurmrestd << 'EOF'
        SLURMRESTD_OPTIONS=""
        SLURM_CONF=/etc/slurm/slurm.conf
        EOF
        
        # tmpfiles.d configs
        mkdir -p /etc/tmpfiles.d
        
        cat > /etc/tmpfiles.d/slurmrestd.conf << 'EOF'
        d /run/slurmrestd 0755 slurmrestd slurmrestd -
        EOF
        
        cat > /etc/tmpfiles.d/slurmdbd.conf << 'EOF'
        d /run/slurmdbd 0755 slurm slurm -
        EOF
        
        cat > /etc/tmpfiles.d/slurmd.conf << 'EOF'
        d /run/slurmd 0755 root root -
        EOF
        
        cat > /etc/tmpfiles.d/slurmctld.conf << 'EOF'
        d /run/slurmctld 0755 slurm slurm -
        EOF
        
        # MySQL configuration
        mkdir -p /etc/mysql/mysql.conf.d
        cat > /etc/mysql/mysql.conf.d/slurm.cnf << 'EOF'
        [mysqld]
        innodb_buffer_pool_size = 1024M
        innodb_lock_wait_timeout = 900
        innodb_log_file_size = 64M
        innodb_flush_log_at_trx_commit = 1
        innodb_file_per_table = 1
        EOF
        
        # Lmod profile
        mkdir -p /etc/profile.d
        cat > /etc/profile.d/z00_lmod.sh << 'EOF'
        . /usr/share/lmod/lmod/init/profile
        module load slurm
        EOF
        
        # SSSD configuration
        mkdir -p /etc/sssd
        cat > /etc/sssd/sssd.conf << 'EOF'
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
        ldap_uri               = $LDAP_URL
        ldap_search_base       = ou=$ORG_ID,ou=organizations,dc=vantagecompute,dc=ai
        ldap_user_search_base  = ou=People,ou=$ORG_ID,ou=organizations,dc=vantagecompute,dc=ai
        ldap_group_search_base = ou=Groups,ou=$ORG_ID,ou=organizations,dc=vantagecompute,dc=ai

        # Credentials for binding to LDAP
        ldap_default_bind_dn      = cn=sssd-binder,ou=ServiceAccounts,ou=$ORG_ID,ou=organizations,dc=vantagecompute,dc=ai
        ldap_default_authtok      = $SSSD_BINDER_PASSWORD
        ldap_default_authtok_type = password
        
        # ─── Access control ───────────────────────────────────────────────────────────
        # Only allow slurm-users to log in
        ldap_access_filter = memberOf=cn=slurm-users,ou=Groups,ou=$ORG_ID,ou=organizations,dc=vantagecompute,dc=ai
        
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
        EOF
        
        # Configure MySQL
        echo "Configuring MySQL..."
        systemctl restart mysql.service

        mysql << END_SQL

        CREATE USER IF NOT EXISTS 'slurm'@'localhost' IDENTIFIED BY 'rats';
        CREATE DATABASE IF NOT EXISTS slurm DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        GRANT ALL PRIVILEGES ON  slurm.* TO 'slurm'@'localhost';

        END_SQL
        
        # Configure InfluxDB
        echo "Configuring InfluxDB..."
        systemctl start influxdb.service
        sleep 5
        
        influx -execute "CREATE USER slurm WITH PASSWORD 'rats'"
        influx -execute 'CREATE DATABASE "slurm-job-metrics"'
        influx -execute 'GRANT ALL ON "slurm-job-metrics" TO "slurm"'
        influx -execute 'CREATE RETENTION POLICY "three_days" ON "slurm-job-metrics" DURATION 3d REPLICATION 1 DEFAULT'

        # Setup Slurm directories
        echo "Setting up Slurm directories..."
        mkdir -p /etc/slurm
        mkdir -p /opt/slurm
        mkdir -p /var/lib/slurm
        mkdir -p /var/lib/slurm/checkpoint
        mkdir -p /var/lib/slurm/slurmd
        mkdir -p /var/lib/slurm/slurmctld
        mkdir -p /var/log/slurm
        mkdir -p /var/spool/slurmd
        
        # Create slurm.key
        echo "Generating Slurm authentication key..."
        openssl rand 2048 | base64 | tr -d '\\n' > /etc/slurm/slurm.key
        
        # Set permissions
        echo "Setting Slurm permissions..."
        chown -R slurm:slurm /var/log/slurm
        chown -R slurm:slurm /var/lib/slurm
        chown slurm /etc/slurm/slurmdbd.conf
        chmod 600 /etc/slurm/slurmdbd.conf
        chown slurm /etc/slurm/slurm.conf
        chown slurm /etc/slurm/slurm.key
        chmod 600 /etc/slurm/slurm.key
        
        # Download and install Slurm Lmod module
        echo "Installing Slurm Lmod module..."
        wget -qO- https://vantage-public-assets.s3.us-west-2.amazonaws.com/slurm/25.05/slurm-module-latest.tar.gz | \\
            tar --no-same-owner --no-same-permissions --touch -xz -C /usr/share/lmod/lmod/modulefiles
        
        # Download Slurm
        echo "Downloading and installing Slurm..."
        wget -qO- https://vantage-public-assets.s3.us-west-2.amazonaws.com/slurm/25.05/slurm-latest.tar.gz | \\
            tar --no-same-owner --no-same-permissions --touch -xz -C /opt/slurm
        
        # Create wrapper scripts for Slurm binaries
        echo "Creating Slurm wrapper scripts..."
        
        for i in /opt/slurm/software/bin/sacct \
          /opt/slurm/software/bin/sacctmgr \
          /opt/slurm/software/bin/salloc \
          /opt/slurm/software/bin/sattach \
          /opt/slurm/software/bin/sbang \
          /opt/slurm/software/bin/sbatch \
          /opt/slurm/software/bin/sbcast \
          /opt/slurm/software/bin/scancel \
          /opt/slurm/software/bin/scontrol \
          /opt/slurm/software/bin/scrontab \
          /opt/slurm/software/bin/sdiag \
          /opt/slurm/software/bin/sh5util \
          /opt/slurm/software/bin/sinfo \
          /opt/slurm/software/bin/sprio \
          /opt/slurm/software/bin/squeue \
          /opt/slurm/software/bin/sreport \
          /opt/slurm/software/bin/srun \
          /opt/slurm/software/bin/sshare \
          /opt/slurm/software/bin/sstat \
          /opt/slurm/software/bin/strigger \
          /opt/slurm/software/sbin/slurmctld \
          /opt/slurm/software/sbin/slurmd \
          /opt/slurm/software/sbin/slurmdbd \
          /opt/slurm/software/sbin/slurmrestd \
          /opt/slurm/software/sbin/slurmstepd; do
        
          BASENAME=$(basename $i)
          
          case $i in
            *sbin*)
              TARGET_DIR="/usr/sbin"
              ;;
            *)
              TARGET_DIR="/usr/bin"
              ;;
          esac
          
          echo "Creating wrapper for $BASENAME in $TARGET_DIR"
          
          # Create wrapper script that sources z00_lmod.sh (which loads slurm module) before executing
          cat > ${TARGET_DIR}/${BASENAME} << WRAPPER_EOF
        #!/bin/bash
        source /etc/profile.d/z00_lmod.sh
        exec $i "\\$@"
        WRAPPER_EOF
          
          # Make wrapper executable
          chmod +x ${TARGET_DIR}/${BASENAME}
        
        done
        
        # Setup Vantage JupyterHub
        echo "Setting up Vantage JupyterHub..."
        mkdir -p /srv/vantage-nfs/working
        mkdir -p /srv/vantage-nfs/logs
        chmod -R 777 /srv/vantage-nfs
        
        wget -qO- https://vantage-public-assets.s3.amazonaws.com/vantage-jupyterhub/vantage-jupyterhub-venv-latest.tar.gz | \\
            tar --dereference --no-same-owner --no-same-permissions --touch -xz -C /srv/vantage-nfs
        
        cp /srv/vantage-nfs/vantage-jupyterhub/vantage-jupyterhub.service /usr/lib/systemd/system/vantage-jupyterhub.service
        
        # Reload systemd
        systemctl daemon-reload
        
        # Configure PAM for mkhomedir
        echo "Configuring PAM for automatic home directory creation..."
        pam-auth-update --enable mkhomedir

        sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurmdbd.conf
        sed -i "s|@HEADNODE_ADDRESS@|$(hostname -I | awk '{print $1}')|g\" /etc/slurm/slurm.conf
        sed -i "s|@HEADNODE_HOSTNAME@|$(hostname)|g" /etc/slurm/slurm.conf
        sed -i "s|^ClusterName=.*|ClusterName=$CLUSTER_NAME|g" /etc/slurm/slurm.conf

        # Enable and start services
        echo "Enabling and starting services..."
        systemctl enable --now mysql
        systemctl enable --now influxdb

        systemctl stop sssd
        systemctl stop oddjobd
        systemctl disable sssd
        systemctl disable oddjobd

        systemctl enable --now slurmdbd
        sleep 10
        systemctl enable --now slurmctld
        systemctl enable --now slurmd
        systemctl enable --now slurmrestd

        #scontrol update NodeName=$(hostname) State=RESUME

        for agent_name in vantage-agent jobbergate-agent; do
            snap set $agent_name base-api-url=$VANTAGE_API_URL
            snap set $agent_name cluster-name=$CLUSTER_NAME
            snap set $agent_name oidc-domain=$OIDC_DOMAIN
            snap set $agent_name oidc-client-id=$OIDC_CLIENT_ID
            snap set $agent_name oidc-client-secret=$OIDC_CLIENT_SECRET
            snap set $agent_name task-jobs-interval-seconds=10
        done
        snap set vantage-agent cluster-name=$CLUSTER_NAME
        snap set jobbergate-agent x-slurm-user-name=ubuntu
        snap set jobbergate-agent influx-dsn=influxdb://slurm:rats@localhost:8086/slurm-job-metrics
        snap start vantage-agent.start --enable
        snap start jobbergate-agent.start --enable

        echo "Configuring JupyterHub..."
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

        echo "=== Provisioning complete ==="
        """
    )
