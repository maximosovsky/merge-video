#!/bin/bash
# Merge Video — Alibaba ECS setup script
# Run as root on a fresh Ubuntu 22.04+ instance

set -e

echo "=== Merge Video Server Setup ==="

# 1. System packages
apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip \
    ffmpeg nginx certbot python3-certbot-nginx \
    git curl wget

# 2. Install yt-dlp
pip3 install yt-dlp

# 3. Create deploy user
useradd -m -s /bin/bash deploy || true

# 4. Clone repo
mkdir -p /opt/merge-video
cd /opt/merge-video
if [ ! -d ".git" ]; then
    git clone https://github.com/maximosovsky/merge-video.git .
else
    git pull
fi
chown -R deploy:deploy /opt/merge-video

# 5. Python virtualenv
python3.12 -m venv /opt/merge-video/venv
/opt/merge-video/venv/bin/pip install -r backend/requirements.txt
/opt/merge-video/venv/bin/pip install -r bot/requirements.txt

# 6. Copy .env files (user must fill these in)
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env 2>/dev/null || true
    echo "⚠️  Fill in backend/.env with your credentials!"
fi

if [ ! -f bot/.env ]; then
    cp bot/.env.example bot/.env 2>/dev/null || true
    echo "⚠️  Fill in bot/.env with your credentials!"
fi

# 7. Nginx config
cp deploy/nginx.conf /etc/nginx/sites-available/merge-video
ln -sf /etc/nginx/sites-available/merge-video /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. SSL (run after DNS is pointed to this server)
echo ""
echo "=== SSL Setup ==="
echo "After pointing DNS to this server, run:"
echo "  certbot --nginx -d merge.osovsky.com"
echo ""

# 9. Systemd services
cp deploy/merge-video.service /etc/systemd/system/
cp deploy/merge-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable merge-video merge-bot

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in backend/.env and bot/.env"
echo "  2. Point DNS to this server's IP"
echo "  3. Run: certbot --nginx -d merge.osovsky.com"
echo "  4. Start services:"
echo "     systemctl start merge-video"
echo "     systemctl start merge-bot"
echo ""
echo "  Check logs:"
echo "     journalctl -u merge-video -f"
echo "     journalctl -u merge-bot -f"
