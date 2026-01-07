#!/usr/bin/env python3
"""
Orchestrator - Agent Delegation Framework

Initializes target projects and orchestrates work using domain agents.

Usage:
    python main.py init /path/to/project         # Initialize project (creates AGENTS.md with Claude)
    python main.py /path/to/project              # Run orchestration
    python main.py /path/to/project -n 5         # Max 5 iterations
    python main.py new /path/to/project          # Start new session (archives old)
    python main.py status /path/to/project       # Show session status
"""

import argparse
import asyncio
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from audit import audit_project, print_audit_report, validate_agents_md
from client import create_client, create_simple_client

# Configuration
AUTO_CONTINUE_DELAY = 3
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# Progress bar characters
BAR_FILLED = "█"
BAR_EMPTY = "░"
BAR_WIDTH = 30


@dataclass
class PhaseStats:
    """Statistics for a single phase."""
    phase_number: int
    agent: str
    description: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    completed: bool = False


@dataclass
class SessionStats:
    """Accumulated statistics for the session."""
    phases: dict[int, PhaseStats] = field(default_factory=dict)
    session_start: float = field(default_factory=time.time)
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def get_phase(self, phase_num: int) -> Optional[PhaseStats]:
        return self.phases.get(phase_num)

    def start_phase(self, phase_num: int, agent: str, description: str) -> None:
        self.phases[phase_num] = PhaseStats(
            phase_number=phase_num,
            agent=agent,
            description=description,
            start_time=time.time(),
        )

    def end_phase(self, phase_num: int, input_tokens: int = 0, output_tokens: int = 0) -> None:
        if phase_num in self.phases:
            self.phases[phase_num].end_time = time.time()
            self.phases[phase_num].input_tokens = input_tokens
            self.phases[phase_num].output_tokens = output_tokens
            self.phases[phase_num].completed = True
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

    def get_phase_duration(self, phase_num: int) -> Optional[float]:
        phase = self.phases.get(phase_num)
        if phase and phase.start_time and phase.end_time:
            return phase.end_time - phase.start_time
        return None

    def get_total_duration(self) -> float:
        return time.time() - self.session_start


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_tokens(tokens: int) -> str:
    """Format token count in human-readable form."""
    if tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"{tokens / 1000:.1f}k"
    else:
        return f"{tokens / 1000000:.2f}M"


def load_orchestrator_prompt() -> str:
    """Load the orchestrator prompt template."""
    prompt_path = Path(__file__).parent / "prompts" / "orchestrator.md"
    return prompt_path.read_text()


def get_session_path(project: Path) -> Path:
    """Get path to session file."""
    return project / ".claude" / "tasks" / "session-current.md"


def parse_phases(content: str) -> list[dict]:
    """Parse phases from session content."""
    phases = []
    for line in content.split('\n'):
        m = re.match(r'(\d+)\. \[([x ])\] (\S+) - (.+)', line.strip())
        if m:
            phases.append({
                "number": int(m.group(1)),
                "complete": m.group(2) == 'x',
                "agent": m.group(3),
                "description": m.group(4),
            })
    return phases


def is_session_complete(project: Path) -> bool:
    """Check if session is complete by parsing session file."""
    session_file = get_session_path(project)
    if not session_file.exists():
        return False

    content = session_file.read_text()

    if "State: complete" in content:
        return True

    phases = re.findall(r'\d+\. \[([x ])\]', content)
    return phases and all(p == 'x' for p in phases)


def get_current_phase(project: Path) -> Optional[dict]:
    """Get the current (first incomplete) phase."""
    session_file = get_session_path(project)
    if not session_file.exists():
        return None

    content = session_file.read_text()
    phases = parse_phases(content)

    for phase in phases:
        if not phase["complete"]:
            return phase
    return None


