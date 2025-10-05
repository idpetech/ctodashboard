#!/bin/bash

# CTO Dashboard MCP Server Startup Script

set -e

echo "Starting CTO Dashboard MCP Server..."

# Check if we're in the right directory
if [ ! -f "mcp_server.py" ]; then
    echo "Error: mcp_server.py not found. Please run this script from the project root."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing MCP dependencies..."
pip install -r requirements-mcp.txt

# Load environment variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Some services may not work properly."
fi

# Start the MCP server
echo "Starting MCP server..."
python3 mcp_server.py

