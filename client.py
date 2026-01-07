"""
Claude SDK Client Configuration

Minimal client setup for orchestration mode.
"""

import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient


# Session MCP tools
SESSION_TOOLS = [
    "mcp__session__session_get_status",
    "mcp__session__session_get_next_phase",
    "mcp__session__session_mark_phase_complete",
    "mcp__session__session_is_complete",
]

# Built-in tools
BUILTIN_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]


def create_client(project: Path, model: str) -> ClaudeSDKClient:
    """Create a Claude SDK client configured for orchestration."""

    return ClaudeSDKClient(
        options=ClaudeAgentOptions(
            model=model,
            system_prompt=(
                "You are an Autonomous Orchestrator. You coordinate specialist agents "
                "to implement features. You are a ROUTER - you delegate work to agents, "
                "you NEVER implement code directly. Read .claude/agents/AGENTS.md for routing."
            ),
            allowed_tools=[*BUILTIN_TOOLS, *SESSION_TOOLS],
            mcp_servers={
                "session": {
                    "command": sys.executable,
                    "args": ["-m", "mcp_server.session"],
                    "env": {
                        "PROJECT_DIR": str(project),
                        "PYTHONPATH": str(Path(__file__).parent),
                    },
                },
            },
            setting_sources=["project"],
            max_turns=1000,
            cwd=str(project),
        )
    )


def create_simple_client(project: Path, model: str) -> ClaudeSDKClient:
    """Create a simple Claude client for one-shot queries (no tools needed)."""

    return ClaudeSDKClient(
        options=ClaudeAgentOptions(
            model=model,
            system_prompt=(
                "You are a helpful assistant that analyzes agent definitions and generates "
                "documentation. Output only the markdown content requested, no explanations or preamble."
            ),
            allowed_tools=[],  # No tools needed - pure text generation
            max_turns=1,  # Single turn only
            cwd=str(project),
        )
    )