def print_progress_bar(project: Path, stats: Optional[SessionStats] = None) -> None:
    """Print a visual progress bar with phase information."""
    session_file = get_session_path(project)
    if not session_file.exists():
        print("   No session file")
        return

    content = session_file.read_text()

    # Get session name
    name_match = re.search(r'^# Session: (.+)$', content, re.MULTILINE)
    name = name_match.group(1) if name_match else "Unknown"

    # Parse phases
    phases = parse_phases(content)
    if not phases:
        print("   No phases found")
        return

    total = len(phases)
    completed = sum(1 for p in phases if p["complete"])
    progress = completed / total if total > 0 else 0

    # Build progress bar
    filled = int(BAR_WIDTH * progress)
    bar = BAR_FILLED * filled + BAR_EMPTY * (BAR_WIDTH - filled)

    print(f"\n   Session: {name}")
    print(f"   [{bar}] {completed}/{total} phases ({progress * 100:.0f}%)")

    # Show phase list with status
    print("\n   Phases:")
    for phase in phases:
        if phase["complete"]:
            status = "✓"
            color = "\033[32m"  # Green
        elif get_current_phase(project) and phase["number"] == get_current_phase(project)["number"]:
            status = "▶"
            color = "\033[33m"  # Yellow
        else:
            status = "○"
            color = "\033[90m"  # Gray

        reset = "\033[0m"

        # Add timing and token info if available
        extra = ""
        if stats:
            phase_stats = stats.get_phase(phase["number"])
            if phase_stats and phase_stats.completed:
                duration = stats.get_phase_duration(phase["number"])
                if duration:
                    tokens = phase_stats.input_tokens + phase_stats.output_tokens
                    extra = f" ({format_duration(duration)}, {format_tokens(tokens)} tokens)"

        print(f"   {color}{status} {phase['number']}. {phase['agent']}: {phase['description']}{extra}{reset}")


def print_session_status(project: Path, stats: Optional[SessionStats] = None) -> None:
    """Print current session status with progress bar."""
    print_progress_bar(project, stats)


def print_stats_summary(stats: SessionStats) -> None:
    """Print final statistics summary."""
    print("\n" + "─" * 60)
    print("   SESSION STATISTICS")
    print("─" * 60)

    total_duration = stats.get_total_duration()
    print(f"   Total time:     {format_duration(total_duration)}")
    print(f"   Input tokens:   {format_tokens(stats.total_input_tokens)}")
    print(f"   Output tokens:  {format_tokens(stats.total_output_tokens)}")
    print(f"   Total tokens:   {format_tokens(stats.total_input_tokens + stats.total_output_tokens)}")

    # Estimate cost (approximate rates for Opus)
    input_cost = (stats.total_input_tokens / 1000000) * 15  # $15/M input
    output_cost = (stats.total_output_tokens / 1000000) * 75  # $75/M output
    total_cost = input_cost + output_cost
    print(f"   Est. cost:      ${total_cost:.2f}")

    if stats.phases:
        print("\n   Per-phase breakdown:")
        for phase_num in sorted(stats.phases.keys()):
            phase = stats.phases[phase_num]
            if phase.completed:
                duration = stats.get_phase_duration(phase_num) or 0
                tokens = phase.input_tokens + phase.output_tokens
                print(f"     {phase_num}. {phase.agent}: {format_duration(duration)}, {format_tokens(tokens)} tokens")


def load_core_context() -> str:
    """Load core framework agents and skills for context injection."""
    orchestrator_dir = Path(__file__).parent
    context_parts = []

    # Load core AGENTS.md
    core_agents_md = orchestrator_dir / ".claude" / "agents" / "AGENTS.md"
    if core_agents_md.exists():
        context_parts.append("## Core Framework Agents\n\n")
        context_parts.append(core_agents_md.read_text())

    # Load ALL orchestrator skills fully - these are the orchestrator's operating manual
    skills_dir = orchestrator_dir / ".claude" / "skills"

    if skills_dir.exists():
        context_parts.append("\n\n## Orchestrator Skills\n")
        context_parts.append("These skills define HOW to orchestrate. Read and follow them.\n")
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    context_parts.append(f"\n### Skill: {skill_dir.name}\n")
                    context_parts.append(skill_file.read_text())

    return "".join(context_parts)


