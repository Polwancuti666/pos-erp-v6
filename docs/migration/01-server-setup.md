# 01 — Server Setup

Complete VPS provisioning guide for Beauty & Shine ERP.

## Requirements

- Ubuntu 22.04 LTS (recommended)
- Minimum: 2 vCPU, 4GB RAM, 40GB SSD
- Root SSH access
- Public IP address

---

## Step 1: Initial Login

```bash
ssh root@YOUR_VPS_IP
```

---

## Step 2: System Update

```bash
# Update package lists
apt update && apt upgrade -y

# Install essential packages
apt install -y \
  curl \
  wget \
  git \
  unzip \
  software-properties-common \
  apt-transport-https \
  ca-certificates \
  gnupg \
  lsb-release \
  htop \
  tree \
  jq \
  fail2ban \
  ufw
```

---

## Step 3: Create Deployment User

```bash
# Create deploy user
useradd -m -s /bin/bash deploy

# Add to sudo group
usermod -aG sudo deploy

# Set password
passwd deploy

# Copy SSH keys from root
cp -r /root/.ssh /home/deploy/
chown -R deploy:deploy /home/deploy/.ssh

# Test login
su - deploy
```

---

## Step 4: SSH Hardening

```bash
# Backup original config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# Edit SSH config
cat > /etc/ssh/sshd_config.d/hardening.conf << 'EOF'
# Security hardening
Port 22
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
AllowUsers deploy
EOF

# Restart SSH
systemctl restart sshd
```

---

## Step 5: Firewall Setup

```bash
# Reset UFW
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH
ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
ufw --force enable

# Verify
ufw status verbose
```

---

## Step 6: Fail2Ban Setup

```bash
# Configure fail2ban
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3
backend  = systemd

[sshd]
enabled = true
port    = 22
filter  = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

# Start fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# Check status
fail2ban-client status sshd
```

---

## Step 7: Install Python 3.11

```bash
# Add deadsnakes PPA
add-apt-repository ppa:deadsnakes/ppa -y
apt update

# Install Python 3.11
apt install -y \
  python3.11 \
  python3.11-venv \
  python3.11-dev \
  python3-pip

# Verify
python3.11 --version
```

---

## Step 8: Install Node.js 20 LTS

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

# Install Node.js
apt install -y nodejs

# Verify
node --version
npm --version

# Install global packages
npm install -g pm2
```

---

## Step 9: Install Nginx

```bash
# Install Nginx
apt install -y nginx

# Start and enable
systemctl enable nginx
systemctl start nginx

# Verify
systemctl status nginx
```

---

## Step 10: Create Application Directory

```bash
# Create directory
mkdir -p /var/www/pos-erp-v6

# Set ownership
chown -R deploy:deploy /var/www/pos-erp-v6

# Create required subdirectories
su - deploy -c "
  mkdir -p /var/www/pos-erp-v6/{logs,backups,static}
"
```

---

## Step 11: Configure Swap (Optional but Recommended)

```bash
# Create 2GB swap file
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Optimize swap usage
cat >> /etc/sysctl.conf << 'EOF'
vm.swappiness=10
vm.vfs_cache_pressure=50
EOF
sysctl -p

# Verify
free -h
```

---

## Step 12: System Tuning

```bash
# Optimize kernel parameters
cat >> /etc/sysctl.conf << 'EOF'
# Network optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# File system
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
EOF
sysctl -p
```

---

## Step 13: Automatic Security Updates

```bash
# Install unattended-upgrades
apt install -y unattended-upgrades

# Configure
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

# Enable
dpkg-reconfigure -plow unattended-upgrades
```

---

## Verification

Run this script to verify the setup:

```bash
#!/bin/bash
echo "=== Server Setup Verification ==="
echo ""

# Check Python
echo -n "Python 3.11: "
python3.11 --version 2>&1 | head -1

# Check Node.js
echo -n "Node.js: "
node --version 2>&1

# Check Nginx
echo -n "Nginx: "
systemctl is-active nginx

# Check UFW
echo -n "Firewall: "
ufw status | head -1

# Check Fail2Ban
echo -n "Fail2Ban: "
systemctl is-active fail2ban

# Check SSH config
echo -n "SSH Root Login: "
grep -c "PermitRootLogin no" /etc/ssh/sshd_config.d/hardening.conf 2>/dev/null && echo "DISABLED ✓" || echo "ENABLED ✗"

# Check swap
echo -n "Swap: "
swapon --show | tail -1 | awk '{print $1, $3}'

echo ""
echo "=== Setup Complete ==="
```

---

## Next Steps

After server setup is complete:

1. [02-database-migration.md](./02-database-migration.md) — Migrate database
2. [03-application-deploy.md](./03-application-deploy.md) — Deploy application
3. [04-ssl-setup.md](./04-ssl-setup.md) — Setup SSL/TLS

---

**Estimated Time:** 30-45 minutes
