#!/bin/bash

# Development startup script for Research Agent API

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "Research Agent API - Development Server"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found. Create one with your GROQ_API_KEY"
fi

echo ""
echo "Starting server on http://localhost:8000"
echo "OpenAPI docs: http://localhost:8000/docs"
echo ""

# Run the server with reload for development
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