def load_project_context(project: Path, audit_result) -> str:
    """Load target project agents and skills for context injection."""
    context_parts = []

    # Load project AGENTS.md if exists
    project_agents_md = project / ".claude" / "agents" / "AGENTS.md"
    if project_agents_md.exists():
        context_parts.append("\n\n## Target Project Agents\n\n")
        context_parts.append(project_agents_md.read_text())

    # List discovered agents
    if audit_result.discovered_agents:
        context_parts.append("\n\n## Discovered Domain Agents\n")
        for agent in audit_result.discovered_agents:
            context_parts.append(f"\n### Agent: {agent.name}\n")
            context_parts.append(f"Description: {agent.description}\n")
            context_parts.append(f"File: {agent.file_path}\n")
            if agent.owns:
                context_parts.append(f"Owns: {', '.join(agent.owns)}\n")

    # Discover target project skills (list only - agents read full content themselves)
    skills_dir = project / ".claude" / "skills"
    if skills_dir.exists():
        skill_names = []
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_names.append(skill_dir.name)

        if skill_names:
            context_parts.append("\n\n## Target Project Skills\n")
            context_parts.append("Domain-specific skills available in `.claude/skills/`:\n")
            for name in skill_names:
                context_parts.append(f"- `{name}` - see `.claude/skills/{name}/SKILL.md`\n")

    return "".join(context_parts)


@dataclass
class SessionResult:
    """Result from a single session run."""
    response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


async def run_planning_session(
    project: Path,
    model: str,
    user_request: str,
    audit_result,
) -> None:
    """Run a planning session to create session-current.md."""
    print("\n" + "-" * 60)
    print("  Creating session plan...")
    print("-" * 60 + "\n")

    # Build planning prompt
    core_context = load_core_context()
    project_context = load_project_context(project, audit_result)

    planning_prompt = f"""You are the session-planner agent. Your task is to analyze the user's request and create a session file.

{core_context}

{project_context}

## User Request

{user_request}

## Instructions

1. Read your agent definition: .claude/agents/session-planner.md
2. Read the project's AGENTS.md for available domain agents
3. Analyze the user request and determine which agents are needed
4. Create a session file at: {project}/.claude/tasks/session-current.md

## CRITICAL: Session File Format

The session file MUST use this EXACT format for MCP tools to work:

```markdown
# Session: [Short name]

## Status
- Phase: 1 of N
- Current Agent: [first-agent]
- State: pending

## User Request
[verbatim request]

## Phases
1. [ ] agent-name - description
2. [ ] other-agent - description
3. [ ] finalize - Validate and commit

## Work Log
(agents will update this)
```

Phase format MUST be: `N. [ ] agent-name - description`
Do NOT use phase headers like `### Phase 1:` or nested task lists.

Begin by reading your agent definition.
"""

    client = create_client(project, model)

    async with client:
        await run_session(client, planning_prompt)


async def run_session(client, prompt: str) -> SessionResult:
    """Run a single orchestration session and return results with token counts."""
    await client.query(prompt)

    result = SessionResult()

    async for msg in client.receive_response():
        if type(msg).__name__ == "AssistantMessage" and hasattr(msg, "content"):
            for block in msg.content:
                if type(block).__name__ == "TextBlock" and hasattr(block, "text"):
                    result.response += block.text
                    print(block.text, end="", flush=True)
                elif type(block).__name__ == "ToolUseBlock" and hasattr(block, "name"):
                    print(f"\n[Tool: {block.name}]", flush=True)

        # Try to extract token usage from the message
        if hasattr(msg, "usage"):
            if hasattr(msg.usage, "input_tokens"):
                result.input_tokens += msg.usage.input_tokens
            if hasattr(msg.usage, "output_tokens"):
                result.output_tokens += msg.usage.output_tokens

    print("\n" + "-" * 60)
    return result


