#!/bin/bash
# Server hardening for merge-video ECS
# Run once via SSH: ssh root@47.84.36.115 "bash -s" < deploy/harden.sh

set -e

echo "=== 1. Install fail2ban ==="
apt install -y fail2ban
systemctl enable fail2ban
systemctl start fail2ban

echo "=== 2. Configure fail2ban for SSH ==="
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled = true
port = 22
maxretry = 5
bantime = 3600
findtime = 600
EOF
systemctl restart fail2ban

echo "=== 3. Setup SSH key auth ==="
mkdir -p /root/.ssh
chmod 700 /root/.ssh
# Append local public key (will be piped separately)
if [ ! -f /root/.ssh/authorized_keys ]; then
    touch /root/.ssh/authorized_keys
fi
chmod 600 /root/.ssh/authorized_keys

echo "=== 4. Disable password auth ==="
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl restart sshd

echo "=== 5. Configure UFW firewall ==="
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

echo "=== 6. Add rate limiting to nginx ==="
# Add limit_req_zone to nginx http block if not present
if ! grep -q "limit_req_zone" /etc/nginx/nginx.conf; then
    sed -i '/http {/a\    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;' /etc/nginx/nginx.conf
fi

echo "=== 7. Deploy hardened nginx config ==="
cat > /etc/nginx/sites-available/merge-video << 'NGINX'
server {
    listen 80;
    server_name merge-video.osovsky.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name merge-video.osovsky.com;

    ssl_certificate /etc/letsencrypt/live/merge-video.osovsky.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/merge-video.osovsky.com/privkey.pem;

    client_max_body_size 5G;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location /merge {
        limit_req zone=api burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
NGINX
nginx -t && systemctl reload nginx

echo "=== Done ==="
echo "fail2ban: $(systemctl is-active fail2ban)"
echo "ufw: $(ufw status | head -1)"
echo "SSH password auth: $(grep PasswordAuthentication /etc/ssh/sshd_config | grep -v '#')"
