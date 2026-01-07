# Core Agent System

This document describes the core AI agent system for orchestrated development workflows.

## Overview

The agent system consists of **specialized agents** that handle different aspects of development. Each agent has:
- **Domain expertise** - Deep knowledge of its area
- **Skills** - Domain knowledge loaded BEFORE execution
- **Coordination protocols** - How to work with other agents

---

## ⚡ Skills-First Execution Protocol

**CRITICAL**: Before ANY agent execution, load required skills.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT EXECUTION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. TRIGGER         User request matches agent capability        │
│       │                                                          │
│       ▼                                                          │
│  2. LOAD SKILLS     Read required skill files FIRST              │
│       │             - sub-agent-invocation (for delegation)      │
│       │             - Domain-specific skills                     │
│       ▼                                                          │
│  3. CONTEXT         Build invocation with:                       │
│       │             - User's original request (verbatim)         │
│       │             - Session file reference (if applicable)     │
│       │             - Dependencies on prior work                 │
│       ▼                                                          │
│  4. EXECUTE         Agent performs work                          │
│       │             - Follows skill patterns                     │
│       │             - Updates session file                       │
│       │             - Tracks progress via TodoWrite              │
│       ▼                                                          │
│  5. SIGNAL          Report completion status                     │
│                     - Artifacts created                          │
│                     - Next agent context                         │
│                     - Follow-up actions required                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Session Integration

When working within a session (`.claude/tasks/session-current.md`):

1. **Read session file** before starting work
2. **Update session file** with implementation notes
3. **Sync TodoWrite** with session checklist
4. **Provide next agent context** in session file

See `session-management` skill for full session lifecycle.

---

## ⚠️ CRITICAL: Agent Ownership Matrix

**Each agent has EXCLUSIVE ownership of specific file paths.** The orchestrator MUST route work to the correct agent. Agents MUST NOT modify files outside their ownership.

| Agent | OWNS (only they modify) | NEVER touches |
|-------|-------------------------|---------------|
| `session-planner` | `.claude/tasks/session-*.md` | Source code |
| `finalize` | NONE (runs commands only) | ALL source files |

### Routing Table

The orchestrator MUST use this routing table:

```
IF task involves...              → SPAWN this agent
─────────────────────────────────────────────────────
Planning multi-phase work        → session-planner
Type gen/validation/commits      → finalize
```

**The orchestrator NEVER modifies source files directly. It ONLY routes to agents.**

---

## Agent Registry

| Agent | File | Purpose | Primary Skill |
|-------|------|---------|---------------|
| Session Planner | `session-planner.md` | Plans multi-phase features, creates session files | session-management |
| Finalize | `finalize.md` | Post-creation validation & commits | git-commits |

---

## How to Use Agents

### Option 1: Direct Agent Invocation

Ask Claude to act as a specific agent:

```
"Act as the session-planner and create a plan for implementing user authentication"
```

### Option 2: Feature Request (Orchestrated)

Describe what you want, and the orchestrator will coordinate:

```
"Create a complete document tagging feature"
```

The orchestrator will:
1. Create a session file
2. Determine which agents are needed
3. Execute in the correct order
4. Verify everything works
5. Propose commit for human approval

---

## Dependency Graph

When building features, components must be created in dependency order:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION ORDER                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. PLANNING       session-planner creates session file                  │
│       │                                                                  │
│       ▼                                                                  │
│  2. DOMAIN WORK    Project-specific agents execute phases                │
│       │            (order defined by session file)                       │
│       ▼                                                                  │
│  3. FINALIZE       Generate types, validate, commit                      │
│                    (ALWAYS last)                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Communication Protocol

When agents coordinate, they follow this pattern:

```
User: "Add document tagging"

ORCHESTRATOR creates session file, analyzes → needs: [domain agents]

ORCHESTRATOR → DOMAIN AGENT 1:
  "Complete Phase 1 tasks"

DOMAIN AGENT 1 updates session file, signals complete

ORCHESTRATOR → DOMAIN AGENT 2:
  "Complete Phase 2 tasks"

DOMAIN AGENT 2 updates session file, signals complete

ORCHESTRATOR → FINALIZE AGENT:
  "Run all validation steps"

FINALIZE AGENT runs validation, proposes commit for approval

ORCHESTRATOR → User:
  "Feature complete! Ready to commit - please review and approve"
```

---

## Skills Reference

Agents reference these skills for detailed domain knowledge:

### Orchestration Skills (Critical Priority)

| Skill | Purpose | Used By |
|-------|---------|---------|
| `session-management` | Multi-phase task coordination | orchestrator |
| `sub-agent-invocation` | Constitutional agent delegation | orchestrator, all agents |
| `orchestrate-feature` | Feature orchestration patterns | orchestrator |
| `git-commits` | Commit orchestration and formatting | finalize |

---

## Extending with Domain Agents

Domain-specific agents are defined in the target project's `.claude/agents/` directory. The orchestrator automatically merges project agents with these core agents.

### Adding a Domain Agent

1. Create agent file: `[project]/.claude/agents/<agent-name>.md`
2. Follow the agent template below
3. Create or update `[project]/.claude/agents/AGENTS.md` to register

### Agent Template

```markdown
---
name: agent-name
description: Brief description for agent selection
---

# <Agent Name> Agent

You are the <Agent Name> Agent...

## Exclusive Ownership

### Files I OWN:
- [paths]

### Files I NEVER touch:
- [paths]

## Your Expertise
- Domain knowledge area 1
- Domain knowledge area 2

## Session Integration

When working within a session:
1. Read session file for context
2. Update session file with implementation notes
3. Mark TodoWrite items as completed
4. Provide next agent context

## Your Workflow
1. Step 1
2. Step 2
3. Step 3

## Quality Checks
- [ ] Check 1
- [ ] Check 2

## Coordination Notes
- When to hand off to other agents
- What context to provide
```
