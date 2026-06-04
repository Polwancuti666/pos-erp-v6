#!/bin/bash
# =============================================================================
# GitHub Actions Secrets Setup Script
# =============================================================================
# This script automates the setup of GitHub Actions secrets for CI/CD.
#
# Usage:
#   ./setup-github-secrets.sh --vps-ip IP --ssh-key PATH
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated
#   - SSH key pair generated
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
VPS_IP=""
SSH_KEY_PATH=""
VPS_USER="deploy"
REPO="Polwancuti666/pos-erp-v6"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --vps-ip)
            VPS_IP="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY_PATH="$2"
            shift 2
            ;;
        --vps-user)
            VPS_USER="$2"
            shift 2
            ;;
        --repo)
            REPO="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate arguments
if [ -z "$VPS_IP" ]; then
    echo -e "${RED}Error: --vps-ip is required${NC}"
    echo "Usage: ./setup-github-secrets.sh --vps-ip IP --ssh-key PATH"
    exit 1
fi

if [ -z "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}No SSH key specified, using default: ~/.ssh/id_ed25519${NC}"
    SSH_KEY_PATH="$HOME/.ssh/id_ed25519"
fi

# Check if SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${RED}Error: SSH key not found: $SSH_KEY_PATH${NC}"
    echo ""
    echo "Generate a new SSH key pair:"
    echo "  ssh-keygen -t ed25519 -C 'github-actions-pos-erp' -f $SSH_KEY_PATH"
    exit 1
fi

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo ""
    echo "Install GitHub CLI:"
    echo "  https://cli.github.com/"
    exit 1
fi

# Check if GitHub CLI is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI is not authenticated${NC}"
    echo ""
    echo "Authenticate with GitHub:"
    echo "  gh auth login"
    exit 1
fi

# =============================================================================
# Setup SSH Key on VPS
# =============================================================================
echo -e "${BLUE}=== Setting up SSH key on VPS ===${NC}"

# Get public key
PUBLIC_KEY=$(cat "${SSH_KEY_PATH}.pub")

echo "Adding public key to VPS..."
echo "$PUBLIC_KEY" | ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no root@"$VPS_IP" "
    mkdir -p /home/$VPS_USER/.ssh
    echo '$PUBLIC_KEY' >> /home/$VPS_USER/.ssh/authorized_keys
    chmod 700 /home/$VPS_USER/.ssh
    chmod 600 /home/$VPS_USER/.ssh/authorized_keys
    chown -R $VPS_USER:$VPS_USER /home/$VPS_USER/.ssh
    echo 'SSH key added successfully'
"

# Test SSH connection
echo "Testing SSH connection..."
ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" "echo 'SSH connection successful'" || {
    echo -e "${RED}Error: SSH connection failed${NC}"
    exit 1
}

# =============================================================================
# Setup GitHub Repository Secrets
# =============================================================================
echo ""
echo -e "${BLUE}=== Setting up GitHub repository secrets ===${NC}"

# Set VPS_HOST
echo "Setting VPS_HOST..."
echo "$VPS_IP" | gh secret set VPS_HOST --repo "$REPO"
echo -e "${GREEN}✓ VPS_HOST set${NC}"

# Set VPS_USER
echo "Setting VPS_USER..."
echo "$VPS_USER" | gh secret set VPS_USER --repo "$REPO"
echo -e "${GREEN}✓ VPS_USER set${NC}"

# Set VPS_SSH_KEY
echo "Setting VPS_SSH_KEY..."
cat "$SSH_KEY_PATH" | gh secret set VPS_SSH_KEY --repo "$REPO"
echo -e "${GREEN}✓ VPS_SSH_KEY set${NC}"

# =============================================================================
# Verify Secrets
# =============================================================================
echo ""
echo -e "${BLUE}=== Verifying secrets ===${NC}"

gh secret list --repo "$REPO"

# =============================================================================
# Test Deployment
# =============================================================================
echo ""
echo -e "${BLUE}=== Testing deployment ===${NC}"

echo "Triggering test deployment..."
echo "test: verify CI/CD setup" | gh workflow run deploy.yml --repo "$REPO" --ref main 2>/dev/null || {
    echo -e "${YELLOW}Note: Could not trigger workflow automatically${NC}"
    echo "Push a commit to trigger deployment:"
    echo "  git commit --allow-empty -m 'test: verify CI/CD setup'"
    echo "  git push origin main"
}

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}=== GitHub Actions Secrets Setup Complete ===${NC}"
echo ""
echo "Repository: $REPO"
echo "VPS IP: $VPS_IP"
echo "VPS User: $VPS_USER"
echo "SSH Key: $SSH_KEY_PATH"
echo ""
echo "Secrets configured:"
echo "  - VPS_HOST: $VPS_IP"
echo "  - VPS_USER: $VPS_USER"
echo "  - VPS_SSH_KEY: [REDACTED]"
echo ""
echo "Next steps:"
echo "1. Push a commit to trigger deployment"
echo "2. Monitor deployment in GitHub Actions"
echo "3. Verify deployment on VPS"
echo ""
echo "View deployment status:"
echo "  gh run list --repo $REPO"
echo "  gh run watch --repo $REPO"
