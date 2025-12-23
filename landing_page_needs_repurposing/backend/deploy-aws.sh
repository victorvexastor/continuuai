#!/bin/bash
# Automated deployment script for IDE backend on AWS server

set -e

echo "🚀 Deploying IDE Backend to AWS..."

# 1. Extract archive
echo "📦 Extracting backend code..."
mkdir -p ~/ide-backend
cd ~/ide-backend
tar -xzf ~/ide-backend.tar.gz

# 2. Install Rust if needed
if ! command -v rustc &> /dev/null; then
    echo "🦀 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source ~/.cargo/env
else
    echo "✅ Rust already installed"
fi

# 3. Install system dependencies
echo "📚 Installing dependencies..."
sudo apt-get update
sudo apt-get install -y pkg-config libssl-dev libgit2-dev build-essential

# 4. Build backend (release mode)
echo "🔨 Building backend (this may take 5-10 minutes)..."
cargo build --release

# 5. Create workspace directory
mkdir -p workspace
cd workspace
git init
echo "# NeuAIs IDE Workspace" > README.md
git add .
git commit -m "Initial commit"
cd ..

# 6. Create systemd service
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/ide-backend.service > /dev/null <<EOF
[Unit]
Description=NeuAIs IDE Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ide-backend
ExecStart=/home/ubuntu/ide-backend/target/release/ide-backend
Restart=always
Environment="RUST_LOG=info"

[Install]
WantedBy=multi-user.target
EOF

# 7. Start service
echo "🎬 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable ide-backend
sudo systemctl start ide-backend

# 8. Wait and check status
sleep 2
sudo systemctl status ide-backend --no-pager

echo ""
echo "✅ Deployment complete!"
echo "🔗 Backend running at: http://15.134.197.186:3002"
echo "📊 Check logs: sudo journalctl -u ide-backend -f"
echo "🔄 Restart: sudo systemctl restart ide-backend"
