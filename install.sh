#!/usr/bin/env bash
set -euo pipefail

# ContinuuAI One-Command Installer
# Usage: bash install.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; exit 1; }

banner() {
  echo ""
  echo "╔═══════════════════════════════════════════════════════╗"
  echo "║                                                       ║"
  echo "║   ██████╗ ██████╗ ███╗   ██╗████████╗██╗███╗   ██╗  ║"
  echo "║  ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██║████╗  ██║  ║"
  echo "║  ██║     ██║   ██║██╔██╗ ██║   ██║   ██║██╔██╗ ██║  ║"
  echo "║  ██║     ██║   ██║██║╚██╗██║   ██║   ██║██║╚██╗██║  ║"
  echo "║  ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║██║ ╚████║  ║"
  echo "║   ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝  ║"
  echo "║                                                       ║"
  echo "║            Context-Aware Memory System                ║"
  echo "║                    v1.0.0                             ║"
  echo "╚═══════════════════════════════════════════════════════╝"
  echo ""
}

check_os() {
  log "Detecting operating system..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    success "Linux detected"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    success "macOS detected"
  else
    error "Unsupported OS: $OSTYPE (only Linux and macOS are supported)"
  fi
}

check_docker() {
  log "Checking Docker installation..."
  if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Install from: https://docs.docker.com/get-docker/"
  fi
  
  if ! docker info &> /dev/null; then
    error "Docker daemon is not running. Start Docker Desktop or run: sudo systemctl start docker"
  fi
  
  success "Docker is installed and running"
  
  # Check Docker Compose
  if ! docker compose version &> /dev/null; then
    error "Docker Compose v2 is not available. Update Docker to latest version."
  fi
  
  success "Docker Compose is available"
}

get_process_on_port() {
  local port=$1
  if [[ "$OS" == "macos" ]]; then
    lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null | head -1
  else
    ss -tulnp 2>/dev/null | grep ":$port " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1
  fi
}

get_process_name() {
  local pid=$1
  ps -p $pid -o comm= 2>/dev/null || echo "unknown"
}

# Ports we're already planning to use (to avoid reassigning to another service's port)
RESERVED_PORTS=(3000 3001 8080 5433)

is_port_reserved() {
  local port=$1
  for p in "${RESERVED_PORTS[@]}"; do
    [ "$p" == "$port" ] && return 0
  done
  return 1
}

find_free_port() {
  local start_port=$1
  local port=$start_port
  while [ $port -lt $((start_port + 100)) ]; do
    # Skip if port is reserved for another ContinuuAI service
    if is_port_reserved $port; then
      port=$((port + 1))
      continue
    fi
    if [[ "$OS" == "macos" ]]; then
      if ! lsof -Pi :$port -sTCP:LISTEN -t &> /dev/null; then
        echo $port
        return 0
      fi
    else
      if ! ss -tuln | grep -q ":$port "; then
        echo $port
        return 0
      fi
    fi
    port=$((port + 1))
  done
  echo $start_port
}

