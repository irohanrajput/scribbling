#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

cd "$(dirname "$0")"

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   Research Agent - Development Server${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Function to kill process on a given port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}Port $port in use. Killing process $pid...${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Step 1: Check and free ports
echo -e "${YELLOW}[1/4] Checking ports...${NC}"
kill_port 8000
kill_port 3000
echo -e "${GREEN}✓ Ports 8000 and 3000 are free${NC}"
echo ""

# Step 2: Check/Start Langfuse (uses vm-api's Langfuse container)
echo -e "${YELLOW}[2/4] Checking Langfuse...${NC}"
if curl -sf http://localhost:3703 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Langfuse already running${NC}"
else
    echo -e "${YELLOW}  Langfuse not running. Starting from vm-api...${NC}"
    if [ -d "$HOME/work/vm-api" ]; then
        # Start db first and wait for it to be healthy
        echo -e "${YELLOW}  Starting langfuse-db...${NC}"
        (cd "$HOME/work/vm-api" && docker compose -f docker-compose.dev.yml up -d langfuse-db)

        # Wait for db to be healthy
        for i in {1..20}; do
            if docker ps --format "{{.Names}} {{.Status}}" | grep -q "langfuse-db.*healthy"; then
                echo -e "${GREEN}✓ langfuse-db healthy${NC}"
                break
            fi
            sleep 2
        done

        # Now start langfuse
        echo -e "${YELLOW}  Starting langfuse...${NC}"
        (cd "$HOME/work/vm-api" && docker compose -f docker-compose.dev.yml up -d langfuse)

        # Wait for Langfuse to be ready
        echo -e "${YELLOW}  Waiting for Langfuse to be ready...${NC}"
        for i in {1..30}; do
            if curl -sf http://localhost:3703 > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Langfuse is ready${NC}"
                break
            fi
            if [ $i -eq 30 ]; then
                echo -e "${YELLOW}⚠ Langfuse may still be starting${NC}"
            fi
            sleep 2
        done
    else
        echo -e "${RED}✗ vm-api not found at ~/work/vm-api${NC}"
    fi
fi
echo ""

# Step 3: Setup Python environment with Poetry
echo -e "${YELLOW}[3/4] Setting up Python environment...${NC}"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}✗ Poetry not installed. Install with: curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Install dependencies with Poetry
echo -e "${YELLOW}  Installing dependencies with Poetry...${NC}"
poetry install --no-interaction

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to install dependencies${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Step 4: Check configuration
echo -e "${YELLOW}[4/4] Checking configuration...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    echo -e "${YELLOW}  Creating default .env file...${NC}"
    cat > .env << 'EOF'
# Groq API
GROQ_API_KEY=your_groq_api_key_here
GROQ_LLM_MODEL=openai/gpt-oss-120b

# Agent settings
MAX_ITERATIONS=100

# Langfuse (uses vm-api's Langfuse container)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=http://localhost:3703
EOF
    echo -e "${YELLOW}  Please edit .env with your API keys${NC}"
else
    echo -e "${GREEN}✓ .env file found${NC}"
fi

# Load environment variables
set -a
source .env
set +a

# Setup frontend
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}  Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
fi
echo -e "${GREEN}✓ Frontend ready${NC}"
echo ""

# Cleanup handler
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start frontend in background and capture output to detect port
echo -e "${YELLOW}Starting frontend...${NC}"
cd frontend
FRONTEND_LOG=$(mktemp)
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start and detect actual port
FRONTEND_PORT=3000
for i in {1..10}; do
    sleep 1
    # Check for port in Vite output
    if grep -q "localhost:" "$FRONTEND_LOG" 2>/dev/null; then
        DETECTED_PORT=$(grep -oP 'localhost:\K[0-9]+' "$FRONTEND_LOG" | head -1)
        if [ -n "$DETECTED_PORT" ]; then
            FRONTEND_PORT=$DETECTED_PORT
            break
        fi
    fi
done
rm -f "$FRONTEND_LOG"

# Print service summary
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}        All services starting...${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${CYAN}Services available:${NC}"
echo -e "  • Frontend:     ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  • Backend API:  ${GREEN}http://localhost:8000${NC}"
echo -e "  • API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • Langfuse:     ${GREEN}http://localhost:3703${NC} (from vm-api)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${CYAN}           FastAPI Server Logs${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Run backend in foreground with Poetry
poetry run uvicorn server:app --host 0.0.0.0 --port 8000 --reload
