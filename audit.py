#!/usr/bin/env python3
"""
Target Project Auditor

Audits a target project's .claude/agents/ directory and ensures it's
compatible with the orchestration framework.

Responsibilities:
- Discover existing agents in target project
- Validate AGENTS.md structure
- Create AGENTS.md if missing
- Fix AGENTS.md if incomplete
- Report audit results
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DiscoveredAgent:
    """An agent discovered in the target project."""
    name: str
    description: str
    file_path: Path
    owns: list[str] = field(default_factory=list)
    never_touches: list[str] = field(default_factory=list)


@dataclass
class AuditResult:
    """Result of auditing a target project."""
    project_path: Path
    has_claude_dir: bool = False
    has_agents_dir: bool = False
    has_agents_md: bool = False
    agents_md_valid: bool = False
    discovered_agents: list[DiscoveredAgent] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        """Check if project is ready for orchestration."""
        return self.has_agents_dir and self.agents_md_valid


def parse_agent_file(file_path: Path) -> Optional[DiscoveredAgent]:
    """Parse an agent definition file and extract metadata."""
    try:
        content = file_path.read_text()
    except Exception:
        return None

    # Parse YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None

    frontmatter = match.group(1)
    name = ""
    description = ""

    for line in frontmatter.split("\n"):
        line = line.strip()
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            description = line.split(":", 1)[1].strip()

    if not name:
        # Use filename as fallback
        name = file_path.stem

    # Try to extract ownership from content
    owns = []
    never_touches = []

    # Look for "Files I OWN" section
    owns_match = re.search(r'Files I OWN[:\s]*\n((?:[-*]\s+.+\n?)+)', content, re.IGNORECASE)
    if owns_match:
        for line in owns_match.group(1).split("\n"):
            line = line.strip()
            if line.startswith(("-", "*")):
                path = line.lstrip("-* ").strip("`")
                if path:
                    owns.append(path)

    # Look for "Files I NEVER touch" section
    never_match = re.search(r'NEVER touch[:\s]*\n((?:[-*]\s+.+\n?)+)', content, re.IGNORECASE)
    if never_match:
        for line in never_match.group(1).split("\n"):
            line = line.strip()
            if line.startswith(("-", "*")):
                path = line.lstrip("-* ").strip("`")
                if path:
                    never_touches.append(path)

    return DiscoveredAgent(
        name=name,
        description=description[:100] if description else f"Agent from {file_path.name}",
        file_path=file_path,
        owns=owns,
        never_touches=never_touches,
    )


def validate_agents_md(content: str) -> tuple[bool, list[str]]:
    """
    Validate AGENTS.md has required structure.

    Returns (is_valid, list_of_issues)
    """
    issues = []

    # Check for required sections
    required_sections = [
        ("Agent Registry", r"Agent Registry|## Agents"),
        ("Ownership Matrix", r"Ownership Matrix"),
        ("Routing Table", r"Routing Table"),
    ]

    for section_name, pattern in required_sections:
        if not re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Missing section: {section_name}")

    return len(issues) == 0, issues


def generate_agents_md(agents: list[DiscoveredAgent], project_name: str = "Project") -> str:
    """Generate a framework-compatible AGENTS.md from discovered agents."""

    # Build agent registry table
    registry_rows = []
    for agent in agents:
        registry_rows.append(
            f"| {agent.name} | `{agent.file_path.name}` | {agent.description[:50]}... |"
        )

    # Build ownership matrix
    ownership_rows = []
    for agent in agents:
        owns = ", ".join(f"`{p}`" for p in agent.owns[:3]) or "TBD"
        never = ", ".join(f"`{p}`" for p in agent.never_touches[:3]) or "TBD"
        ownership_rows.append(f"| `{agent.name}` | {owns} | {never} |")

    # Build routing table
    routing_rows = []
    for agent in agents:
        trigger = agent.description[:30] if agent.description else agent.name
        routing_rows.append(f"| {trigger} | `{agent.name}` |")

    return f'''# {project_name} Agent System

This document is the **single source of truth** for agent coordination.

---

## Agent Registry

| Agent | File | Purpose |
|-------|------|---------|
{chr(10).join(registry_rows)}

---

## Ownership Matrix

**Each agent has EXCLUSIVE ownership of specific file paths.**

| Agent | OWNS (only they modify) | NEVER touches |
|-------|-------------------------|---------------|
{chr(10).join(ownership_rows)}

---

## Routing Table

| IF task involves... | SPAWN this agent |
|---------------------|------------------|
{chr(10).join(routing_rows)}

---

## Dependency Graph

```
[Define execution order here]
    │
    ▼
finalize (ALWAYS last)
```

---

## Notes

This AGENTS.md was auto-generated by the orchestrator.
Review and customize the ownership matrix and routing table.
'''


def audit_project(project_path: Path, auto_fix: bool = True) -> AuditResult:
    """
    Audit a target project for orchestration compatibility.

    Args:
        project_path: Path to the target project
        auto_fix: If True, create/fix missing files

    Returns:
        AuditResult with findings and actions taken
    """
    result = AuditResult(project_path=project_path)

    claude_dir = project_path / ".claude"
    agents_dir = claude_dir / "agents"
    tasks_dir = claude_dir / "tasks"
    agents_md = agents_dir / "AGENTS.md"

    # Check directory structure
    result.has_claude_dir = claude_dir.exists()
    result.has_agents_dir = agents_dir.exists()
    result.has_agents_md = agents_md.exists()

    # Discover agents
    if result.has_agents_dir:
        for agent_file in agents_dir.glob("*.md"):
            if agent_file.name == "AGENTS.md":
                continue

            agent = parse_agent_file(agent_file)
            if agent:
                result.discovered_agents.append(agent)

    # Validate AGENTS.md if exists
    if result.has_agents_md:
        content = agents_md.read_text()
        result.agents_md_valid, issues = validate_agents_md(content)
        result.issues.extend(issues)
    else:
        result.issues.append("AGENTS.md not found")

    # Auto-fix if requested
    if auto_fix:
        # Create directories if missing
        if not result.has_claude_dir:
            claude_dir.mkdir(parents=True, exist_ok=True)
            result.actions_taken.append("Created .claude/ directory")
            result.has_claude_dir = True

        if not result.has_agents_dir:
            agents_dir.mkdir(parents=True, exist_ok=True)
            result.actions_taken.append("Created .claude/agents/ directory")
            result.has_agents_dir = True

        if not tasks_dir.exists():
            tasks_dir.mkdir(parents=True, exist_ok=True)
            result.actions_taken.append("Created .claude/tasks/ directory")

        # Create or fix AGENTS.md
        if not result.has_agents_md or not result.agents_md_valid:
            if result.discovered_agents:
                # Generate from discovered agents
                project_name = project_path.name.replace("-", " ").title()
                content = generate_agents_md(result.discovered_agents, project_name)
                agents_md.write_text(content)
                result.actions_taken.append(
                    f"Generated AGENTS.md from {len(result.discovered_agents)} discovered agents"
                )
            else:
                # Create minimal template
                content = generate_minimal_agents_md(project_path.name)
                agents_md.write_text(content)
                result.actions_taken.append("Created minimal AGENTS.md template")

            result.has_agents_md = True
            result.agents_md_valid = True
            result.issues = [i for i in result.issues if "AGENTS.md" not in i]

    return result


def generate_minimal_agents_md(project_name: str) -> str:
    """Generate a minimal AGENTS.md template for projects with no agents."""
    return f'''# {project_name} Agent System

This document is the **single source of truth** for agent coordination.

---

## Agent Registry

| Agent | File | Purpose |
|-------|------|---------|
| (no domain agents defined) | - | - |

---

## Ownership Matrix

| Agent | OWNS (only they modify) | NEVER touches |
|-------|-------------------------|---------------|
| (define domain agents) | - | - |

---

## Routing Table

| IF task involves... | SPAWN this agent |
|---------------------|------------------|
| (define routing rules) | - |

---

## Adding Domain Agents

1. Create `.claude/agents/your-agent.md` with:
   ```markdown
   ---
   name: your-agent
   description: What this agent does
   ---

   You are the [Name] Agent...

   ## Files I OWN:
   - path/to/files/

   ## Files I NEVER touch:
   - other/paths/
   ```

2. Update this AGENTS.md to register the agent

---

## Notes

This is a minimal template. Add domain-specific agents for your project.
'''


def print_audit_report(result: AuditResult) -> None:
    """Print a formatted audit report."""
    print("\n" + "=" * 60)
    print("  PROJECT AUDIT REPORT")
    print("=" * 60)
    print(f"Project: {result.project_path}")
    print()

    # Structure check
    print("Structure:")
    print(f"  .claude/           {'✓' if result.has_claude_dir else '✗'}")
    print(f"  .claude/agents/    {'✓' if result.has_agents_dir else '✗'}")
    print(f"  AGENTS.md          {'✓' if result.has_agents_md else '✗'}")
    print(f"  AGENTS.md valid    {'✓' if result.agents_md_valid else '✗'}")
    print()

    # Discovered agents
    if result.discovered_agents:
        print(f"Discovered Agents ({len(result.discovered_agents)}):")
        for agent in result.discovered_agents:
            print(f"  • {agent.name}: {agent.description[:50]}...")
            if agent.owns:
                print(f"    owns: {', '.join(agent.owns[:3])}")
    else:
        print("Discovered Agents: None")
    print()

    # Issues
    if result.issues:
        print("Issues:")
        for issue in result.issues:
            print(f"  ⚠ {issue}")
        print()

    # Actions taken
    if result.actions_taken:
        print("Actions Taken:")
        for action in result.actions_taken:
            print(f"  → {action}")
        print()

    # Status
    if result.is_ready:
        print("Status: ✓ Ready for orchestration")
    else:
        print("Status: ✗ Not ready (see issues above)")

    print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audit.py <project-path>")
        sys.exit(1)

    project = Path(sys.argv[1]).resolve()
    if not project.exists():
        print(f"Error: Project not found: {project}")
        sys.exit(1)

    result = audit_project(project)
    print_audit_report(result)