check_ports() {
  log "Checking for existing ContinuuAI services..."
  
  # Check if docker compose services are already running
  if docker compose ps 2>/dev/null | grep -q "continuuai"; then
    warn "ContinuuAI services are already running"
    echo "   Services detected: $(docker compose ps --format '{{.Service}}' | tr '\n' ', ' | sed 's/,$//')"
    read -p "Stop existing services and redeploy? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      log "Stopping existing services..."
      docker compose down
      success "Services stopped"
    else
      log "Updating/restarting existing services..."
      return 0
    fi
  fi
  
  # Check for non-ContinuuAI port conflicts
  log "Checking for port conflicts..."
  
  declare -A PORT_NAMES=(
    [3000]="USER_APP_PORT"
    [3001]="ADMIN_DASHBOARD_PORT"
    [8080]="API_PORT"
    [5433]="POSTGRES_PORT"
  )
  declare -A PORT_DESC=(
    [3000]="user app"
    [3001]="admin dashboard"
    [8080]="API gateway"
    [5433]="database"
  )
  
  PORTS=(3000 3001 8080 5433)
  CONFLICT_PORTS=()
  CONFLICT_PIDS=()
  CONFLICT_NAMES=()
  
  for PORT in "${PORTS[@]}"; do
    local pid=""
    if [[ "$OS" == "macos" ]]; then
      pid=$(lsof -Pi :$PORT -sTCP:LISTEN -t 2>/dev/null | head -1)
    else
      if ss -tuln | grep -q ":$PORT "; then
        pid=$(get_process_on_port $PORT)
      fi
    fi
    
    if [ -n "$pid" ]; then
      local pname=$(get_process_name $pid)
      warn "Port $PORT (${PORT_DESC[$PORT]}) is in use by $pname (PID: $pid)"
      CONFLICT_PORTS+=("$PORT")
      CONFLICT_PIDS+=("$pid")
      CONFLICT_NAMES+=("$pname")
    fi
  done
  
  if [ ${#CONFLICT_PORTS[@]} -gt 0 ]; then
    echo ""
    echo "   Options:"
    echo "   [1] Kill conflicting processes and use default ports"
    echo "   [2] Auto-assign alternative ports (will update .env)"
    echo "   [3] Continue anyway (services may fail to start)"
    echo "   [4] Cancel installation"
    echo ""
    read -p "   Choose option [1-4]: " -n 1 -r
    echo
    
    case $REPLY in
      1)
        log "Stopping conflicting processes..."
        for i in "${!CONFLICT_PIDS[@]}"; do
          local pid=${CONFLICT_PIDS[$i]}
          local port=${CONFLICT_PORTS[$i]}
          local pname=${CONFLICT_NAMES[$i]}
          log "Killing $pname (PID: $pid) on port $port..."
          kill $pid 2>/dev/null || sudo kill $pid 2>/dev/null || warn "Failed to kill PID $pid"
        done
        sleep 2
        success "Conflicting processes stopped"
        ;;
      2)
        log "Finding alternative ports..."
        for i in "${!CONFLICT_PORTS[@]}"; do
          local old_port=${CONFLICT_PORTS[$i]}
          local new_port=$(find_free_port $old_port)
          local env_var=${PORT_NAMES[$old_port]}
          
          if [ "$new_port" != "$old_port" ]; then
            log "Reassigning ${PORT_DESC[$old_port]}: $old_port → $new_port"
            
            # Update or add to .env
            if grep -q "^${env_var}=" .env 2>/dev/null; then
              sed -i.bak "s/^${env_var}=.*/${env_var}=${new_port}/" .env
            else
              echo "${env_var}=${new_port}" >> .env
            fi
            
            # Store new port for display later
            eval "NEW_${env_var}=${new_port}"
          fi
        done
        rm -f .env.bak
        success "Alternative ports configured in .env"
        ;;
      3)
        warn "Continuing with port conflicts - some services may fail"
        ;;
      4|*)
        error "Installation cancelled."
        ;;
    esac
  else
    success "All required ports are available"
  fi
}

check_disk_space() {
  log "Checking disk space..."
  
  if [[ "$OS" == "macos" ]]; then
    AVAILABLE_GB=$(df -g . | tail -1 | awk '{print $4}')
  else
    AVAILABLE_GB=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
  fi
  
  if [ "$AVAILABLE_GB" -lt 5 ]; then
    warn "Low disk space: ${AVAILABLE_GB}GB available (recommend 5GB+)"
  else
    success "Sufficient disk space: ${AVAILABLE_GB}GB available"
  fi
}

setup_env() {
  log "Setting up environment configuration..."
  
  if [ -f .env ]; then
    log "Using existing .env file"
    # Check if passwords are still defaults
    if grep -q "continuuai_secure_password_change_me" .env 2>/dev/null; then
      warn "Default passwords detected in .env"
      read -p "Generate secure passwords? [Y/n] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        if command -v openssl &> /dev/null; then
          log "Generating secure passwords..."
          # Generate passwords without special chars that break sed
          DB_PASS=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
          ADMIN_TOKEN=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
          DEBUG_TOKEN=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
          JWT_SECRET=$(openssl rand -base64 64 | tr -d '/+=' | head -c 64)
          
          # Use temporary file to avoid sed issues
          cp .env .env.tmp
          sed "s|continuuai_secure_password_change_me|${DB_PASS}|g" .env.tmp | \
          sed "s|admin_secret_token_change_me|${ADMIN_TOKEN}|g" | \
          sed "s|debug_token_change_me|${DEBUG_TOKEN}|g" | \
          sed "s|your_jwt_secret_change_me|${JWT_SECRET}|g" > .env.new
          mv .env.new .env
          rm -f .env.tmp
          
          success "Generated secure credentials"
        fi
      fi
    fi
  else
    cp .env.example .env
    success "Created .env file from template"
    
    # Generate secure passwords for new installs
    if command -v openssl &> /dev/null; then
      log "Generating secure passwords..."
      DB_PASS=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
      ADMIN_TOKEN=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
      DEBUG_TOKEN=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
      JWT_SECRET=$(openssl rand -base64 64 | tr -d '/+=' | head -c 64)
      
      cp .env .env.tmp
      sed "s|continuuai_secure_password_change_me|${DB_PASS}|g" .env.tmp | \
      sed "s|admin_secret_token_change_me|${ADMIN_TOKEN}|g" | \
      sed "s|debug_token_change_me|${DEBUG_TOKEN}|g" | \
      sed "s|your_jwt_secret_change_me|${JWT_SECRET}|g" > .env.new
      mv .env.new .env
      rm -f .env.tmp
      
      success "Generated secure credentials"
    else
      warn "OpenSSL not found - using default passwords (INSECURE for production!)"
    fi
  fi
}

