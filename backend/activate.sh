#!/bin/bash
# Simple activation script for development
# Usage: source activate.sh

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

if [ ! -f ".venv/pyvenv.cfg" ] || [ requirements.txt -nt .venv/pyvenv.cfg ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo "Virtual environment ready!"
echo "Run: python main.py"