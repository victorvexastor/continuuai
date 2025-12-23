# Deploying IDE Backend to Fly.io

## Prerequisites

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login to Fly.io**:
   ```bash
   flyctl auth login
   ```

## Deploy Backend

### First Time Deployment

```bash
cd backend

# Create new Fly.io app (if not already created)
flyctl launch --no-deploy

# Or if app exists, just deploy
flyctl deploy

# Check status
flyctl status

# View logs
flyctl logs
```

### Get App URL

```bash
flyctl info
# Your backend will be at: https://neuais-ide-backend.fly.dev
```

## Update Frontend

After deploying, update the frontend API URL:

**File**: `frontend/src/services/ideApi.js`

```javascript
// Change from:
const API_URL = 'http://localhost:3002';

// To:
const API_URL = 'https://neuais-ide-backend.fly.dev';
```

## Environment Variables (if needed)

```bash
# Set environment variables
flyctl secrets set RUST_LOG=debug

# List secrets
flyctl secrets list
```

## Scaling

```bash
# Scale up
flyctl scale show
flyctl scale vm shared-cpu-1x --memory 1024

# Scale down (save costs)
flyctl scale vm shared-cpu-1x --memory 512
```

## Monitoring

```bash
# View metrics
flyctl dashboard

# Real-time logs
flyctl logs -f

# SSH into machine
flyctl ssh console
```

## Cost Optimization

- **Auto-stop/start**: Machines stop when idle (configured in fly.toml)
- **Minimal resources**: 512MB RAM, 1 shared CPU (very cheap!)
- **Free tier**: Fly.io offers free allowance for small apps

## Troubleshooting

```bash
# Check build logs
flyctl logs --app neuais-ide-backend

# Restart app  
flyctl apps restart neuais-ide-backend

# Destroy and redeploy
flyctl apps destroy neuais-ide-backend
flyctl launch
```

## Persistent Storage (Optional)

If you need persistent workspace files:

```bash
# Create volume
flyctl volumes create workspace_data --size 1

# Update fly.toml
[[mounts]]
  source = "workspace_data"
  destination = "/app/workspace"
```

---

**Your IDE backend will be live at**: `https://neuais-ide-backend.fly.dev`