pull_images() {
  log "Pulling Docker base images (this may take a few minutes)..."
  docker compose pull postgres || warn "Failed to pull postgres image (will build locally)"
  success "Base images ready"
}

build_services() {
  log "Building ContinuuAI services..."
  docker compose build --parallel || error "Build failed"
  success "All services built successfully"
}

start_services() {
  log "Starting ContinuuAI stack..."
  
  # Build and start services
  log "Building containers (this may take a few minutes on first run)..."
  docker compose up -d --build || error "Failed to start services"
  
  log "Waiting for services to become healthy..."
  TIMEOUT=180  # Increased for frontend builds
  ELAPSED=0
  
  while [ $ELAPSED -lt $TIMEOUT ]; do
    # Count running services
    RUNNING=$(docker compose ps --format '{{.State}}' | grep -c "running" || echo "0")
    TOTAL=$(docker compose ps --format '{{.State}}' | wc -l)
    
    if [ "$RUNNING" -ge 8 ]; then
      break
    fi
    
    if [ $((ELAPSED % 10)) -eq 0 ]; then
      echo "   $RUNNING/$TOTAL services running..."
    fi
    
    sleep 2
    ELAPSED=$((ELAPSED + 2))
  done
  
  if [ $ELAPSED -ge $TIMEOUT ]; then
    warn "Services taking longer than expected to start"
    warn "Check logs: make logs"
  else
    success "All services started"
  fi
}

verify_deployment() {
  log "Verifying deployment..."
  
  if [ -f scripts/verify_deployment.sh ]; then
    bash scripts/verify_deployment.sh || warn "Some health checks failed"
  else
    log "Checking API Gateway..."
    sleep 3
    if curl -sf http://localhost:8080/healthz > /dev/null; then
      success "API Gateway is responding"
    else
      warn "API Gateway not responding yet (may still be starting)"
    fi
  fi
}

show_next_steps() {
  # Read actual ports from .env or use defaults
  local user_port=$(grep "^USER_APP_PORT=" .env 2>/dev/null | cut -d= -f2 || echo "3000")
  local admin_port=$(grep "^ADMIN_DASHBOARD_PORT=" .env 2>/dev/null | cut -d= -f2 || echo "3001")
  local api_port=$(grep "^API_PORT=" .env 2>/dev/null | cut -d= -f2 || echo "8080")
  local db_port=$(grep "^POSTGRES_PORT=" .env 2>/dev/null | cut -d= -f2 || echo "5433")
  
  # Use defaults if empty
  user_port=${user_port:-3000}
  admin_port=${admin_port:-3001}
  api_port=${api_port:-8080}
  db_port=${db_port:-5433}
  
  echo ""
  echo "╔═══════════════════════════════════════════════════════╗"
  echo "║                                                       ║"
  echo "║  ✅  ContinuuAI is now running!                       ║"
  echo "║                                                       ║"
  echo "╚═══════════════════════════════════════════════════════╝"
  echo ""
  echo "📍 Access Points:"
  echo "   • User App:        http://localhost:${user_port}"
  echo "   • Admin Dashboard: http://localhost:${admin_port}"
  echo "   • API Gateway:     http://localhost:${api_port}"
  echo "   • Database:        localhost:${db_port}"
  echo ""
  echo "📊 Useful Commands:"
  echo "   • make logs       - View all logs"
  echo "   • make status     - Check service status"
  echo "   • make verify     - Run health checks"
  echo "   • make stop       - Stop all services"
  echo "   • make restart    - Restart all services"
  echo "   • make help       - Show all commands"
  echo ""
  echo "📚 Documentation: docs/README.md"
  echo "🔧 Configuration:  .env"
  echo ""
  
  # Try to open browser (optional)
  if command -v xdg-open &> /dev/null; then
    log "Opening user app in browser..."
    xdg-open "http://localhost:${user_port}" &> /dev/null || true
  elif command -v open &> /dev/null; then
    log "Opening user app in browser..."
    open "http://localhost:${user_port}" &> /dev/null || true
  fi
}

main() {
  banner
  
  log "Starting ContinuuAI installation..."
  echo ""
  
  check_os
  check_docker
  check_ports
  check_disk_space
  setup_env
  pull_images
  build_services
  start_services
  verify_deployment
  show_next_steps
  
  success "Installation complete!"
}

# Run main function
main
