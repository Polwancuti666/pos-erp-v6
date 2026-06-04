# 06 — GitHub Actions Secrets

Complete guide for setting up CI/CD secrets for automated deployment.

## Overview

This guide covers:

1. Generating SSH key pair
2. Adding SSH key to VPS
3. Configuring GitHub repository secrets
4. Testing the deployment workflow

---

## Step 1: Generate SSH Key Pair

### On your LOCAL machine (or the old server):

```bash
# Generate SSH key pair for GitHub Actions
ssh-keygen -t ed25519 -C "github-actions-pos-erp" -f ~/.ssh/github-actions-pos-erp -N ""

# This creates two files:
# ~/.ssh/github-actions-pos-erp (private key)
# ~/.ssh/github-actions-pos-erp.pub (public key)

# View the private key (you'll need this for GitHub)
cat ~/.ssh/github-actions-pos-erp

# View the public key (you'll add this to VPS)
cat ~/.ssh/github-actions-pos-erp.pub
```

---

## Step 2: Add Public Key to New VPS

### On the NEW VPS:

```bash
# Login as deploy user
su - deploy

# Add public key to authorized_keys
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Verify
cat ~/.ssh/authorized_keys

# Test SSH connection from local machine
ssh -i ~/.ssh/github-actions-pos-erp deploy@NEW_VPS_IP "echo 'SSH connection successful'"
```

---

## Step 3: Configure GitHub Repository Secrets

### Option A: Using GitHub CLI (Recommended)

```bash
# Install GitHub CLI if not installed
# https://cli.github.com/

# Login to GitHub
gh auth login

# Set repository secrets
gh secret set VPS_HOST --body "NEW_VPS_IP"
gh secret set VPS_USER --body "deploy"
gh secret set VPS_SSH_KEY --body "$(cat ~/.ssh/github-actions-pos-erp)"

# Verify secrets are set
gh secret list
```

### Option B: Using GitHub Web Interface

1. Go to your repository: https://github.com/Polwancuti666/pos-erp-v6
2. Click **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Add the following secrets:

#### Secret 1: VPS_HOST
- **Name:** `VPS_HOST`
- **Value:** Your VPS IP address (e.g., `203.0.113.50`)
- Click **Add secret**

#### Secret 2: VPS_USER
- **Name:** `VPS_USER`
- **Value:** `deploy`
- Click **Add secret**

#### Secret 3: VPS_SSH_KEY
- **Name:** `VPS_SSH_KEY`
- **Value:** The entire private key content (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`)
- Click **Add secret**

### Verify Secrets

After adding secrets, you should see:

| Secret | Value |
|--------|-------|
| VPS_HOST | `***` |
| VPS_USER | `***` |
| VPS_SSH_KEY | `***` |

---

## Step 4: Test SSH Connection

```bash
# Test SSH connection using the key
ssh -i ~/.ssh/github-actions-pos-erp -o StrictHostKeyChecking=no deploy@NEW_VPS_IP "echo 'Connection successful' && whoami && pwd"

# Expected output:
# Connection successful
# deploy
# /home/deploy
```

---

## Step 5: Update Deploy Workflow (If Needed)

The current deploy workflow should work with these secrets. Verify the workflow file:

```yaml
# .github/workflows/deploy.yml
name: Deploy to VPS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /var/www/pos-erp-v6
            git pull origin main
            source .venv/bin/activate
            pip install -r requirements.txt
            cd frontend && npm ci && npm run build && cd ..
            cp -r frontend/dist/* static/
            sudo systemctl restart pos-erp
```

---

## Step 6: Test Automated Deployment

### Trigger a Test Deployment

```bash
# Make a small change
echo "# Test deployment" >> README.md

# Commit and push
git add README.md
git commit -m "test: trigger deployment test"
git push origin main

# Monitor the deployment
gh run list
gh run watch
```

### Check Deployment Status

1. Go to **Actions** tab in GitHub repository
2. Click on the latest workflow run
3. Monitor the deployment steps
4. Check for any errors

### Verify Deployment

```bash
# After deployment completes
ssh -i ~/.ssh/github-actions-pos-erp deploy@NEW_VPS_IP "
  cd /var/www/pos-erp-v6
  git log --oneline -1
  systemctl status pos-erp
"
```

---

## Troubleshooting

### Permission Denied (publickey)

```bash
# Check if key is added to agent
ssh-add ~/.ssh/github-actions-pos-erp

# Check authorized_keys on VPS
cat ~/.ssh/authorized_keys

# Verify key format (should be one line)
wc -l ~/.ssh/authorized_keys
```

### Host Key Verification Failed

```bash
# Add host key to known_hosts
ssh-keyscan -H NEW_VPS_IP >> ~/.ssh/known_hosts

# Or disable strict host key checking (not recommended for production)
ssh -o StrictHostKeyChecking=no deploy@NEW_VPS_IP
```

### Deployment Fails

1. Check GitHub Actions logs for errors
2. Verify VPS is accessible
3. Check if application directory exists
4. Verify permissions on VPS

### Secret Not Found

```bash
# List all secrets
gh secret list

# Delete and recreate secret
gh secret delete VPS_HOST
gh secret set VPS_HOST --body "NEW_VPS_IP"
```

---

## Security Best Practices

1. **Use dedicated SSH key** — Don't reuse personal keys
2. **Limit key permissions** — Add key only to deploy user
3. **Rotate keys regularly** — Generate new keys every 6-12 months
4. **Monitor access** — Check SSH logs for unauthorized access
5. **Use passphrase** — Protect private key with passphrase (optional)

### Generate Key with Passphrase

```bash
# Generate key with passphrase
ssh-keygen -t ed25519 -C "github-actions-pos-erp" -f ~/.ssh/github-actions-pos-erp

# When prompted, enter a passphrase
# You'll need to add this passphrase to GitHub secrets as well
```

---

## Additional Secrets (Optional)

For advanced deployments, you may need additional secrets:

| Secret | Purpose |
|--------|---------|
| `DOCKERHUB_USERNAME` | Docker Hub login (if using Docker) |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `SLACK_WEBHOOK` | Slack notifications |
| `SENTRY_DSN` | Error tracking |

### Adding Docker Hub Secrets

```bash
gh secret set DOCKERHUB_USERNAME --body "your-username"
gh secret set DOCKERHUB_TOKEN --body "your-access-token"
```

---

## Checklist

- [ ] SSH key pair generated
- [ ] Public key added to VPS
- [ ] VPS_HOST secret configured
- [ ] VPS_USER secret configured
- [ ] VPS_SSH_KEY secret configured
- [ ] SSH connection tested
- [ ] Deploy workflow updated (if needed)
- [ ] Test deployment triggered
- [ ] Deployment verified

---

## Next Steps

After GitHub secrets are configured:

1. [07-monitoring.md](./07-monitoring.md) — Setup monitoring
2. [08-verification.md](./08-verification.md) — Run verification tests

---

**Estimated Time:** 15-30 minutes
