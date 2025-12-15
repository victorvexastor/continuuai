.PHONY: help deploy stop restart logs clean verify test test-ui reset setup dev prod

# Default target
help:
	@echo "ContinuuAI - One-Command Deployment"
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup        - First-time setup (creates .env, pulls images)"
	@echo "  make deploy       - Start all services"
	@echo "  make verify       - Check system health"
	@echo ""
	@echo "Common Commands:"
	@echo "  make stop         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make logs         - Tail all logs (Ctrl+C to exit)"
	@echo "  make clean        - Stop and remove containers/volumes"
	@echo "  make reset        - Nuclear option: clean + fresh deploy"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start with dev mode enabled"
	@echo "  make test         - Run all backend tests"
	@echo "  make test-ui      - Run frontend tests (Playwright)"
	@echo ""
	@echo "Monitoring:"
	@echo "  make status       - Show running containers"
	@echo "  make ps           - Alias for status"
	@echo "  make top          - Show resource usage"
	@echo ""
	@echo "Services:"
	@echo "  make logs-api     - API Gateway logs"
	@echo "  make logs-db      - Database logs"
	@echo "  make logs-retrieval - Retrieval service logs"
	@echo ""
	@echo "Advanced:"
	@echo "  make build        - Rebuild all images"
	@echo "  make shell-db     - PostgreSQL shell"
	@echo "  make backup       - Backup database"

# First-time setup
setup:
	@echo "🚀 Setting up ContinuuAI..."
	@if [ ! -f .env ]; then \
		cp .env.example .env && \
		echo "✅ Created .env file (edit if needed)"; \
	else \
		echo "⚠️  .env already exists, skipping"; \
	fi
	@echo "📦 Pulling Docker images (this may take a few minutes)..."
	@docker compose pull postgres || true
	@echo "✅ Setup complete! Run 'make deploy' to start."

# Deploy everything
deploy: setup
	@echo "🚀 Starting ContinuuAI..."
	@docker compose up -d
	@echo ""
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@$(MAKE) verify
	@echo ""
	@echo "✅ ContinuuAI is running!"
	@echo ""
	@echo "📍 URLs:"
	@echo "   User App:        http://localhost:3000"
	@echo "   Admin Dashboard: http://localhost:3001"
	@echo "   API Gateway:     http://localhost:8080"
	@echo "   Database:        localhost:5433"
	@echo ""
	@echo "📊 Next steps:"
	@echo "   make logs      - Watch logs"
	@echo "   make verify    - Check health"
	@echo "   make stop      - Stop services"

# Development mode
dev:
	@echo "🔧 Starting in development mode..."
	@DEV_MODE=true docker compose up

# Production mode (daemon)
prod: deploy

# Stop all services
stop:
	@echo "⏹️  Stopping ContinuuAI..."
	@docker compose stop

# Restart services
restart: stop deploy

# View logs
logs:
	@docker compose logs -f

logs-api:
	@docker compose logs -f api

logs-db:
	@docker compose logs -f postgres

logs-retrieval:
	@docker compose logs -f retrieval

logs-inference:
	@docker compose logs -f inference

logs-graph:
	@docker compose logs -f graph-deriver

# Container status
status:
	@docker compose ps

ps: status

# Resource usage
top:
	@docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Clean up (preserves volumes)
clean:
	@echo "🧹 Cleaning up containers..."
	@docker compose down
	@echo "✅ Containers removed (volumes preserved)"

# Nuclear reset (destroys data!)
reset:
	@echo "⚠️  WARNING: This will DELETE ALL DATA!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "💥 Removing all containers and volumes..."; \
		docker compose down -v; \
		rm -f .env; \
		$(MAKE) setup; \
		$(MAKE) deploy; \
	else \
		echo "Cancelled."; \
	fi

# Verify system health
verify:
	@bash scripts/verify_deployment.sh

# Run backend tests
test:
	@echo "🧪 Running backend tests..."
	@bash scripts/run_all_tests.sh

# Run frontend tests (when implemented)
test-ui:
	@echo "🧪 Running frontend tests..."
	@echo "⚠️  Not implemented yet (Phase 2)"

# Build/rebuild images
build:
	@echo "🔨 Building Docker images..."
	@docker compose build

# Database shell
shell-db:
	@docker compose exec postgres psql -U continuuai -d continuuai

# Backup database
backup:
	@echo "💾 Backing up database..."
	@mkdir -p backups
	@docker compose exec -T postgres pg_dump -U continuuai continuuai > backups/backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "✅ Backup saved to backups/"

# Restore database (use: make restore BACKUP=backups/backup-20240101-120000.sql)
restore:
	@if [ -z "$(BACKUP)" ]; then \
		echo "❌ Usage: make restore BACKUP=backups/backup-20240101-120000.sql"; \
		exit 1; \
	fi
	@echo "⚠️  Restoring database from $(BACKUP)..."
	@docker compose exec -T postgres psql -U continuuai continuuai < $(BACKUP)
	@echo "✅ Database restored"

# Update dependencies
update:
	@echo "📦 Updating Docker images..."
	@docker compose pull
	@echo "✅ Images updated. Run 'make restart' to apply."
