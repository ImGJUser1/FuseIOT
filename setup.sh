#!/bin/bash
# setup.sh - Setup script for FuseIoT

echo "Setting up FuseIoT..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate || source .venv/Scripts/activate

# Upgrade pip
pip install --upgrade pip

# Install with all dependencies
echo "Installing FuseIoT with all dependencies..."
pip install -e ".[all]"

# Run tests
echo "Running tests..."
pytest tests/ -v --tb=short

echo "Setup complete!"
echo ""
echo "Quick start:"
echo "  fuseiot --help"
echo "  python examples/basic_relay.py"