def archive_session(project: Path) -> None:
    """Archive current session file to session-N.md."""
    session_path = get_session_path(project)
    if not session_path.exists():
        return

    tasks_dir = session_path.parent

    # Find next available session number
    existing = list(tasks_dir.glob("session-*.md"))
    max_num = 0
    for f in existing:
        if f.name == "session-current.md":
            continue
        try:
            num = int(f.stem.split("-")[1])
            max_num = max(max_num, num)
        except (IndexError, ValueError):
            pass

    new_name = f"session-{max_num + 1}.md"
    new_path = tasks_dir / new_name
    session_path.rename(new_path)
    print(f"  Archived: {session_path.name} → {new_name}")


async def run_orchestration(
    project: Path,
    model: str,
    max_iterations: int | None,
    new_session: bool = False,
) -> None:
    """
    Main orchestration loop.

    Args:
        project: Target project path
        model: Claude model to use
        max_iterations: Max iterations (None = unlimited)
        new_session: If True, archive old session and start fresh
    """

    print("\n" + "=" * 60)
    print("  ORCHESTRATOR")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"Model: {model}")

    # Step 1: Check AGENTS.md exists and is valid
    agents_md_path = project / ".claude" / "agents" / "AGENTS.md"

    if not agents_md_path.exists():
        print("\n✗ AGENTS.md not found")
        print("\nRun 'init' first to initialize the project:")
        print(f"  ./run.sh init {project}")
        return

    content = agents_md_path.read_text()
    is_valid, issues = validate_agents_md(content)

    if not is_valid:
        print("\n✗ AGENTS.md is invalid:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nRun 'init' to regenerate:")
        print(f"  ./run.sh init {project}")
        return

    print("\n✓ AGENTS.md valid")

    # Step 2: Discover agents for display
    audit_result = audit_project(project, auto_fix=False)

    if audit_result.discovered_agents:
        print(f"\nAvailable agents ({len(audit_result.discovered_agents)}):")
        for agent in audit_result.discovered_agents:
            print(f"  • {agent.name}")

    # Step 3: Handle existing session
    session_path = get_session_path(project)
    session_exists = session_path.exists()

    if new_session and session_exists:
        print("\n  Starting new session...")
        archive_session(project)
        session_exists = False

    if session_exists and is_session_complete(project):
        print("\n✓ Existing session is complete!")
        print("\nTo start a new session: ./run.sh new /path/to/project")
        return

    if not session_exists:
        # No session - enter planning mode
        print("\n" + "-" * 60)
        print("  PLANNING MODE")
        print("-" * 60)

        print("\nDescribe what you want to build:")
        print("(The session-planner will create a session file)")
        print()

        try:
            user_request = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting.")
            return

        if not user_request:
            print("No input provided. Exiting.")
            return

        # Create planning session
        await run_planning_session(project, model, user_request, audit_result)

        # Check if session was created
        if not get_session_path(project).exists():
            print("\nNo session file created. Exiting.")
            return

        print("\nSession file created. Starting execution...")

    # Initialize stats tracking
    stats = SessionStats()

    # Print execution header
    print("\n" + "=" * 60)
    print("  EXECUTION")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"Model: {model}")
    print_session_status(project, stats)
    print()

    # Load prompt with core context (skills) and project context
    base_prompt = load_orchestrator_prompt()
    core_context = load_core_context()
    project_context = load_project_context(project, audit_result)

    prompt = f"""# CONTEXT

{core_context}

{project_context}

---

{base_prompt}
"""

    # Main loop
    iteration = 0
    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        if is_session_complete(project):
            print("\n" + "=" * 60)
            print("  SESSION COMPLETE")
            print("=" * 60)
            print_session_status(project, stats)
            print_stats_summary(stats)
            break

        # Get current phase for tracking
        current_phase = get_current_phase(project)
        if current_phase:
            stats.start_phase(
                current_phase["number"],
                current_phase["agent"],
                current_phase["description"]
            )

        print(f"\n--- Iteration {iteration} ---")
        if current_phase:
            print(f"    Phase {current_phase['number']}: {current_phase['agent']}")
        print()

        client = create_client(project, model)
        iteration_start = time.time()

        async with client:
            result = await run_session(client, prompt)

        iteration_duration = time.time() - iteration_start

        # Check if phase completed and update stats
        new_phase = get_current_phase(project)
        if current_phase and (new_phase is None or new_phase["number"] != current_phase["number"]):
            # Phase changed, mark previous as complete
            stats.end_phase(
                current_phase["number"],
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens
            )
            print(f"\n   Phase {current_phase['number']} completed in {format_duration(iteration_duration)}")
            if result.input_tokens or result.output_tokens:
                print(f"   Tokens: {format_tokens(result.input_tokens)} in / {format_tokens(result.output_tokens)} out")

        print_session_status(project, stats)
        print(f"\nContinuing in {AUTO_CONTINUE_DELAY}s...")
        await asyncio.sleep(AUTO_CONTINUE_DELAY)

    print_stats_summary(stats)
    print("\nDone!")


