#!/bin/bash -x
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

nvidia-smi || true

mkdir -p /nfs || true
mount -t nfs @head_node_private_ip_address@:/nfs /nfs
export SLURM_HOME=/nfs/slurm

# configure munge
cp /nfs/munge.key /etc/munge
chown munge:munge /etc/munge/munge.key
chmod 600 /etc/munge/munge.key
chown -R munge /etc/munge/ /var/log/munge/
chmod 0700 /etc/munge/ /var/log/munge/
systemctl enable munge
systemctl start munge
sleep 15

INSTANCE_ID=`curl http://instance-data/latest/meta-data/instance-id`
INSTANCE_NAME=$(aws ec2 describe-tags --filter Name=resource-id,Values=$INSTANCE_ID --output text --query 'Tags[?Key==`Name`].Value | [0]')

cat > /tmp/mount-volumes_cron.sh <<'EOF'
#!/bin/bash
# Fetch instance and VPC ID
INSTANCE_ID=$(curl http://instance-data/latest/meta-data/instance-id)
VPC_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query "Reservations[].Instances[].VpcId" --output text)

# Fetch target instance ID based on the private IP
TARGET_INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=network-interface.addresses.private-ip-address,Values='@head_node_private_ip_address@'" "Name=vpc-id,Values=$VPC_ID" --query "Reservations[].Instances[].InstanceId" --output text)

# Fetch mount targets from tags
MOUNT_POINT_OBJ=$(aws ec2 describe-tags --filters "Name=resource-id,Values=$TARGET_INSTANCE_ID" --query 'Tags[?contains(Key, `mount-target`)].{Key: Key, Value: Value}' | jq '[.[] | {FSID: (.Key | split("/")[1]), Value: .Value}]')

# Loop over the mount points and mount them
echo "$MOUNT_POINT_OBJ" | jq -c '.[]' | while read -r obj; do
    # Extract FSID and Value for each object
    FSID=$(echo "$obj" | jq -r '.FSID')
    MOUNT_POINT=$(echo "$obj" | jq -r '.Value')

    # Loop over the currently mounted EFS points and check if the current FSID is already mounted
    # If not, mount the FSID at the specified mount point
    if ! df --output=target | grep -q "^$MOUNT_POINT$"; then
        echo "Mounting $FSID at $MOUNT_POINT"
        mkdir -p $MOUNT_POINT
        mount -t efs -o tls $FSID:/ $MOUNT_POINT
        chown -R ubuntu:ubuntu $MOUNT_POINT

        if [ $? -eq 0 ]; then
            echo "Mounted $FSID successfully."
        else
            echo "Failed to mount $FSID."
        fi
    else
        echo "$MOUNT_POINT is already mounted."
    fi
done
EOF
chmod +x /tmp/mount-volumes_cron.sh
crontab -l | { cat; echo "*/2 * * * * /bin/bash /tmp/mount-volumes_cron.sh"; } | crontab -

cat > /tmp/unmount-volumes_cron.sh <<'EOF'
#!/bin/bash

# Fetch all NFS mount points dynamically. Adjust this line if you're using a different filesystem type.
MOUNT_POINTS=$(mount -t nfs4 -l | awk '{print $3}')

# Timeout duration in seconds
TIMEOUT_DURATION=2

for MOUNT_POINT in $MOUNT_POINTS; do
    # Use the `stat` command with a timeout to check each mount's health
    if ! timeout "${TIMEOUT_DURATION}s" stat "$MOUNT_POINT" > /dev/null 2>&1; then
        echo "Mount point $MOUNT_POINT is not responsive. Attempting to unmount."

        # Attempt lazy unmount
        umount -l "$MOUNT_POINT"
    else
        echo "Mount point $MOUNT_POINT is responsive."
    fi
done
EOF
chmod +x /tmp/unmount-volumes_cron.sh
crontab -l | { cat; echo "*/2 * * * * /bin/bash /tmp/unmount-volumes_cron.sh"; } | crontab -

mkdir -p /var/spool/slurm || true
cat > /lib/systemd/system/slurmd.service <<EOF
[Unit]
Description=Slurm node daemon
After=munge.service network.target remote-fs.target

[Service]
Type=simple
EnvironmentFile=-/etc/sysconfig/slurmd
ExecStart=/usr/sbin/slurmd -D -s --conf-server @head_node_private_ip_address@:6817 \$SLURMD_OPTIONS -vvvv -N $INSTANCE_NAME
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
LimitNOFILE=131072
LimitMEMLOCK=infinity
LimitSTACK=infinity
Delegate=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl restart munge
systemctl enable slurmd.service
systemctl start slurmd.service