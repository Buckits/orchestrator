#!/usr/bin/env python3
"""
Session MCP Server

Manages orchestration session state via markdown files.
Provides tools for reading status, getting next phase, and marking completion.
"""

import json
import os
import re
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


PROJECT_DIR = Path(os.environ.get("PROJECT_DIR", ".")).resolve()

mcp = FastMCP("session")


def get_session_path() -> Path:
    return PROJECT_DIR / ".claude" / "tasks" / "session-current.md"


def parse_session(content: str) -> dict:
    """Parse session markdown into structured data."""
    result = {
        "name": "",
        "phase": 0,
        "total_phases": 0,
        "current_agent": "",
        "state": "unknown",
        "user_request": "",
        "phases": [],
        "work_log": "",
    }

    # Session name
    match = re.search(r'^# Session: (.+)$', content, re.MULTILINE)
    if match:
        result["name"] = match.group(1).strip()

    # Status section
    match = re.search(r'## Status\s*\n((?:- .+\n)+)', content, re.MULTILINE)
    if match:
        status = match.group(1)

        m = re.search(r'Phase: (\d+) of (\d+)', status)
        if m:
            result["phase"] = int(m.group(1))
            result["total_phases"] = int(m.group(2))

        m = re.search(r'Current Agent: (\S+)', status)
        if m:
            result["current_agent"] = m.group(1)

        m = re.search(r'State: (\w+)', status)
        if m:
            result["state"] = m.group(1)

    # User request
    match = re.search(r'## User Request\s*\n([\s\S]*?)(?=\n## |\Z)', content)
    if match:
        result["user_request"] = match.group(1).strip()

    # Phases
    match = re.search(r'## Phases\s*\n((?:\d+\. .+\n)+)', content, re.MULTILINE)
    if match:
        for line in match.group(1).strip().split('\n'):
            m = re.match(r'(\d+)\. \[([x ])\] (\S+) - (.+)', line.strip())
            if m:
                result["phases"].append({
                    "number": int(m.group(1)),
                    "complete": m.group(2) == 'x',
                    "agent": m.group(3),
                    "description": m.group(4),
                })

    # Work log
    match = re.search(r'## Work Log\s*\n([\s\S]*?)(?=\n## |\Z)', content)
    if match:
        result["work_log"] = match.group(1).strip()

    return result


def format_session(session: dict) -> str:
    """Format session data back to markdown."""
    phases = "\n".join([
        f"{p['number']}. [{'x' if p['complete'] else ' '}] {p['agent']} - {p['description']}"
        for p in session["phases"]
    ])

    work_log = session.get("work_log") or "(agents will update this)"

    return f"""# Session: {session['name']}

## Status
- Phase: {session['phase']} of {session['total_phases']}
- Current Agent: {session['current_agent']}
- State: {session['state']}

## User Request
{session['user_request']}

## Phases
{phases}

## Work Log
{work_log}
"""


@mcp.tool()
def session_get_status() -> str:
    """Get current session status including name, phase, agent, and state."""
    path = get_session_path()

    if not path.exists():
        return json.dumps({
            "error": "No session file found",
            "hint": "Create .claude/tasks/session-current.md"
        }, indent=2)

    return json.dumps(parse_session(path.read_text()), indent=2)


@mcp.tool()
def session_get_next_phase() -> str:
    """Get the next incomplete phase to work on."""
    path = get_session_path()

    if not path.exists():
        return json.dumps({"error": "No session file found"}, indent=2)

    session = parse_session(path.read_text())

    for phase in session["phases"]:
        if not phase["complete"]:
            completed = [p["agent"] for p in session["phases"]
                        if p["complete"] and p["number"] < phase["number"]]
            return json.dumps({
                "phase_number": phase["number"],
                "agent": phase["agent"],
                "description": phase["description"],
                "depends_on": completed,
                "user_request": session["user_request"],
            }, indent=2)

    return json.dumps({
        "all_complete": True,
        "message": "All phases complete!"
    }, indent=2)


@mcp.tool()
def session_mark_phase_complete(
    phase_number: Annotated[int, Field(description="Phase number to mark complete", ge=1)],
    notes: Annotated[str, Field(description="Notes about work done")] = ""
) -> str:
    """Mark a phase as complete and update the session file."""
    path = get_session_path()

    if not path.exists():
        return json.dumps({"error": "No session file found"}, indent=2)

    session = parse_session(path.read_text())

    # Mark phase complete
    phase_agent = ""
    for phase in session["phases"]:
        if phase["number"] == phase_number:
            phase["complete"] = True
            phase_agent = phase["agent"]
            break
    else:
        return json.dumps({"error": f"Phase {phase_number} not found"}, indent=2)

    # Find next phase
    next_phase = None
    for phase in session["phases"]:
        if not phase["complete"]:
            next_phase = phase
            break

    if next_phase:
        session["phase"] = next_phase["number"]
        session["current_agent"] = next_phase["agent"]
        session["state"] = "pending"
    else:
        session["state"] = "complete"
        session["current_agent"] = "none"

    # Add notes to work log
    if notes:
        log = session.get("work_log", "")
        if log and log != "(agents will update this)":
            log += f"\n\n### Phase {phase_number} ({phase_agent})\n{notes}"
        else:
            log = f"### Phase {phase_number} ({phase_agent})\n{notes}"
        session["work_log"] = log

    path.write_text(format_session(session))

    return json.dumps({
        "success": True,
        "phase_marked": phase_number,
        "next_phase": next_phase["number"] if next_phase else None,
        "next_agent": next_phase["agent"] if next_phase else None,
        "all_complete": next_phase is None,
    }, indent=2)


@mcp.tool()
def session_is_complete() -> str:
    """Check if all phases are complete."""
    path = get_session_path()

    if not path.exists():
        return json.dumps({"error": "No session file found"}, indent=2)

    session = parse_session(path.read_text())

    completed = [p for p in session["phases"] if p["complete"]]
    remaining = [p for p in session["phases"] if not p["complete"]]

    return json.dumps({
        "complete": len(remaining) == 0,
        "completed_count": len(completed),
        "total_count": len(session["phases"]),
        "remaining": [f"{p['number']}. {p['agent']} - {p['description']}" for p in remaining],
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