async def init_command(project: Path, model: str) -> None:
    """Initialize project: create directories and generate AGENTS.md with Claude."""
    print("\n" + "=" * 60)
    print("  INITIALIZING PROJECT")
    print("=" * 60)
    print(f"Project: {project}")
    print(f"Model: {model}")
    print()

    # Step 1: Create directories
    claude_dir = project / ".claude"
    agents_dir = claude_dir / "agents"
    tasks_dir = claude_dir / "tasks"

    for dir_path in [claude_dir, agents_dir, tasks_dir]:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {dir_path.relative_to(project)}")

    # Step 2: Discover existing agents
    agent_files = list(agents_dir.glob("*.md"))
    agent_files = [f for f in agent_files if f.name != "AGENTS.md"]

    print(f"\n  Found {len(agent_files)} agent file(s)")
    for f in agent_files:
        print(f"    • {f.name}")

    # Step 3: Discover skills
    skills_dir = project / ".claude" / "skills"
    skill_files = []
    if skills_dir.exists():
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir():
                skill_file = item / "SKILL.md"
                if skill_file.exists():
                    skill_files.append((item.name, skill_file))

    if skill_files:
        print(f"\n  Found {len(skill_files)} skill(s)")
        for skill_name, _ in skill_files:
            print(f"    • {skill_name}")
    else:
        print("\n  No skills found")

    # Step 4: Check if AGENTS.md needs generation
    agents_md_path = agents_dir / "AGENTS.md"
    needs_generation = False

    if not agents_md_path.exists():
        print("\n  AGENTS.md: Not found - will generate")
        needs_generation = True
    else:
        content = agents_md_path.read_text()
        is_valid, issues = validate_agents_md(content)
        if not is_valid:
            print(f"\n  AGENTS.md: Invalid - will regenerate")
            for issue in issues:
                print(f"    - {issue}")
            needs_generation = True
        else:
            print("\n  AGENTS.md: Valid")

    if not needs_generation:
        print("\n  Project already initialized!")
        return

    # Step 5: Generate AGENTS.md using Claude
    if not agent_files:
        print("\n  No agent files to analyze.")
        print("  Creating minimal AGENTS.md template...")
        content = generate_minimal_agents_md(project.name)
        agents_md_path.write_text(content)
        print(f"  Created: {agents_md_path.relative_to(project)}")
        return

    print("\n  Generating AGENTS.md with Claude...")
    print("-" * 60)

    # Build prompt with all agent file contents
    agent_contents = []
    for agent_file in sorted(agent_files):
        content = agent_file.read_text()
        agent_contents.append(f"### File: {agent_file.name}\n\n```markdown\n{content}\n```\n")

    # Build skills content for prompt
    skills_content = ""
    if skill_files:
        skills_content = "\n\n## Skills Available\n\n"
        for skill_name, _ in skill_files:
            skills_content += f"- `{skill_name}/SKILL.md`\n"

    prompt = f"""Analyze these agent definition files from the project "{project.name}" and generate an AGENTS.md file.

CRITICAL: Only include information that is EXPLICITLY stated in the agent files below. Do NOT invent, assume, or hallucinate any details. If something is not mentioned in the files, do not include it.

## Agent Files to Analyze

{chr(10).join(agent_contents)}
{skills_content}

## Required Sections for AGENTS.md

1. **Agent Registry** - Table: Agent | File | Purpose
   - Only list agents from the files above
   - Purpose must come directly from the agent's description/content

2. **Ownership Matrix** - Table: Agent | OWNS | NEVER touches
   - ONLY include paths explicitly listed in "Files I OWN" sections
   - ONLY include paths explicitly listed in "Files I NEVER touch" sections
   - If an agent doesn't specify ownership, leave those cells empty or say "Not specified"

3. **Routing Table** - Table: IF task involves... | SPAWN this agent
   - Base routing rules ONLY on what the agent descriptions say they handle

4. **Dependency Graph** - Show execution order based on agent types:
   - session-planner first
   - domain agents in middle
   - finalize last

5. **Skills Reference** - Table: Skill | Purpose | Used By
   - List the skills from: {', '.join(s[0] for s in skill_files) if skill_files else 'none found'}
   - Map to agents based on their stated responsibilities

Output ONLY the markdown. Start with "# {project.name} Agent System".
"""

    # Use Claude SDK which auto-detects credentials from ~/.claude
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    # Tell Claude to write the file directly using the Write tool
    write_prompt = f"""{prompt}

IMPORTANT: Use the Write tool to write the AGENTS.md content directly to: {agents_md_path}
Do NOT use the Read tool. All the information you need is provided above.
"""

    client = ClaudeSDKClient(
        options=ClaudeAgentOptions(
            model=model,
            system_prompt="You generate documentation files. Write files directly using the Write tool.",
            allowed_tools=["Write"],
            max_turns=5,
            cwd=str(project),
        )
    )

    try:
        async with client:
            await client.query(write_prompt)

            step = 0
            async for msg in client.receive_response():
                msg_type = type(msg).__name__

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        if hasattr(block, "text") and block.text.strip():
                            print(f"\n{block.text}", flush=True)
                        elif hasattr(block, "name"):
                            step += 1
                            if block.name == "Write":
                                print(f"  [{step}] Writing AGENTS.md...", flush=True)
                            else:
                                print(f"  [{step}] {block.name}...", flush=True)
                elif msg_type == "UserMessage":
                    # Tool result - file was written
                    pass
                elif msg_type == "ResultMessage":
                    print("  Done!", flush=True)
    except Exception as e:
        import traceback
        print(f"\n\nError: {e}")
        print(traceback.format_exc())
        return

    print("\n" + "-" * 60)

    # Check if Claude wrote the file
    if agents_md_path.exists():
        result_text = agents_md_path.read_text()
        print(f"\n  Generated: {agents_md_path.relative_to(project)}")

        # Validate the result
        is_valid, issues = validate_agents_md(result_text)
        if is_valid:
            print("  Validation: ✓ Valid")
        else:
            print("  Validation: ⚠ Has issues (may need manual review)")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n  Error: No content generated")

    print("\n  Initialization complete!")


