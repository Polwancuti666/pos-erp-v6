# 🚀 Setup Auto-Deploy GitHub Actions

## Step 1: Add SSH Key to VPS

```bash
# On your VPS, add this public key to authorized_keys:
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL0SoPw6yBYiIweJuKveQCAiestlHsxRBEa4fcc7lF2Y github-actions-deploy" >> ~/.ssh/authorized_keys
```

## Step 2: Add GitHub Secrets

Go to: **https://github.com/Polwancuti666/pos-erp-v6/settings/secrets/actions**

Add these **Repository Secrets**:

| Secret Name | Value |
|-------------|-------|
| `VPS_HOST` | `erp.beautynshine.web.id` atau IP VPS |
| `VPS_USER` | `root` |
| `VPS_SSH_KEY` | *(private key - ambil dari server)* |

### Cara ambil private key:
```bash
cat /root/.ssh/deploy_key
```

Copy **SELURUH** output (termasuk `-----BEGIN...` dan `-----END...`) sebagai value `VPS_SSH_KEY`.

## Step 3: Test Auto-Deploy

```bash
# Push any change to trigger deploy
cd /root/pos-erp-v6
echo "# Updated" >> README.md
git add README.md
git commit -m "test: trigger auto-deploy"
git push origin main
```

## Manual Deploy (tanpa GitHub Actions)

```bash
ssh root@erp.beautynshine.web.id 'bash /root/pos-erp-v6/deploy.sh'
```

## Troubleshooting

```bash
# Check GitHub Actions status
# https://github.com/Polwancuti666/pos-erp-v6/actions

# Check service on VPS
sudo systemctl status pos-erp
sudo journalctl -u pos-erp -f
```
