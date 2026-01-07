#!/bin/bash
#
# Run orchestrator in Docker
#
# Usage:
#   ./docker-run.sh init /path/to/project        # Initialize (generate AGENTS.md)
#   ./docker-run.sh /path/to/project             # Run orchestration
#   ./docker-run.sh new /path/to/project         # Start new session (archives old)
#   ./docker-run.sh status /path/to/project      # Session status
#
# Authentication:
#   Mounts ~/.claude from host - Claude SDK auto-detects credentials
#   (login with: claude login)
#
# Environment:
#   CLAUDE_MODEL - Model to use (default: claude-opus-4-5-20251101)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="orchestrator"

show_help() {
    echo "Usage: $0 <command> <project-path> [options]"
    echo ""
    echo "Commands:"
    echo "  init <project>       Initialize project (generate AGENTS.md with Claude)"
    echo "  <project>            Run orchestration (default)"
    echo "  new <project>        Start new session (archives existing)"
    echo "  status <project>     Show session status"
    echo ""
    echo "Options:"
    echo "  --max-iterations N   Limit iterations"
    echo "  --model MODEL        Claude model to use"
    echo ""
    echo "Environment:"
    echo "  CLAUDE_MODEL         Model (default: claude-opus-4-5-20251101)"
    echo ""
    echo "Examples:"
    echo "  $0 init /path/to/project"
    echo "  $0 /path/to/project"
    echo "  $0 new /path/to/project"
    echo "  $0 status /path/to/project"
}

# Check arguments
if [ -z "$1" ]; then
    show_help
    exit 1
fi

# Handle help
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

# Parse command
COMMAND=""
PROJECT_PATH=""

case "$1" in
    init|new|status)
        COMMAND="$1"
        shift
        if [ -z "$1" ]; then
            echo "Error: Project path required for '$COMMAND' command"
            exit 1
        fi
        PROJECT_PATH="$(cd "$1" && pwd)"
        shift
        ;;
    *)
        PROJECT_PATH="$(cd "$1" && pwd)"
        shift
        ;;
esac

# Check for Claude credentials
if [ ! -f "$HOME/.claude/.credentials.json" ]; then
    echo "Error: No Claude credentials found"
    echo ""
    echo "Please login first:"
    echo "  claude login"
    exit 1
fi

# Get host user/group IDs for permission mapping
HOST_UID=$(id -u)
HOST_GID=$(id -g)

echo "=========================================="
echo "  ORCHESTRATOR (Docker)"
echo "=========================================="
echo "Project: $PROJECT_PATH"
echo "Model: ${CLAUDE_MODEL:-claude-opus-4-5-20251101}"
echo "User: $HOST_UID:$HOST_GID"
echo ""

# Build image
echo "Building image..."
docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/docker/Dockerfile" "$SCRIPT_DIR"

echo ""
if [ -n "$COMMAND" ]; then
    echo "Running: $COMMAND"
else
    echo "Running orchestrator..."
fi
echo ""

# Build docker command
DOCKER_ARGS=(
    -it --rm
    -v "$PROJECT_PATH:/project"
    -v "$HOME/.claude:/home/orchestrator/.claude"
    -e CLAUDE_MODEL="${CLAUDE_MODEL:-claude-opus-4-5-20251101}"
    -e HOST_UID="$HOST_UID"
    -e HOST_GID="$HOST_GID"
    -e HOME="/home/orchestrator"
)

# Build python command
if [ -n "$COMMAND" ]; then
    PYTHON_CMD="python main.py $COMMAND /project $*"
else
    PYTHON_CMD="python main.py /project $*"
fi

# Run container
exec docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME" $PYTHON_CMD
