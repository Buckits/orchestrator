#!/bin/bash
# Orchestrator - Agent Delegation Framework
#
# Usage:
#   ./run.sh init /path/to/project         # Initialize (generate AGENTS.md with Claude)
#   ./run.sh /path/to/project              # Run orchestration
#   ./run.sh status /path/to/project       # Show session status

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup venv if needed
if [ ! -f "$DIR/venv/bin/activate" ]; then
    echo "Setting up Python environment..."
    python3 -m venv "$DIR/venv"
    source "$DIR/venv/bin/activate"
    pip install -q -r "$DIR/requirements.txt"
else
    source "$DIR/venv/bin/activate"
fi

# Run orchestrator
exec python "$DIR/main.py" "$@"
