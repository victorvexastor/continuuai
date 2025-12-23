# Deploy IDE Backend to AWS EC2 (FREE TIER!)

You already have AWS credentials, so let's use EC2 free tier!

## Step 1: Launch EC2 Instance

```bash
# AWS Console → EC2 → Launch Instance
# - AMI: Ubuntu 22.04 LTS
# - Instance Type: t2.micro (FREE TIER - 750 hrs/month!)
# - Security Group: Allow ports 22, 80, 443, 3002
# - Create/use existing key pair
```

## Step 2: Connect & Install Rust

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Install dependencies
sudo apt update
sudo apt install -y pkg-config libssl-dev libgit2-dev build-essential
```

## Step 3: Deploy Backend

```bash
# Clone/copy your code
git clone <your-repo> # or scp the backend folder

cd backend

# Build
cargo build --release

# Run with systemd (auto-restart)
sudo nano /etc/systemd/system/ide-backend.service
```

**Service file (`/etc/systemd/system/ide-backend.service`):**
```ini
[Unit]
Description=NeuAIs IDE Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/backend
ExecStart=/home/ubuntu/backend/target/release/ide-backend
Restart=always
Environment="RUST_LOG=info"

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl daemon-reload
sudo systemctl enable ide-backend
sudo systemctl start ide-backend
sudo systemctl status ide-backend
```

## Step 4: Setup Domain (Optional)

**Option A: Use Elastic IP**
```bash
# AWS Console → EC2 → Elastic IPs → Allocate
# Associate with your instance
# Use: http://YOUR-ELASTIC-IP:3002
```

**Option B: Use CloudFlare Proxy (FREE SSL!)**
```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

# Create tunnel
cloudflared tunnel login
cloudflared tunnel create ide-backend
cloudflared tunnel route dns ide-backend ide-api.neuais.com

# Run tunnel
cloudflared tunnel --config ~/.cloudflared/config.yml run
```

**CloudFlare config (`~/.cloudflared/config.yml`):**
```yaml
tunnel: YOUR-TUNNEL-ID
credentials-file: /home/ubuntu/.cloudflared/YOUR-TUNNEL-ID.json

ingress:
  - hostname: ide-api.neuais.com
    service: http://localhost:3002
  - service: http_status:404
```

## Step 5: Update Frontend

```javascript
// frontend/src/services/ideApi.js
const API_URL = 'https://ide-api.neuais.com';  // Or http://YOUR-EC2-IP:3002
```

---

## Costs

- **EC2 t2.micro**: FREE for 12 months (750 hrs/month)
- **Elastic IP**: FREE if attached to running instance
- **CloudFlare Tunnel**: FREE
- **Total**: $0 for first year!

After free tier ends:
- t2.micro: ~$8.50/month
- Still cheaper than other options!

---

## Monitoring

```bash
# View logs
sudo journalctl -u ide-backend -f

# Check status
sudo systemctl status ide-backend

# Restart
sudo systemctl restart ide-backend
```

---

## Alternative: Use Your Existing AWS Infrastructure

If you already have EC2 instances running, you can:
1. SSH into existing instance
2. Run backend alongside existing services
3. Use nginx reverse proxy to route /api/* to backend

**Even better: You're already paying for it!** 🎉
