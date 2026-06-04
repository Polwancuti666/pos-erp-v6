#!/bin/bash
cd /root/pos-erp-v6/frontend
node node_modules/vite/bin/vite.js build
echo "BUILD_EXIT=$?"