def generate_minimal_agents_md(project_name: str) -> str:
    """Generate minimal AGENTS.md when no agents exist."""
    return f'''# {project_name} Agent System

This document is the **single source of truth** for agent coordination.

---

## Agent Registry

| Agent | File | Purpose |
|-------|------|---------|
| (no agents defined yet) | - | - |

---

## Ownership Matrix

| Agent | OWNS (only they modify) | NEVER touches |
|-------|-------------------------|---------------|
| (add agents first) | - | - |

---

## Routing Table

| IF task involves... | SPAWN this agent |
|---------------------|------------------|
| (add routing rules) | - |

---

## Adding Agents

Create agent files in `.claude/agents/` with this format:

```markdown
---
name: agent-name
description: What this agent does
---

You are the [Name] Agent...

## Files I OWN:
- path/to/files/

## Files I NEVER touch:
- other/paths/
```

Then run `init` again to regenerate this AGENTS.md.
'''


def status_command(project: Path) -> None:
    """Show session status without running."""
    if not get_session_path(project).exists():
        print(f"No session file found at {get_session_path(project)}")
        return

    print("\n" + "=" * 60)
    print("  SESSION STATUS")
    print("=" * 60)
    print(f"Project: {project}")
    print_session_status(project)

    if is_session_complete(project):
        print("\n   Status: COMPLETE")
    else:
        current = get_current_phase(project)
        if current:
            print(f"\n   Next: Phase {current['number']} ({current['agent']})")


