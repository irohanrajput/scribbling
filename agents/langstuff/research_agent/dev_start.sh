#!/bin/bash

# Development startup script for Research Agent API + Frontend

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "Research Agent - Development Server"
echo "=========================================="

# Function to kill process on a given port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Kill any existing processes on required ports
echo "Checking ports..."
kill_port 8000
kill_port 3000
echo "Ports 8000 and 3000 are free"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "WARNING: .env file not found!"
    echo "Create one with: GROQ_API_KEY=your_key_here"
    echo ""
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo ""
echo "=========================================="
echo "Starting services..."
echo "=========================================="
echo ""
echo "  Backend API:  http://localhost:8000"
echo "  OpenAPI docs: http://localhost:8000/docs"
echo "  Frontend:     http://localhost:3000"
echo ""
echo "=========================================="
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start frontend in background (silent)
echo "Starting frontend..."
cd frontend
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 2
echo "Frontend running at http://localhost:3000"
echo ""
echo "=========================================="
echo "FastAPI Server Logs (Ctrl+C to stop)"
echo "=========================================="
echo ""

# Run backend in foreground - all logs visible here
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
