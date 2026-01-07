# Orchestrator - Minimal Agent Delegation Framework
#
# Runs the orchestration loop with target project mounted as volume.

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Node.js for Claude Code CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY main.py client.py audit.py ./
COPY mcp_server/ ./mcp_server/
COPY prompts/ ./prompts/

# Make app readable by all users (entrypoint runs as host user)
RUN chmod -R a+rX /app

# Entrypoint script for user mapping
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Mount point
RUN mkdir -p /project
VOLUME /project

# Environment
ENV CLAUDE_MODEL="claude-opus-4-5-20251101"
ENV HOST_UID=1000
ENV HOST_GID=1000
ENV HOME=/home/orchestrator

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py", "--project", "/project"]
