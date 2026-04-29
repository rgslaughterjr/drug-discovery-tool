#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== Drug Discovery Tool — Local Dev Setup ==="
echo ""

# 1. Check prerequisites
echo "[1/5] Checking prerequisites..."
for cmd in docker mkcert; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "  ERROR: '$cmd' not found."
    if [ "$cmd" = "mkcert" ]; then
      echo "  Install: brew install mkcert  (macOS)  or  sudo apt install mkcert  (Linux)"
    fi
    if [ "$cmd" = "docker" ]; then
      echo "  Install Docker Desktop from https://docs.docker.com/get-docker/"
    fi
    exit 1
  fi
done
echo "  OK: docker and mkcert found"

# 2. Generate locally-trusted HTTPS certs
echo ""
echo "[2/5] Generating HTTPS certificates (mkcert)..."
mkdir -p dev/certs
mkcert -install 2>/dev/null || true
mkcert \
  -cert-file dev/certs/local.pem \
  -key-file  dev/certs/local-key.pem \
  localhost 127.0.0.1 ::1
echo "  OK: Certificates written to dev/certs/"

# 3. Write .env.local from template if missing
echo ""
echo "[3/5] Checking .env.local..."
if [ ! -f .env.local ]; then
  cp dev/.env.local.example .env.local
  echo "  Created .env.local from template."
  echo ""
  echo "  *** ACTION REQUIRED ***"
  echo "  Edit .env.local and add your API keys:"
  echo "    - ANTHROPIC_API_KEY  (for agentic mode)"
  echo "    - NVIDIA_API_KEY     (free at https://build.nvidia.com/)"
  echo ""
  read -rp "  Press Enter when you've added your keys, or Ctrl+C to exit..."
else
  echo "  .env.local already exists — skipping."
fi

# 4. Create data directory for SQLite
echo ""
echo "[4/5] Setting up local data directory..."
mkdir -p data
echo "  OK: data/ directory ready (SQLite will live at data/research.db)"

# 5. Start the stack
echo ""
echo "[5/5] Starting Docker Compose stack..."
docker compose -f dev/docker-compose.dev.yml --env-file .env.local up --build -d

echo ""
echo "=== Setup complete ==="
echo ""
echo "  Web UI (HTTPS):  https://localhost"
echo "  Backend API:     http://localhost:8000"
echo "  API docs:        http://localhost:8000/docs"
echo ""
echo "  Both servers have hot-reload enabled."
echo "  Edit src/ or web/src/ and changes apply instantly."
echo ""
echo "  To stop:  docker compose -f dev/docker-compose.dev.yml down"
echo "  Logs:     docker compose -f dev/docker-compose.dev.yml logs -f"
echo "  SQLite:   sqlite3 data/research.db"
