# Local Development Setup

### Prerequisites
```bash
# Install Node.js 18+ and Python 3.10+
node --version  # Should be 18.0.0+
python --version  # Should be 3.10+

# Install pnpm for faster package management
npm install -g pnpm

# Install Turborepo for monorepo management
npm install -g turbo

# Install Docker for local services
docker --version
```

### Initial Setup
```bash
# Clone repository
git clone https://github.com/your-org/promptcraft.git
cd promptcraft

# Install all dependencies
pnpm install

# Set up environment files
cp .env.example .env.local
cp apps/api/.env.example apps/api/.env

# Start local database and Redis
docker-compose up -d postgres redis

# Run database migrations
cd apps/api && python -m alembic upgrade head && cd ../..

# Build shared packages
turbo build --filter=@promptcraft/shared
turbo build --filter=@promptcraft/ui
```

### Development Commands
```bash
# Start all services (web, api, cli sync)
turbo dev

# Start frontend only
turbo dev --filter=@promptcraft/web

# Start backend only
turbo dev --filter=@promptcraft/api

# Run tests across all packages
turbo test

# Run specific test suites
turbo test --filter=@promptcraft/web
turbo test --filter=@promptcraft/api
turbo test --filter=@promptcraft/cli

# Build production bundles
turbo build

# Lint and format code
turbo lint
turbo format
```
