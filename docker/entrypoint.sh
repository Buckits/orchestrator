#!/bin/bash
#
# Entrypoint script that runs as the host user's UID/GID
# This ensures files created in mounted volumes have correct ownership

set -e

# Create group if it doesn't exist
if ! getent group "$HOST_GID" > /dev/null 2>&1; then
    groupadd -g "$HOST_GID" orchestrator
fi

# Create user if it doesn't exist
if ! id -u "$HOST_UID" > /dev/null 2>&1; then
    useradd -u "$HOST_UID" -g "$HOST_GID" -m -s /bin/bash orchestrator
fi

# Get the username for this UID
USERNAME=$(getent passwd "$HOST_UID" | cut -d: -f1)

# Ensure home directory exists (but don't touch .claude - it's mounted from host)
HOME_DIR=$(getent passwd "$HOST_UID" | cut -d: -f6)
mkdir -p "$HOME_DIR"
chown "$HOST_UID:$HOST_GID" "$HOME_DIR"

# Run command as the mapped user
exec gosu "$USERNAME" "$@"