if __name__ == "__main__":
    import sys

    # Get model from environment or use default
    default_model = os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)

    # Simple command detection (before argparse)
    # This handles the case where first arg is a path, not a subcommand
    if len(sys.argv) > 1 and sys.argv[1] not in ("init", "new", "status", "-h", "--help"):
        # First arg is not a command - treat as project path (run mode)
        parser = argparse.ArgumentParser(
            description="Run orchestration on a project",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument("project", type=Path, help="Project directory")
        parser.add_argument("--model", "-m", type=str, default=default_model, help="Claude model")
        parser.add_argument("--max-iterations", "-n", type=int, default=None, help="Max iterations")

        args = parser.parse_args()

        try:
            asyncio.run(run_orchestration(
                args.project.resolve(),
                args.model,
                args.max_iterations,
            ))
        except KeyboardInterrupt:
            print("\n\nInterrupted. Progress saved in session file.")
    else:
        # Use subcommand parser
        parser = argparse.ArgumentParser(
            description="Orchestrator - Agent Delegation Framework",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s init /path/to/project         # Initialize project (generates AGENTS.md)
  %(prog)s /path/to/project              # Run/resume orchestration
  %(prog)s new /path/to/project          # Start new session (archives old)
  %(prog)s status /path/to/project       # Check session status
"""
        )

        subparsers = parser.add_subparsers(dest="command", help="Command to run")

        # Init subcommand
        init_parser = subparsers.add_parser("init", help="Initialize project (create AGENTS.md)")
        init_parser.add_argument("project", type=Path, help="Project directory")
        init_parser.add_argument("--model", "-m", type=str, default=default_model, help="Claude model")

        # New session subcommand
        new_parser = subparsers.add_parser("new", help="Start new session (archives existing)")
        new_parser.add_argument("project", type=Path, help="Project directory")
        new_parser.add_argument("--model", "-m", type=str, default=default_model, help="Claude model")
        new_parser.add_argument("--max-iterations", "-n", type=int, default=None, help="Max iterations")

        # Status subcommand
        status_parser = subparsers.add_parser("status", help="Show session status")
        status_parser.add_argument("project", type=Path, help="Project directory")

        args = parser.parse_args()

        try:
            if args.command == "init":
                asyncio.run(init_command(args.project.resolve(), args.model))
            elif args.command == "new":
                asyncio.run(run_orchestration(
                    args.project.resolve(),
                    args.model,
                    args.max_iterations,
                    new_session=True,
                ))
            elif args.command == "status":
                status_command(args.project.resolve())
            else:
                parser.print_help()
        except KeyboardInterrupt:
            print("\n\nInterrupted. Progress saved in session file.")
