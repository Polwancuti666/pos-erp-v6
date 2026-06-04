#!/bin/bash
# Deploy script for POS ERP v6
set -e

echo "🚀 Deploying POS ERP v6..."

cd /root/pos-erp-v6

# Pull latest
echo "📥 Pulling latest code..."
git pull origin main

# Build frontend
echo "🔨 Building frontend..."
cd frontend
npm install --production=false
npm run build
cd ..

# Copy to static
echo "📁 Copying to static..."
cp -r frontend/dist/* static/

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart pos-erp

# Check status
echo "✅ Checking status..."
sudo systemctl status pos-erp --no-pager | head -5

echo ""
echo "✅ Deploy complete!"
echo "🔗 https://erp.beautynshine.web.id/app"
