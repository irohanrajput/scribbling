#!/bin/bash

# Development startup script for Research Agent API + Frontend

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "Research Agent - Development Server"
echo "=========================================="

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
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend in background
echo "Starting backend..."
uvicorn server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend in background
echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Both services running. Press Ctrl+C to stop."
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
