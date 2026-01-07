#!/bin/bash
#
# Setup script for Orchestrator
#
# Usage:
#   ./setup.sh          # Create venv and install dependencies
#   source venv/bin/activate  # Activate venv (run after setup)
#

set -e

echo "=================================="
echo "  Orchestrator Setup"
echo "=================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    echo "Install Python 3.11+ and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Check for minimum version (3.11)
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo "Warning: Python 3.11+ recommended (found $PYTHON_VERSION)"
fi

# Create virtual environment
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Created venv/"
fi

# Activate and install
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "=================================="
echo "  Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Login to Claude (if not already):"
echo "     claude login"
echo ""
echo "  3. Run orchestrator:"
echo "     ./run.sh init /path/to/project"
echo "     ./run.sh /path/to/project"
echo ""
